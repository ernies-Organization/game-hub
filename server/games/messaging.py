class MessagingRoom:
    def __init__(self):
        self.players = []

    def add_player(self, sock, name):
        self.players.append({
            "sock": sock,
            "name": name,
        })
        return None

    def full(self):
        return len(self.players) == 2

    def send(self, sock, message: str):
        sock.sendall((message + "\n").encode())

    def broadcast(self, message: str):
        for player in self.players:
            self.send(player["sock"], message)