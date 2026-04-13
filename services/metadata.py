import logging
from typing import Optional

from services.kb import wrap_system_prompt
from services.llm import LLMClient, default_client
from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 YouTube Shorts 음악 채널 SEO 전문가입니다.
장르와 곡 정보를 바탕으로 YouTube Shorts에 최적화된 메타데이터를 생성합니다.

요구사항:
- title: 곡 제목 + 분위기 이모지 + #Shorts 포함. 최대 100자.
- description: 곡 설명 1~2줄 + 해시태그. 간결하게.
- tags: 장르 관련 + 분위기 관련 + "Shorts" 포함. 10~15개.
- first_comment: 운영자가 고정으로 거는 첫 댓글. 아래 포맷을 정확히 지킬 것.
  * 줄1: 분위기 이모지 + 곡 소개 1문장
  * 줄2: 청자에게 건네는 감정/분위기 묘사 1문장
  * 줄3: LIKE/SUBSCRIBE 유도 1문장
  * 빈 줄 1개 (\n\n)
  * 마지막 줄: 해시태그 5~7개를 공백으로 구분해서 한 줄
  총 3줄 본문 + 빈 줄 1개 + 해시태그 1줄 = 5줄. 본문 줄 사이에는 절대 빈 줄 넣지 말 것.
  최대 500자. 곡 언어(영어면 영어, 한국어면 한국어)에 맞춰 작성.
  예시:
  🔥 MACHINE PULSE is here to crush your speakers! This EBM-Schranz fusion brings that raw industrial energy we all crave.
  Feel the machine's heartbeat pounding through your veins! 🤖⚡
  Smash that LIKE if this hits different and SUBSCRIBE for more underground bangers! 🔥

  #Schranz #EBM #Industrial #MachinePulse #UndergroundVibes

음악 Shorts 제목 패턴:
- "곡제목 🎵 장르 키워드 #Shorts"
- "곡제목 | mood keyword #Shorts"

반드시 JSON 포맷으로만 응답하세요:
{
  "title": "...",
  "description": "...",
  "tags": ["...", "..."],
  "first_comment": "..."
}"""


class MetadataGenerator:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        model: str = "haiku",
    ):
        self.llm = llm or default_client()
        self.model = model

    def generate(
        self,
        genre: str,
        title_suggestion: str = "",
        lyrics: Optional[str] = None,
        instrumental: bool = False,
        substyle: Optional[str] = None,
    ) -> dict:
        user_prompt = f"장르: {genre}\n"
        if substyle:
            user_prompt += f"서브스타일: {substyle}\n"
        if title_suggestion:
            user_prompt += f"곡 제목: {title_suggestion}\n"
        if instrumental:
            user_prompt += "Instrumental (가사 없음)\n"
        if lyrics:
            user_prompt += f"가사 발췌: {lyrics[:200]}\n"

        user_prompt += "\nYouTube Shorts 음악 채널용 메타데이터를 생성해주세요."

        response_text = self.llm.complete(
            system=wrap_system_prompt(SYSTEM_PROMPT),
            user=user_prompt,
            model=self.model,
            max_tokens=2048,
        )

        metadata = parse_claude_json(response_text)

        if "Shorts" not in metadata.get("tags", []):
            metadata.setdefault("tags", []).append("Shorts")

        return metadata
