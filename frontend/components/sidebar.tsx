"use client";

import { useState } from "react";
import {
  Boxes,
  Clapperboard,
  Clock3,
  FolderKanban,
  History,
  Library,
  Settings,
  Sparkles,
  UsersRound,
  Workflow
} from "lucide-react";

const items = [
  { label: "Projects", icon: FolderKanban },
  { label: "Workflows", icon: Workflow },
  { label: "Assets", icon: Boxes },
  { label: "Characters", icon: UsersRound },
  { label: "Templates", icon: Library },
  { label: "History", icon: History },
  { label: "Queue", icon: Clock3 }
];

export function Sidebar() {
  const [activeItem, setActiveItem] = useState("Projects");

  return (
    <aside className="flex min-h-screen flex-col border-r border-line/80 bg-panel">
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="grid size-10 place-items-center rounded-md bg-teal text-canvas">
          <Sparkles size={20} aria-hidden />
        </div>
        <div className="hidden min-w-0 lg:block">
          <p className="truncate text-sm font-semibold">AI Video Director</p>
          <p className="truncate text-xs text-muted">Animation workspace</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {items.map((item) => (
          <button
            key={item.label}
            type="button"
            aria-label={item.label}
            aria-pressed={activeItem === item.label}
            onClick={() => setActiveItem(item.label)}
            className={`group flex h-11 items-center gap-3 rounded-md px-3 text-sm transition ${
              activeItem === item.label
                ? "bg-panelSoft text-ink shadow-workspace"
                : "text-muted hover:bg-panelSoft hover:text-ink"
            }`}
            title={item.label}
          >
            <item.icon size={18} aria-hidden />
            <span className="hidden truncate lg:inline">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="space-y-2 border-t border-line/80 p-3">
        <button
          type="button"
          aria-label="Render Preview"
          aria-pressed={activeItem === "Render Preview"}
          onClick={() => setActiveItem("Render Preview")}
          className={`flex h-11 w-full items-center gap-3 rounded-md px-3 text-sm ${
            activeItem === "Render Preview"
              ? "bg-panelSoft text-ink"
              : "text-muted hover:bg-panelSoft hover:text-ink"
          }`}
        >
          <Clapperboard size={18} aria-hidden />
          <span className="hidden lg:inline">Render Preview</span>
        </button>
        <button
          type="button"
          aria-label="Settings"
          aria-pressed={activeItem === "Settings"}
          onClick={() => setActiveItem("Settings")}
          className={`flex h-11 w-full items-center gap-3 rounded-md px-3 text-sm ${
            activeItem === "Settings"
              ? "bg-panelSoft text-ink"
              : "text-muted hover:bg-panelSoft hover:text-ink"
          }`}
        >
          <Settings size={18} aria-hidden />
          <span className="hidden lg:inline">Settings</span>
        </button>
      </div>
    </aside>
  );
}
