from __future__ import annotations


class BaseRoom:
    def __init__(self, game_id: str, title: str, min_players: int, max_players: int) -> None:
        self.game_id = game_id
        self.title = title
        self.min_players = min_players
        self.max_players = max_players
        self.players = []
        self.spectators = []
        self.started = False
        self.closed = False
        self.status = "Waiting for players."
        self.chat_history: list[dict[str, str]] = []

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def spectator_count(self) -> int:
        return len(self.spectators)

    def all_sessions(self):
        return self.players + self.spectators

    def add_player(self, session):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def handle_command(self, session, command: str, payload: str) -> None:
        raise NotImplementedError

    def broadcast(self, message: str) -> None:
        stale_sessions = []
        for session in self.all_sessions():
            try:
                session.send_line(message)
            except OSError:
                stale_sessions.append(session)
        for stale in stale_sessions:
            self.remove_player(stale)

    def _chat_tag_for_session(self, session) -> str:
        role = getattr(session, "room_role", "spectator")
        token = getattr(session, "room_token", "")
        if role == "player" and token:
            return f"Player {token}"
        return "Spectator"

    def _encode_chat_entry(self, entry: dict[str, str]) -> str:
        return "\t".join(
            [
                entry["sender"].replace("\t", " ").replace("\n", " "),
                entry["tag"].replace("\t", " ").replace("\n", " "),
                entry["message"].replace("\t", " ").replace("\n", " "),
            ]
        )

    def add_chat_message(self, session, message: str) -> None:
        entry = {
            "sender": session.name,
            "tag": self._chat_tag_for_session(session),
            "message": message,
        }
        self.chat_history.append(entry)
        self.chat_history = self.chat_history[-100:]
        self.broadcast(f"CHAT_FROM {self._encode_chat_entry(entry)}")

    def send_chat_history(self, session) -> None:
        for entry in self.chat_history:
            session.send_line(f"CHAT_HISTORY {self._encode_chat_entry(entry)}")

    def clear_chat(self) -> None:
        self.chat_history.clear()
        self.broadcast("CHAT_RESET")

    def remove_player(self, session) -> None:
        self.players = [player for player in self.players if player.client_id != session.client_id]
        self.spectators = [spectator for spectator in self.spectators if spectator.client_id != session.client_id]
        if not self.players:
            self.started = False
            self.closed = False
            self.status = "Waiting for players."

    def host_state(self) -> dict:
        return {
            "game_id": self.game_id,
            "title": self.title,
            "started": self.started,
            "closed": self.closed,
            "status": self.status,
            "players": [
                {
                    "name": player.name,
                    "token": getattr(player, "room_token", ""),
                }
                for player in self.players
            ],
            "spectators": [
                {
                    "name": spectator.name,
                }
                for spectator in self.spectators
            ],
            "chat_count": len(self.chat_history),
        }
