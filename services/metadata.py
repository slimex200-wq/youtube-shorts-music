import json
import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 YouTube Shorts 음악 채널 SEO 전문가입니다.
장르와 곡 정보를 바탕으로 YouTube Shorts에 최적화된 메타데이터를 생성합니다.

요구사항:
- title: 곡 제목 + 분위기 이모지 + #Shorts 포함. 최대 100자.
- description: 곡 설명 1~2줄 + 해시태그. 간결하게.
- tags: 장르 관련 + 분위기 관련 + "Shorts" 포함. 10~15개.

음악 Shorts 제목 패턴:
- "곡제목 🎵 장르 키워드 #Shorts"
- "곡제목 | mood keyword #Shorts"

반드시 JSON 포맷으로만 응답하세요:
{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."]
}"""


class MetadataGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        genre: str,
        title_suggestion: str = "",
        lyrics: str = None,
        instrumental: bool = False,
    ) -> dict:
        user_prompt = f"장르: {genre}\n"
        if title_suggestion:
            user_prompt += f"곡 제목: {title_suggestion}\n"
        if instrumental:
            user_prompt += "Instrumental (가사 없음)\n"
        if lyrics:
            user_prompt += f"가사 발췌: {lyrics[:200]}\n"

        user_prompt += "\nYouTube Shorts 음악 채널용 메타데이터를 생성해주세요."

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

        metadata = json.loads(response_text.strip())

        if "Shorts" not in metadata.get("tags", []):
            metadata.setdefault("tags", []).append("Shorts")

        return metadata
