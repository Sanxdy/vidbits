"""
Integration test — run on demand only.

Requires:
  - tests/assets/dummy.mp4 (2-second, 1920x1080, H.264 + AAC)
  - ffmpeg installed

Verifies: output exists, 9:16 aspect ratio, has audio stream.
"""

import os
import subprocess
import tempfile

import pytest

from app.models.segment import WordTimestamp
from app.pipelines.edit import render_clip

pytestmark = pytest.mark.skipif(
    not os.path.isfile("tests/assets/dummy.mp4"),
    reason="dummy.mp4 not found in tests/assets/",
)


@pytest.mark.asyncio
async def test_full_render_pipeline():
    input_path = "tests/assets/dummy.mp4"

    words = [
        WordTimestamp(word="This", start=0.0, end=0.3),
        WordTimestamp(word="is", start=0.3, end=0.5),
        WordTimestamp(word="a", start=0.5, end=0.7),
        WordTimestamp(word="test", start=0.7, end=1.0),
        WordTimestamp(word="clip", start=1.0, end=1.3),
    ]

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        output_path = f.name

    try:
        result = await render_clip(
            input_path=input_path,
            output_path=output_path,
            start_time=0.0,
            end_time=2.0,
            words=words,
        )

        assert os.path.isfile(result)
        assert os.path.getsize(result) > 0

        # Check 9:16 with ffprobe
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                output_path,
            ],
            capture_output=True, text=True,
        )
        assert probe.returncode == 0
        parts = probe.stdout.strip().split(",")
        assert len(parts) == 2
        width, height = int(parts[0]), int(parts[1])
        assert abs(width / height - 9 / 16) < 0.01

        # Check audio stream exists
        audio_check = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                output_path,
            ],
            capture_output=True, text=True,
        )
        assert audio_check.returncode == 0
        assert "audio" in audio_check.stdout

    finally:
        os.unlink(output_path)
