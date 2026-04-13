from __future__ import annotations

from dataclasses import dataclass, field

import flet as ft

from core.game_types import GameDefinition
from games.base import BaseRoom

WIN_CONDITIONS = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


@dataclass
class TicTacToeEngine:
    board: list[str] = field(default_factory=lambda: [""] * 9)
    current_turn: str = "X"

    def clone(self) -> "TicTacToeEngine":
        return TicTacToeEngine(board=self.board.copy(), current_turn=self.current_turn)

    def available_moves(self) -> list[int]:
        return [index for index, value in enumerate(self.board) if not value]

    def winner(self) -> str | None:
        for a, b, c in WIN_CONDITIONS:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if all(self.board):
            return "DRAW"
        return None

    def apply_move(self, index: int, token: str) -> tuple[bool, str]:
        if not 0 <= index < 9:
            return False, "Move must be between 0 and 8."
        if self.winner() is not None:
            return False, "Match already finished."
        if token != self.current_turn:
            return False, "Not your turn."
        if self.board[index]:
            return False, "Square already taken."

        self.board[index] = token
        if self.winner() is None:
            self.current_turn = "O" if token == "X" else "X"
        return True, "Move accepted."

    def board_payload(self) -> str:
        return "".join(cell if cell else "-" for cell in self.board)

    @classmethod
    def from_payload(cls, payload: str) -> "TicTacToeEngine":
        board = ["" if cell == "-" else cell for cell in payload[:9]]
        board.extend([""] * (9 - len(board)))
        return cls(board=board)


def choose_best_move(engine: TicTacToeEngine, ai_token: str = "O") -> int:
    human_token = "X" if ai_token == "O" else "O"

    def score_position(state: TicTacToeEngine) -> int:
        result = state.winner()
        if result == ai_token:
            return 1
        if result == human_token:
            return -1
        if result == "DRAW":
            return 0

        scores = []
        for move in state.available_moves():
            next_state = state.clone()
            next_state.apply_move(move, next_state.current_turn)
            scores.append(score_position(next_state))

        return max(scores) if state.current_turn == ai_token else min(scores)

    best_move = engine.available_moves()[0]
    best_score = -2
    for move in engine.available_moves():
        next_state = engine.clone()
        next_state.apply_move(move, ai_token)
        position_score = score_position(next_state)
        if position_score > best_score:
            best_score = position_score
            best_move = move
    return best_move


