from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from core.game_registry import create_room, list_online_games
from core.protocol import APP_VERSION, DEFAULT_PORT


def detect_local_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


@dataclass
class ClientSession:
    client_id: int
    sock: socket.socket
    address: tuple[str, int]
    name: str = "Guest"
    joined_game: str | None = None
    room_token: str = ""
    hello_version: str = ""
    connected_at: float = field(default_factory=time.time)
    closed: bool = False
    send_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send_line(self, line: str) -> None:
        with self.send_lock:
            self.sock.sendall((line.strip() + "\n").encode("utf-8"))

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class HostServer:
    def __init__(self, on_event: Callable[[str, str], None] | None = None) -> None:
        self._on_event = on_event or (lambda *_: None)
        self._lock = threading.RLock()
        self._server_socket: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._running = False
        self._next_client_id = 1
        self._clients: dict[int, ClientSession] = {}
        self._selected_game_id = list_online_games()[0].id
        self._room = create_room(self._selected_game_id)
        self._host = "0.0.0.0"
        self._port = DEFAULT_PORT
        self._local_ip = detect_local_ip()
        self._event_log: list[str] = []

    def emit(self, event_type: str, message: str = "") -> None:
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {event_type.upper()}: {message}"
        self._event_log.append(entry)
        self._event_log = self._event_log[-100:]
        self._on_event(event_type, message)

    def start(self, port: int = DEFAULT_PORT) -> tuple[bool, str]:
        with self._lock:
            if self._running:
                return False, "Host server is already running."

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self._host, port))
            server.listen()
            server.settimeout(1.0)

            self._server_socket = server
            self._port = server.getsockname()[1]
            self._local_ip = detect_local_ip()
            self._running = True
            self._room = create_room(self._selected_game_id)
            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                daemon=True,
                name="host-server-accept",
            )
            self._accept_thread.start()

        self.emit("server", f"Hosting on {self._local_ip}:{self._port}")
        return True, f"Hosting on {self._local_ip}:{self._port}"

    def stop(self) -> None:
        with self._lock:
            self._running = False
            server = self._server_socket
            self._server_socket = None
            if server is not None:
                try:
                    server.close()
                except OSError:
                    pass

            clients = list(self._clients.values())
            self._clients.clear()
            self._room = create_room(self._selected_game_id)

        for client in clients:
            client.close()

        self.emit("server", "Host server stopped.")

    def snapshot(self) -> dict:
        with self._lock:
            room_state = self._room.host_state()
            return {
                "running": self._running,
                "host": self._host,
                "port": self._port,
                "local_ip": self._local_ip,
                "selected_game": self._selected_game_id,
                "available_games": [game.id for game in list_online_games()],
                "connected_clients": [
                    {
                        "id": client.client_id,
                        "name": client.name,
                        "address": f"{client.address[0]}:{client.address[1]}",
                        "joined_game": client.joined_game or "",
                    }
                    for client in self._clients.values()
                ],
                "room": room_state,
                "event_log": self._event_log[-25:],
            }

    def set_selected_game(self, game_id: str) -> tuple[bool, str]:
        with self._lock:
            if game_id == self._selected_game_id:
                return True, "Game already selected."
            if self._room.player_count > 0 or self._room.started:
                return False, "Cannot change game while players are in the room."

            self._selected_game_id = game_id
            self._room = create_room(game_id)

        self.emit("room", f"Selected game: {game_id}")
        return True, f"Selected game: {game_id}"

    def start_match(self) -> tuple[bool, str]:
        with self._lock:
            ok, message = self._room.start()
        self.emit("room", message)
        return ok, message

    def clear_room_chat(self) -> tuple[bool, str]:
        with self._lock:
            self._room.clear_chat()
        self.emit("room", "Room chat cleared.")
        return True, "Room chat cleared."

    def _accept_loop(self) -> None:
        while self._running:
            server = self._server_socket
            if server is None:
                return

            try:
                sock, address = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return

            sock.settimeout(1.0)
            with self._lock:
                session = ClientSession(
                    client_id=self._next_client_id,
                    sock=sock,
                    address=address,
                )
                self._next_client_id += 1
                self._clients[session.client_id] = session

            self.emit("client", f"Client connected from {address[0]}:{address[1]}")
            threading.Thread(
                target=self._client_loop,
                args=(session,),
                daemon=True,
                name=f"host-client-{session.client_id}",
            ).start()

    def _client_loop(self, session: ClientSession) -> None:
        buffer = ""
        try:
            while self._running and not session.closed:
                try:
                    data = session.sock.recv(4096)
                except socket.timeout:
                    continue

                if not data:
                    break

                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    raw_line, buffer = buffer.split("\n", 1)
                    line = raw_line.strip()
                    if line and not self._handle_command(session, line):
                        return
        except OSError:
            pass
        finally:
            self._disconnect_client(session)

    def _handle_command(self, session: ClientSession, line: str) -> bool:
        command, _, payload = line.partition(" ")
        command = command.upper()

        if command == "HELLO":
            session.hello_version = payload.strip()
            self._safe_send(session, f"VERSION {APP_VERSION}")
            self._safe_send(
                session,
                "GAMES " + ",".join(game.id for game in list_online_games()),
            )
            self._safe_send(session, "MESSAGE Welcome to Game Hub host.")
            return True

        if command == "JOIN":
            parts = payload.strip().split(" ", 1)
            if len(parts) != 2:
                self._safe_send(session, "ERROR JOIN must be: JOIN <game> <name>")
                return True

            game_id, name = parts[0].strip().lower(), parts[1].strip()
            if not name:
                self._safe_send(session, "ERROR Player name cannot be empty.")
                return True

            with self._lock:
                if game_id != self._selected_game_id:
                    self._safe_send(
                        session,
                        f"ERROR Host is currently running {self._selected_game_id}.",
                    )
                    return True

                session.name = name
                ok, message = self._room.add_player(session)
                if ok:
                    session.joined_game = game_id
                self.emit("room", message)

            self._safe_send(session, ("MESSAGE " if ok else "ERROR ") + message)
            return True

        if command in {"CHAT", "MOVE"}:
            with self._lock:
                if session.joined_game != self._selected_game_id:
                    self._safe_send(session, "ERROR Join the selected game first.")
                    return True
                self._room.handle_command(session, command, payload)
            self.emit("room", "Room updated.")
            return True

        if command == "QUIT":
            self._safe_send(session, "MESSAGE Goodbye")
            return False

        self._safe_send(session, "ERROR Unknown command.")
        return True

    def _safe_send(self, session: ClientSession, line: str) -> None:
        try:
            session.send_line(line)
        except OSError:
            self._disconnect_client(session)

    def _disconnect_client(self, session: ClientSession) -> None:
        with self._lock:
            if session.client_id not in self._clients:
                session.close()
                return

            self._clients.pop(session.client_id, None)
            self._room.remove_player(session)

            if self._room.closed and self._room.player_count == 0:
                self._room = create_room(self._selected_game_id)

        session.close()
        self.emit("client", f"Client disconnected: {session.name}")
