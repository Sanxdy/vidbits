import os
import tempfile

from app.models.segment import WordTimestamp
from app.subtitle.ass_generator import generate_ass


def test_word_timestamps_to_ass():
    words = [
        WordTimestamp(word="Hello", start=0.0, end=0.3),
        WordTimestamp(word="world", start=0.4, end=0.8),
        WordTimestamp(word="test", start=0.9, end=1.2),
    ]
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as f:
        tmp_path = f.name

    try:
        generate_ass(words, tmp_path)
        with open(tmp_path) as f:
            content = f.read()

        assert "[Script Info]" in content
        assert "Style: Highlighted" in content
        assert "Style: Dimmed" in content

        assert "Hello" in content
        assert "world" in content
        assert "test" in content

        for line in content.splitlines():
            if line.startswith("Dialogue:"):
                parts = line.split(",")
                assert len(parts) >= 10
                start = parts[1].strip()
                end = parts[2].strip()
                assert ":" in start
                assert ":" in end
    finally:
        os.unlink(tmp_path)


def test_empty_words():
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as f:
        tmp_path = f.name

    try:
        generate_ass([], tmp_path)
        with open(tmp_path) as f:
            content = f.read()

        assert "[Script Info]" in content
        lines = content.splitlines()
        dialogue_lines = [line for line in lines if line.startswith("Dialogue:")]
        assert len(dialogue_lines) == 0
    finally:
        os.unlink(tmp_path)


def test_overlapping_timestamps():
    words = [
        WordTimestamp(word="First", start=0.0, end=0.5),
        WordTimestamp(word="Second", start=0.3, end=0.8),
        WordTimestamp(word="Third", start=0.7, end=1.0),
    ]
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as f:
        tmp_path = f.name

    try:
        generate_ass(words, tmp_path)
        with open(tmp_path) as f:
            content = f.read()

        assert "First" in content
        assert "Second" in content
        assert "Third" in content
        assert content.count("Dialogue:") == 6
    finally:
        os.unlink(tmp_path)
