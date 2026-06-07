"use client";

import { useState } from "react";

interface Props {
  jobId: number;
  videoPath: string | null;
}

export default function PublishPanel({ jobId, videoPath }: Props) {
  const [publishing, setPublishing] = useState(false);
  const [result, setResult] = useState("");

  async function handlePublish() {
    if (!videoPath) return;
    setPublishing(true);
    setResult("");

    try {
      const res = await fetch(
        `http://localhost:8000/jobs/${jobId}/publish`,
        { method: "POST" }
      );
      const data = await res.json();
      if (res.ok) {
        setResult(`Published! https://youtu.be/${data.video_id}`);
      } else {
        setResult(data.detail || "Publish failed");
      }
    } catch {
      setResult("Backend unreachable");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 p-4">
      <h3 className="mb-3 text-sm font-medium">Publish to YouTube</h3>
      <button
        onClick={handlePublish}
        disabled={publishing || !videoPath}
        className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
      >
        {publishing ? "Publishing..." : "Publish Short"}
      </button>
      {result && (
        <p className="mt-2 text-sm text-zinc-400">{result}</p>
      )}
    </div>
  );
}
