import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


async def download_video(url: str, job_id: int) -> str:
    output_dir = Path(f"data/raw/{job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_template,
        "--print", "filename",
        url,
    ]

    logger.info("Downloading %s to %s", url, output_dir)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error("yt-dlp failed: %s", error_msg)
        raise RuntimeError(f"Download failed: {error_msg}")

    file_path = stdout.decode().strip()
    if not file_path or not os.path.isfile(file_path):
        raise FileNotFoundError(f"yt-dlp completed but file not found: {file_path}")

    logger.info("Downloaded to %s", file_path)
    return file_path
