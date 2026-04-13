from __future__ import annotations

import asyncio
import queue

import flet as ft

from core.game_registry import get_game, list_offline_games, list_online_games
from core.host_server import HostServer
from core.network import LineClient
from core.protocol import APP_VERSION, DEFAULT_PORT, PROTOCOL_VERSION, SETTINGS_ENV_VAR
from core.storage import get_settings_file, load_settings, save_settings


def main(page: ft.Page):
    settings = load_settings()
    event_queue: queue.Queue[tuple[str, str]] = queue.Queue()

    session = {
        "client": None,
        "connected": False,
        "host": "",
        "port": DEFAULT_PORT,
        "server_version": "",
        "games": [],
        "status": "",
        "current_view": "main",
        "current_handler": None,
        "host_server": None,
        "event_log": [],
        "is_local_host_client": False,
        "disconnect_in_progress": False,
        "ignore_disconnect_event": False,
    }

    page.title = "Game Hub"
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    page.window_width = 430
    page.window_height = 860

    content = ft.Column(expand=True, spacing=16)
    page.add(content)

    def apply_theme():
        mode = settings.get("theme_mode", "system").lower()
        if mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif mode == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM

    def is_debug_mode() -> bool:
        return bool(settings.get("debug_mode", False))

    apply_theme()

    def queue_host_event(event_type: str, message: str):
        event_queue.put((f"host:{event_type}", message))

    session["host_server"] = HostServer(on_event=queue_host_event)

    async def ui_event_pump():
        while True:
            while not event_queue.empty():
                event_type, payload = event_queue.get()
                if event_type == "line":
                    handle_server_line(payload)
                elif event_type == "disconnect":
                    handle_disconnect()
                elif event_type.startswith("host:"):
                    session["status"] = payload
                    append_event_log(f"{event_type[5:].upper()}: {payload}")
                    refresh_current_view()
            await asyncio.sleep(0.05)

    page.run_task(ui_event_pump)

    def back_header(title: str, back_action):
        return ft.Row(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: back_action()),
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
            ]
        )

    def append_event_log(message: str):
        session["event_log"].append(message)
        session["event_log"] = session["event_log"][-100:]

    def refresh_current_view():
        if session["current_view"] == "connected":
            refresh_connected_server_view()
        elif session["current_view"] == "host":
            refresh_host_view()

    def handle_server_line(line: str):
        handled = False
        handler = session["current_handler"]
        if handler is not None:
            handled = bool(handler(line))
        if handled:
            return

        if line.startswith("VERSION "):
            session["server_version"] = line[8:]
        elif line.startswith("GAMES "):
            session["games"] = [item.strip() for item in line[6:].split(",") if item.strip()]
        elif line.startswith("MESSAGE "):
            session["status"] = line[8:]
            append_event_log(f"SERVER: {line[8:]}")
        elif line.startswith("ERROR "):
            session["status"] = f"Error: {line[6:]}"
            append_event_log(f"ERROR: {line[6:]}")

        refresh_current_view()

    def handle_disconnect():
        if session["ignore_disconnect_event"]:
            session["ignore_disconnect_event"] = False
            return
        if session["disconnect_in_progress"]:
            return
        session["disconnect_in_progress"] = True
        client = session["client"]
        if client is not None:
            client.close()
        return_to_host = session["is_local_host_client"] and session["host_server"].snapshot()["running"]
        session["client"] = None
        session["connected"] = False
        session["server_version"] = ""
        session["games"] = []
        session["current_handler"] = None
        session["is_local_host_client"] = False
        session["status"] = "Disconnected from server."
        append_event_log("CLIENT: Disconnected from server.")
        if session["current_view"] in {"connected", "game"}:
            if return_to_host:
                show_host_game()
            else:
                show_join_game()
        session["disconnect_in_progress"] = False

    def disconnect_server(return_view=None):
        if session["disconnect_in_progress"]:
            return
        session["disconnect_in_progress"] = True
        if return_view is None:
            return_view = show_host_game if session["host_server"].snapshot()["running"] else show_join_game
        client = session["client"]
        if client is not None:
            try:
                client.send_line("QUIT")
            except Exception:
                pass
            session["ignore_disconnect_event"] = True
            client.close()
        session["client"] = None
        session["connected"] = False
        session["host"] = ""
        session["port"] = DEFAULT_PORT
        session["server_version"] = ""
        session["games"] = []
        session["current_handler"] = None
        session["is_local_host_client"] = False
        session["status"] = "Disconnected from server."
        append_event_log("CLIENT: Disconnected from server.")
        session["disconnect_in_progress"] = False
        if session["current_view"] in {"connected", "game"}:
            return_view()

    def connect_to_server(host: str, port: int, return_view=None, local_host_client: bool = False) -> tuple[bool, str]:
        disconnect_server()

        client = LineClient()

        def on_line(line: str):
            event_queue.put(("line", line))

        def on_disconnect():
            event_queue.put(("disconnect", ""))

        try:
            client.connect(host=host, port=port, on_line=on_line, on_disconnect=on_disconnect)
            session["client"] = client
            session["connected"] = True
            session["host"] = host
            session["port"] = port
            session["games"] = []
            session["server_version"] = ""
            session["is_local_host_client"] = local_host_client
            session["status"] = "Connected. Waiting for server information..."
            append_event_log(f"CLIENT: Connected to {host}:{port}")
            client.send_line(f"HELLO {PROTOCOL_VERSION}")
            if return_view is not None:
                return_view()
            else:
                show_connected_server()
            return True, "Connected."
        except Exception as exc:
            session["status"] = f"Could not connect: {exc}"
            return False, session["status"]

    def show_main_menu():
        session["current_view"] = "main"
        session["current_handler"] = None
        host_snapshot = session["host_server"].snapshot()
        content.controls = [
            ft.Text("Game Hub", size=30, weight=ft.FontWeight.BOLD),
            ft.Text("Offline and online multiplayer games in one modular app."),
            ft.Text(f"Player name: {settings['player_name']}"),
            ft.Button("Offline", on_click=lambda _: show_offline_games()),
            ft.Button("Join Game", on_click=lambda _: show_join_game()),
            ft.Button("Host Game", on_click=lambda _: show_host_game()),
            ft.Button("Settings", on_click=lambda _: show_settings()),
            ft.Divider(),
            ft.Text(
                "Host status: "
                + (
                    f"Running on {host_snapshot['local_ip']}:{host_snapshot['port']}"
                    if host_snapshot["running"]
                    else "Stopped"
                )
            ),
            ft.Text("Ready for LAN, public IP, Tailscale, and other VPN-style networking."),
        ]
        if is_debug_mode():
            content.controls.insert(2, ft.Text(f"App version: {APP_VERSION}"))
            content.controls.insert(4, ft.Text(f"Settings file: {get_settings_file()}"))
            content.controls.insert(5, ft.Text(f"Environment variable: {SETTINGS_ENV_VAR}"))
            content.controls.insert(10, ft.Button("Test Checklist", on_click=lambda _: show_test_checklist()))
        page.update()

    def show_offline_games():
        session["current_view"] = "offline"
        session["current_handler"] = None
        controls = [
            back_header("Offline Games", show_main_menu),
            ft.Text("Play locally on this device."),
        ]
        for game in list_offline_games():
            controls.append(
                ft.Button(
                    game.title,
                    on_click=lambda _, game_id=game.id: open_game_screen(game_id, online=False, on_back=show_offline_games),
                )
            )
        content.controls = controls
        page.update()

    def show_join_game():
        session["current_view"] = "join"
        session["current_handler"] = None
        status_text = ft.Text(session["status"])
        host_field = ft.TextField(label="Server IP / host", expand=True)
        port_field = ft.TextField(label="Port", value=str(DEFAULT_PORT), width=120)
        label_field = ft.TextField(label="Saved server name")
        saved_servers = ft.Column(spacing=8)

        def refresh_saved_servers():
            saved_servers.controls.clear()
            if not settings["saved_servers"]:
                saved_servers.controls.append(ft.Text("No saved servers yet."))
            for server in settings["saved_servers"]:
                saved_servers.controls.append(
                    ft.ListTile(
                        title=ft.Text(server["name"]),
                        subtitle=ft.Text(f"{server['host']}:{server['port']}"),
                        trailing=ft.TextButton(
                            "Connect",
                            on_click=lambda _, s=server: connect_from_join_screen(s["host"], int(s["port"])),
                        ),
                    )
                )

        def connect_from_join_screen(host: str, port: int):
            status_text.value = "Connecting..."
            page.update()
            ok, message = connect_to_server(host=host, port=port, return_view=show_connected_server)
            if not ok:
                status_text.value = message
                page.update()

        def save_server(_):
            name = label_field.value.strip()
            host = host_field.value.strip()
            port_text = port_field.value.strip()
            if not name or not host or not port_text.isdigit():
                status_text.value = "Enter a name, host, and numeric port."
                page.update()
                return

            settings["saved_servers"].append(
                {
                    "name": name,
                    "host": host,
                    "port": int(port_text),
                }
            )
            save_settings(settings)
            refresh_saved_servers()
            status_text.value = "Server saved."
            page.update()

        refresh_saved_servers()
        content.controls = [
            back_header("Join Game", show_main_menu),
            ft.Text("Connect by LAN IP, public IP, VPN, or Tailscale address."),
            ft.Text(
                "Direct mobile-data hosting only works when the host device is reachable from the internet. "
                "Many carriers use CGNAT, so VPNs like Tailscale are usually the safer option.",
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            saved_servers,
            ft.Divider(),
            host_field,
            port_field,
            label_field,
            ft.Row(
                [
                    ft.Button(
                        "Connect",
                        on_click=lambda _: connect_from_join_screen(
                            host_field.value.strip(),
                            int(port_field.value.strip()) if port_field.value.strip().isdigit() else DEFAULT_PORT,
                        ),
                    ),
                    ft.OutlinedButton("Save Server", on_click=save_server),
                ]
            ),
            status_text,
        ]
        page.update()

    connected_info = ft.Text("")
    connected_status = ft.Text("")
    connected_games = ft.Column(spacing=8)

    def refresh_connected_server_view():
        connected_info.value = (
            f"Connected to {session['host']}:{session['port']}\n"
            f"Server version: {session['server_version'] or 'Waiting...'}\n"
            f"Protocol version: {PROTOCOL_VERSION}"
        )
        connected_status.value = session["status"]
        connected_games.controls.clear()

        if not session["games"]:
            connected_games.controls.append(ft.Text("Waiting for game list..."))
        else:
            for game_id in session["games"]:
                definition = get_game(game_id)
                player_label = (
                    f"{definition.min_players} players"
                    if definition.min_players == definition.max_players
                    else f"{definition.min_players}-{definition.max_players} players"
                )
                connected_games.controls.append(
                    ft.ListTile(
                        title=ft.Text(definition.title),
                        subtitle=ft.Text(player_label),
                        trailing=ft.TextButton("Join", on_click=lambda _, selected=game_id: join_online_game(selected)),
                    )
                )
        page.update()

    def show_connected_server():
        session["current_view"] = "connected"
        session["current_handler"] = None
        content.controls = [
            back_header("Connected Server", leave_server),
            connected_info,
            connected_status,
            ft.Divider(),
            ft.Text("Available games", size=20, weight=ft.FontWeight.BOLD),
            connected_games,
        ]
        refresh_connected_server_view()

    def leave_server():
        target_view = show_host_game if session["host_server"].snapshot()["running"] else show_join_game
        disconnect_server(return_view=target_view)

    def leave_online_game():
        target_view = show_host_game if session["host_server"].snapshot()["running"] else show_join_game
        disconnect_server(return_view=target_view)

    def join_online_game(game_id: str):
        client: LineClient | None = session["client"]
        if client is None:
            session["status"] = "Not connected."
            refresh_connected_server_view()
            return

        try:
            client.send_line(f"JOIN {game_id} {settings['player_name']}")
        except Exception as exc:
            session["status"] = f"Could not join game: {exc}"
            refresh_connected_server_view()
            return

        open_game_screen(game_id, online=True, on_back=leave_online_game)
        append_event_log(f"CLIENT: Requested join for {game_id}")

    def open_game_screen(game_id: str, online: bool, on_back):
        session["current_view"] = "game"
        definition = get_game(game_id)
        screen = definition.create_screen(
            page=page,
            on_back=on_back,
            settings=settings,
            network=session["client"] if online else None,
            online=online,
        )
        session["current_handler"] = screen.handle_server_line if online else None
        content.controls = [screen.build()]
        page.update()

    host_status = ft.Text("")
    host_server_details = ft.Text("")
    host_players = ft.Column(spacing=6)
    host_room_status = ft.Text("")
    host_event_log = ft.ListView(expand=False, spacing=4, height=180, auto_scroll=True)
    host_game_dropdown = ft.Dropdown(
        label="Selected game",
        options=[ft.dropdown.Option(game.id, game.title) for game in list_online_games()],
    )
    host_port_field = ft.TextField(label="Port", value=str(DEFAULT_PORT), width=120)

    def refresh_host_view():
        if session["current_view"] != "host":
            return

        snapshot = session["host_server"].snapshot()
        host_status.value = session["status"] or ("Server running." if snapshot["running"] else "Server stopped.")
        host_server_details.value = (
            f"Local IP: {snapshot['local_ip']}\n"
            f"Port: {snapshot['port']}\n"
            f"Selected game: {snapshot['selected_game']}"
        )
        host_room_status.value = (
            f"{snapshot['room']['status']}\n"
            f"Players: {len(snapshot['room'].get('players', []))} | "
            f"Spectators: {len(snapshot['room'].get('spectators', []))} | "
            f"Chat messages: {snapshot['room'].get('chat_count', 0)}"
        )
        host_game_dropdown.value = snapshot["selected_game"]

        host_players.controls.clear()
        if not snapshot["connected_clients"]:
            host_players.controls.append(ft.Text("No connected players yet."))
        for client in snapshot["connected_clients"]:
            joined = client["joined_game"] or "Browsing"
            host_players.controls.append(ft.Text(f"{client['name']} ({client['address']}) - {joined}"))
        host_event_log.controls = [ft.Text(line, size=12) for line in snapshot.get("event_log", [])]
        page.update()

    def show_host_game():
        session["current_view"] = "host"
        session["current_handler"] = None

        def start_host(_):
            port_text = host_port_field.value.strip()
            port = int(port_text) if port_text.isdigit() else DEFAULT_PORT
            try:
                _, message = session["host_server"].start(port=port)
            except OSError as exc:
                message = f"Could not start host server: {exc}"
            session["status"] = message
            refresh_host_view()

        def stop_host(_):
            if session["is_local_host_client"] and session["connected"]:
                disconnect_server()
            session["host_server"].stop()
            session["status"] = "Host server stopped."
            refresh_host_view()

        def select_game(_):
            if not host_game_dropdown.value:
                return
            _, message = session["host_server"].set_selected_game(host_game_dropdown.value)
            session["status"] = message
            refresh_host_view()

        def start_match(_):
            _, message = session["host_server"].start_match()
            session["status"] = message
            refresh_host_view()

        def clear_chat(_):
            _, message = session["host_server"].clear_room_chat()
            session["status"] = message
            refresh_host_view()

        def join_as_host(_):
            snapshot = session["host_server"].snapshot()
            if not snapshot["running"]:
                session["status"] = "Start the host server first."
                refresh_host_view()
                return

            ok, message = connect_to_server(
                host="127.0.0.1",
                port=int(snapshot["port"]),
                return_view=show_connected_server,
                local_host_client=True,
            )
            session["status"] = "Joined your hosted server." if ok else message
            if not ok:
                refresh_host_view()

        content.controls = [
            back_header("Host Game", show_main_menu),
            ft.Text("Run a multiplayer host directly inside this client app."),
            ft.Row(
                [
                    host_port_field,
                    ft.Button("Start Server", on_click=start_host),
                    ft.OutlinedButton("Stop", on_click=stop_host),
                ]
            ),
            host_game_dropdown,
            ft.Row(
                [
                    ft.OutlinedButton("Apply Game", on_click=select_game),
                    ft.Button("Start Match", on_click=start_match),
                    ft.OutlinedButton("Restart Match", on_click=start_match),
                    ft.OutlinedButton("Clear Chat", on_click=clear_chat),
                    ft.Button("Join as Host", on_click=join_as_host),
                ]
            ),
            host_server_details,
            host_room_status,
            ft.Divider(),
            ft.Text("Connected players", size=20, weight=ft.FontWeight.BOLD),
            host_players,
            host_status,
            ft.Text(
                "Share the host IP and port with players. For mobile-data or internet play, "
                "the host device must be publicly reachable or on a VPN like Tailscale.",
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
        ]
        if is_debug_mode():
            content.controls.insert(
                11,
                ft.Text("Recent host events", size=20, weight=ft.FontWeight.BOLD),
            )
            content.controls.insert(
                12,
                ft.Container(
                    host_event_log,
                    border=ft.Border.all(1, ft.Colors.OUTLINE),
                    border_radius=12,
                    padding=8,
                ),
            )
        refresh_host_view()

    def show_test_checklist():
        session["current_view"] = "test"
        session["current_handler"] = None
        checks = [
            "1. Open the app on your computer and on your phone at the same time.",
            "2. On the computer, open Host Game and start the server.",
            "3. Choose Tic-Tac-Toe, then join as host or from another device.",
            "4. On the phone, use Join Game and connect to the computer IP and host port.",
            "5. Use the in-game room chat from both devices and confirm spectators can see it.",
            "6. Confirm Tic-Tac-Toe starts automatically when the second player joins.",
            "7. Disconnect one side during a match and verify the other side gets a safe message.",
            "8. Test spectator mode by joining after the game has already started.",
            "9. Test saved servers and a custom settings file via GAME_HUB_SETTINGS_FILE.",
            "10. For the most reliable first test, host on the computer and join from the phone.",
        ]
        recent_events = ft.ListView(
            controls=[ft.Text(line, size=12) for line in session["event_log"]],
            expand=False,
            height=180,
            spacing=4,
            auto_scroll=True,
        )
        content.controls = [
            back_header("Test Checklist", show_main_menu),
            ft.Text("Recommended setup: computer hosts, phone joins."),
            ft.Column([ft.Text(item) for item in checks], spacing=8),
            ft.Divider(),
            ft.Text("Recent app events", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(
                recent_events,
                border=ft.Border.all(1, ft.Colors.OUTLINE),
                border_radius=12,
                padding=8,
            ),
            ft.Text("Developer note: copy games/template_game.py and follow ADDING_GAMES.md to add more games."),
        ]
        page.update()

    def show_settings():
        session["current_view"] = "settings"
        session["current_handler"] = None
        name_field = ft.TextField(label="Player name", value=settings["player_name"])
        theme_label = ft.Text("")
        saved_servers_column = ft.Column(spacing=8)

        def refresh_saved_servers():
            saved_servers_column.controls.clear()
            if not settings["saved_servers"]:
                saved_servers_column.controls.append(ft.Text("No saved servers."))
            for index, server in enumerate(settings["saved_servers"]):
                saved_servers_column.controls.append(
                    ft.Row(
                        [
                            ft.Text(f"{server['name']} - {server['host']}:{server['port']}", expand=True),
                            ft.IconButton(ft.Icons.DELETE, on_click=lambda _, idx=index: delete_server(idx)),
                        ]
                    )
                )

        def save_name(_):
            value = name_field.value.strip()
            if not value:
                return
            settings["player_name"] = value
            save_settings(settings)
            session["status"] = "Player name saved."
            page.update()

        def set_theme(mode: str):
            settings["theme_mode"] = mode
            save_settings(settings)
            apply_theme()
            theme_label.value = f"Theme set to {mode}"
            page.update()

        def delete_server(index: int):
            if 0 <= index < len(settings["saved_servers"]):
                settings["saved_servers"].pop(index)
                save_settings(settings)
                refresh_saved_servers()
                page.update()

        refresh_saved_servers()
        content.controls = [
            back_header("Settings", show_main_menu),
            name_field,
            ft.Button("Save Name", on_click=save_name),
            ft.Divider(),
            ft.Text("Theme"),
            ft.Row(
                [
                    ft.OutlinedButton("System", on_click=lambda _: set_theme("system")),
                    ft.OutlinedButton("Light", on_click=lambda _: set_theme("light")),
                    ft.OutlinedButton("Dark", on_click=lambda _: set_theme("dark")),
                ]
            ),
            theme_label,
            ft.Divider(),
            ft.Row(
                [
                    ft.Text("Debug mode", expand=True),
                    ft.Switch(
                        value=is_debug_mode(),
                        on_change=lambda e: set_debug_mode(bool(e.control.value)),
                    ),
                ]
            ),
            ft.Divider(),
            ft.Text("Saved servers"),
            saved_servers_column,
        ]
        if is_debug_mode():
            content.controls.insert(10, ft.Text(f"Settings file path: {get_settings_file()}"))
            content.controls.insert(11, ft.Text(f"Set {SETTINGS_ENV_VAR} to use a different settings file."))
            content.controls.insert(12, ft.Text("To add more games, start from ADDING_GAMES.md and games/template_game.py."))
        page.update()

        def set_debug_mode(enabled: bool):
            settings["debug_mode"] = enabled
            save_settings(settings)
            show_settings()

    show_main_menu()


ft.run(main)
