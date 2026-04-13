from __future__ import annotations

from core.game_types import GameDefinition
from games import tictactoe


def _build_registry() -> dict[str, GameDefinition]:
    return {
        tictactoe.GAME_DEFINITION.id: tictactoe.GAME_DEFINITION,
    }


GAMES = _build_registry()


def list_games() -> list[GameDefinition]:
    return list(GAMES.values())


def list_offline_games() -> list[GameDefinition]:
    return [game for game in GAMES.values() if game.supports_offline]


def list_online_games() -> list[GameDefinition]:
    return [game for game in GAMES.values() if game.supports_online]


def get_game(game_id: str) -> GameDefinition:
    return GAMES[game_id]


def create_room(game_id: str):
    return get_game(game_id).create_room()
