"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useScrollPhase } from "./useScrollPhase";
import { DemoCanvas } from "./DemoCanvas";
import { ScenarioTabs } from "./ScenarioTabs";
import {
  heartFailureScenario,
  qtProlongationScenario,
  hcmScenario,
  hypoglycemiaScenario,
} from "@/lib/demo-scenarios";

const SCENARIO_TABS = [
  { id: "heart-failure", label: "Heart Failure", scenario: heartFailureScenario },
  { id: "qt-prolongation", label: "QT Prolongation", scenario: qtProlongationScenario },
  { id: "hcm", label: "Young Athlete", scenario: hcmScenario },
  { id: "hypoglycemia", label: "Hypoglycemia", scenario: hypoglycemiaScenario },
];

export function DemoSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const scrollDriverRef = useRef<HTMLDivElement>(null);
  const [activeTabId, setActiveTabId] = useState(SCENARIO_TABS[0].id);
  const { phase, reset: resetPhase } = useScrollPhase(scrollDriverRef);

  const activeScenario = useMemo(
    () => SCENARIO_TABS.find((t) => t.id === activeTabId)!.scenario,
    [activeTabId],
  );

  const handleTabSelect = useCallback(
    (id: string) => {
      if (id === activeTabId) return;
      setActiveTabId(id);
      resetPhase();
      sectionRef.current?.scrollIntoView({ behavior: "smooth" });
    },
    [activeTabId, resetPhase],
  );

  return (
    <section ref={sectionRef} className="relative px-8 py-16 md:py-24">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
          See CruxMD in action
        </h2>

        <ScenarioTabs
          tabs={SCENARIO_TABS}
          activeId={activeTabId}
          onSelect={handleTabSelect}
        />

        {/* Scroll-driven layout */}
        <div ref={scrollDriverRef} className="relative flex gap-8" style={{ height: "600vh" }}>
          {/* Scroll driver (invisible — provides scroll height) */}
          <div className="w-[45%] shrink-0" aria-hidden="true" />

          {/* Sticky canvas */}
          <div
            className="w-[55%] shrink-0 sticky top-[80px] self-start"
            style={{ maxHeight: "calc(100vh - 100px)" }}
            role="region"
            aria-label="Interactive demo preview"
          >
            <div className="rounded-xl border border-border bg-background overflow-y-auto" style={{ maxHeight: "calc(100vh - 120px)" }}>
              <div className="max-w-3xl mx-auto px-4 pt-8 pb-8">
                <DemoCanvas scenario={activeScenario} phase={phase} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
