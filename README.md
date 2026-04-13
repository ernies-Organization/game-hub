# Game Hub

Game Hub is a modular multiplayer project built in Python with Flet.

The main app lives in [client/](./client/) and includes:

- offline play
- online play over direct IP
- in-app hosting with no separate server required
- spectator support
- modular game support

Most users should start with [client/app.py](./client/app.py).

## Quick Start

From the repository root, run:

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

## Repository

- [client/](./client/) - the main app
- [client/README.md](./client/README.md) - client setup and usage
- [client/app.py](./client/app.py) - main entry point
- [client/core/](./client/core/) - shared app and networking code
- [client/games/](./client/games/) - game modules
- [client/tests/](./client/tests/) - automated tests
- [server/](./server/) - separate standalone server code kept for reference and future work

## License

This repository uses the [MIT License](https://github.com/ernies-Organization/game-hub/blob/main/LICENSE).
