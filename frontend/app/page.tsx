import { CommandCenter } from "@/components/command-center";
import { PlanProvider } from "@/components/plan-context";
import { QueuePanel } from "@/components/queue-panel";
import { Sidebar } from "@/components/sidebar";
import { WorkflowCanvas } from "@/components/workflow-canvas";
import { ModelRoutingPanel } from "@/components/model-routing-panel";

export default function Home() {
  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen grid-cols-[72px_minmax(0,1fr)] lg:grid-cols-[260px_minmax(0,1fr)]">
        <Sidebar />
        <section className="grid min-w-0 grid-rows-[auto_minmax(0,1fr)] border-l border-line/80">
          <PlanProvider>
            <CommandCenter />
            <div className="grid min-h-0 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px]">
              <WorkflowCanvas />
              <aside className="grid min-h-0 gap-4 xl:grid-rows-[1fr_1fr]">
                <ModelRoutingPanel />
                <QueuePanel />
              </aside>
            </div>
          </PlanProvider>
        </section>
      </div>
    </main>
  );
}
