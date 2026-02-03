"use client";

import { useCallback, useRef } from "react";
import Image from "next/image";
import type { DemoScenario } from "@/lib/demo-scenarios";

interface Tab {
  id: string;
  label: string;
  scenario: DemoScenario;
  avatar?: string;
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

  const activeTab = tabs.find((t) => t.id === activeId);

  return (
    <div className="relative mb-6">
      {/* Patient avatar — floats above tabs */}
      <div className="flex justify-center mb-4">
        <div className="relative h-16 w-16 rounded-full overflow-hidden ring-2 ring-border/50 shadow-lg">
          {activeTab?.avatar ? (
            <Image
              src={activeTab.avatar}
              alt={activeTab.scenario.patient}
              width={200}
              height={200}
              className="h-full w-full object-cover"
              unoptimized
            />
          ) : (
            <div className="h-full w-full bg-muted flex items-center justify-center">
              <span className="text-2xl text-muted-foreground/50">
                {activeTab?.scenario.patient.charAt(0)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Patient name */}
      <p className="text-center text-sm text-muted-foreground mb-4">
        {activeTab?.scenario.patient}
      </p>

      {/* Tab buttons */}
      <div
        role="tablist"
        aria-label="Demo scenarios"
        className="flex justify-center gap-1 border-b border-border"
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
    </div>
  );
}
