import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
SETTINGS_PATH = BASE_DIR / "config" / "settings.json"


def _load_settings() -> dict:
    """Load saved settings from config/settings.json (UI-configured values)."""
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_setting(key: str, default: str = "") -> str:
    """Read a setting: UI-saved value takes precedence over .env."""
    saved = _load_settings().get(key)
    if saved:
        return saved
    return os.getenv(key, default)


ARTIST_NAME = get_setting("ARTIST_NAME", "Artist")
CHANNEL_HANDLE = get_setting("YOUTUBE_CHANNEL_HANDLE", "")


@dataclass
class Config:
    anthropic_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=get_setting("ANTHROPIC_API_KEY", ""),
        )
