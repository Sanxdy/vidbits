import pytest


def _make_ffmpeg_cmd(
    start_time: float,
    duration: float,
    input_path: str,
    output_path: str,
    filtergraph: str,
) -> list[str]:
    if duration <= 0:
        raise ValueError("Duration must be positive")

    return [
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


def _crop_filter_string(frame_w: int, frame_h: int) -> str:
    target_ratio = 9 / 16
    input_ratio = frame_w / frame_h

    if abs(input_ratio - target_ratio) < 0.01:
        return f"crop={frame_w}:{frame_h}:0:0"

    crop_h = int(frame_w / target_ratio)
    if crop_h <= frame_h:
        crop_y = (frame_h - crop_h) // 2
        return f"crop={frame_w}:{crop_h}:0:{crop_y}"

    crop_w = int(frame_h * target_ratio)
    crop_x = (frame_w - crop_w) // 2
    return f"crop={crop_w}:{frame_h}:{crop_x}:0"


def test_crop_filter_string():
    result = _crop_filter_string(1920, 1080)
    assert result == "crop=607:1080:656:0"


def test_crop_filter_string_portrait():
    result = _crop_filter_string(1080, 1920)
    assert result == "crop=1080:1920:0:0"


def test_crop_filter_string_wide():
    result = _crop_filter_string(2560, 1440)
    assert result == "crop=810:1440:875:0"


def test_full_command_build():
    cmd = _make_ffmpeg_cmd(
        start_time=120.5,
        duration=45.0,
        input_path="/tmp/input.mp4",
        output_path="/tmp/output.mp4",
        filtergraph="crop=1080:1920:420:0,ass=sub.ass",
    )
    assert "-ss" in cmd
    assert "120.5" in cmd
    assert "-t" in cmd
    assert "45.0" in cmd
    assert "-vf" in cmd
    assert "-c:a" in cmd and "aac" in cmd
    assert "-c:v" in cmd and "libx264" in cmd
    assert "-preset" in cmd and "fast" in cmd
    assert "-pix_fmt" in cmd and "yuv420p" in cmd
    assert "-y" in cmd


def test_invalid_duration_raises():
    with pytest.raises(ValueError, match="Duration must be positive"):
        _make_ffmpeg_cmd(
            start_time=10, duration=0, input_path="a", output_path="b", filtergraph="c"
        )
