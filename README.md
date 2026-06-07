# vidbits

Turn long videos into viral YouTube Shorts — automatically.

## Prerequisites

- Python 3.11+ (via Homebrew: `brew install python@3.11`)
- Node.js 18+ (via Homebrew: `brew install node`)
- FFmpeg 6+: `brew install ffmpeg`
- uv: `pip install uv` or `brew install uv`

## Quick start

### 1. Backend setup

```bash
cd backend

# Create .env from template (edit with your API keys)
cp .env.example .env

# Install Python deps (includes torch, faster-whisper — 3-5 min first time)
uv sync

# Start the API server
uv run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

### 2. Frontend setup

```bash
cd frontend

# Install JS deps
npm install

# Start the dev server
npm run dev
```

Open `http://localhost:3000` in your browser.

### 3. Run your first job

```bash
curl -X POST "http://localhost:8000/jobs?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Poll for status
curl http://localhost:8000/jobs/1
```

When status is `ready`, your clip is at `http://localhost:8000/output/1/clip.mp4`.

## Configuration

All config lives in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Your OpenAI API key (for highlight selection + hook generation) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `WHISPER_MODEL` | `distil-large-v3` | `large-v3` (slow, accurate) or `distil-large-v3` (fast, good) |
| `GOOGLE_CLIENT_ID` | — | For YouTube OAuth upload |
| `GOOGLE_CLIENT_SECRET` | — | For YouTube OAuth upload |

**Important:** The pipeline will run without an LLM API key — it will simply skip the LLM highlight selection step and use heuristic scoring only.

## Project structure

```
foryou_clipper/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI server + pipeline orchestrator
│   │   ├── config.py              # pydantic-settings (reads .env)
│   │   ├── database.py            # SQLite engine via SQLModel
│   │   ├── models/                # Job + Segment data models
│   │   ├── pipelines/             # 6 pipeline stages
│   │   │   ├── download.py        # yt-dlp downloader
│   │   │   ├── transcribe.py      # faster-whisper ASR
│   │   │   ├── analyze.py         # Feature extraction + scoring
│   │   │   ├── highlight.py       # LLM highlight selection
│   │   │   ├── edit.py            # FFmpeg rendering
│   │   │   └── publish.py         # YouTube upload
│   │   ├── llm/                   # OpenAI + Ollama providers
│   │   ├── subtitle/              # ASS karaoke subtitle generator
│   │   ├── reframe/               # MediaPipe face tracker
│   │   └── templates/             # Style presets (Clean, Gaming, Podcast)
│   ├── tests/                     # 20 tests across 5 suites
│   └── pyproject.toml
├── frontend/
│   ├── app/                       # Next.js 15 App Router
│   ├── components/                # JobSubmit, JobStatus, ClipPreview
│   └── package.json
├── data/                          # Temporary downloads + output clips (gitignored)
├── AGENTS.md                      # AI agent context for assistant tools
└── README.md
```

## Pipeline stages

When you submit a URL, the job flows through:

```
pending → downloading → transcribing → analyzing → editing → ready
```

1. **Download** — yt-dlp fetches the best available MP4 + audio
2. **Transcribe** — faster-whisper generates word-level timestamps
3. **Analyze** — segments video into 5s windows, extracts loudness/WPM/sentiment
4. **Score** — heuristic scoring finds top candidate windows, LLM picks the best
5. **Edit** — FFmpeg crops to 9:16, burns ASS karaoke captions, renders the clip
6. **Ready** — preview in the dashboard at `http://localhost:8000/output/{id}/clip.mp4`

## Tests

```bash
cd backend
uv run pytest tests/ -v    # 20 tests, ~0.2s
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| First run is slow | Whisper downloading model | Normal — ~2GB download on first `transcribe()` call |
| `ffmpeg not found` | FFmpeg not installed | `brew install ffmpeg` |
| Port 8000 in use | Another server running | Kill it or change port: `uvicorn ... --port 8001` |
| LLM step fails | No API key or Ollama not running | Set `OPENAI_API_KEY` in `.env` or skip LLM by leaving it blank |
| `ModuleNotFoundError` | Deps not installed | `cd backend && uv sync` |
| Frontend can't connect | Backend not running | Start backend first, then frontend |
