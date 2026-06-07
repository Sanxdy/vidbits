import json
import logging
import os

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info("Loading Whisper model: %s (CPU int8)", settings.whisper_model)
        _model = WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )
    return _model


def transcribe_audio(audio_path: str) -> dict:
    model = _get_model()
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    result = {
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": [],
    }

    for seg in segments:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word.strip(),
                    "start": w.start,
                    "end": w.end,
                })
        result["segments"].append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": words,
        })

    return result


def save_transcription(result: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "whisper_output.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    return path
