import asyncio
import logging
import os

from app.models.segment import WordTimestamp
from app.subtitle.ass_generator import generate_ass

logger = logging.getLogger(__name__)

# ffmpeg filtergraph:
#
#  [0:v] crop   ─►  ass   ─►  format  ─►  [v]
#        1080:1920    subtitles    yuv420p
#
#  [0:a] ─────────────────────────────────► [a]


def _build_filtergraph(
    ass_path: str,
    crop_x: int = 0,
    crop_y: int = 0,
    crop_w: int = 1080,
    crop_h: int = 1920,
) -> str:
    crop = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
    escaped = ass_path.replace(":", "\\:")
    return f"{crop},ass={escaped},format=yuv420p"


async def render_clip(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    words: list[WordTimestamp],
    input_w: int = 1920,
    input_h: int = 1080,
) -> str:
    """Render a vertical 9:16 clip with ASS karaoke captions.

    By default center-crops landscape (16:9) to vertical (9:16).
    Face-tracked crop coordinates can be passed via crop_x/crop_y.
    """
    duration = end_time - start_time

    ass_path = os.path.join(os.path.dirname(output_path), "subtitles.ass")
    generate_ass(words, ass_path, duration=duration)

    crop_h = input_w * 9 // 16
    crop_y = (input_h - crop_h) // 2

    filtergraph = _build_filtergraph(
        ass_path=ass_path,
        crop_w=input_w,
        crop_h=crop_h,
        crop_x=0,
        crop_y=crop_y,
    )

    cmd = [
        "ffmpeg",
        "-ss", str(start_time),
        "-i", input_path,
        "-t", str(duration),
        "-vf", filtergraph,
        "-c:a", "aac",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path,
        "-y",
    ]

    logger.info("Rendering clip: %s", " ".join(str(c) for c in cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        error = stderr.decode()
        logger.error("FFmpeg failed: %s", error)
        raise RuntimeError(f"FFmpeg error (code {proc.returncode}): {error}")

    logger.info("Rendered clip to %s", output_path)
    return output_path
