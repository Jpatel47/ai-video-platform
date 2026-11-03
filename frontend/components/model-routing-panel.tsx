"use client";

import { Route } from "lucide-react";
import { useState } from "react";

import { usePlan } from "@/components/plan-context";

interface RouteRow {
  capability: string;
  model: string;
  mode: string;
  reason?: string;
}

const placeholderRoutes: RouteRow[] = [
  { capability: "Image generation", model: "FLUX Image Provider", mode: "Local" },
  { capability: "Image to video", model: "LTX Video Provider", mode: "Cloud" },
  { capability: "Voice generation", model: "Kokoro Voice Provider", mode: "Local" },
  { capability: "Final rendering", model: "FFmpeg Composition Engine", mode: "Hybrid" }
];

function toTitle(value: string): string {
  return value.replaceAll("_", " ").replace(/^./, (char) => char.toUpperCase());
}

export function ModelRoutingPanel() {
  const { plan } = usePlan();
  const [selectedCapability, setSelectedCapability] = useState<string | null>(null);

  const routes: RouteRow[] = plan
    ? plan.stages
        .filter((stage) => stage.route !== null)
        .map((stage) => ({
          capability: toTitle(stage.required_capability),
          model: stage.route!.model.display_name,
          mode: toTitle(stage.route!.model.execution_mode),
          reason: stage.route!.reason
        }))
    : placeholderRoutes;

  const selected = routes.find((route) => route.capability === selectedCapability) ?? null;

  return (
    <section className="min-h-0 overflow-auto rounded-md border border-line bg-panel p-4 shadow-workspace">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Router</h2>
          <p className="text-sm text-muted">
            {plan ? "Live routing decisions for this plan" : "Example routing decisions"}
          </p>
        </div>
        <div className="grid size-9 place-items-center rounded-md bg-panelSoft text-teal">
          <Route size={18} aria-hidden />
        </div>
      </div>

      <div className="grid gap-2">
        {routes.map((route) => (
          <button
            key={route.capability}
            type="button"
            aria-label={`Select ${route.capability} route`}
            onClick={() => setSelectedCapability(route.capability)}
            className={`rounded-md border bg-canvas p-3 text-left transition ${
              selectedCapability === route.capability
                ? "border-teal"
                : "border-line hover:border-cobalt"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-medium">{route.capability}</p>
              <span className="rounded-md bg-panelSoft px-2 py-1 text-xs text-muted">
                {route.mode}
              </span>
            </div>
            <p className="mt-1 truncate text-xs text-muted">{route.model}</p>
          </button>
        ))}
      </div>

      {selected?.reason && (
        <div className="mt-3 rounded-md border border-line bg-canvas px-3 py-2 text-xs leading-5 text-muted">
          {selected.reason}
        </div>
      )}
    </section>
  );
}
