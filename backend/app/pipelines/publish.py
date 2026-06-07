import logging
import os

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload_shorts(
    video_path: str,
    title: str,
    description: str,
    token_path: str,
    privacy_status: str = "private",
) -> str:
    """Upload a video to YouTube as a Short.

    Args:
        video_path: Path to the rendered MP4 file.
        title: Video title (must contain #Shorts).
        description: Video description.
        token_path: Path to stored OAuth token JSON.
        privacy_status: 'private', 'unlisted', or 'public'.

    Returns:
        YouTube video ID.

    Raises:
        FileNotFoundError: If video or token file missing.
        RuntimeError: If upload fails.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.isfile(token_path):
        raise FileNotFoundError(f"OAuth token not found: {token_path}")

    if "#Shorts" not in title:
        title = title + " #Shorts"

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    try:
        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = request.execute()
        video_id = response["id"]
        logger.info("Uploaded Short: https://youtu.be/%s", video_id)
        return video_id

    except RefreshError as e:
        logger.error("OAuth token expired: %s", e)
        raise RuntimeError("YouTube OAuth token expired. Re-authenticate.") from e
    except Exception as e:
        logger.error("YouTube upload failed: %s", e)
        raise RuntimeError(f"YouTube upload failed: {e}") from e
