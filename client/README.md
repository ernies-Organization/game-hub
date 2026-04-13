# Game Hub

Game Hub is a modular Python multiplayer app built with Flet.

It includes:

- offline Tic-Tac-Toe
- online Tic-Tac-Toe
- in-app hosting with no separate server process
- host join support
- spectator support
- per-room chat
- settings with `GAME_HUB_SETTINGS_FILE`
- a plug-and-play game registry for adding more games later

## Current Status

This is a testing build focused on local and direct-IP multiplayer.

Right now the playable game is:

- Tic-Tac-Toe

The networking model is:

- host from the client app itself
- join by IP address and port
- works well on LAN
- can work over VPNs like Tailscale
- direct internet or mobile-data hosting depends on whether the host device is reachable from the internet

## Project Structure

- [app.py](./app.py)
- [core/](./core/)
- [games/](./games/)
- [tests/](./tests/)
- [ADDING_GAMES.md](./ADDING_GAMES.md)
- [requirements.txt](./requirements.txt)
- [.gitignore](./.gitignore)
- [../LICENSE](https://github.com/ernies-Organization/game-hub/blob/main/LICENSE)

Important files:

- [app.py](./app.py) - main Flet app
- [core/host_server.py](./core/host_server.py) - threaded in-app host server
- [core/network.py](./core/network.py) - TCP line client
- [core/game_registry.py](./core/game_registry.py) - game registration
- [core/protocol.py](./core/protocol.py) - app and protocol constants
- [core/storage.py](./core/storage.py) - saved settings and env-based settings file support
- [games/tictactoe.py](./games/tictactoe.py) - current game implementation
- [games/template_game.py](./games/template_game.py) - starter template for new games
- [ADDING_GAMES.md](./ADDING_GAMES.md) - guide for adding games
- [../LICENSE](https://github.com/ernies-Organization/game-hub/blob/main/LICENSE) - repository license

## Requirements

- Python 3.14
- Flet 0.84.0

## Install

Create a virtual environment, activate it, and install the dependency:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run On Computer

```powershell
py app.py
```

## Run For Android Preview

```powershell
.\venv\Scripts\flet.exe run --android --port 8560 .\app.py
```

This prints a local URL and QR code. You can:

- open the app on your phone with the QR code
- open the same URL on your computer browser
- host on the computer and join from the phone

## Recommended Multiplayer Test Flow

1. Start the app on your computer.
2. Go to `Host Game`.
3. Start the server.
4. Tap `Join as Host`.
5. Open the app on your phone.
6. Use `Join Game` and connect to the computer IP and shown port.
7. Join Tic-Tac-Toe.
8. Confirm the game auto-starts when the second player joins.
9. Open another client if needed and confirm it joins as a spectator.

## Features

- offline PvP Tic-Tac-Toe
- offline AI Tic-Tac-Toe
- online host inside the client
- host can join their own server
- automatic match start when enough players join
- spectator mode for full or active games
- room chat with player and spectator tags
- unmoderated chat warning
- clean disconnect and back-button handling
- debug mode for developer-only tools

## Settings

The app supports a custom settings file path through:

```text
GAME_HUB_SETTINGS_FILE
```

Example in PowerShell:

```powershell
$env:GAME_HUB_SETTINGS_FILE="C:\temp\gamehub-settings.json"
py app.py
```

## Testing

Run tests with:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

You can also compile-check the project with:

```powershell
.\venv\Scripts\python.exe -m compileall app.py core games tests
```

## Adding New Games

To add a new game:

1. Copy `games/template_game.py`
2. Implement the game room and screen
3. Register it in `core/game_registry.py`

See [ADDING_GAMES.md](./ADDING_GAMES.md) for the full guide.

## Notes

- Room chat is not automatically moderated.
- Do not share sensitive information in chat.
- This project is currently a testing build, not a finished store release.
