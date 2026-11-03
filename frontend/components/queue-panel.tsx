"use client";

import { CheckCircle2, Clock3, Loader2 } from "lucide-react";
import { useState } from "react";

const jobs = [
  { title: "Prompt expansion", status: "complete", icon: CheckCircle2, time: "8s" },
  { title: "Scene cards", status: "complete", icon: CheckCircle2, time: "10s" },
  { title: "Character sheet", status: "running", icon: Loader2, time: "45s" },
  { title: "Motion pass", status: "queued", icon: Clock3, time: "2m" },
  { title: "Final render", status: "queued", icon: Clock3, time: "1m" }
];

export function QueuePanel() {
  const [isPaused, setIsPaused] = useState(false);
  const [selectedJob, setSelectedJob] = useState("Character sheet");

  return (
    <section className="min-h-0 rounded-md border border-line bg-panel p-4 shadow-workspace">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Rendering Queue</h2>
          <p className="text-sm text-muted">Local, cloud, and hybrid execution</p>
        </div>
        <button
          type="button"
          onClick={() => setIsPaused((value) => !value)}
          className={`h-9 rounded-md border px-3 text-sm ${
            isPaused
              ? "border-amber bg-amber/15 text-amber"
              : "border-line bg-panelSoft text-muted hover:text-ink"
          }`}
        >
          {isPaused ? "Resume" : "Pause"}
        </button>
      </div>

      <div className="space-y-2">
        {jobs.map((job) => (
          <button
            key={job.title}
            type="button"
            onClick={() => setSelectedJob(job.title)}
            className={`flex w-full items-center gap-3 rounded-md border bg-canvas p-3 text-left ${
              selectedJob === job.title ? "border-teal" : "border-line hover:border-cobalt"
            }`}
          >
            <div
              className={`grid size-9 place-items-center rounded-md ${
                job.status === "complete"
                  ? "bg-teal/15 text-teal"
                  : job.status === "running"
                    ? "bg-amber/15 text-amber"
                    : "bg-panelSoft text-muted"
              }`}
            >
              <job.icon size={17} aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{job.title}</p>
              <p className="text-xs text-muted">{job.status}</p>
            </div>
            <span className="text-xs text-muted">{job.time}</span>
          </button>
        ))}
      </div>
      <div className="mt-3 rounded-md border border-line bg-canvas px-3 py-2 text-xs text-muted">
        Selected job: <span className="text-teal">{selectedJob}</span>
      </div>
    </section>
  );
}
