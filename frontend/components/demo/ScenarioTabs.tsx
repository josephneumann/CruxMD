"use client";

import { useCallback, useRef } from "react";
import type { DemoScenario } from "@/lib/demo-scenarios";

interface Tab {
  id: string;
  label: string;
  scenario: DemoScenario;
}

interface ScenarioTabsProps {
  tabs: Tab[];
  activeId: string;
  onSelect: (id: string) => void;
}

export function ScenarioTabs({ tabs, activeId, onSelect }: ScenarioTabsProps) {
  const lastClickRef = useRef(0);

  const handleClick = useCallback(
    (id: string) => {
      const now = Date.now();
      if (now - lastClickRef.current < 300) return;
      lastClickRef.current = now;
      onSelect(id);
    },
    [onSelect],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIndex = tabs.findIndex((t) => t.id === activeId);
      let nextIndex = -1;

      if (e.key === "ArrowRight") {
        nextIndex = (currentIndex + 1) % tabs.length;
      } else if (e.key === "ArrowLeft") {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (e.key === "Home") {
        nextIndex = 0;
      } else if (e.key === "End") {
        nextIndex = tabs.length - 1;
      }

      if (nextIndex >= 0) {
        e.preventDefault();
        handleClick(tabs[nextIndex].id);
        // Focus the new tab button
        const tablist = e.currentTarget;
        const buttons = tablist.querySelectorAll<HTMLButtonElement>('[role="tab"]');
        buttons[nextIndex]?.focus();
      }
    },
    [tabs, activeId, handleClick],
  );

  return (
    <div
      role="tablist"
      aria-label="Demo scenarios"
      className="flex gap-1 border-b border-border mb-6"
      onKeyDown={handleKeyDown}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => handleClick(tab.id)}
            className={`px-4 py-2.5 text-sm transition-colors relative whitespace-nowrap ${
              isActive
                ? "font-semibold text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        );
      })}
    </div>
  );
}
