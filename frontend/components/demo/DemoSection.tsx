"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAutoplay, INTRO_PHASES } from "./useAutoplay";
import { useTypewriter } from "./useTypewriter";
import { DemoCanvas } from "./DemoCanvas";
import { DemoHomeScreen } from "./DemoHomeScreen";
import { ScenarioTabs } from "./ScenarioTabs";
import {
  heartFailureScenario,
  qtProlongationScenario,
  hcmScenario,
  hypoglycemiaScenario,
} from "@/lib/demo-scenarios";

const SCENARIO_TABS = [
  { id: "heart-failure", label: "Heart Failure", scenario: heartFailureScenario, avatar: "/brand/demo/avatar-margaret-chen.png" },
  { id: "qt-prolongation", label: "QT Prolongation", scenario: qtProlongationScenario, avatar: "/brand/demo/avatar-dorothy-williams.png" },
  { id: "hcm", label: "Young Athlete", scenario: hcmScenario },
  { id: "hypoglycemia", label: "Hypoglycemia", scenario: hypoglycemiaScenario },
];

export function DemoSection() {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [activeTabId, setActiveTabId] = useState(SCENARIO_TABS[0].id);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeScenario = useMemo(
    () => SCENARIO_TABS.find((t) => t.id === activeTabId)!.scenario,
    [activeTabId],
  );

  const { phase, reset: resetAutoplay, introMessage } = useAutoplay(canvasRef, activeScenario);

  const isIntro = phase < INTRO_PHASES;
  const isTyping = phase === 1;
  const isSubmitted = phase >= 2;

  // Typewriter text for the home screen input
  const typedText = useTypewriter(introMessage, isTyping);

  // Auto-scroll canvas to bottom as new content appears
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [phase, scrollToBottom]);

  const handleTabSelect = useCallback(
    (id: string) => {
      if (id === activeTabId) return;
      setActiveTabId(id);
      resetAutoplay();
    },
    [activeTabId, resetAutoplay],
  );

  return (
    <section className="relative px-8 py-16 md:py-24">
      <div className="max-w-4xl mx-auto">
        {/* Scenario tabs — fade in after intro */}
        <div
          className={`transition-all duration-700 ease-out ${
            isIntro ? "opacity-0 translate-y-2 pointer-events-none" : "opacity-100 translate-y-0"
          }`}
        >
          <ScenarioTabs
            tabs={SCENARIO_TABS}
            activeId={activeTabId}
            onSelect={handleTabSelect}
          />
        </div>

        {/* Canvas frame */}
        <div
          ref={canvasRef}
          className="rounded-xl border border-border bg-background"
          role="region"
          aria-label="Interactive demo preview"
        >
          <div
            ref={scrollRef}
            className="overflow-y-auto transition-[height] duration-700 ease-out"
            style={{ height: isIntro ? "auto" : "70vh", maxHeight: "70vh" }}
          >
            {/* Home screen — visible during intro phases */}
            {isIntro && (
              <DemoHomeScreen
                inputText={isTyping ? typedText : ""}
                submitted={isSubmitted}
              />
            )}

            {/* Canvas — visible after intro */}
            {!isIntro && (
              <div className="max-w-3xl mx-auto px-4 pt-8 pb-8 animate-in fade-in slide-in-from-bottom-2 duration-700 ease-out">
                <DemoCanvas scenario={activeScenario} phase={phase} onContentGrow={scrollToBottom} />
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
