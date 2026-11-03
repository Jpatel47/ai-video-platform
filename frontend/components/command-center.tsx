"use client";

import {
  ArrowUpRight,
  ImagePlus,
  Languages,
  type LucideIcon,
  Mic2,
  Music2,
  WandSparkles
} from "lucide-react";
import { useState } from "react";

import { usePlan } from "@/components/plan-context";
import { planWorkflow } from "@/lib/api";

const modes = [
  "Text to Video",
  "Image to Video",
  "Storyboard"
];

const initialPrompt =
  "Create a magical children's story about a rabbit learning addition. Use warm characters, clear math visuals, gentle camera moves, narration, music, subtitles, and a final recap.";

export function CommandCenter() {
  const { setPlan } = usePlan();
  const [activeMode, setActiveMode] = useState("Text to Video");
  const [prompt, setPrompt] = useState(initialPrompt);
  const [enabledTools, setEnabledTools] = useState<string[]>(["Images", "Voice", "Music"]);
  const [planStatus, setPlanStatus] = useState("Ready to generate a workflow plan");
  const [isPlanning, setIsPlanning] = useState(false);

  async function generatePlan() {
    setIsPlanning(true);
    setPlanStatus("Planning workflow...");

    try {
      const plan = await planWorkflow(prompt, "high");
      setPlan(plan);
      setPlanStatus(`Plan ready: ${plan.stages.length} stages routed`);
    } catch (error) {
      setPlan(null);
      setPlanStatus(error instanceof Error ? error.message : "Planning failed");
    } finally {
      setIsPlanning(false);
    }
  }

  function toggleTool(label: string) {
    setEnabledTools((current) =>
      current.includes(label) ? current.filter((item) => item !== label) : [...current, label]
    );
  }

  return (
    <header className="border-b border-line/80 bg-canvas/95 px-4 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-4">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <h1 className="text-xl font-semibold">Rabbit Addition Story</h1>
            <p className="text-sm text-muted">Draft project - classroom animation - 60 seconds</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {modes.map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={activeMode === mode}
                onClick={() => setActiveMode(mode)}
                className={`h-9 rounded-md border px-3 text-sm ${
                  activeMode === mode
                    ? "border-teal bg-teal text-canvas"
                    : "border-line bg-panel text-muted hover:text-ink"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 rounded-md border border-line bg-panel p-3 shadow-workspace lg:grid-cols-[1fr_auto]">
          <textarea
            className="min-h-24 resize-none rounded-md border border-line bg-canvas px-4 py-3 text-sm leading-6 text-ink outline-none ring-0 placeholder:text-muted focus:border-teal"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            aria-label="Director prompt"
          />
          <div className="grid grid-cols-3 gap-2 lg:w-56 lg:grid-cols-2">
            <IconButton
              label="Images"
              icon={ImagePlus}
              active={enabledTools.includes("Images")}
              onClick={() => toggleTool("Images")}
            />
            <IconButton
              label="Voice"
              icon={Mic2}
              active={enabledTools.includes("Voice")}
              onClick={() => toggleTool("Voice")}
            />
            <IconButton
              label="Music"
              icon={Music2}
              active={enabledTools.includes("Music")}
              onClick={() => toggleTool("Music")}
            />
            <IconButton
              label="Translate"
              icon={Languages}
              active={enabledTools.includes("Translate")}
              onClick={() => toggleTool("Translate")}
            />
            <button
              type="button"
              onClick={generatePlan}
              disabled={isPlanning}
              className="col-span-3 flex h-11 items-center justify-center gap-2 rounded-md bg-amber px-3 text-sm font-semibold text-canvas disabled:cursor-wait disabled:opacity-70 lg:col-span-2"
            >
              <WandSparkles size={17} aria-hidden />
              {isPlanning ? "Planning" : "Generate Plan"}
              <ArrowUpRight size={16} aria-hidden />
            </button>
          </div>
        </div>
        <div className="flex min-h-9 items-center justify-between rounded-md border border-line bg-panel px-3 py-2 text-sm">
          <span className="text-muted">{planStatus}</span>
          <span className="rounded-md bg-panelSoft px-2 py-1 text-xs text-teal">{activeMode}</span>
        </div>
      </div>
    </header>
  );
}

function IconButton({
  label,
  icon: Icon,
  active,
  onClick
}: {
  label: string;
  icon: LucideIcon;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={`flex h-11 items-center justify-center gap-2 rounded-md border text-sm ${
        active
          ? "border-teal bg-teal/15 text-teal"
          : "border-line bg-panelSoft text-muted hover:text-ink"
      }`}
      title={label}
    >
      <Icon size={17} aria-hidden />
      <span className="hidden sm:inline lg:hidden xl:inline">{label}</span>
    </button>
  );
}
