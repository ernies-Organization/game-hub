import socket
import threading
from typing import Callable


class LineClient:
    def __init__(self) -> None:
        self.sock: socket.socket | None = None
        self.running = False
        self._thread: threading.Thread | None = None
        self._send_lock = threading.Lock()
        self._disconnect_lock = threading.Lock()
        self._disconnect_notified = False
        self._on_disconnect: Callable[[], None] | None = None

    def connect(
        self,
        host: str,
        port: int,
        on_line: Callable[[str], None],
        on_disconnect: Callable[[], None],
        timeout: float = 8.0,
    ) -> None:
        if self.running:
            self.close()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        self.sock.settimeout(1.0)

        self.running = True
        self._disconnect_notified = False
        self._on_disconnect = on_disconnect
        self._thread = threading.Thread(
            target=self._receive_loop,
            args=(on_line, on_disconnect),
            daemon=True,
            name="line-client-recv",
        )
        self._thread.start()

    def _receive_loop(
        self,
        on_line: Callable[[str], None],
        on_disconnect: Callable[[], None],
    ) -> None:
        sock = self.sock
        if sock is None:
            return

        buffer = ""
        try:
            while self.running:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    continue

                if not data:
                    break

                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        on_line(line)
        except OSError:
            pass
        finally:
            self.running = False
            self._shutdown_socket()
            self._notify_disconnect()

    def send_line(self, line: str) -> None:
        if not self.running or self.sock is None:
            raise RuntimeError("Not connected")

        payload = (line.strip() + "\n").encode("utf-8")
        with self._send_lock:
            self.sock.sendall(payload)

    def _shutdown_socket(self) -> None:
        sock = self.sock
        self.sock = None
        if sock is None:
            return

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def close(self) -> None:
        self.running = False
        self._shutdown_socket()

    def _notify_disconnect(self) -> None:
        callback = self._on_disconnect
        if callback is None:
            return
        with self._disconnect_lock:
            if self._disconnect_notified:
                return
            self._disconnect_notified = True
        callback()
