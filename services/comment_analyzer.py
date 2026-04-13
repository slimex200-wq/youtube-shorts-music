"""YouTube comment sentiment analysis per substyle."""
import json
import logging
from typing import Optional

from googleapiclient.discovery import build

from config import get_setting
from services.llm import LLMClient, default_client
from services.utils import parse_claude_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a YouTube comment analyst for a hard techno / schranz music channel.

Analyze the comments below and return a JSON object:
{
  "sentiment": "positive" | "mixed" | "negative",
  "top_themes": ["theme1", "theme2", "theme3"],
  "notable_quotes": ["quote1", "quote2"],
  "engagement_quality": "high" | "medium" | "low",
  "summary": "1-2 sentence summary of audience reaction"
}

Focus on what the audience likes/dislikes about the music, production quality, and energy.
Return ONLY the JSON object, no other text."""


def fetch_comments(video_id: str, max_results: int = 50, api_key: str = None) -> list[str]:
    """Fetch top-level comments for a video using YouTube Data API."""
    key = api_key or get_setting("YOUTUBE_API_KEY", "")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY not set")

    youtube = build("youtube", "v3", developerKey=key)
    comments = []
    page_token = None

    while len(comments) < max_results:
        try:
            resp = youtube.commentThreads().list(
                videoId=video_id,
                part="snippet",
                maxResults=min(50, max_results - len(comments)),
                order="relevance",
                pageToken=page_token,
            ).execute()
        except Exception as e:
            logger.warning("Comment fetch failed for %s: %s", video_id, e)
            break

        for item in resp.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return comments


def analyze_comments(
    comments: list[str],
    genre: str = "shranz",
    substyle: str = None,
    llm: Optional[LLMClient] = None,
) -> dict:
    """Analyze comment sentiment using LLM."""
    if not comments:
        return {
            "sentiment": "unknown",
            "top_themes": [],
            "notable_quotes": [],
            "engagement_quality": "low",
            "summary": "No comments to analyze.",
        }

    client = llm or default_client()
    comments_text = "\n".join(f"- {c}" for c in comments[:30])
    context = f"Genre: {genre}"
    if substyle:
        context += f", Substyle: {substyle}"

    user_prompt = f"""{context}
Video has {len(comments)} comments. Here are the top ones:

{comments_text}"""

    raw = client.complete(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="haiku",
        max_tokens=512,
    )
    return parse_claude_json(raw)
