import socket
import threading

SERVER_VERSION = "0.3.1"
PROTOCOL_VERSION = 1
HOST = "0.0.0.0"
PORT = 5000
AVAILABLE_GAMES = ["tictactoe", "messaging"]

ttt_waiting = []
msg_waiting = []
rooms_lock = threading.Lock()


def send(sock, message: str) -> bool:
    try:
        sock.sendall((message + "\n").encode())
        return True
    except OSError:
        return False


def get_local_ip():
    temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        temp.connect(("8.8.8.8", 80))
        ip = temp.getsockname()[0]
    finally:
        temp.close()
    return ip


def read_line_buffer(sock, callback):
    buffer = ""
    while True:
        data = sock.recv(1024).decode()
        if not data:
            return
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line:
                callback(line)


def safe_close(sock):
    try:
        sock.close()
    except OSError:
        pass


def handle_tictactoe_room(player_x, player_o):
    board = [" "] * 9
    turn = "X"
    players = {
        "X": player_x,
        "O": player_o,
    }

    def board_string():
        return ",".join(board)

    def broadcast(message):
        dead = []
        for token, p in players.items():
            if not send(p["sock"], message):
                dead.append(token)
        return dead

    def check_winner():
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for a, b, c in wins:
            if board[a] != " " and board[a] == board[b] == board[c]:
                return board[a]
        if " " not in board:
            return "DRAW"
        return None

    for token, player in players.items():
        send(player["sock"], f"TOKEN {token}")
    send(player_x["sock"], f"PLAYER_X {player_x['name']}")
    send(player_x["sock"], f"PLAYER_O {player_o['name']}")
    send(player_o["sock"], f"PLAYER_X {player_x['name']}")
    send(player_o["sock"], f"PLAYER_O {player_o['name']}")

    broadcast("MESSAGE Tic-Tac-Toe started")
    broadcast(f"BOARD {board_string()}")
    broadcast("TURN X")

    buffers = {"X": "", "O": ""}

    while True:
        for token in ["X", "O"]:
            sock = players[token]["sock"]

            try:
                sock.settimeout(0.1)
                data = sock.recv(1024).decode()
                if not data:
                    continue
                buffers[token] += data
            except socket.timeout:
                continue
            except OSError:
                broadcast("MESSAGE A player disconnected.")
                safe_close(player_x["sock"])
                safe_close(player_o["sock"])
                return

            while "\n" in buffers[token]:
                line, buffers[token] = buffers[token].split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                print(f"[TICTACTOE] {players[token]['name']} ({token}): {line}")

                parts = line.split()

                if parts[0] == "MOVE" and len(parts) == 2 and parts[1].isdigit():
                    move = int(parts[1])

                    if token != turn:
                        send(sock, "ERROR Not your turn")
                        continue

                    if not (1 <= move <= 9):
                        send(sock, "ERROR Move must be 1-9")
                        continue

                    if board[move - 1] != " ":
                        send(sock, "ERROR Square already used")
                        continue

                    board[move - 1] = token
                    broadcast(f"BOARD {board_string()}")

                    result = check_winner()
                    if result == "DRAW":
                        broadcast("RESULT DRAW")
                        safe_close(player_x["sock"])
                        safe_close(player_o["sock"])
                        return

                    if result in ("X", "O"):
                        winner_name = players[result]["name"]
                        broadcast(f"RESULT WIN {winner_name}")
                        safe_close(player_x["sock"])
                        safe_close(player_o["sock"])
                        return

                    turn = "O" if turn == "X" else "X"
                    broadcast(f"TURN {turn}")

                elif parts[0] == "QUIT":
                    send(sock, "MESSAGE Goodbye")
                    broadcast("MESSAGE A player left the game.")
                    safe_close(player_x["sock"])
                    safe_close(player_o["sock"])
                    return


