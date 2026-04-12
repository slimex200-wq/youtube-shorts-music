import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"


ARTIST_NAME = os.getenv("ARTIST_NAME", "Artist")
CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "")


@dataclass
class Config:
    anthropic_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )
