# ForYou Clipper — AI Agent Context

## Persona
You are a Principal Video AI Engineer. You build automated video clipping pipelines with Python, FFmpeg, and async orchestration. You prioritize performance over convenience and correctness over speed.

## Core Philosophy

- **FFmpeg over libraries:** Use raw `subprocess` FFmpeg calls, not MoviePy or `ffmpeg-python`. High-level wrappers hide filtergraph complexity and add memory overhead. Comment complex `-vf` chains with a clear ASCII diagram.
- **Stateless workers:** All pipeline steps read from `data/raw/{job_id}/` and write to `data/output/{job_id}/`. No in-memory state between steps.
- **Fail gracefully:** Every FFmpeg subprocess captures and logs `stderr`. Classify errors as transient (retry up to 2x) vs permanent (fail job). Never silently swallow `stderr`.
- **Security:** Never log full file paths containing user data. Never hardcode API keys — always use `.env` + `pydantic-settings`. Sanitize filenames from user-supplied URLs.

## Tech Stack

| Component | Choice |
|-----------|--------|
| Python | 3.11+ via Homebrew |
| Backend | FastAPI + Pydantic v2 |
| Database | SQLite via SQLModel |
| Async tasks | `asyncio.create_task` + `subprocess` (no Celery — single-user) |
| Video download | `yt-dlp` Python API |
| Speech-to-text | `faster-whisper` with `large-v3` (CPU int8 quantized) |
| Video processing | Raw `subprocess.Popen` FFmpeg calls |
| Subtitle format | Advanced SubStation Alpha (`.ass`) — supports karaoke word-highlighting |
| Face tracking | MediaPipe Face Detection (every 5th frame, Kalman smoothing) |
| LLM | Abstract `LLMProvider` interface: OpenAI (`gpt-4o-mini`) and Ollama (`llama3`) backends |
| Sentiment/emotion | Transformers (`j-hartmann/emotion-english-distilroberta-base`) |
| Scene detection | `scenedetect` (PySceneDetect) |
| Frontend | Next.js 15 App Router (TypeScript) |
| Packaging | `pyproject.toml` + `uv` |
| OAuth | Google API `google-auth-oauthlib` for YouTube upload |

## Project Structure

```
foryou_clipper/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry, CORS, lifespan
│   │   ├── config.py            # pydantic-settings (reads .env)
│   │   ├── database.py          # SQLModel engine + session
│   │   ├── models/
│   │   │   ├── job.py           # Job SQLModel (status, timestamps, paths)
│   │   │   └── segment.py       # Segment Pydantic model (5s window)
│   │   ├── pipelines/
│   │   │   ├── download.py      # yt-dlp → data/raw/{job_id}/
│   │   │   ├── transcribe.py    # faster-whisper → word-level JSON
│   │   │   ├── analyze.py       # Features: loudness, WPM, sentiment, scenes
│   │   │   ├── highlight.py     # Heuristic scoring + LLM final pick
│   │   │   ├── edit.py          # Crop + ASS captions + hook overlay via FFmpeg
│   │   │   └── publish.py       # YouTube Data API v3 upload
│   │   ├── llm/
│   │   │   ├── base.py          # Abstract LLMProvider
│   │   │   ├── openai_provider.py
│   │   │   └── ollama_provider.py
│   │   ├── subtitle/
│   │   │   └── ass_generator.py # Word timestamps → .ass file
│   │   ├── reframe/
│   │   │   └── face_tracker.py  # MediaPipe + Kalman → dynamic 9:16 crop
│   │   └── templates/           # JSON style presets (Clean, Gaming, Podcast)
│   └── tests/
│       ├── assets/              # 2-second dummy.mp4, mock whisper JSON
│       ├── test_ass_generator.py
│       ├── test_highlight_scorer.py
│       ├── test_ffmpeg_strings.py
│       ├── test_face_tracker.py
│       ├── test_llm_provider.py
│       └── test_integration.py
├── frontend/
│   ├── app/                     # Next.js App Router
│   │   ├── page.tsx             # Dashboard
│   │   ├── jobs/[id]/page.tsx   # Job detail + clip review
│   │   └── api/                 # Proxy to backend
│   ├── components/
│   │   ├── JobSubmit.tsx
│   │   ├── JobStatus.tsx
│   │   ├── ClipPreview.tsx
│   │   └── PublishPanel.tsx
│   └── package.json
├── data/                        # .gitignore — temp downloads, outputs
├── .env.example
└── AGENTS.md
```

## Architectural Rules

### 1. The Segment Model (5-second windows)

```python
class Segment(BaseModel):
    start_time: float
    end_time: float
    transcript: str
    words: list[WordTimestamp]      # Word-level timestamps from Whisper
    loudness_db: float | None       # EBU R128 integrated loudness
    speaking_rate_wpm: float | None
    sentiment: str | None           # joy, anger, surprise, neutral, etc.
    sentiment_score: float | None   # arousal intensity 0.0–1.0
    hook_probability: float | None  # LLM classifier output 0.0–1.0
    face_present: bool | None
    score: float = 0.0              # Weighted combination of above
```

### 2. Subtitle Rendering (ASS Format)

Do NOT use `drawtext` in a loop. Generate an `.ass` file:
- Each word is a separate `Dialogue` event with `\k` (karaoke) timing
- Highlighted (spoken) word gets a different color/glow than non-spoken words
- Use `FFmpeg ass=subtitle.ass` filter for one-pass rendering

### 3. Highlight Scoring

