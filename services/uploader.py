"""YouTube 업로드 — openclaw youtube_upload.py 기반"""

import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class YouTubeUploader:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token_upload.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path

    def _get_service(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"credentials.json이 필요합니다: {self.credentials_path}\n"
                        "Google Cloud Console > APIs & Services > Credentials에서 다운로드하세요."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "w") as f:
                f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def _build_body(self, title: str, description: str, tags: list[str], privacy: str) -> dict:
        return {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "10",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] = None,
        privacy: str = "private",
    ) -> dict:
        youtube = self._get_service()
        body = self._build_body(title, description, tags or [], privacy)

        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media,
        )

        logger.info("업로드 시작: %s", title)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info("진행률: %d%%", int(status.progress() * 100))

        video_id = response["id"]
        logger.info("업로드 완료: https://youtube.com/watch?v=%s", video_id)
        return response

    def post_comment(self, video_id: str, text: str) -> dict:
        """Post a comment on a video. Returns the comment resource."""
        youtube = self._get_service()
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text,
                    }
                }
            }
        }
        response = youtube.commentThreads().insert(
            part="snippet", body=body,
        ).execute()
        comment_id = response["id"]
        logger.info("댓글 게시 완료: %s on %s", comment_id, video_id)
        return response
