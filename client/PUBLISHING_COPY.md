# Publishing Copy

## GitHub Repository Description

Modular Python + Flet multiplayer game hub with in-app hosting, online Tic-Tac-Toe, spectators, room chat, and plug-and-play game support.

## GitHub Short Intro

Game Hub is a modular multiplayer app built in Python with Flet. It supports offline play, direct-IP online play, hosting from inside the client, spectators, room chat, and an easy-to-extend game system.

## itch.io Short Description

A mobile-friendly multiplayer Game Hub built with Python and Flet. Host from your own device, join by IP, play Tic-Tac-Toe, spectate live matches, and test direct multiplayer without a separate server.

## itch.io Full Description

Game Hub is a modular multiplayer app prototype built with Python and Flet.

This testing version includes:

- offline and online Tic-Tac-Toe
- hosting directly inside the client app
- join by IP and port
- spectators for active games
- per-room chat
- host join support
- settings and saved servers
- an expandable system for adding more games later

This build is best for testing on:

- Windows and desktop Python
- Android preview with Flet
- LAN play
- VPN play such as Tailscale

Important notes:

- direct internet or mobile-data hosting depends on whether the host device is reachable from the internet
- room chat is not automatically moderated
- this is a testing build, not a final store release

## itch.io Upload Notes

If you are uploading source for testers:

- include `app.py`
- include `core/`
- include `games/`
- include `tests/`
- include `README.md`
- include `requirements.txt`

Do not include:

- `venv/`
- `__pycache__/`
- private settings files
- temporary local build output
