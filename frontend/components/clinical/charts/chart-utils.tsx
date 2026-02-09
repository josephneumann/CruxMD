"use client";

import { useTheme } from "next-themes";
import type { MedTimelineRow } from "@/lib/types";

// -- Types ------------------------------------------------------------------

export interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    unit?: string;
    color?: string;
    payload?: Record<string, unknown>;
  }>;
  label?: string;
}

// -- Theme-aware chart colors ------------------------------------------------

export function useChartColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return {
    line: isDark ? "#E8E8E3" : "#1A1A18",
    grid: isDark ? "#4A4A48" : "#E5E4DF",
    tick: isDark ? "#BFBFBA" : "#666663",
    chart1: isDark ? "#4A9A88" : "#2F5E52",
    chart4: isDark ? "#749BB0" : "#4A7A8C",
    chart5: isDark ? "#66BB6A" : "#388E3C",
    warning: isDark ? "#EBC47C" : "#D9A036",
    critical: isDark ? "#D46F65" : "#C24E42",
    gradientFrom: isDark ? 0.45 : 0.3,
    gradientTo: isDark ? 0.05 : 0,
    bandSubtle: isDark ? 0.12 : 0.08,
    bandMedium: isDark ? 0.18 : 0.12,
  };
}

// -- Shared chart margin -----------------------------------------------------

export const CHART_MARGIN = { top: 10, right: 30, left: -10, bottom: 0 };

// -- Custom tooltip ----------------------------------------------------------

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const multi = payload.length > 1;
  return (
    <div className="rounded-lg border bg-card px-3 py-2 shadow-md">
      <p className="text-xs text-muted-foreground">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-1.5 mt-0.5">
          {multi && (
            <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
          )}
          {multi && <span className="text-sm text-muted-foreground">{entry.name}</span>}
          <span className="text-sm font-medium">{entry.value}{entry.unit ?? ""}</span>
        </div>
      ))}
      {typeof payload[0]?.payload?.event === "string" && (
        <p className="text-xs text-primary mt-1.5 border-t pt-1.5">
          {payload[0].payload.event}
        </p>
      )}
    </div>
  );
}

// -- Multi-medication timeline -----------------------------------------------

export function MultiMedTimeline({ rows }: { rows: MedTimelineRow[] }) {
  const c = useChartColors();
  return (
    <div className="mt-3 ml-4 mr-8">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 font-medium">
        Medications
      </p>
      <div className="space-y-px">
        {rows.map((row, ri) => (
          <div key={ri} className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground w-16 shrink-0 truncate text-right">
              {row.drug}
            </span>
            <div className="flex gap-px flex-1">
              {row.segments.map((seg, si) => (
                <div
                  key={si}
                  className="relative h-5 rounded-sm text-[10px] flex items-center px-1.5 truncate overflow-hidden"
                  style={{ flex: seg.flex }}
                >
                  {seg.active && (
                    <div
                      className="absolute inset-0 rounded-sm"
                      style={{ backgroundColor: c.chart1, opacity: 0.2 }}
                    />
                  )}
                  {seg.label && (
                    <span className="relative text-[10px] font-medium">{seg.label}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
