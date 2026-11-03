"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { ApiWorkflowPlan } from "@/lib/api";

interface PlanContextValue {
  plan: ApiWorkflowPlan | null;
  setPlan: (plan: ApiWorkflowPlan | null) => void;
}

const PlanContext = createContext<PlanContextValue | null>(null);

export function PlanProvider({ children }: { children: ReactNode }) {
  const [plan, setPlan] = useState<ApiWorkflowPlan | null>(null);
  const value = useMemo(() => ({ plan, setPlan }), [plan]);
  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlan(): PlanContextValue {
  const context = useContext(PlanContext);
  if (!context) {
    throw new Error("usePlan must be used inside a PlanProvider");
  }
  return context;
}
