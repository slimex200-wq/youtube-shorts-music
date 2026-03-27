import logging

import anthropic

from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert visual prompt engineer for AI-generated music videos.
Given a music genre, mood, and scene breakdown, you produce high-quality prompts for YouTube Shorts (9:16 vertical).

# Output Format
For each scene, return image_prompt and video_prompt in a JSON array.
- image_prompt: for Midjourney / DALL-E / Flux. English only. MUST end with ", 9:16 vertical".
- video_prompt: for Runway / Kling. English only. Include camera movement + duration. MUST end with ", 9:16 vertical, N seconds".
- lyrics_line: matched lyric line (Korean OK) or null if instrumental.

# Prompt Structure (image_prompt)
Build each prompt in this order:
1. Subject & scene — what is depicted, specific and concrete (not vague)
2. Art style / medium — e.g. "digital illustration", "3D render", "analog film photography", "oil painting"
3. Lighting — e.g. "volumetric fog with cyan rim light", "golden hour backlight", "harsh top-down fluorescent"
4. Color palette — name 2-4 specific colors, e.g. "deep indigo, electric magenta, muted gold"
5. Composition — camera angle + framing, e.g. "extreme close-up", "low-angle wide shot", "bird's-eye view"
6. Detail / texture — e.g. "film grain", "bokeh background", "wet reflections on asphalt"
7. Quality tokens — append: "highly detailed, cinematic composition, professional color grading"

# Prompt Structure (video_prompt)
Same as image_prompt, plus:
- Camera movement: dolly in, slow pan left, orbit, static, pull-back reveal, handheld shake, etc.
- Pacing hint: "slow and dreamy" vs "rapid cuts" to match BPM.

# Genre → Visual Vocabulary
Map the genre to a coherent visual world. Examples:
- lo-fi hip hop → cozy room interiors, rain on window, warm analog tones, soft bokeh, Studio Ghibli influence
- dark trap → deserted urban streets, neon signs, wet asphalt, high contrast, teal-and-orange split toning
- acid techno → underground warehouse, laser grids, CRT green phosphor, industrial textures, glitch artifacts
- R&B / soul → golden hour skin tones, silk fabrics, candlelight, shallow depth of field, intimate framing
- k-pop → hyper-saturated candy colors, clean studio lighting, bold graphic shapes, fashion editorial
- ambient / chill → vast landscapes, fog, aerial drone shots, muted pastels, slow dissolve transitions
- rock / punk → gritty film grain, high ISO noise, stage smoke, harsh flash, dutch angle
- shranz / schranz / hard techno → underground warehouse, industrial concrete, laser grids, CRT phosphor green, distorted glitch textures, strobe flash, brutalist architecture
Use these as starting points; adapt and blend based on the specific mood and keywords provided.

# Art Style Override
If the user specifies an art style (e.g. "anime"), apply it consistently to ALL scenes:
- anime → Japanese anime illustration featuring a young female anime character (late teens/early 20s) as the central subject in EVERY scene. Character design: expressive large eyes, detailed hair with dynamic movement, stylish outfit that fits the genre mood (e.g. techwear/streetwear for techno, school uniform for chill, gothic for dark genres). The character interacts with or is immersed in the scene environment — NOT just standing still. Vary her pose and expression per scene (walking, looking over shoulder, headphones on, dancing, gazing at city lights, sitting contemplatively). Art style: cel-shaded with soft shading in the tradition of Makoto Shinkai, Violet Evergarden, and Chainsaw Man. Rich color palettes with dramatic lighting. Hand-painted background art with layered depth. Expressive atmospheric effects: god rays, floating particles, rain streaks, cherry blossom petals, lens flares. Film grain reminiscent of 35mm anime film stock. Avoid: western cartoon, 3D CGI, chibi/SD, static T-pose, overly sexualized poses
- cyberpunk → neon-drenched, rain-slicked streets, holographic UI overlays, chrome and glass, Blade Runner palette
- retro / vaporwave → pastel gradients, Roman busts, palm trees, VHS grain, 80s grid, sunset purple-pink
- watercolor → soft wet edges, paper texture, translucent color washes, minimal linework
The art style takes priority over genre defaults for rendering technique, but genre still guides subject matter and mood.

# Shot Variety Rules
Across the full set of scenes, you MUST vary:
- Scale: mix wide / medium / close-up / extreme close-up / macro
- Angle: mix eye-level / low-angle / high-angle / overhead / dutch tilt
- Movement: mix static / pan / dolly / orbit / handheld
Never repeat the same composition two scenes in a row.

# Visual Continuity
- Maintain a consistent color palette and art style across ALL scenes.
- Evolve intensity: start subtle → build energy toward the climax → resolve at the end.
- If there are lyrics, the visual should amplify the emotional arc of the words.

# Avoid
- Generic descriptions ("beautiful scene", "nice atmosphere")
- Cliches without specificity ("epic cinematic shot" alone is not enough)
- Text, watermarks, or UI elements in the image
- Overloaded prompts (max 80 words per prompt)
- Human faces in extreme close-up (AI artifacts)

Respond ONLY with a JSON array:
[
  {
    "id": 1,
    "image_prompt": "..., 9:16 vertical",
    "video_prompt": "..., 9:16 vertical, N seconds",
    "lyrics_line": "lyric line or null"
  }
]"""


class PromptGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        genre: str,
        scenes: list[dict],
        lyrics: str = None,
        instrumental: bool = False,
        suno_prompt: dict = None,
        style: str = None,
    ) -> list[dict]:
        user_prompt = f"장르: {genre}\n"
        user_prompt += f"씬 수: {len(scenes)}\n\n"

        if style:
            user_prompt += f"아트 스타일: {style}\n모든 씬에 이 아트 스타일을 일관되게 적용하세요.\n\n"

        if suno_prompt:
            user_prompt += f"곡 분위기: {suno_prompt.get('prompt', '')}\n"

        if instrumental:
            user_prompt += "Instrumental (가사 없음) — lyrics_line은 모두 null로.\n"
        elif lyrics:
            user_prompt += f"\n가사:\n{lyrics}\n\n가사를 씬에 자연스럽게 배분해주세요.\n"

        user_prompt += "\n씬 정보:\n"
        for scene in scenes:
            duration = round(scene["end_sec"] - scene["start_sec"], 1)
            user_prompt += f"- 씬 {scene['id']}: {scene['start_sec']}초~{scene['end_sec']}초 ({duration}초, {scene['beat_count']}비트)\n"

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        prompts = parse_claude_json(response_text)

        # 기존 씬 데이터에 프롬프트 머지
        prompt_map = {p["id"]: p for p in prompts}
        for scene in scenes:
            if scene["id"] in prompt_map:
                p = prompt_map[scene["id"]]
                scene["image_prompt"] = p.get("image_prompt")
                scene["video_prompt"] = p.get("video_prompt")
                scene["lyrics_line"] = p.get("lyrics_line")

        return scenes
