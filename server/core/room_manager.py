from games.tictactoe import TicTacToeRoom
from games.messaging import MessagingRoom


class RoomManager:
    def __init__(self):
        self.waiting_rooms = {
            "tictactoe": [],
            "messaging": [],
        }

    def create_room(self, game_name: str):
        if game_name == "tictactoe":
            return TicTacToeRoom()
        if game_name == "messaging":
            return MessagingRoom()
        raise ValueError(f"Unknown game: {game_name}")

    def get_or_create_waiting_room(self, game_name: str):
        rooms = self.waiting_rooms[game_name]

        if not rooms or rooms[-1].full():
            rooms.append(self.create_room(game_name))

        return rooms[-1]

    def pop_if_full(self, game_name: str, room):
        rooms = self.waiting_rooms[game_name]
        if room in rooms and room.full():
            rooms.remove(room)