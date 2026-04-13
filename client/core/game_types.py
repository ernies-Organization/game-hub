from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class GameDefinition:
    id: str
    title: str
    min_players: int
    max_players: int
    supports_offline: bool
    supports_online: bool
    create_screen: Callable
    create_room: Callable
