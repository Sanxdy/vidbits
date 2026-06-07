"use client";

interface JobData {
  id: number;
  output_path: string | null;
  selected_start: number | null;
  selected_end: number | null;
  hook_title: string | null;
}

interface Props {
  job: JobData;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function ClipPreview({ job }: Props) {
  if (!job.output_path) {
    return (
      <div className="rounded-lg border border-zinc-800 p-4 text-sm text-zinc-500">
        No output available
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-800 p-4">
      <h3 className="mb-3 text-sm font-medium">Preview</h3>

      <video
        controls
        className="mx-auto max-h-[480px] w-full rounded-lg bg-black"
        style={{ aspectRatio: "9/16" }}
      >
        <source
          src={`http://localhost:8000/output/${job.id}/clip.mp4`}
          type="video/mp4"
        />
      </video>

      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
        <div>
          {job.selected_start != null && (
            <span>{formatTime(job.selected_start)}</span>
          )}
          {job.selected_end != null && (
            <span> — {formatTime(job.selected_end)}</span>
          )}
          <span className="ml-2 text-zinc-600">
            ({job.selected_end != null && job.selected_start != null
              ? `${(job.selected_end - job.selected_start).toFixed(0)}s`
              : ""}
          </span>
        </div>
        {job.hook_title && (
          <span className="rounded bg-zinc-800 px-2 py-0.5 text-emerald-400">
            {job.hook_title}
          </span>
        )}
      </div>
    </div>
  );
}
