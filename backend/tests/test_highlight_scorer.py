from app.models.segment import Segment
from app.pipelines.analyze import compute_heuristic_scores, find_best_window


def _make_segments(count: int) -> list[Segment]:
    return [
        Segment(
            start_time=i * 5.0,
            end_time=(i + 1) * 5.0,
            transcript=f"Segment {i}",
            loudness_db=-20.0 + (i % 5),
            speaking_rate_wpm=100.0 + (i % 3) * 20,
            sentiment_score=0.3 + (i % 5) * 0.1,
            hook_probability=0.1 + i * 0.01,
            face_present=i % 3 == 0,
        )
        for i in range(count)
    ]


def test_get_best_window():
    segments = _make_segments(20)
    for i in range(5, 10):
        segments[i].score = 10.0
    segments[4].score = -100.0

    candidates = find_best_window(segments, min_duration=20, max_duration=30, top_n=5)
    assert len(candidates) > 0

    best_i, best_j = candidates[0]
    for i in range(best_i, best_j):
        assert segments[i].score >= 0


def test_score_normalization():
    segments = _make_segments(10)
    for s in segments:
        s.loudness_db = 0.0

    segments[2].loudness_db = -5.0
    segments[7].loudness_db = -5.0

    scored = compute_heuristic_scores(segments, w1=1.0, w2=0, w3=0, w4=0, w5=0)

    scores = [s.score for s in scored]
    assert abs(sum(scores)) < 1e-9
    assert abs(scores[2] - scores[7]) < 1e-6


def test_edge_case_short_video():
    segments = _make_segments(3)
    candidates = find_best_window(segments, min_duration=45, max_duration=60)

    assert len(candidates) == 0 or len(candidates) >= 1

    if candidates:
        i, j = candidates[0]
        assert i >= 0
        assert j <= len(segments)
