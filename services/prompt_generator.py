import logging
from typing import Optional

from services.llm import LLMClient, default_client
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
Map the genre to a coherent visual world. Each genre has MULTIPLE environment/subject options — pick DIFFERENT ones per scene. Never reuse the same setting in consecutive scenes.

## lo-fi hip hop
Environments: cozy bedroom with desk lamp, rooftop at dusk overlooking city, rainy cafe window booth, vinyl record shop interior, quiet library corner, train window at night, balcony with hanging plants
Textures: warm analog film grain, soft bokeh, VHS tape artifacts, dusty vinyl crackle overlay, watercolor wash edges
Palette: warm amber, muted terracotta, soft cream, faded denim blue, sage green
Lighting: warm tungsten desk lamp, golden hour diffused, neon sign glow through rain, soft overcast window light

## dark trap
Environments: abandoned parking garage at 3am, rain-slicked alley with flickering neon, empty rooftop helipad, fog-filled underpass, luxury car interior at night, dimly lit recording studio, desolate highway overpass
Textures: wet reflections on asphalt, chrome and glass surfaces, smoke trails, shattered glass, metallic paint drips
Palette: deep black, teal, burnt orange, neon violet, blood red accents
Lighting: single harsh streetlamp, neon sign reflection pools, headlight beams through fog, underlighting from phone screen

## acid techno
Environments: underground warehouse rave, fluorescent-lit subway tunnel, abandoned swimming pool with projection mapping, server room corridors, chemical plant at night, concrete skatepark with UV lights
Textures: CRT scanlines, data moshing glitch, phosphor green glow, acid-etched metal, VHS tracking errors, liquid crystal patterns
Palette: toxic green, electric cyan, phosphor white, deep purple, acid yellow
Lighting: UV blacklight, strobe freeze-frame, laser grid projections, oscillating LED tubes, emergency exit red

## R&B / soul
Environments: candlelit bedroom with silk curtains, rooftop pool at golden hour, vintage recording studio with wood panels, slow-dance ballroom, bathwater with rose petals, sunset beach boardwalk
Textures: silk and satin fabric folds, condensation on glass, warm skin tones, gold jewelry glint, analog film halation
Palette: warm gold, deep burgundy, chocolate brown, blush pink, honey amber
Lighting: candlelight flicker, golden hour backlight through curtains, warm spotlight with lens diffusion, fireplace glow

## k-pop
Environments: glossy white photo studio, candy-colored set pieces, holographic stage with LED floor, retro diner in pastel, rooftop garden with neon art installations, mirror room infinity reflections
Textures: clean sharp edges, metallic chrome accents, holographic foil, confetti freeze-frame, bubble reflections
Palette: hot pink, electric blue, mint green, sunflower yellow, pure white, lavender
Lighting: ring light beauty, multi-color LED wash, clean studio flash, RGB strip accents, backlit silhouette

## ambient / chill
Environments: fog-blanketed mountain lake, aurora borealis over snow field, underwater kelp forest, cloud layer from above, moss-covered forest floor, desert dunes at blue hour, glacial ice cave
Textures: soft focus lens blur, mist diffusion, light leak film artifacts, watercolor dissolved edges, frost crystal macro
Palette: slate blue, sage green, dusty rose, pearl grey, ice white, lavender mist
Lighting: diffused overcast, bioluminescent glow, twilight blue hour, soft volumetric god rays, moonlight reflection on water

## rock / punk
Environments: dive bar stage with duct-taped mic, garage rehearsal space, mosh pit from above, graffiti alley at night, tour van interior, rooftop with city skyline, record store basement show
Textures: high ISO noise grain, torn poster layers, scratched leather, amp distortion visualization, sticker-bombed surface, cigarette smoke
Palette: black, fire engine red, safety yellow, bruise purple, raw concrete grey
Lighting: harsh on-camera flash, single bare bulb, stage par can with haze, flickering fluorescent tube, match flame in dark

## edm
Environments: massive festival stage with CO2 cannons, beach club at sunset, neon tunnel DJ set, pool party aerial, desert rave at dawn, ice hotel DJ booth, rooftop club overlooking skyline
Textures: confetti and glitter freeze-frame, laser beam trails, LED panel pixel grids, water splash freeze, pyrotechnic spark trails
Palette: electric blue, magenta, lime green, pure white, UV purple
Lighting: moving head beam arrays, CO2 cannon backlight, sunrise golden rim, laser fan patterns, LED wristband crowd glow

