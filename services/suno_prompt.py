import logging

import anthropic

from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert music producer and Suno AI prompt engineer.
Given a genre and options, generate a Suno-compatible prompt that produces professional-quality tracks.

# Output Fields
- style: Suno "Style of Music" field. Genre + specific instruments + production techniques + mood. English. Max 200 chars. Be SPECIFIC — name exact synths, drum machines, effects.
- prompt: Suno prompt field. Describe the sonic character, energy arc, and production quality. English. Target: YouTube Shorts (under 60 seconds) — short, high-impact, immediate hook.
- title_suggestion: Song title suggestion. English.
- bpm_suggestion: Genre-appropriate BPM (integer).
- exclude_styles: Suno "Exclude styles" field. Genres/styles to avoid. English. Empty string if none.
- vocal_gender: "Male" or "Female". null if instrumental.
- lyrics_mode: "Manual" if lyrics provided, else "Auto".
- weirdness: Suno experimentalism 0-100. Match to genre character.
- style_influence: Suno style influence 0-100. Higher = more faithful to prompt.

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

# Genre Production Knowledge

## Shranz / Schranz / Hard Techno
- BPM: 150-165
- Core: heavily distorted kick drums (THE defining element — battering ram punch), razor-sharp hi-hats in frantic patterns, atonal synth stabs, noisy sweeps
- Sound chain: heavy compression → saturation → bitcrushing for industrial grit
- Instruments: TR-909 kicks (distorted through multiple stages), TB-303 acid lines, metallic percussion, industrial noise layers
- Texture: "fried yet clean" — extreme processing on individual channels but clear mixdown. Gritty, dystopian, mechanical.
- Structure: relentless driving loop, minimal breakdowns, hypnotic repetition, builds intensity through texture not melody
- Exclude: pop, melodic, soft, ambient, acoustic
- Weirdness: 60-80 (experimental but structured)
- Style influence: 70-85 (strong genre identity)

## Lo-fi Hip Hop
- BPM: 70-90
- Core: dusty vinyl crackle, detuned piano/Rhodes, mellow jazz samples, tape hiss, relaxed boom-bap drums
- Instruments: Rhodes piano, jazz guitar, muted trumpet, SP-404 sampler character, vinyl noise
- Texture: warm, analog, imperfect, cozy
- Weirdness: 20-35 / Style influence: 55-70

## Dark Trap
- BPM: 130-150
- Core: 808 sub bass (distorted), rapid hi-hat rolls, dark minor-key melodies, spacey reverb pads
- Instruments: 808 bass, TR-808 hi-hats, dark synth leads, ambient pads, pitched vocal chops
- Texture: heavy low end, spacious highs, aggressive yet atmospheric

## Acid Techno
- BPM: 135-150
- Core: TB-303 squelching basslines (THE signature), 909 drums, resonance sweeps, hypnotic repetition
- Instruments: Roland TB-303, TR-909, analog synths, acid resonance filters
- Texture: wet, squelchy, psychedelic, relentless

## K-Pop
- BPM: 100-130
- Core: polished production, layered harmonies, genre-blending (EDM drops + R&B bridges), catchy hooks
- Instruments: layered synths, clean drums, vocal processing, bass drops
- Texture: hyper-produced, bright, punchy, dynamic

## Ambient / Chill
- BPM: 60-90
- Core: evolving pad textures, granular synthesis, field recordings, slow harmonic movement
- Instruments: granular synths, reverb-drenched piano, nature samples, tape loops
- Texture: vast, spacious, meditative, ethereal

## R&B / Soul
- BPM: 65-100
- Core: smooth bass, lush chord voicings, intimate vocal presence, warm production
- Instruments: Fender Rhodes, Moog bass, fingerpicked guitar, live drums with swing
- Texture: warm, silky, analog saturation, intimate

Respond ONLY with JSON:
{
  "style": "genre, specific instruments, production techniques, mood",
  "prompt": "Detailed sonic description with energy arc...",
  "title_suggestion": "Song Title",
  "bpm_suggestion": 120,
  "exclude_styles": "genres to avoid",
  "vocal_gender": "Male",
  "lyrics_mode": "Auto",
  "weirdness": 43,
  "style_influence": 55
}"""


class SunoPromptGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        genre: str,
        bpm: int = None,
        mood: str = None,
        instruments: list[str] = None,
        lyrics: str = None,
        instrumental: bool = False,
    ) -> dict:
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

        user_prompt += "\nYouTube Shorts용 60초 이내 곡에 맞는 Suno 프롬프트를 생성해주세요."

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        return parse_claude_json(response_text)
