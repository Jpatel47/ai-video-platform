"use client";

import {
  Aperture,
  Clapperboard,
  Film,
  Image,
  Layers,
  ListChecks,
  type LucideIcon,
  Mic2,
  Music2,
  PenTool,
  Sparkles
} from "lucide-react";
import { useState } from "react";

import { usePlan } from "@/components/plan-context";
import { formatDuration, renderStrategy } from "@/lib/api";

const stageIcons: Record<string, LucideIcon> = {
  story_generation: PenTool,
  scene_planning: ListChecks,
  prompt_enhancement: Sparkles,
  character_generation: Aperture,
  image_generation: Image,
  image_to_video: Film,
  voice_generation: Mic2,
  music_generation: Music2,
  video_composition: Layers,
  final_rendering: Clapperboard
};

const placeholderStages = [
  { key: "story_generation", label: "Story", model: "Local Director LLM" },
  { key: "scene_planning", label: "Scenes", model: "Local Director LLM" },
  { key: "prompt_enhancement", label: "Prompts", model: "Local Director LLM" },
  { key: "character_generation", label: "Characters", model: "FLUX Image Provider" },
  { key: "image_generation", label: "Images", model: "FLUX Image Provider" },
  { key: "image_to_video", label: "Motion", model: "LTX Video Provider" },
  { key: "voice_generation", label: "Voice", model: "Kokoro Voice Provider" },
  { key: "music_generation", label: "Music", model: "MusicGen Provider" },
  { key: "video_composition", label: "Compose", model: "FFmpeg Composition Engine" },
  { key: "final_rendering", label: "Render", model: "FFmpeg Composition Engine" }
];

interface CanvasStage {
  key: string;
  label: string;
  model: string;
  latency?: number;
  cost?: number;
}

export function WorkflowCanvas() {
  const { plan } = usePlan();
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const stages: CanvasStage[] = plan
    ? plan.stages.map((stage) => ({
        key: stage.key,
        label: stage.label,
        model: stage.route?.model.display_name ?? "Unrouted",
        latency: stage.estimated_latency_seconds,
        cost: stage.estimated_cost_units
      }))
    : placeholderStages;

  const runtime = plan ? formatDuration(plan.total_estimated_latency_seconds) : "-";
  const cost = plan ? plan.total_estimated_cost_units.toFixed(2) : "-";
  const strategy = plan ? renderStrategy(plan) : "-";

  return (
    <section className="min-h-0 rounded-md border border-line bg-panel p-4 shadow-workspace">
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-base font-semibold">
            {plan ? "Generated Workflow" : "Workflow Preview"}
          </h2>
          <p className="text-sm text-muted">
            {plan
              ? plan.director_summary
              : "Generate a plan to see capability-based stages with real model routing"}
          </p>
        </div>
        <span
          className={`h-9 rounded-md border px-3 text-sm leading-9 ${
            plan ? "border-teal bg-teal/15 text-teal" : "border-line bg-panelSoft text-muted"
          }`}
        >
          {plan ? `Status: ${plan.status}` : "No plan yet"}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
        {stages.map((stage, index) => {
          const Icon = stageIcons[stage.key] ?? Sparkles;
          return (
            <div
              key={stage.key}
              role="button"
              aria-label={`Select ${stage.label} stage`}
              tabIndex={0}
              onClick={() => setSelectedStage(stage.label)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  setSelectedStage(stage.label);
                }
              }}
              className={`relative min-h-32 rounded-md border bg-canvas p-3 transition ${
                selectedStage === stage.label ? "border-teal" : "border-line hover:border-cobalt"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="grid size-10 place-items-center rounded-md bg-panelSoft text-teal">
                  <Icon size={18} aria-hidden />
                </div>
                {stage.latency !== undefined && (
                  <span className="rounded-md bg-panelSoft px-2 py-1 text-xs text-muted">
                    {formatDuration(stage.latency)}
                  </span>
                )}
              </div>
              <div className="mt-5">
                <p className="text-xs text-muted">Stage {String(index + 1).padStart(2, "0")}</p>
                <h3 className="mt-1 text-sm font-semibold">{stage.label}</h3>
                <p className="mt-2 text-xs leading-5 text-muted">{stage.model}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <Metric label="Estimated runtime" value={runtime} />
        <Metric label="Estimated cost units" value={cost} />
        <Metric label="Render strategy" value={strategy} />
      </div>
      {selectedStage && (
        <div className="mt-3 rounded-md border border-line bg-canvas px-4 py-3 text-sm">
          <span className="text-teal">Selected: {selectedStage}</span>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-canvas px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
