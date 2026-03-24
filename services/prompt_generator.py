import logging

import anthropic

from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 AI 영상 제작용 이미지/영상 프롬프트 전문가입니다.
음악 장르와 씬 정보를 바탕으로 YouTube Shorts(9:16 세로)에 사용할 비주얼 프롬프트를 생성합니다.

요구사항:
- 각 씬마다 image_prompt와 video_prompt를 생성
- image_prompt: AI 이미지 생성 도구용 (Midjourney/DALL-E 스타일). 영어. 반드시 "9:16 vertical" 포함.
- video_prompt: AI 영상 생성 도구용 (Runway/Kling 스타일). 영어. 카메라 무브먼트 포함. "9:16 vertical" + 대략적 초 단위 길이 포함.
- 장르 분위기에 맞는 비주얼 일관성 유지 (색감, 톤, 스타일)
- 가사가 있으면 lyrics_line에 해당 씬에 매칭되는 가사 라인 배분
- 가사가 없으면(instrumental) lyrics_line은 null

반드시 JSON 배열로만 응답하세요:
[
  {
    "id": 1,
    "image_prompt": "..., 9:16 vertical",
    "video_prompt": "..., 9:16 vertical, N seconds",
    "lyrics_line": "가사 라인 또는 null"
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
    ) -> list[dict]:
        user_prompt = f"장르: {genre}\n"
        user_prompt += f"씬 수: {len(scenes)}\n\n"

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
