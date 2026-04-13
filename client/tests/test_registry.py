import unittest

from core.game_registry import get_game, list_offline_games, list_online_games


class RegistryTests(unittest.TestCase):
    def test_tictactoe_is_in_both_lists(self):
        offline_ids = {game.id for game in list_offline_games()}
        online_ids = {game.id for game in list_online_games()}
        self.assertIn("tictactoe", offline_ids)
        self.assertIn("tictactoe", online_ids)

    def test_registry_contains_only_current_playable_game(self):
        self.assertEqual(get_game("tictactoe").title, "Tic-Tac-Toe")
        self.assertEqual([game.id for game in list_online_games()], ["tictactoe"])


if __name__ == "__main__":
    unittest.main()
