"""YouTube channel sync — pull video metadata + thumbnails into the library.

Uses YouTube Data API v3 with an API key (read-only, no OAuth).
"""
import logging
import os
import urllib.request
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build

from config import PROJECTS_DIR
from models.project import Project

logger = logging.getLogger(__name__)

CHANNEL_HANDLE = "@Eisenherzyy"


def _get_service(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def _resolve_channel_id(youtube, handle: str) -> Optional[str]:
    resp = youtube.channels().list(forHandle=handle.lstrip("@"), part="id").execute()
    items = resp.get("items", [])
    if not items:
        resp = youtube.search().list(q=handle, type="channel", part="id", maxResults=1).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]["channelId"]
        return None
    return items[0]["id"]


def _get_uploads_playlist(youtube, channel_id: str) -> Optional[str]:
    resp = youtube.channels().list(id=channel_id, part="contentDetails").execute()
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _list_playlist_videos(youtube, playlist_id: str, max_results: int = 200) -> list[str]:
    """Return list of video IDs from a playlist."""
    video_ids = []
    page_token = None
    per_page = min(max_results, 50)

    while len(video_ids) < max_results:
        resp = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="contentDetails",
            maxResults=per_page,
            pageToken=page_token,
        ).execute()

        for item in resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:max_results]


def _get_video_details(youtube, video_ids: list[str]) -> list[dict]:
    """Batch fetch video snippet + statistics + contentDetails."""
    results = []
    # API allows max 50 IDs per call
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        resp = youtube.videos().list(
            id=",".join(chunk),
            part="snippet,statistics,contentDetails",
        ).execute()
        results.extend(resp.get("items", []))
    return results


def _parse_iso_duration(iso: str) -> float:
    """Parse ISO 8601 duration (PT1M30S) to seconds."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0.0
    hours = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    return hours * 3600 + mins * 60 + secs


def _detect_aspect_ratio(video: dict) -> str:
    """Determine 9:16 (Shorts) vs 16:9 (Video) from YouTube data.

    Heuristic: duration ≤ 60s AND title/tags contain #Shorts → 9:16
    Otherwise → 16:9
    """
    cd = video.get("contentDetails", {})
    duration = _parse_iso_duration(cd.get("duration", ""))

    snippet = video.get("snippet", {})
    title = snippet.get("title", "")
    tags = snippet.get("tags", [])

    has_shorts_tag = (
        "#shorts" in title.lower()
        or "shorts" in title.lower()
        or any("shorts" in t.lower() for t in tags)
    )

    if duration <= 75:
        return "9:16"
    return "16:9"


def _download_thumbnail(url: str, dest: Path) -> bool:
    """Download thumbnail image to dest. Returns True on success."""
    try:
        urllib.request.urlretrieve(url, str(dest))
        return True
    except Exception as e:
        logger.warning("Thumbnail download failed: %s — %s", url, e)
        return False


def _find_existing_by_video_id(video_id: str, base_dir: Path = None) -> Optional[Project]:
    """Find a project that was synced from this video."""
    base = base_dir or PROJECTS_DIR
    for p in Project.list_all(base_dir=base):
        if p.youtube_video_id == video_id:
            return p
    return None


def _extract_genre_from_tags(tags: list[str]) -> str:
    """Best-effort genre extraction from YouTube tags."""
    genre_keywords = [
        "shranz", "schranz", "hard techno", "techno", "dark techno",
        "industrial", "acid techno", "edm", "lo-fi", "lofi",
        "dark trap", "trap", "ambient", "k-pop", "r&b",
    ]
    tags_lower = [t.lower() for t in tags]
    for keyword in genre_keywords:
        for tag in tags_lower:
            if keyword in tag:
                return keyword
    return tags_lower[0] if tags_lower else "shranz"


def sync_channel(
    api_key: str = None,
    handle: str = CHANNEL_HANDLE,
    max_videos: int = 200,
    base_dir: Path = None,
) -> dict:
    """Sync YouTube channel videos into the project library.

    Returns {"synced": int, "updated": int, "skipped": int, "errors": [str]}
    """
    key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY not set")

    base = base_dir or PROJECTS_DIR
    youtube = _get_service(key)

    # Resolve channel
    channel_id = _resolve_channel_id(youtube, handle)
    if not channel_id:
        raise RuntimeError(f"Channel not found: {handle}")

    uploads_playlist = _get_uploads_playlist(youtube, channel_id)
    if not uploads_playlist:
        raise RuntimeError(f"Uploads playlist not found for channel {channel_id}")

    # List all video IDs
    video_ids = _list_playlist_videos(youtube, uploads_playlist, max_results=max_videos)
    logger.info("Found %d videos on %s", len(video_ids), handle)

    # Fetch details in batches
    videos = _get_video_details(youtube, video_ids)

    result = {"synced": 0, "updated": 0, "skipped": 0, "errors": []}

    for v in videos:
        vid = v["id"]
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})

        try:
            existing = _find_existing_by_video_id(vid, base_dir=base)

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            tags = snippet.get("tags", [])
            published_at = snippet.get("publishedAt", "")

            # Pick best thumbnail
            thumbs = snippet.get("thumbnails", {})
            thumb_url = (
                (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {})
                .get("url", "")
            )

            yt_stats = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            }

            aspect_ratio = _detect_aspect_ratio(v)
            cd = v.get("contentDetails", {})
            yt_duration = _parse_iso_duration(cd.get("duration", ""))

            if existing:
                # Update stats + metadata, don't overwrite manual edits
                existing.youtube_stats = yt_stats
                existing.thumbnail_url = thumb_url
                existing.aspect_ratio = aspect_ratio
                if yt_duration and not existing.duration_sec:
                    existing.duration_sec = yt_duration
                if published_at and existing.youtube_video_id:
                    existing.created_at = published_at
                if not existing.metadata:
                    existing.metadata = {
                        "title": title,
                        "description": description,
                        "tags": tags,
                    }
                existing.save()
                result["updated"] += 1
                continue

            # Create new project from YouTube data
            genre = _extract_genre_from_tags(tags)
            project = Project.create(genre=genre, base_dir=base, aspect_ratio=aspect_ratio)
            if published_at:
                project.created_at = published_at
            if yt_duration:
                project.duration_sec = yt_duration
            project.youtube_video_id = vid
            project.youtube_stats = yt_stats
            project.thumbnail_url = thumb_url
            project.title_lock = title
            project.metadata = {
                "title": title,
                "description": description,
                "tags": tags,
            }
            project.motif_tags = [t.lower().strip() for t in tags[:10] if t.strip()]

            # Download thumbnail as first visual ref
            if thumb_url:
                refs_dir = project.project_dir / "refs"
                refs_dir.mkdir(exist_ok=True)
                thumb_path = refs_dir / "youtube_thumb.jpg"
                if _download_thumbnail(thumb_url, thumb_path):
                    project.visual_refs = ["youtube_thumb.jpg"]

            project.update_status("created", step_name="create")
            project.save()
            result["synced"] += 1

        except Exception as e:
            logger.error("Error syncing video %s: %s", vid, e)
            result["errors"].append(f"{vid}: {str(e)}")

    return result
