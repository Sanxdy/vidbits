from pydantic import BaseModel


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class Segment(BaseModel):
    start_time: float
    end_time: float
    transcript: str
    words: list[WordTimestamp] = []
    loudness_db: float | None = None
    speaking_rate_wpm: float | None = None
    sentiment: str | None = None
    sentiment_score: float | None = None
    hook_probability: float | None = None
    face_present: bool | None = None
    score: float = 0.0
