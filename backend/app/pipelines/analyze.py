import json
import logging
import math

from app.models.segment import Segment, WordTimestamp

logger = logging.getLogger(__name__)


def load_transcription(path: str) -> list[Segment]:
    """Parse whisper_output.json into 5-second Segment windows."""
    with open(path) as f:
        data = json.load(f)

    segments = []
    for seg_data in data.get("segments", []):
        words = [
            WordTimestamp(word=w["word"], start=w["start"], end=w["end"])
            for w in seg_data.get("words", [])
        ]
        segments.append(Segment(
            start_time=seg_data["start"],
            end_time=seg_data["end"],
            transcript=seg_data["text"],
            words=words,
        ))

    windows = _sliding_windows(segments, window_duration=5.0)
    return windows


def _sliding_windows(
    segments: list[Segment], window_duration: float = 5.0
) -> list[Segment]:
    """Group raw Whisper segments into fixed-duration sliding windows."""
    if not segments:
        return []

    total_end = max(s.end_time for s in segments)
    windows: list[Segment] = []
    t = segments[0].start_time

    while t < total_end:
        window_end = min(t + window_duration, total_end)
        overlapping = [
            s for s in segments
            if s.start_time < window_end and s.end_time > t
        ]
        transcript = " ".join(s.transcript for s in overlapping)
        words = []
        for s in overlapping:
            for w in s.words:
                if w.start < window_end and w.end > t:
                    words.append(WordTimestamp(
                        word=w.word,
                        start=max(w.start - t, 0),
                        end=min(w.end, window_end) - t,
                    ))
        words.sort(key=lambda w: w.start)

        loudness = None
        wpm = None
        if words and window_end - t > 0:
            total_sec = window_end - t
            word_count = len(words)
            wpm = round(word_count / (total_sec / 60), 1)

        windows.append(Segment(
            start_time=t,
            end_time=window_end,
            transcript=transcript,
            words=words,
            loudness_db=loudness,
            speaking_rate_wpm=wpm,
        ))
        t += window_duration

    return windows


def compute_heuristic_scores(
    segments: list[Segment],
    w1: float = 0.25,
    w2: float = 0.20,
    w3: float = 0.25,
    w4: float = 0.20,
    w5: float = 0.10,
) -> list[Segment]:
    """Score segments using weighted heuristic, with Z-score normalization."""
    if not segments:
        return segments

    loudness_vals = [s.loudness_db or 0.0 for s in segments]
    wpm_vals = [s.speaking_rate_wpm or 0.0 for s in segments]
    sentiment_vals = [s.sentiment_score or 0.0 for s in segments]
    hook_vals = [s.hook_probability or 0.0 for s in segments]
    face_vals = [1.0 if s.face_present else 0.0 for s in segments]

    def zscore(vals: list[float]) -> list[float]:
        mu = sum(vals) / len(vals)
        std = (sum((x - mu) ** 2 for x in vals) / len(vals)) ** 0.5
        if std < 1e-9:
            return [0.0] * len(vals)
        return [(x - mu) / std for x in vals]

    scores = zip(
        zscore(loudness_vals),
        zscore(wpm_vals),
        zscore(sentiment_vals),
        zscore(hook_vals),
        zscore(face_vals),
    )

    for seg, (ln, rt, st, hk, fc) in zip(segments, scores):
        seg.score = w1 * ln + w2 * rt + w3 * st + w4 * hk + w5 * fc

    return segments


def find_best_window(
    segments: list[Segment],
    min_duration: float = 45.0,
    max_duration: float = 60.0,
    top_n: int = 5,
) -> list[tuple[int, int]]:
    """Find top-N contiguous windows with the highest cumulative score."""
    if not segments:
        return []

    segment_dur = max(s.end_time - s.start_time for s in segments) if segments else 5.0
    min_count = max(1, int(math.ceil(min_duration / segment_dur)))
    max_count = max(1, int(math.ceil(max_duration / segment_dur)))

    candidates = []
    for i in range(len(segments)):
        for j in range(i + min_count, min(i + max_count, len(segments)) + 1):
            total = sum(s.score for s in segments[i:j])
            candidates.append((total, i, j))

    candidates.sort(key=lambda x: -x[0])
    return [(i, j) for _, i, j in candidates[:top_n]]
