import json
import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 Suno AI 음악 생성 프롬프트 전문가입니다.
주어진 장르와 옵션에 맞는 Suno 호환 프롬프트를 생성합니다.

요구사항:
- style: Suno의 "Style of Music" 필드에 들어갈 값. 장르 + 악기 + 분위기를 콤마로 나열. 영어. 최대 200자.
- prompt: Suno의 프롬프트 필드. 곡의 분위기와 스토리를 설명. 영어. YouTube Shorts(60초 이내)에 적합한 짧고 임팩트 있는 곡.
- title_suggestion: 곡 제목 제안. 영어.
- bpm_suggestion: 장르에 적합한 BPM 제안 (숫자).

Suno 스타일 작성 팁:
- 구체적 악기명 포함 (예: "acoustic guitar", "808 bass", "vinyl crackle")
- 분위기 형용사 포함 (예: "melancholic", "energetic", "dreamy")
- 장르 혼합 가능 (예: "lo-fi hip hop, jazz fusion")
- 피해야 할 것: 아티스트 이름, 곡 이름 직접 언급

반드시 아래 JSON 포맷으로만 응답하세요:
{
  "style": "genre, instruments, mood descriptors",
  "prompt": "Detailed description of the song...",
  "title_suggestion": "Song Title",
  "bpm_suggestion": 120
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

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
