# Game Hub

Game Hub is a modular multiplayer project built in Python with Flet.

The main app lives in [client/](./client/) and includes:

- offline play
- online play over direct IP
- in-app hosting with no separate server required
- spectator support
- modular game support

Most users should start with [client/app.py](./client/app.py).

## License

This repository uses the [MIT License](LICENSE).


# Disclaimer
The content provided herein is intended strictly for educational purposes. Any misuse or abuse of this information that contradicts this purpose, including but not limited to the unauthorized distribution, reproduction, or alteration of content, or the use of information for illicit activities, is strictly prohibited and may constitute a violation of applicable laws and regulations. This could lead to serious consequences including legal action. Educational resources are to be used responsibly, ethically, and with integrity. I reserve the right to restrict access to these resources for anyone found violating these terms. I also reserve the right to change any important information without notice.

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

