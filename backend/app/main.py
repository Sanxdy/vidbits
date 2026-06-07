import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.database import create_db_and_tables, engine
from app.models.job import Job
from app.pipelines.analyze import (
    compute_heuristic_scores,
    find_best_window,
    load_transcription,
)
from app.pipelines.download import download_video
from app.pipelines.edit import render_clip
from app.pipelines.highlight import llm_pick_best_window
from app.pipelines.transcribe import save_transcription, transcribe_audio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("vidbits")

app = FastAPI(title="vidbits", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


os.makedirs("data/output", exist_ok=True)
app.mount("/output", StaticFiles(directory="data/output"), name="output")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs")
async def create_job(url: str):
    with Session(engine) as session:
        job = Job(url=url, status="pending")
        session.add(job)
        session.commit()
        session.refresh(job)

    asyncio.create_task(_run_pipeline(job.id))
    return {"job_id": job.id, "status": job.status}


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "id": job.id,
            "url": job.url,
            "status": job.status,
            "progress": job.progress,
            "output_path": job.output_path,
            "selected_start": job.selected_start,
            "selected_end": job.selected_end,
            "hook_title": job.hook_title,
            "error_message": job.error_message,
        }


async def _run_pipeline(job_id: int):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Job %s not found at pipeline start", job_id)
            return

    try:
        _update_job(job_id, status="downloading", progress=0.1)
        source_path = await download_video(job.url, job_id)
        _update_job(job_id, status="transcribing", progress=0.3)

        raw_dir = f"data/raw/{job_id}"
        transcription = transcribe_audio(source_path)
        transcription_path = save_transcription(transcription, raw_dir)
        _update_job(job_id, status="analyzing", progress=0.5)

        segments = load_transcription(transcription_path)
        segments = compute_heuristic_scores(segments)
        candidates = find_best_window(segments)

        best_window = await llm_pick_best_window(segments, candidates)
        if best_window:
            start_i, end_i = best_window
            start_time = segments[start_i].start_time
            end_time = segments[end_i - 1].end_time
        elif candidates:
            start_i, end_i = candidates[0]
            start_time = segments[start_i].start_time
            end_time = segments[end_i - 1].end_time
        else:
            start_time = segments[0].start_time
            end_time = segments[-1].end_time

        output_dir = f"data/output/{job_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "clip.mp4")

        _update_job(job_id, status="editing", progress=0.7)

        all_words = []
        for seg in segments:
            all_words.extend(seg.words)

        await render_clip(
            input_path=source_path,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time,
            words=all_words,
        )

        _update_job(
            job_id,
            status="ready",
            progress=1.0,
            output_path=output_path,
            selected_start=start_time,
            selected_end=end_time,
        )

    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        _update_job(job_id, status="failed", error_message=str(e))


def _update_job(job_id: int, **kwargs):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job:
            for k, v in kwargs.items():
                setattr(job, k, v)
            session.add(job)
            session.commit()
