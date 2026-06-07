"use client";

import { useParams } from "next/navigation";
import JobStatus from "@/components/JobStatus";

export default function JobPage() {
  const params = useParams();
  const jobId = Number(params.id);

  return (
    <div className="flex flex-col items-center gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Job #{jobId}</h1>
      <JobStatus jobId={jobId} />
    </div>
  );
}
