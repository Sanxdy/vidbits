"use client";

import { useState } from "react";
import JobSubmit from "@/components/JobSubmit";
import JobStatus from "@/components/JobStatus";

export default function Home() {
  const [jobId, setJobId] = useState<number | null>(null);

  return (
    <div className="flex flex-col items-center gap-8">
      <div className="max-w-lg text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          Turn long videos into viral Shorts
        </h1>
        <p className="mt-2 text-zinc-400">
          Paste a YouTube link. We transcribe, find the best clip, add captions,
          and produce a 9:16 Short.
        </p>
      </div>

      <JobSubmit onJobCreated={setJobId} />

      {jobId && <JobStatus jobId={jobId} />}
    </div>
  );
}
