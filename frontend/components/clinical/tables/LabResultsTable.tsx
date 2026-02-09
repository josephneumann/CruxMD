"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { CardContent } from "@/components/ui/card";
import type { HL7Interpretation, HistoryPoint } from "@/lib/types";
import {
  TH,
  SortHeader,
  useSortState,
  sortRows,
  RangeBar,
  SparklineWithDelta,
} from "./table-primitives";

type LabSortKey = "test" | "value" | "date";

interface LabRow {
  test: string;
  value: number;
  unit: string;
  rangeLow: number;
  rangeHigh: number;
  interpretation: HL7Interpretation;
  date: string;
  history: HistoryPoint[];
  panel?: string;
}

function asLabRow(row: Record<string, unknown>): LabRow {
  return {
    test: String(row.test ?? ""),
    value: Number(row.value ?? 0),
    unit: String(row.unit ?? ""),
    rangeLow: Number(row.rangeLow ?? 0),
    rangeHigh: Number(row.rangeHigh ?? 0),
    interpretation: (row.interpretation as HL7Interpretation) ?? "N",
    date: String(row.date ?? ""),
    history: (row.history as HistoryPoint[]) ?? [],
    panel: row.panel ? String(row.panel) : undefined,
  };
}

function labAccessor(row: LabRow, key: string): string | number {
  if (key === "value") return row.value;
  return String(row[key as keyof LabRow] ?? "");
}

function LabResultRow({ row, indented }: { row: LabRow; indented?: boolean }) {
  const isCritical = row.interpretation === "HH" || row.interpretation === "LL";
  const isAbnormal = row.interpretation !== "N";
  const textSize = indented ? "text-[13px]" : "";
  return (
    <tr className={isCritical ? "bg-[#C24E42]/5" : ""}>
      <td className={`px-3 py-2.5 font-medium ${textSize} ${indented ? "pl-8" : ""}`}>
        {row.test}
      </td>
      <td className={`px-3 py-2.5 ${textSize}`}>
        <span
          className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}
        >
          {row.value} <span className="text-muted-foreground font-normal">{row.unit}</span>
        </span>
      </td>
      <td className="px-3 py-2.5">
        <RangeBar
          value={row.value}
          low={row.rangeLow}
          high={row.rangeHigh}
          interpretation={row.interpretation}
        />
      </td>
      <td className="px-3 py-2.5">
        {row.history.length > 0 && (
          <SparklineWithDelta
            data={row.history}
            interpretation={row.interpretation}
            unit={row.unit}
          />
        )}
      </td>
      <td className="px-3 py-2.5 text-muted-foreground">{row.date}</td>
    </tr>
  );
}

export function LabResultsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<LabSortKey>();
  const labRows = rows.map(asLabRow);

  // Group into panels and standalone
  const panelMap = new Map<string, LabRow[]>();
  const standalone: LabRow[] = [];

  for (const row of labRows) {
    if (row.panel) {
      const existing = panelMap.get(row.panel) ?? [];
      existing.push(row);
      panelMap.set(row.panel, existing);
    } else {
      standalone.push(row);
    }
  }

  // Sort within panels and standalone
  const sortedStandalone = sortRows(standalone, sortKey, sortDir, labAccessor);
  const sortedPanels = Array.from(panelMap.entries()).map(([name, results]) => ({
    name,
    results: sortRows(results, sortKey, sortDir, labAccessor),
  }));

  const [expandedPanels, setExpandedPanels] = useState<Set<string>>(() => {
    // Default: first panel expanded
    const first = sortedPanels[0]?.name;
    return first ? new Set([first]) : new Set();
  });

  const togglePanel = (name: string) => {
    setExpandedPanels((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <CardContent className="p-0 overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Test"
              active={sortKey === "test"}
              direction={sortKey === "test" ? sortDir : null}
              onClick={() => toggle("test")}
            />
            <SortHeader
              label="Result"
              active={sortKey === "value"}
              direction={sortKey === "value" ? sortDir : null}
              onClick={() => toggle("value")}
            />
            <th className={TH}>Reference Range</th>
            <th className={TH}>Trend</th>
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
          </tr>
        </thead>
        <tbody className="divide-y">
          {/* Standalone results */}
          {sortedStandalone.map((row) => (
            <LabResultRow key={row.test} row={row} />
          ))}
          {/* Panel groups */}
          {sortedPanels.map((panel) => {
            const isExpanded = expandedPanels.has(panel.name);
            const PanelChevron = isExpanded ? ChevronDown : ChevronRight;
            return [
              <tr
                key={`panel-${panel.name}`}
                className="bg-muted/20 cursor-pointer hover:bg-muted/40"
                onClick={() => togglePanel(panel.name)}
              >
                <td colSpan={5} className="px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span>
                      <span className="font-medium">{panel.name}</span>{" "}
                      <span className="text-xs text-muted-foreground">
                        ({panel.results.length} components)
                      </span>
                    </span>
                    <PanelChevron className="size-4 text-muted-foreground" />
                  </div>
                </td>
              </tr>,
              ...(isExpanded
                ? panel.results.map((row) => (
                    <LabResultRow
                      key={`${panel.name}-${row.test}`}
                      row={row}
                      indented
                    />
                  ))
                : []),
            ];
          })}
        </tbody>
      </table>
    </CardContent>
  );
}
