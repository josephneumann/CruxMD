"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import {
  ChevronDown,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Building2,
  Cross,
  Hospital,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  YAxis,
  Tooltip,
} from "recharts";
import type { HL7Interpretation, HistoryPoint } from "@/lib/types";

// -- Theme-aware colors -------------------------------------------------------

export function useTableColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return {
    chart1: isDark ? "#4A9A88" : "#2F5E52",
    warning: isDark ? "#EBC47C" : "#D9A036",
    critical: isDark ? "#D46F65" : "#C24E42",
    rangeBg: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
    rangeNormal: isDark ? "#66BB6A" : "#388E3C",
    rangeWarning: isDark ? "#EBC47C" : "#D9A036",
    rangeCritical: isDark ? "#D46F65" : "#C24E42",
  };
}

// -- Table header cell --------------------------------------------------------

export const TH =
  "text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider";

// -- Collapsible card wrapper -------------------------------------------------

export function CollapsibleTableCard({
  icon: Icon,
  title,
  count,
  countLabel,
  defaultExpanded = true,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  count: number;
  countLabel: string;
  defaultExpanded?: boolean;
  children: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const Chevron = expanded ? ChevronDown : ChevronRight;
  return (
    <Card className="py-0 gap-0">
      <div
        className={`flex items-center gap-2 px-4 py-2 cursor-pointer select-none hover:bg-muted/20 transition-colors ${expanded ? "border-b" : ""}`}
        onClick={() => setExpanded(!expanded)}
      >
        <Icon className="size-4 text-muted-foreground" />
        <span className="text-sm font-medium">{title}</span>
        {!expanded && (
          <span className="text-xs text-muted-foreground">
            ({count} {countLabel})
          </span>
        )}
        <Chevron className="size-4 text-muted-foreground ml-auto" />
      </div>
      {expanded && children}
    </Card>
  );
}

// -- Sortable column infrastructure -------------------------------------------

export type SortDir = "asc" | "desc" | null;

export function SortHeader({
  label,
  active,
  direction,
  onClick,
}: {
  label: string;
  active: boolean;
  direction: SortDir;
  onClick: () => void;
}) {
  const Icon = active
    ? direction === "asc"
      ? ArrowUp
      : ArrowDown
    : ArrowUpDown;
  return (
    <th
      className={`${TH} cursor-pointer select-none hover:text-foreground transition-colors`}
      onClick={onClick}
    >
      <div className="flex items-center gap-1">
        {label}
        <Icon className={`size-3 ${active ? "text-foreground" : ""}`} />
      </div>
    </th>
  );
}

export function useSortState<K extends string>(defaultKey?: K) {
  const [sortKey, setSortKey] = useState<K | null>(defaultKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const toggle = (key: K) => {
    if (sortKey === key) {
      if (sortDir === "asc") setSortDir("desc");
      else if (sortDir === "desc") {
        setSortKey(null);
        setSortDir(null);
      } else setSortDir("asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  return { sortKey, sortDir, toggle };
}

export function sortRows<T>(
  rows: T[],
  key: string | null,
  dir: SortDir,
  accessor: (row: T, key: string) => string | number,
): T[] {
  if (!key || !dir) return rows;
  return [...rows].sort((a, b) => {
    const va = accessor(a, key);
    const vb = accessor(b, key);
    if (typeof va === "number" && typeof vb === "number")
      return dir === "asc" ? va - vb : vb - va;
    return dir === "asc"
      ? String(va).localeCompare(String(vb))
      : String(vb).localeCompare(String(va));
  });
}

// -- Range bar ----------------------------------------------------------------

export function RangeBar({
  value,
  low,
  high,
  interpretation,
}: {
  value: number;
  low: number;
  high: number;
  interpretation: HL7Interpretation;
}) {
  const c = useTableColors();

  const rangeSpan = high - low;
  const padding = rangeSpan * 0.3;
  const displayLow = low - padding;
  const displayHigh = high + padding;
  const displaySpan = displayHigh - displayLow;

  const position = Math.max(
    3,
    Math.min(97, ((value - displayLow) / displaySpan) * 100),
  );
  const rangeStart = ((low - displayLow) / displaySpan) * 100;
  const rangeWidth = ((high - low) / displaySpan) * 100;

  const isCritical = interpretation === "HH" || interpretation === "LL";
  const isAbnormal = interpretation === "H" || interpretation === "L";
  const markerColor = isCritical
    ? c.rangeCritical
    : isAbnormal
      ? c.rangeWarning
      : c.rangeNormal;

  return (
    <div className="flex items-center gap-2.5 min-w-[160px]">
      <div className="relative flex-1 h-2">
        <div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: c.rangeBg }}
        />
        <div
          className="absolute top-0 h-full rounded-full"
          style={{
            left: `${rangeStart}%`,
            width: `${rangeWidth}%`,
            backgroundColor: c.rangeNormal,
            opacity: 0.2,
          }}
        />
        <div
          className="absolute top-1/2 size-2.5 rounded-full border-2 border-background"
          style={{
            left: `${position}%`,
            transform: "translate(-50%, -50%)",
            backgroundColor: markerColor,
          }}
        />
      </div>
      <span className="text-[11px] text-muted-foreground tabular-nums whitespace-nowrap">
        {low}&ndash;{high}
      </span>
    </div>
  );
}

// -- Sparkline tooltip ---------------------------------------------------------

function SparklineTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: { value: number; date: string } }>;
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const { value, date } = payload[0].payload;
  return (
    <div className="rounded border bg-card px-2 py-1 shadow-md text-[11px] leading-snug">
      <p className="font-medium tabular-nums">{value}</p>
      <p className="text-muted-foreground">{date}</p>
    </div>
  );
}

// -- Sparkline with delta -----------------------------------------------------

export function SparklineWithDelta({
  data,
  interpretation,
  unit,
}: {
  data: HistoryPoint[];
  interpretation: HL7Interpretation;
  unit: string;
}) {
  const c = useTableColors();

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || 0.5;
  const domain: [number, number] = [min - pad, max + pad];

  const isCritical = interpretation === "HH" || interpretation === "LL";
  const isAbnormal = interpretation === "H" || interpretation === "L";
  const strokeColor = isCritical
    ? c.critical
    : isAbnormal
      ? c.warning
      : c.chart1;

  const first = values[0];
  const last = values[values.length - 1];
  const pctChange =
    first !== 0 ? Math.round(((last - first) / first) * 100) : 0;
  const arrow = pctChange > 0 ? "\u2191" : pctChange < 0 ? "\u2193" : "\u2192";
  const deltaColor = isCritical
    ? "text-[#C24E42]"
    : isAbnormal
      ? "text-[#D9A036]"
      : "text-muted-foreground";

  const sinceDate = data[0].date;

  return (
    <div className="flex items-center gap-2">
      <div className="w-[72px] h-[28px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
          >
            <YAxis domain={domain} hide />
            <Tooltip
              content={<SparklineTooltip />}
              cursor={false}
              position={{ y: -38 }}
              allowEscapeViewBox={{ x: true, y: true }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3, fill: strokeColor, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-[11px] leading-tight whitespace-nowrap">
        <span className={`font-medium ${deltaColor}`}>
          {arrow} {Math.abs(pctChange)}%
        </span>
        <br />
        <span className="text-muted-foreground">since {sinceDate}</span>
      </div>
    </div>
  );
}

// -- Status text components ---------------------------------------------------

export function MedStatusBadge({
  status,
}: {
  status: "active" | "completed";
}) {
  if (status === "active") {
    return (
      <span className="text-xs text-[#388E3C] dark:text-[#66BB6A]">
        Active
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">Completed</span>;
}

export function ConditionStatusText({
  status,
}: {
  status: "active" | "resolved";
}) {
  if (status === "active") {
    return (
      <span className="text-xs text-[#388E3C] dark:text-[#66BB6A]">
        Active
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">Resolved</span>;
}

export function CriticalityText({
  criticality,
}: {
  criticality: "high" | "low";
}) {
  if (criticality === "high") {
    return (
      <span className="text-xs text-[#C24E42] dark:text-[#D46F65]">High</span>
    );
  }
  return <span className="text-xs text-muted-foreground">Low</span>;
}

export function AllergyStatusText({
  status,
}: {
  status: "active" | "inactive";
}) {
  if (status === "active") {
    return (
      <span className="text-xs text-[#388E3C] dark:text-[#66BB6A]">
        Active
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">Inactive</span>;
}

export function EncounterClassText({
  encounterClass,
}: {
  encounterClass: "AMB" | "EMER" | "IMP";
}) {
  const config: Record<
    string,
    {
      label: string;
      style: string;
      icon: React.ComponentType<{ className?: string }>;
    }
  > = {
    AMB: {
      label: "Ambulatory",
      style: "text-xs text-muted-foreground",
      icon: Building2,
    },
    EMER: {
      label: "Emergency",
      style: "text-xs text-[#C24E42] dark:text-[#D46F65]",
      icon: Cross,
    },
    IMP: {
      label: "Inpatient",
      style: "text-xs text-[#D9A036] dark:text-[#EBC47C]",
      icon: Hospital,
    },
  };
  const { label, style, icon: Icon } = config[encounterClass] ?? config.AMB;
  return (
    <span className={style}>
      <span className="inline-flex items-center gap-1">
        <Icon className="size-3" />
        {label}
      </span>
    </span>
  );
}
