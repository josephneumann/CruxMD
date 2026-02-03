"use client";

import { useRef } from "react";
import { useScrollPhase } from "./useScrollPhase";
import { DemoCanvas } from "./DemoCanvas";
import { heartFailureScenario } from "@/lib/demo-scenarios";

export function DemoSection() {
  const scrollDriverRef = useRef<HTMLDivElement>(null);
  const { phase } = useScrollPhase(scrollDriverRef);

  return (
    <section className="relative px-8 py-16 md:py-24">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
          See CruxMD in action
        </h2>

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
                <DemoCanvas scenario={heartFailureScenario} phase={phase} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
