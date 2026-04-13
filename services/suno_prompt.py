import json
import logging
from pathlib import Path
from typing import Optional

from services.kb import wrap_system_prompt
from services.llm import LLMClient, default_client
from services.shranz_substyles import (
    build_substyle_prompt_section,
    get_used_substyles_from_projects,
    is_shranz_genre,
    pick_substyle,
)
from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

GENRES_JSON = Path(__file__).parent.parent / "config" / "genres.json"


def _load_substyle_stats(projects_dir: str) -> dict[str, dict] | None:
    """Aggregate YouTube stats per substyle from existing projects."""
    import json as _json

    result: dict[str, dict] = {}
    projects_path = Path(projects_dir)
    if not projects_path.exists():
        return None

    has_stats = False
    for d in projects_path.iterdir():
        pj = d / "project.json"
        if not pj.exists():
            continue
        try:
            data = _json.loads(pj.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        sp = data.get("suno_prompt") or {}
        substyle = sp.get("substyle")
        if not substyle:
            continue
        stats = data.get("youtube_stats") or {}
        views = stats.get("views", 0)
        if substyle not in result:
            result[substyle] = {"count": 0, "views": 0}
        result[substyle]["count"] += 1
        result[substyle]["views"] += views
        if views > 0:
            has_stats = True

    return result if has_stats else None


def _load_genre_sections() -> str:
    """Load genre production knowledge from config/genres.json."""
    if not GENRES_JSON.exists():
        return ""
    try:
        data = json.loads(GENRES_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    genres = data.get("genres", {})
    sections = []
    for name, info in genres.items():
        lines = [f"## {name.title()}"]
        if info.get("bpm"):
            lines.append(f"- BPM: {info['bpm']}")
        if info.get("core"):
            lines.append(f"- Core: {info['core']}")
        if info.get("instruments"):
            lines.append(f"- Instruments: {info['instruments']}")
        if info.get("texture"):
            lines.append(f"- Texture: {info['texture']}")
        if info.get("weirdness"):
            lines.append(f"- Weirdness: {info['weirdness']} / Style influence: {info.get('style_influence', '')}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)

SYSTEM_PROMPT = """You are an expert music producer and Suno AI prompt engineer.
Given a genre and options, generate a Suno-compatible prompt that produces professional-quality tracks.

# Output Fields
- style: Suno "Style of Music" field. Genre + specific instruments + production techniques + mood. English. Be SPECIFIC — name exact synths, drum machines, effects.
- prompt: Suno prompt field. Describe the sonic character, energy arc, and production quality. English. Target: YouTube Shorts (under 60 seconds) — short, high-impact, immediate hook.
- CRITICAL: style + prompt combined MUST be under 1000 characters total. Keep style ~200 chars and prompt ~700 chars max. Be dense and specific, not verbose.
- title_suggestion: Song title suggestion. English.
- bpm_suggestion: Genre-appropriate BPM (integer).
- exclude_styles: Suno "Exclude styles" field. Genres/styles to avoid. English. Empty string if none.
- vocal_gender: "Male" or "Female" only. If instrumental is better for this genre, set to null.
- lyrics_mode: "Manual" if you provide lyrics below, "Auto" if Suno should generate, "Instrumental" if no vocals.
- lyrics: Suno-format structured lyrics with section markers. Use markers like [Verse 1], [Verse 2], [Pre-Chorus], [Chorus], [Bridge], [Final Chorus], [Outro] etc. Each section should have 2-4 lines. Write lyrics in the language that best fits the genre and mood (Japanese for Japanese-influenced genres, Korean for K-pop, English for Western genres, etc.). null if instrumental is recommended. For genres like shranz, hard techno, ambient — almost always null.
- weirdness: Suno experimentalism 0-100. Match to genre character.
- style_influence: Suno style influence 0-100. Higher = more faithful to prompt.
- substyle: The substyle name used (only for schranz variants). null for other genres.

# Style Writing Rules
1. Name SPECIFIC instruments and sound sources, not generic categories:
   BAD: "electronic drums, synthesizer"
   GOOD: "TR-909 kick, razor-sharp hi-hats, TB-303 acid bassline, bitcrushed percussion"
2. Include production technique descriptors:
   "sidechain compression", "tape saturation", "heavy distortion", "vinyl warmth", "lo-fi bitcrushing"
3. Include texture/space descriptors:
   "cavernous reverb", "dry and punchy", "wide stereo field", "gritty and raw"
4. NEVER mention artist names or song titles.
5. For Shorts: emphasize immediate impact — no long intros. Hook within first 5 seconds.
6. For schranz variants: a specific substyle will be provided below. Follow its sonic identity EXACTLY. Do NOT mix in elements from other substyles.

# Genre Production Knowledge

{shranz_section}

{genre_sections}

Respond ONLY with JSON:
{{
  "style": "genre, specific instruments, production techniques, mood",
  "prompt": "Detailed sonic description with energy arc...",
  "title_suggestion": "Song Title",
  "bpm_suggestion": 120,
  "exclude_styles": "genres to avoid",
  "vocal_gender": "Male or Female or null",
  "lyrics_mode": "Manual or Auto or Instrumental",
  "lyrics": "[Verse 1]\\nLine 1\\nLine 2\\n\\n[Chorus]\\nHook line 1\\nHook line 2\\n... or null if instrumental",
  "weirdness": 43,
  "style_influence": 55,
  "substyle": "substyle_name or null"
}}"""

DEFAULT_SHRANZ_SECTION = """## Shranz / Schranz / Hard Techno
- BPM: 150-165
- Core: heavily distorted kick drums, razor-sharp hi-hats, atonal synth stabs, noisy sweeps
- Exclude: pop, melodic, soft, ambient, acoustic
- Weirdness: 60-80 / Style influence: 70-85"""


class SunoPromptGenerator:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        projects_dir: Optional[str] = None,
        model: str = "sonnet",
    ):
        self.llm = llm or default_client()
        self.projects_dir = projects_dir
        self.model = model

    def _build_system_prompt(
        self,
        genre: str,
        substyle_name: str | None = None,
    ) -> tuple[str, str | None]:
        """시스템 프롬프트를 빌드한다. shranz 계열이면 서브스타일을 주입.

        Returns:
            (system_prompt, selected_substyle_name)
        """
        genre_sections = _load_genre_sections()
        if not is_shranz_genre(genre):
            return SYSTEM_PROMPT.format(shranz_section=DEFAULT_SHRANZ_SECTION, genre_sections=genre_sections), None

        exclude_names = []
        if self.projects_dir:
            exclude_names = get_used_substyles_from_projects(self.projects_dir)

        # Load substyle performance stats for weighted selection
        substyle_stats = _load_substyle_stats(self.projects_dir) if self.projects_dir else None

        substyle = pick_substyle(
            exclude_names=exclude_names,
            preferred_name=substyle_name,
            substyle_stats=substyle_stats,
        )
        section = build_substyle_prompt_section(substyle)
        return SYSTEM_PROMPT.format(shranz_section=section, genre_sections=genre_sections), substyle.name

    def generate(
        self,
        genre: str,
        bpm: int | None = None,
        mood: str | None = None,
        instruments: list[str] | None = None,
        lyrics: str | None = None,
        instrumental: bool = False,
        substyle: str | None = None,
    ) -> dict:
        system_prompt, selected_substyle = self._build_system_prompt(genre, substyle)

        user_prompt = f"장르: {genre}\n"

        if bpm:
            user_prompt += f"BPM: {bpm}\n"
        if mood:
            user_prompt += f"분위기: {mood}\n"
        if instruments:
            user_prompt += f"악기: {', '.join(instruments)}\n"
        if instrumental:
            user_prompt += "Instrumental (가사 없음)\n"
        if lyrics:
            user_prompt += f"\n가사:\n{lyrics}\n"
        if selected_substyle:
            user_prompt += f"\n서브스타일: {selected_substyle} — 이 서브스타일의 고유한 사운드를 정확히 반영해주세요.\n"

        user_prompt += "\nYouTube Shorts용 60초 이내 곡에 맞는 Suno 프롬프트를 생성해주세요."

        response_text = self.llm.complete(
            system=wrap_system_prompt(system_prompt),
            user=user_prompt,
            model=self.model,
            max_tokens=2048,
        )
        result = parse_claude_json(response_text)

        if selected_substyle and not result.get("substyle"):
            result["substyle"] = selected_substyle

        return result