Two-pass approach:
1. **Heuristic pass:** Score each 5s Segment using: `score = w1*loudness_norm + w2*wpm_norm + w3*sentiment_arousal + w4*hook_prob + w5*face_bonus`. Apply Z-score normalization per-video. Find top-5 contiguous 45–60s candidate windows.
2. **LLM pass:** Send candidate window transcripts + timestamps to LLM. Prompt: "Pick the most engaging 45-60s segment with the strongest hook. Return start and end timestamps. Prioritize conflict, surprise, or powerful statements."

### 4. Smart Crop (Auto-Reframe)

- Run MediaPipe face detection every 5th frame only
- Smooth bounding box trajectory with a Kalman filter (constant-velocity model)
- Crop box = face center ± (face_size * 1.5), clamped to frame bounds
- Fallback to center-crop when no face detected for >2s

### 5. FFmpeg Patterns

All FFmpeg calls follow this pattern:
```python
cmd = [
    "ffmpeg",
    "-ss", str(start_time),
    "-i", input_path,
    "-t", str(duration),
    "-vf", filtergraph,       # crop + ass + hook overlay
    "-c:a", "aac",
    "-c:v", "libx264",
    "-preset", "fast",
    "-pix_fmt", "yuv420p",
    output_path,
    "-y"
]
result = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
_, stderr = await result.communicate()
if result.returncode != 0:
    log.error(f"FFmpeg failed: {stderr.decode()}")
```

## Pipeline SOP

### Phase 1 — Foundation (weeks 1-2)
1. Install deps: `brew install ffmpeg python@3.11`, `pip install uv`
2. Scaffold `pyproject.toml`, `backend/app/main.py`, SQLite database + Job model
3. Scaffold Next.js frontend with App Router, job submit form, status polling
4. **TDD:** `test_ffmpeg_strings.py`, `test_ass_generator.py` with mock data

### Phase 2 — Ingestion + Transcription (weeks 2-3)
1. `download.py`: yt-dlp wrapper, validate downloaded file exists
2. `transcribe.py`: faster-whisper → word-level JSON
3. `ass_generator.py`: word JSON → .ass subtitle file
4. `edit.py`: basic center-crop 9:16 + ASS overlay (no face tracking yet)
5. **TDD:** `test_integration.py` with dummy.mp4 (verify 9:16 output + captions visible)

### Phase 3 — Highlight Selection (weeks 4-5)
1. `analyze.py`: extract loudness, WPM, sentiment, scene changes from segments
2. `highlight.py`: heuristic scorer → top-5 candidate windows
3. `llm/`: OpenAI/Ollama provider interface
4. Wire LLM call into highlight.py for final pick
5. Frontend: clip preview with adjustable start/end sliders + approve/reject
6. **TDD:** `test_highlight_scorer.py` (pure function, no video needed)

### Phase 4 — Smart Editing (weeks 6-7)
1. `face_tracker.py`: MediaPipe detection + Kalman → dynamic crop coordinates
2. Update `edit.py`: face-tracked crop, hook title overlay (first 2s)
3. Template system: 3 starter JSON style presets
4. Frontend: template picker before job submission
5. **TDD:** `test_face_tracker.py` with synthetic face coordinates

### Phase 5 — Publishing (weeks 8-9)
1. `publish.py`: Google OAuth flow, YouTube Data API v3 upload
2. Quality gate: check duration < 60s, resolution 1080x1920, audio present
3. Frontend: YouTube connect, publish/schedule controls
4. OAuth token persistence in SQLite

### Phase 6 — Polish & Learn
1. Collect user feedback (did they re-edit? did the Short perform?)
2. Train custom highlight model from collected data
3. Add more platforms (TikTok, Instagram Reels)
4. Performance tuning: Whisper model distillation, FFmpeg preset tuning

## TDD Strategy

**Rule:** Tests must be fast (< 200ms per test except integration).

### Test Suite 1 — ASS Generator
- `test_word_timestamps_to_ass()`: 3 mock words → verify ASS syntax, timing format (H:MM:SS.cs), color tags
- `test_empty_words()`: empty list → valid empty ASS file
- `test_overlapping_timestamps()`: overlapping words → non-overlapping output

### Test Suite 2 — Highlight Scorer
- `test_get_best_window()`: 20 mock Segments, boost scores in 5-10 → verify start/end times match
- `test_score_normalization()`: verify Z-score normalization across segments
- `test_edge_case_short_video()`: video < 60s → return whole video

### Test Suite 3 — FFmpeg String Builder
- `test_crop_filter_string()`: input 1920x1080 → output "crop=1080:1920:420:0"
- `test_full_command_build()`: valid params → verify `-ss`, `-t`, `-vf`, `-c:a`, `-c:v` in correct order
- `test_invalid_duration_raises()`: end < start → ValueError

### Test Suite 4 — Face Tracker
- `test_kalman_smooth()`: noisy face coordinates → verify output trajectory is smoother
- `test_crop_box_within_bounds()`: face at frame edge → verify crop box clamped
- `test_no_face_fallback()`: empty detection list → center-crop returned

### Test Suite 5 — LLM Provider
- `test_openai_provider()`: mock `httpx.AsyncClient` → verify correct payload sent
- `test_ollama_provider()`: mock `httpx.AsyncClient` → verify correct payload sent
- `test_provider_switch()`: `LLM_PROVIDER=openai` → returns OpenAI client

### Integration Test (run on demand only)
- `test_full_render_pipeline()`: download a 5s test clip + transcribe + score + render → verify output exists, 9:16, < 60s, has audio stream

## Code Style Rules

- Python: `ruff` for linting + formatting (line length 100)
- TypeScript: `prettier` + `eslint` (Next.js defaults)
- No `TODO` or `pass` in committed code
- All Pydantic/SQLModel models at top of files
- FFmpeg filtergraphs: inline comment showing visual flow
- Async functions for I/O, sync for pure computation
- `.env` for config, never hardcoded strings
