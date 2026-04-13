import unittest

from games.tictactoe import TicTacToeEngine, TicTacToeRoom, choose_best_move


class FakeSession:
    def __init__(self, client_id: int, name: str):
        self.client_id = client_id
        self.name = name
        self.room_token = ""
        self.room_role = ""
        self.lines: list[str] = []

    def send_line(self, line: str) -> None:
        self.lines.append(line)


class TicTacToeTests(unittest.TestCase):
    def test_winner_detection(self):
        engine = TicTacToeEngine(board=["X", "X", "X", "", "", "", "", "", ""])
        self.assertEqual(engine.winner(), "X")

    def test_draw_detection(self):
        engine = TicTacToeEngine(board=["X", "O", "X", "X", "O", "O", "O", "X", "X"])
        self.assertEqual(engine.winner(), "DRAW")

    def test_ai_plays_winning_move(self):
        engine = TicTacToeEngine(board=["O", "O", "", "X", "X", "", "", "", ""], current_turn="O")
        self.assertEqual(choose_best_move(engine, "O"), 2)

    def test_room_auto_starts_when_second_player_joins(self):
        room = TicTacToeRoom()
        player_one = FakeSession(1, "Alice")
        player_two = FakeSession(2, "Bob")

        room.add_player(player_one)
        room.add_player(player_two)

        self.assertTrue(room.started)
        self.assertIn("TURN X", player_one.lines)
        self.assertIn("TURN X", player_two.lines)

    def test_room_allows_spectators_after_players(self):
        room = TicTacToeRoom()
        player_one = FakeSession(1, "Alice")
        player_two = FakeSession(2, "Bob")
        spectator = FakeSession(3, "Charlie")

        room.add_player(player_one)
        room.add_player(player_two)
        room.add_player(spectator)

        self.assertEqual(spectator.room_role, "spectator")
        self.assertTrue(any(line.startswith("ROLE SPECTATOR") for line in spectator.lines))

    def test_room_can_restart_after_finished_match(self):
        room = TicTacToeRoom()
        player_one = FakeSession(1, "Alice")
        player_two = FakeSession(2, "Bob")

        room.add_player(player_one)
        room.add_player(player_two)
        room.handle_command(player_one, "MOVE", "0")
        room.handle_command(player_two, "MOVE", "3")
        room.handle_command(player_one, "MOVE", "1")
        room.handle_command(player_two, "MOVE", "4")
        room.handle_command(player_one, "MOVE", "2")

        self.assertTrue(room.closed)

        ok, message = room.start()
        self.assertTrue(ok)
        self.assertEqual(message, "Rematch started.")
        self.assertFalse(room.closed)
        self.assertEqual(room.engine.board, [""] * 9)


if __name__ == "__main__":
    unittest.main()