class TicTacToeRoom(BaseRoom):
    def __init__(self) -> None:
        super().__init__("tictactoe", "Tic-Tac-Toe", min_players=2, max_players=2)
        self.engine = TicTacToeEngine()

    def add_player(self, session):
        if session in self.all_sessions():
            return True, f"{session.name} is already in the room."

        if not self.started and self.player_count < self.max_players:
            session.room_role = "player"
            session.room_token = "X" if self.player_count == 0 else "O"
            self.players.append(session)
            message = f"{session.name} joined as {session.room_token}."
        else:
            session.room_role = "spectator"
            session.room_token = ""
            self.spectators.append(session)
            message = f"{session.name} joined as a spectator."

        self.status = message
        self._broadcast_player_info()
        self._sync_state_to_session(session)

        if not self.started and self.player_count >= self.min_players:
            _, start_message = self.start()
            return True, f"{message} {start_message}"

        return True, message

    def start(self):
        if self.player_count < self.min_players:
            return False, "Need 2 players to start Tic-Tac-Toe."

        restarting = self.closed or any(self.engine.board)
        self.started = True
        self.closed = False
        self.status = "Match in progress."
        self.engine = TicTacToeEngine()
        self._sync_state_to_all()
        if restarting:
            self.broadcast("CHAT_RESET")
            self.broadcast("MESSAGE Rematch started.")
            return True, "Rematch started."
        self.broadcast("MESSAGE Tic-Tac-Toe match started.")
        return True, "Tic-Tac-Toe match started."

    def handle_command(self, session, command: str, payload: str) -> None:
        if command == "CHAT":
            message = payload.strip()
            if not message:
                session.send_line("ERROR Message cannot be empty.")
                return
            self.add_chat_message(session, message)
            return

        if command != "MOVE":
            session.send_line("ERROR Tic-Tac-Toe only accepts MOVE or CHAT commands.")
            return
        if getattr(session, "room_role", "") != "player":
            session.send_line("ERROR Spectators cannot make moves.")
            return
        if not self.started or self.closed:
            session.send_line("ERROR Match is not active.")
            return

        move_text = payload.strip()
        if not move_text.lstrip("-").isdigit():
            session.send_line("ERROR Move must be a number.")
            return

        move = int(move_text)
        index = move if 0 <= move <= 8 else move - 1
        ok, message = self.engine.apply_move(index, session.room_token)
        if not ok:
            session.send_line(f"ERROR {message}")
            return

        self.broadcast(f"BOARD {self.engine.board_payload()}")
        result = self.engine.winner()
        if result == "DRAW":
            self.started = False
            self.closed = True
            self.status = "Match ended in a draw."
            self.broadcast("RESULT DRAW")
            return

        if result in {"X", "O"}:
            self.started = False
            self.closed = True
            winner_name = next(player.name for player in self.players if player.room_token == result)
            self.status = f"{winner_name} won the match."
            self.broadcast(f"RESULT WIN {winner_name}")
            return

        self.broadcast(f"TURN {self.engine.current_turn}")

    def remove_player(self, session) -> None:
        was_player = session in self.players
        had_started = self.started and not self.closed
        super().remove_player(session)
        if was_player and had_started:
            self.closed = True
            self.started = False
            self.status = "A player disconnected."
            self.broadcast("MESSAGE A player disconnected. Match closed.")
        self._broadcast_player_info()

    def host_state(self) -> dict:
        state = super().host_state()
        state["board"] = self.engine.board_payload()
        state["turn"] = self.engine.current_turn
        state["result"] = self.engine.winner() or ""
        return state

    def _broadcast_player_info(self) -> None:
        player_x = next((player.name for player in self.players if player.room_token == "X"), "Waiting...")
        player_o = next((player.name for player in self.players if player.room_token == "O"), "Waiting...")
        self.broadcast(f"PLAYER_X {player_x}")
        self.broadcast(f"PLAYER_O {player_o}")
        self.broadcast(f"SPECTATORS {','.join(spectator.name for spectator in self.spectators)}")

    def _sync_state_to_session(self, session) -> None:
        role = getattr(session, "room_role", "spectator").upper()
        token = getattr(session, "room_token", "")
        session.send_line(f"ROLE {role} {token}".strip())
        player_x = next((player.name for player in self.players if player.room_token == "X"), "Waiting...")
        player_o = next((player.name for player in self.players if player.room_token == "O"), "Waiting...")
        session.send_line(f"PLAYER_X {player_x}")
        session.send_line(f"PLAYER_O {player_o}")
        session.send_line(f"SPECTATORS {','.join(spectator.name for spectator in self.spectators)}")
        session.send_line(f"BOARD {self.engine.board_payload()}")
        self.send_chat_history(session)
        if self.closed:
            result = self.engine.winner()
            if result == "DRAW":
                session.send_line("RESULT DRAW")
            elif result in {"X", "O"}:
                winner_name = next(player.name for player in self.players if player.room_token == result)
                session.send_line(f"RESULT WIN {winner_name}")
        elif self.started:
            session.send_line(f"TURN {self.engine.current_turn}")

    def _sync_state_to_all(self) -> None:
        self._broadcast_player_info()
        for session in self.all_sessions():
            self._sync_state_to_session(session)


