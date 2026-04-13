WIN_CONDITIONS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


class TicTacToeRoom:
    def __init__(self):
        self.players = []
        self.board = [" "] * 9
        self.turn = "X"

    def add_player(self, sock, name):
        token = "X" if len(self.players) == 0 else "O"
        self.players.append({
            "sock": sock,
            "name": name,
            "token": token,
        })
        return token

    def full(self):
        return len(self.players) == 2

    def send(self, sock, message: str):
        sock.sendall((message + "\n").encode())

    def broadcast(self, message: str):
        for player in self.players:
            self.send(player["sock"], message)

    def board_string(self):
        return ",".join(self.board)

    def check_winner(self):
        for a, b, c in WIN_CONDITIONS:
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if " " not in self.board:
            return "DRAW"
        return None

    def place_move(self, token: str, move: int):
        if token != self.turn:
            return False, "Not your turn"
        if not (1 <= move <= 9):
            return False, "Move must be 1-9"
        if self.board[move - 1] != " ":
            return False, "That square is already taken"

        self.board[move - 1] = token
        return True, "Move accepted"

    def switch_turn(self):
        self.turn = "O" if self.turn == "X" else "X"