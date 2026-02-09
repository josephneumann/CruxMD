"use client";

import type { ClinicalVisualization as ClinicalVizType } from "@/lib/types";
import { TrendChart } from "./charts/TrendChart";
import { EncounterTimeline } from "./charts/EncounterTimeline";

export function ClinicalVisualization({ viz }: { viz: ClinicalVizType }) {
  switch (viz.type) {
    case "trend_chart":
      return <TrendChart viz={viz} />;
    case "encounter_timeline":
      return <EncounterTimeline viz={viz} />;
    default:
      return null;
  }
}