def handle_messaging_room(player_a, player_b):
    players = [player_a, player_b]

    def broadcast(message):
        alive = []
        for p in players:
            if send(p["sock"], message):
                alive.append(p)
        return alive

    broadcast("MESSAGE Messaging room started.")

    buffers = ["", ""]

    while True:
        for i, player in enumerate(players):
            sock = player["sock"]

            try:
                sock.settimeout(0.1)
                data = sock.recv(1024).decode()
                if not data:
                    continue
                buffers[i] += data
            except socket.timeout:
                continue
            except OSError:
                broadcast("MESSAGE A player disconnected.")
                for p in players:
                    safe_close(p["sock"])
                return

            while "\n" in buffers[i]:
                line, buffers[i] = buffers[i].split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                print(f"[MESSAGING] {player['name']}: {line}")

                if line.startswith("CHAT "):
                    broadcast(f"CHAT_FROM {player['name']}: {line[5:]}")
                elif line == "QUIT":
                    send(sock, "MESSAGE Goodbye")
                    broadcast("MESSAGE A player left the chat.")
                    for p in players:
                        safe_close(p["sock"])
                    return


def try_start_room(game_name, player):
    with rooms_lock:
        if game_name == "tictactoe":
            ttt_waiting.append(player)
            if len(ttt_waiting) >= 2:
                p1 = ttt_waiting.pop(0)
                p2 = ttt_waiting.pop(0)
                threading.Thread(target=handle_tictactoe_room, args=(p1, p2), daemon=True).start()
                return True
            return False

        if game_name == "messaging":
            msg_waiting.append(player)
            if len(msg_waiting) >= 2:
                p1 = msg_waiting.pop(0)
                p2 = msg_waiting.pop(0)
                threading.Thread(target=handle_messaging_room, args=(p1, p2), daemon=True).start()
                return True
            return False

    return False


def handle_client(sock, addr):
    print(f"[CONNECT] {addr}")

    handed_off_to_room = False

    def on_line(line: str):
        nonlocal handed_off_to_room

        print(f"[{addr}] {line}")

        if line.startswith("HELLO "):
            send(sock, f"VERSION {SERVER_VERSION}")
            send(sock, f"PROTOCOL {PROTOCOL_VERSION}")
            send(sock, f"GAMES {','.join(AVAILABLE_GAMES)}")
            send(sock, "MESSAGE Server info sent")

        elif line.startswith("JOIN "):
            parts = line.split(maxsplit=2)
            if len(parts) < 3:
                send(sock, "ERROR JOIN must be: JOIN <game> <name>")
                return

            game_name = parts[1].lower()
            player_name = parts[2].strip()

            if game_name not in AVAILABLE_GAMES:
                send(sock, "ERROR Unknown game")
                return

            started = try_start_room(game_name, {"sock": sock, "name": player_name})

            if started:
                send(sock, f"MESSAGE Joined {game_name} as {player_name}")
            else:
                send(sock, f"MESSAGE Waiting for another player for {game_name}")

            # IMPORTANT:
            # after JOIN, the room now owns the socket
            handed_off_to_room = True
            raise ConnectionAbortedError

        elif line == "QUIT":
            send(sock, "MESSAGE Goodbye")
            raise ConnectionAbortedError

        else:
            send(sock, "ERROR Unknown command")

    try:
        read_line_buffer(sock, on_line)
    except Exception:
        pass
    finally:
        if not handed_off_to_room:
            safe_close(sock)
            print(f"[DISCONNECT] {addr}")
        else:
            print(f"[HANDOFF] {addr} moved to room")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print("Server started")
    print(f"Server version: {SERVER_VERSION}")
    print(f"Protocol version: {PROTOCOL_VERSION}")
    print(f"IP: {get_local_ip()}")
    print(f"PORT: {PORT}")
    print(f"Games: {', '.join(AVAILABLE_GAMES)}")

    while True:
        sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(sock, addr), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer shutting down...")