## shranz / schranz / hard techno → See "Schranz Visual Vocabulary" section below for substyle-specific visuals.

Use these as starting points; adapt and blend based on the specific mood and keywords provided. For genres not listed, derive a visual vocabulary from the genre's cultural context and sonic character.

# Schranz Visual Vocabulary (by substyle)
Each schranz substyle has a DISTINCT visual world. Do NOT default to "warehouse + lasers" for everything.

- classic_german → raw concrete bunker, single overhead industrial lamp, claustrophobic corridor, grey-on-grey monotone, analog CCTV grain, cold fluorescent flicker, Berlin U-Bahn tunnel aesthetic
- emo_schranz → neon-lit rain on glass, emotional bokeh city lights, silhouette against LED wall, split-toning teal/magenta, cinematic anamorphic lens flare, moody portrait lighting
- industrial_schranz → rusted steel mill, molten metal pour, slag heap at night, furnace glow orange-black, crane silhouettes, iron oxide textures, thermal camera palette
- acid_schranz → liquid mercury surfaces, UV blacklight reactive paint splatter, chemical iridescence, microscopic crystal structures, psychedelic color inversion, oil-on-water rainbow
- hardgroove → vinyl record macro, DJ booth low-angle, turntable needle close-up, warm amber club lighting, sweat on skin, handheld camera shake, intimate dancefloor energy
- deep_hardtechno → deep underground cave system, bioluminescent fungi, subterranean lake reflection, pitch darkness with single light source, mist rising from below, cavernous echo visual
- peak_time → massive festival main stage, CO2 cannon blast, confetti explosion, stadium laser array, crowd hands from stage POV, pyrotechnic sparks, wide-angle lens distortion
- tekk → abandoned squat party, DIY sound system stacks, spray-painted walls, handheld flashlight in dark, raw concrete with graffiti, chaotic energy, fisheye lens
- trancecore_hybrid → 90s rave nostalgia, smiley face motifs, VHS recording artifacts, warehouse with colored gels, euphoric crowd aerial shot, retro CRT monitor glow, candy raver aesthetic
- noise_experimental → abstract data visualization, oscilloscope waveforms, circuit board macro, white noise static pattern, scientific lab equipment, electron microscope textures
- latin_schranz → fire dancers at night, tribal masks with LED eyes, desert rave at sunset, bonfire sparks rising, earth-tone body paint, drum circle silhouettes, ritual geometry
- ebm_schranz → brutalist architecture facades, marching formation shadows, monochrome high contrast, leather texture macro, cold steel and glass, geometric repetition, surveillance aesthetic

Pick visuals that match the substyle indicated in the suno_prompt. If no substyle is given, vary across the full vocabulary — do NOT repeat the same environment across scenes.

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
    def __init__(self, llm: Optional[LLMClient] = None, model: str = "sonnet"):
        self.llm = llm or default_client()
        self.model = model

    def generate(
        self,
        genre: str,
        scenes: list[dict],
        lyrics: Optional[str] = None,
        instrumental: bool = False,
        suno_prompt: Optional[dict] = None,
        style: Optional[str] = None,
    ) -> list[dict]:
        user_prompt = f"장르: {genre}\n"
        user_prompt += f"씬 수: {len(scenes)}\n\n"

        if style:
            user_prompt += f"아트 스타일: {style}\n모든 씬에 이 아트 스타일을 일관되게 적용하세요.\n\n"

        if suno_prompt:
            user_prompt += f"곡 분위기: {suno_prompt.get('prompt', '')}\n"
            if suno_prompt.get("substyle"):
                user_prompt += f"서브스타일: {suno_prompt['substyle']} — 이 서브스타일의 비주얼 보캐뷸러리를 사용하세요.\n"

        if instrumental:
            user_prompt += "Instrumental (가사 없음) — lyrics_line은 모두 null로.\n"
        elif lyrics:
            user_prompt += f"\n가사:\n{lyrics}\n\n가사를 씬에 자연스럽게 배분해주세요.\n"

        user_prompt += "\n씬 정보:\n"
        for scene in scenes:
            duration = round(scene["end_sec"] - scene["start_sec"], 1)
            user_prompt += f"- 씬 {scene['id']}: {scene['start_sec']}초~{scene['end_sec']}초 ({duration}초, {scene['beat_count']}비트)\n"

        response_text = self.llm.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=self.model,
            max_tokens=4096,
        )
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
