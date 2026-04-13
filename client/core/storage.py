import json
import os
from pathlib import Path
from typing import Any

from core.protocol import SETTINGS_ENV_VAR


def get_settings_file() -> Path:
    configured = os.getenv(SETTINGS_ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / "settings.json").resolve()


def default_settings() -> dict[str, Any]:
    return {
        "player_name": "Player",
        "theme_mode": "system",
        "saved_servers": [],
        "debug_mode": False,
    }


def load_settings() -> dict[str, Any]:
    settings_file = get_settings_file()

    if not settings_file.exists():
        data = default_settings()
        save_settings(data)
        return data

    try:
        with settings_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_settings()
        save_settings(data)
        return data

    defaults = default_settings()
    for key, value in defaults.items():
        if key not in data:
            data[key] = value

    if not isinstance(data["saved_servers"], list):
        data["saved_servers"] = []

    return data


def save_settings(settings: dict[str, Any]) -> None:
    settings_file = get_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with settings_file.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
