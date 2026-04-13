from __future__ import annotations

import flet as ft

from core.game_types import GameDefinition
from games.base import BaseRoom


class TemplateRoom(BaseRoom):
    def __init__(self) -> None:
        super().__init__("template_game", "Template Game", min_players=1, max_players=4)

    def add_player(self, session):
        if self.player_count >= self.max_players:
            return False, "Room is full."
        self.players.append(session)
        self.status = f"{session.name} joined."
        return True, f"{session.name} joined the room."

    def start(self):
        if self.started:
            return False, "Game already started."
        if self.player_count < self.min_players:
            return False, "Not enough players."
        self.started = True
        self.closed = False
        self.status = "Game started."
        for player in self.players:
            player.send_line("MESSAGE Template game started.")
        return True, "Template game started."

    def handle_command(self, session, command: str, payload: str) -> None:
        session.send_line("ERROR Template game does not implement network commands yet.")


class TemplateGameScreen:
    def __init__(self, page: ft.Page, on_back, settings: dict, network, online: bool):
        self.page = page
        self.on_back = on_back
        self.settings = settings
        self.network = network
        self.online = online
        self.status = ft.Text("Replace this screen with your game UI.")

    def build(self):
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.on_back()),
                        ft.Text("Template Game", size=24, weight=ft.FontWeight.BOLD),
                    ]
                ),
                self.status,
            ],
            spacing=16,
        )

    def handle_server_line(self, line: str) -> bool:
        if line.startswith("MESSAGE "):
            self.status.value = line[8:]
            self.page.update()
            return True
        if line.startswith("ERROR "):
            self.status.value = f"Error: {line[6:]}"
            self.page.update()
            return True
        return False


def create_screen(page: ft.Page, on_back, settings: dict, network, online: bool):
    return TemplateGameScreen(page=page, on_back=on_back, settings=settings, network=network, online=online)


def create_room():
    return TemplateRoom()


GAME_DEFINITION = GameDefinition(
    id="template_game",
    title="Template Game",
    min_players=1,
    max_players=4,
    supports_offline=False,
    supports_online=True,
    create_screen=create_screen,
    create_room=create_room,
)
