"use client";

import { useEffect, useState } from "react";
import ClipPreview from "./ClipPreview";

interface JobData {
  id: number;
  url: string;
  status: string;
  progress: number;
  output_path: string | null;
  selected_start: number | null;
  selected_end: number | null;
  hook_title: string | null;
  error_message: string | null;
}

interface Props {
  jobId: number;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Queued",
  downloading: "Downloading video",
  transcribing: "Transcribing audio",
  analyzing: "Analyzing content",
  editing: "Rendering clip",
  ready: "Ready",
  failed: "Failed",
};

export default function JobStatus({ jobId }: Props) {
  const [job, setJob] = useState<JobData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/jobs/${jobId}`);
        if (!res.ok) throw new Error("Failed to fetch job");
        const data: JobData = await res.json();
        setJob(data);

        if (data.status === "ready" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Fetch failed");
        clearInterval(interval);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [jobId]);

  if (error) {
    return (
      <div className="w-full max-w-xl rounded-lg border border-red-800 bg-red-950/50 p-4 text-sm text-red-400">
        {error}
      </div>
    );
  }

  if (!job) {
    return (
      <div className="w-full max-w-xl rounded-lg border border-zinc-800 p-4 text-sm text-zinc-500">
        Loading...
      </div>
    );
  }

  const statusLabel = STATUS_LABELS[job.status] || job.status;
  const isFailed = job.status === "failed";
  const isReady = job.status === "ready";

  return (
    <div className="w-full max-w-xl space-y-4">
      <div className="rounded-lg border border-zinc-800 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium">{statusLabel}</span>
          <span className="text-xs text-zinc-500">
            {Math.round(job.progress * 100)}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${job.progress * 100}%` }}
          />
        </div>
        {isFailed && job.error_message && (
          <p className="mt-2 text-sm text-red-400">{job.error_message}</p>
        )}
      </div>

      {isReady && <ClipPreview job={job} />}
    </div>
  );
}
