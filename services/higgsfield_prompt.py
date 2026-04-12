"""Higgsfield 4-set video prompt generator.

Takes a reference image, analyzes it with Claude vision, and produces
four distinct Higgsfield/Kling video prompts — each with a different
camera movement and motion style.
"""
import logging
from typing import Optional

from services.kb import wrap_system_prompt
from services.llm import LLMClient, default_client
from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert video prompt engineer for AI video generation tools (Higgsfield, Kling 3.0).

Given a reference image, you analyze its content, composition, subject, mood, and lighting,
then produce exactly 4 video prompts — each with a DIFFERENT motion style.

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
1. Subject & scene description (from the image — be SPECIFIC about what you see)
2. Camera movement instruction
3. Motion/animation details
4. Lighting & mood
5. Color palette (2-3 colors)
6. Quality tokens: "cinematic, high quality, smooth motion"
7. Aspect ratio: end with ", 9:16 vertical, 5 seconds"

# Rules

- Prompts in ENGLISH only
- Each prompt must be 2-3 sentences, 40-80 words
- Describe what you ACTUALLY SEE in the image — don't invent new subjects
- Keep the same subject/scene across all 4 prompts, only vary camera + motion
- Match the mood/tone of the original image
- For realistic/masked characters: motion_strength 4-5
- For anime/illustrated style: motion_strength 1-2

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

USER_TEMPLATE = """Analyze this reference image and generate 4 Higgsfield video prompts.

{context}

Return ONLY a JSON array with exactly 4 prompt objects. No other text."""


class HiggsFieldPromptGenerator:
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
        image_data: bytes,
        image_media_type: str,
        genre: str = "",
        mood_tags: list[str] | None = None,
        motif_tags: list[str] | None = None,
        notes: str = "",
    ) -> list[dict]:
        """Generate 4 Higgsfield video prompts from a reference image."""
        client = self.llm or default_client()
        system = wrap_system_prompt(SYSTEM_PROMPT, self.channel)

        context_parts = []
        if genre:
            context_parts.append(f"Genre: {genre}")
        if mood_tags:
            context_parts.append(f"Mood: {', '.join(mood_tags)}")
        if motif_tags:
            context_parts.append(f"Motifs: {', '.join(motif_tags)}")
        if notes:
            context_parts.append(f"Notes: {notes}")

        context = "\n".join(context_parts) if context_parts else "No additional context."
        user_text = USER_TEMPLATE.format(context=context)

        response = client.complete_vision(
            system=system,
            user_text=user_text,
            image_data=image_data,
            image_media_type=image_media_type,
            model=self.model,
            max_tokens=2048,
            timeout=120,
        )

        prompts = parse_claude_json(response)
        if not isinstance(prompts, list) or len(prompts) != 4:
            raise ValueError(
                f"Expected 4 prompts, got {len(prompts) if isinstance(prompts, list) else type(prompts)}"
            )

        return prompts