class TicTacToeScreen:
    def __init__(self, page: ft.Page, on_back, settings: dict, network, online: bool):
        self.page = page
        self.on_back = on_back
        self.settings = settings
        self.network = network
        self.online = online
        self.engine = TicTacToeEngine()
        self.mode = "pvp"
        self.my_token = ""
        self.my_role = "spectator"
        self.player_x = settings.get("player_name", "Player")
        self.player_o = "Player 2"
        self.spectators: list[str] = []
        self.status_text = ft.Text("Choose a mode to begin." if not online else "Waiting for players...")
        self.role_text = ft.Text("", weight=ft.FontWeight.BOLD)
        self.player_x_text = ft.Text("")
        self.player_o_text = ft.Text("")
        self.spectator_count_text = ft.Text("")
        self.roster_text = ft.Text("")
        self.player_two_field = ft.TextField(label="Player 2", value="Player 2")
        self.buttons: list[ft.Button] = []
        self.chat_input = ft.TextField(label="Room chat", expand=True, on_submit=self._send_chat)
        self.chat_messages = ft.ListView(expand=True, spacing=6, auto_scroll=True)

    def build(self):
        board = self._build_board()
        header = ft.Row(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.on_back()),
                ft.Text(
                    "Online Tic-Tac-Toe" if self.online else "Offline Tic-Tac-Toe",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
            ]
        )

        if self.online:
            self._refresh_info()
            return ft.Column(
                [
                    header,
                    self._build_online_lobby(),
                    self.status_text,
                    board,
                    ft.Text("Room chat"),
                    ft.Container(
                        self.chat_messages,
                        border=ft.Border.all(1, ft.Colors.OUTLINE),
                        border_radius=12,
                        padding=8,
                        height=180,
                    ),
                    ft.Row(
                        [
                            self.chat_input,
                            ft.Button("Send", on_click=self._send_chat),
                        ]
                    ),
                    ft.Text(
                        "This room chat is not automatically moderated. Use it at your own risk and do not share anything sensitive.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            )

        return ft.Column(
            [
                header,
                ft.Text(f"Player X: {self.player_x}"),
                self.player_two_field,
                ft.Row(
                    [
                        ft.Button("Player vs Player", on_click=self._set_pvp),
                        ft.Button("Player vs AI", on_click=self._set_ai),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                self.status_text,
                board,
                ft.Button("Reset", on_click=self._reset_offline),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        )

    def handle_server_line(self, line: str) -> bool:
        if line.startswith("MESSAGE "):
            self.status_text.value = line[8:]
            self.page.update()
            return True
        if line.startswith("ERROR "):
            self.status_text.value = f"Error: {line[6:]}"
            self.page.update()
            return True
        if line.startswith("ROLE "):
            parts = line.split(" ", 2)
            self.my_role = parts[1].lower()
            self.my_token = parts[2].strip() if len(parts) > 2 else ""
            self._refresh_info()
            self._sync_online_buttons()
            self.page.update()
            return True
        if line.startswith("PLAYER_X "):
            self.player_x = line[9:]
            self._refresh_info()
            self.page.update()
            return True
        if line.startswith("PLAYER_O "):
            self.player_o = line[9:]
            self._refresh_info()
            self.page.update()
            return True
        if line.startswith("CHAT_FROM "):
            self.chat_messages.controls.append(self._build_chat_message(line[10:]))
            self.page.update()
            return True
        if line.startswith("CHAT_HISTORY "):
            self.chat_messages.controls.append(self._build_chat_message(line[13:]))
            self.page.update()
            return True
        if line == "CHAT_RESET":
            self.chat_messages.controls.clear()
            self.page.update()
            return True
        if line.startswith("SPECTATORS "):
            raw = line[11:].strip()
            self.spectators = [name for name in raw.split(",") if name]
            self._refresh_info()
            self.page.update()
            return True
        if line.startswith("BOARD "):
            self.engine = TicTacToeEngine.from_payload(line[6:].strip())
            self._render_board()
            self._sync_online_buttons()
            self.page.update()
            return True
        if line.startswith("TURN "):
            token = line.split(" ", 1)[1].strip()
            self.engine.current_turn = token
            name = self.player_x if token == "X" else self.player_o
            self.status_text.value = f"Turn: {name} ({token})"
            self._sync_online_buttons()
            self.page.update()
            return True
        if line.startswith("RESULT WIN "):
            self.status_text.value = f"{line[11:]} wins!"
            self._disable_all_buttons()
            self.page.update()
            return True
        if line == "RESULT DRAW":
            self.status_text.value = "Draw!"
            self._disable_all_buttons()
            self.page.update()
            return True
        return False

    def _build_board(self):
        rows = []
        self.buttons = []
        for row_index in range(3):
            row_controls = []
            for column_index in range(3):
                index = row_index * 3 + column_index
                button = ft.Button(
                    " ",
                    width=86,
                    height=86,
                    on_click=(lambda _, move=index: self._online_tap(move))
                    if self.online
                    else (lambda _, move=index: self._offline_tap(move)),
                )
                self.buttons.append(button)
                row_controls.append(button)
            rows.append(ft.Row(row_controls, alignment=ft.MainAxisAlignment.CENTER))
        return ft.Column(rows, spacing=8)

    def _set_pvp(self, _):
        self.mode = "pvp"
        self.player_o = self.player_two_field.value.strip() or "Player 2"
        self._reset_offline()

    def _set_ai(self, _):
        self.mode = "ai"
        self.player_o = "AI"
        self._reset_offline()

    def _reset_offline(self, _=None):
        self.engine = TicTacToeEngine()
        self.status_text.value = f"Turn: {self.player_x} (X)"
        self._render_board()
        self._enable_valid_buttons()
        self.page.update()

    def _offline_tap(self, index: int):
        ok, message = self.engine.apply_move(index, self.engine.current_turn)
        if not ok:
            self.status_text.value = message
            self.page.update()
            return

        self._render_board()
        result = self.engine.winner()
        if self._finish_if_needed(result):
            return

        if self.mode == "ai" and self.engine.current_turn == "O":
            ai_move = choose_best_move(self.engine, "O")
            self.engine.apply_move(ai_move, "O")
            self._render_board()
            result = self.engine.winner()
            if self._finish_if_needed(result):
                return

        current_name = self.player_x if self.engine.current_turn == "X" else self.player_o
        self.status_text.value = f"Turn: {current_name} ({self.engine.current_turn})"
        self.page.update()

    def _finish_if_needed(self, result: str | None) -> bool:
        if result is None:
            return False
        if result == "DRAW":
            self.status_text.value = "Draw!"
        else:
            winner_name = self.player_x if result == "X" else self.player_o
            self.status_text.value = f"{winner_name} wins!"
        self._disable_all_buttons()
        self.page.update()
        return True

    def _online_tap(self, index: int):
        if self.network is None:
            return
        try:
            self.network.send_line(f"MOVE {index}")
        except OSError:
            self.status_text.value = "Connection lost while sending move."
            self.page.update()

    def _send_chat(self, _):
        if self.network is None:
            return
        message = self.chat_input.value.strip()
        if not message:
            return
        try:
            self.network.send_line(f"CHAT {message}")
            self.chat_input.value = ""
            self.page.update()
        except OSError:
            self.status_text.value = "Connection lost while sending chat."
            self.page.update()

    def _build_online_lobby(self):
        return ft.Container(
            ft.Column(
                [
                    self.role_text,
                    ft.Row(
                        [
                            ft.Container(
                                ft.Column(
                                    [
                                        ft.Text("Player X", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                        self.player_x_text,
                                    ],
                                    spacing=2,
                                ),
                                padding=10,
                                border_radius=10,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                expand=True,
                            ),
                            ft.Container(
                                ft.Column(
                                    [
                                        ft.Text("Player O", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                        self.player_o_text,
                                    ],
                                    spacing=2,
                                ),
                                padding=10,
                                border_radius=10,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    self.spectator_count_text,
                    self.roster_text,
                ],
                spacing=10,
            ),
            padding=12,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

    def _build_chat_message(self, payload: str):
        parts = payload.split("\t", 2)
        if len(parts) != 3:
            return ft.Text(payload)

        sender, tag, message = parts
        normalized_tag = tag.lower()
        if normalized_tag == "player x":
            bubble_color = ft.Colors.BLUE_50
            border_color = ft.Colors.BLUE_200
            name_color = ft.Colors.BLUE_900
        elif normalized_tag == "player o":
            bubble_color = ft.Colors.GREEN_50
            border_color = ft.Colors.GREEN_200
            name_color = ft.Colors.GREEN_900
        else:
            bubble_color = ft.Colors.AMBER_50
            border_color = ft.Colors.AMBER_200
            name_color = ft.Colors.AMBER_900

        return ft.Container(
            ft.Column(
                [
                    ft.Text(message),
                    ft.Text(
                        f"{sender} ({tag})",
                        size=11,
                        color=name_color,
                        italic=True,
                    ),
                ],
                spacing=2,
            ),
            padding=8,
            border=ft.Border.all(1, border_color),
            border_radius=10,
            bgcolor=bubble_color,
        )

    def _render_board(self):
        for index, button in enumerate(self.buttons):
            button.content = self.engine.board[index] or " "

    def _enable_valid_buttons(self):
        for index, button in enumerate(self.buttons):
            button.disabled = bool(self.engine.board[index])

    def _disable_all_buttons(self):
        for button in self.buttons:
            button.disabled = True

    def _sync_online_buttons(self):
        can_play = self.my_role == "player" and self.my_token and self.my_token == self.engine.current_turn
        for index, button in enumerate(self.buttons):
            button.disabled = (not can_play) or bool(self.engine.board[index])

    def _refresh_info(self):
        if self.my_role == "spectator":
            role_text = "Spectating this match"
        else:
            role_text = f"Playing as {self.my_token}"
        self.role_text.value = f"Role: {role_text}"
        self.player_x_text.value = self.player_x
        self.player_o_text.value = self.player_o
        self.spectator_count_text.value = f"Spectators: {len(self.spectators)}"
        spectator_text = ", ".join(self.spectators) if self.spectators else "None"
        self.roster_text.value = f"Spectators: {spectator_text}"


def create_screen(page: ft.Page, on_back, settings: dict, network, online: bool):
    return TicTacToeScreen(page=page, on_back=on_back, settings=settings, network=network, online=online)


def create_room():
    return TicTacToeRoom()


GAME_DEFINITION = GameDefinition(
    id="tictactoe",
    title="Tic-Tac-Toe",
    min_players=2,
    max_players=2,
    supports_offline=True,
    supports_online=True,
    create_screen=create_screen,
    create_room=create_room,
)
