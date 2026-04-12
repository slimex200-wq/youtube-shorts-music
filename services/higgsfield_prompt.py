"""Video prompt generator — text-based, runs alongside Suno prompt.

Generates 4 Higgsfield/Kling video prompts from genre, mood, and style context.
No image input required.
"""
import logging
from typing import Optional

from services.kb import wrap_system_prompt
from services.llm import LLMClient, default_client
from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert video prompt engineer for AI video generation tools (Higgsfield, Kling 3.0).

Given a music genre, mood, and visual style, produce exactly 4 video prompts — each with a DIFFERENT motion style.
These prompts will be used to generate short video clips for YouTube Shorts music videos.

# The 4 Motion Types (MUST produce all 4)

1. **ZOOM** — Slow zoom in or out. Contemplative, atmospheric. Draws viewer into the subject.
   Camera: slow zoom in / slow dolly in / gradual push-in
   Motion strength: 2-3

2. **PAN** — Camera orbit or pan revealing the scene. Dramatic, environmental.
   Camera: slow pan left/right / orbit around subject / tracking shot
   Motion strength: 3-4

3. **SUBJECT** — The subject moves while camera is mostly static. Character-driven.
   Camera: static or subtle handheld / subject turns head / walks forward / gestures
   Motion strength: 4-5

4. **ATMOSPHERE** — Environmental particles and effects in motion. Mystical, immersive.
   Camera: static or very slow zoom / particles drift / smoke rises / embers float / rain falls
   Motion strength: 3-4

# Prompt Structure

Each prompt must follow this formula in order:
1. Subject & scene description (create a vivid scene matching the music genre and mood)
2. Camera movement instruction
3. Motion/animation details
4. Lighting & mood
5. Color palette (2-3 colors)
6. Quality tokens: "cinematic, high quality, smooth motion"
7. Aspect ratio: end with ", 9:16 vertical, 5 seconds"

# Rules

- Prompts in ENGLISH only
- Each prompt must be 2-3 sentences, 40-80 words
- All 4 prompts should share the same scene/subject, only varying camera + motion
- Match the mood and aesthetic of the music genre
- For anime style: use anime/illustration visual language, motion_strength 1-2
- For cyberpunk: neon lights, rain, holograms
- For dark/industrial: concrete, steel, smoke, harsh lighting

# Output Format

Return a JSON array of exactly 4 objects:
```json
[
  {
    "type": "zoom",
    "label": "Slow Zoom",
    "prompt": "...",
    "motion_strength": 3,
    "camera": "slow zoom in",
    "duration": "5s"
  },
  ...
]
```
"""

USER_TEMPLATE = """Generate 4 video prompts for a YouTube Shorts music video.

Genre: {genre}
Visual Style: {style}
{extras}

Return ONLY a JSON array with exactly 4 prompt objects. No other text."""


class VideoPromptGenerator:
    def __init__(
        self,
        channel: str = "default",
        llm: Optional[LLMClient] = None,
        model: str = "sonnet",
    ) -> None:
        self.channel = channel
        self.llm = llm
        self.model = model

    def generate(
        self,
        genre: str,
        style: str = "",
        mood_tags: list[str] | None = None,
        motif_tags: list[str] | None = None,
    ) -> list[dict]:
        """Generate 4 video prompts from genre/style/mood context."""
        client = self.llm or default_client()
        system = wrap_system_prompt(SYSTEM_PROMPT, self.channel)

        extras_parts = []
        if mood_tags:
            extras_parts.append(f"Mood: {', '.join(mood_tags)}")
        if motif_tags:
            extras_parts.append(f"Motifs: {', '.join(motif_tags)}")
        extras = "\n".join(extras_parts) if extras_parts else ""

        user_text = USER_TEMPLATE.format(
            genre=genre,
            style=style or "genre-based",
            extras=extras,
        )

        response = client.complete(
            system=system,
            user=user_text,
            model=self.model,
            max_tokens=2048,
        )

        prompts = parse_claude_json(response)
        if not isinstance(prompts, list) or len(prompts) != 4:
            raise ValueError(
                f"Expected 4 prompts, got {len(prompts) if isinstance(prompts, list) else type(prompts)}"
            )

        return prompts
