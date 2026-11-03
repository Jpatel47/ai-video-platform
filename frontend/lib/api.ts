const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ApiModelDefinition {
  slug: string;
  display_name: string;
  provider_slug: string;
  execution_mode: "local" | "cloud" | "hybrid";
}

export interface ApiModelRoute {
  capability: string;
  model: ApiModelDefinition;
  score: number;
  reason: string;
}

export interface ApiWorkflowStage {
  id: string;
  key: string;
  label: string;
  required_capability: string;
  depends_on: string[];
  route: ApiModelRoute | null;
  estimated_latency_seconds: number;
  estimated_cost_units: number;
}

export interface ApiWorkflowPlan {
  id: string;
  status: string;
  stages: ApiWorkflowStage[];
  total_estimated_latency_seconds: number;
  total_estimated_cost_units: number;
  director_summary: string;
}

// Mirrors the backend StageResult / WorkflowRunResult returned by POST /api/v1/workflows/execute.
// "simulated" means the mock provider ran the stage and no media was produced.
export type ApiStageStatus = "completed" | "simulated" | "failed" | "skipped";

export interface ApiStageResult {
  stage_key: string;
  label: string;
  model_slug: string;
  provider_slug: string;
  status: ApiStageStatus;
  output: Record<string, unknown>;
  error: string | null;
}

export interface ApiWorkflowRunResult {
  plan_id: string;
  status: string;
  stage_results: ApiStageResult[];
  simulated_stages: string[];
  director_summary: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers }
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }
  return (await response.json()) as T;
}

export function planWorkflow(prompt: string, quality = "high"): Promise<ApiWorkflowPlan> {
  return request<ApiWorkflowPlan>("/api/v1/workflows/plan", {
    method: "POST",
    body: JSON.stringify({ prompt, quality })
  });
}

export function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

export function renderStrategy(plan: ApiWorkflowPlan): string {
  const modes = new Set(
    plan.stages.map((stage) => stage.route?.model.execution_mode).filter(Boolean)
  );
  if (modes.size > 1) return "Hybrid";
  const [only] = modes;
  return only ? only.charAt(0).toUpperCase() + only.slice(1) : "Unknown";
}
