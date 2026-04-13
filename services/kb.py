"""Channel knowledge-base loader.

Loads the visual system Markdown file that describes the channel's
visual identity, tone, and prompt conventions. Generators prepend
this block to their system prompts so every LLM call stays on-brand.
"""
import logging
from functools import lru_cache
from pathlib import Path

from config import BASE_DIR

logger = logging.getLogger(__name__)

KB_PATH = BASE_DIR / "config" / "visual_system.md"

KB_HEADER = "# CHANNEL CONTEXT — Visual System & Tone"
KB_FOOTER = "# END CHANNEL CONTEXT"


@lru_cache(maxsize=1)
def load_visual_system() -> str:
    """Return the channel KB as a string, or '' if the file is missing."""
    if not KB_PATH.exists():
        logger.info("No visual_system.md at %s", KB_PATH)
        return ""
    try:
        return KB_PATH.read_text(encoding="utf-8").strip()
    except OSError as e:
        logger.warning("Failed to read %s: %s", KB_PATH, e)
        return ""


def wrap_system_prompt(base_system: str) -> str:
    """Prepend the channel KB to a system prompt."""
    kb = load_visual_system()
    if not kb:
        return base_system
    return f"{KB_HEADER}\n\n{kb}\n\n{KB_FOOTER}\n\n{base_system}"


def reset_cache() -> None:
    """Test hook — invalidate the lru_cache so edits are picked up."""
    load_visual_system.cache_clear()
