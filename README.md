# Game Hub Workspace

This repository contains the Game Hub multiplayer project.

It currently has two main parts:

- [client/](./client/) - the active Flet app with in-app hosting, offline play, online play, spectators, and modular game support
- [server/](./server/) - a separate standalone server codebase kept in the repository for reference and future use

## Recommended Main Entry

The main project most people should run is:

- [client/app.py](./client/app.py)

That client app already includes its own host server, so a separate server process is not required for normal use.

## Quick Start

Open a terminal in the repository root, then run:

```powershell
cd .\client
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

For Android preview with Flet:

```powershell
cd .\client
.\venv\Scripts\flet.exe run --android --port 8560 .\app.py
```

If you want more setup details, see [client/README.md](./client/README.md).

## License

This repository uses the [MIT License](https://github.com/ernies-Organization/game-hub/blob/main/LICENSE).

## Repository Layout

- [client/](./client/)
- [client/README.md](./client/README.md)
- [client/app.py](./client/app.py)
- [client/core/](./client/core/)
- [client/games/](./client/games/)
- [client/tests/](./client/tests/)
- [client/ADDING_GAMES.md](./client/ADDING_GAMES.md)
- [server/](./server/)
- [server/server.py](./server/server.py)
- [server/core/](./server/core/)
- [server/games/](./server/games/)
- [.gitignore](./.gitignore)
- [LICENSE](https://github.com/ernies-Organization/game-hub/blob/main/LICENSE)

## Notes

- [client/](./client/) is the main app you should show to users and testers.
- [server/](./server/) is useful to keep on GitHub for development history, experiments, or future dedicated-server work.
