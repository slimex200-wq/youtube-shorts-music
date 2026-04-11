"""Channel knowledge-base loader.

Each channel has a Markdown file describing its visual identity, tone,
and prompt conventions. Generators prepend this block to their system
prompts so every LLM call (Suno, Metadata, Higgsfield) stays on-brand.

Files live at config/channels/<channel>/visual_system.md. When absent,
the loader returns an empty string — generators then fall back to their
built-in defaults.
"""
import logging
from functools import lru_cache
from pathlib import Path

from config import BASE_DIR

logger = logging.getLogger(__name__)

CHANNELS_DIR = BASE_DIR / "config" / "channels"

KB_HEADER = "# CHANNEL CONTEXT — Visual System & Tone"
KB_FOOTER = "# END CHANNEL CONTEXT"


def _kb_path(channel: str) -> Path:
    return CHANNELS_DIR / channel / "visual_system.md"


@lru_cache(maxsize=8)
def load_visual_system(channel: str = "default") -> str:
    """Return the channel KB as a string, or '' if the file is missing."""
    path = _kb_path(channel)
    if not path.exists():
        logger.info("No visual_system.md for channel=%s at %s", channel, path)
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return ""


def wrap_system_prompt(base_system: str, channel: str = "default") -> str:
    """Prepend the channel KB to a system prompt.

    The header/footer markers are stable so Claude's prompt cache stays
    valid across calls that share the same channel. Do NOT reorder or
    reformat them without understanding cache invalidation.
    """
    kb = load_visual_system(channel)
    if not kb:
        return base_system

    return f"{KB_HEADER}\n\n{kb}\n\n{KB_FOOTER}\n\n{base_system}"


def reset_cache() -> None:
    """Test hook — invalidate the lru_cache so edits are picked up."""
    load_visual_system.cache_clear()
