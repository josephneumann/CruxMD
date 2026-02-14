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
  useResponsiveColumns,
  tableClass,
  type ColumnPriority,
} from "./table-primitives";

type LabSortKey = "test" | "value";

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

/** Format "2024-03-15" as "Mar 15, 2024" */
function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function LabResultRow({
  row,
  maxPriority,
}: {
  row: LabRow;
  maxPriority: ColumnPriority;
}) {
  const isCritical = row.interpretation === "HH" || row.interpretation === "LL";
  const isAbnormal = row.interpretation !== "N";
  return (
    <tr className={isCritical ? "bg-[#C24E42]/5" : ""}>
      <td className="font-medium">{row.test}</td>
      <td>
        <span
          className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}
        >
          {row.value} <span className="text-muted-foreground font-normal">{row.unit}</span>
        </span>
      </td>
      {maxPriority >= 2 && (
        <td>
          {row.history.length > 0 && (
            <SparklineWithDelta
              data={row.history}
              interpretation={row.interpretation}
              unit={row.unit}
            />
          )}
        </td>
      )}
      {maxPriority >= 3 && (
        <td>
          <RangeBar
            value={row.value}
            low={row.rangeLow}
            high={row.rangeHigh}
            interpretation={row.interpretation}
          />
        </td>
      )}
    </tr>
  );
}

export function LabResultsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<LabSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();
  const labRows = rows.map(asLabRow);

  // Count visible columns for colSpan on date dividers
  const colCount = 2 + (maxPriority >= 2 ? 1 : 0) + (maxPriority >= 3 ? 1 : 0);

  // Group by date
  const dateMap = new Map<string, LabRow[]>();
  for (const row of labRows) {
    const key = row.date || "Unknown";
    const existing = dateMap.get(key) ?? [];
    existing.push(row);
    dateMap.set(key, existing);
  }

  // Sort date groups descending (most recent first)
  const sortedDates = Array.from(dateMap.keys()).sort((a, b) => b.localeCompare(a));

  // Default: most recent date expanded, rest collapsed
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(sortedDates.length > 0 ? [sortedDates[0]] : []),
  );

  const toggleDate = (date: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  };

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className={tableClass(maxPriority)}>
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
            {maxPriority >= 2 && <th className={TH}>Trend</th>}
            {maxPriority >= 3 && <th className={TH}>Reference Range</th>}
          </tr>
        </thead>
        <tbody>
          {sortedDates.map((date) => {
            const groupRows = sortRows(dateMap.get(date)!, sortKey, sortDir, labAccessor);
            return (
              <DateGroup
                key={date}
                date={date}
                rows={groupRows}
                colCount={colCount}
                maxPriority={maxPriority}
                isExpanded={expanded.has(date)}
                onToggle={() => toggleDate(date)}
              />
            );
          })}
        </tbody>
      </table>
    </CardContent>
  );
}

function DateGroup({
  date,
  rows,
  colCount,
  maxPriority,
  isExpanded,
  onToggle,
}: {
  date: string;
  rows: LabRow[];
  colCount: number;
  maxPriority: ColumnPriority;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Chevron = isExpanded ? ChevronDown : ChevronRight;
  return (
    <>
      {/* Date divider — clickable */}
      <tr className="bg-muted/20 cursor-pointer hover:bg-muted/40" onClick={onToggle}>
        <td colSpan={colCount} className="px-3 py-1.5">
          <div className="flex items-center gap-1.5">
            <Chevron className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {formatDate(date)}
            </span>
            <span className="text-xs text-muted-foreground/60">
              ({rows.length})
            </span>
          </div>
        </td>
      </tr>
      {/* Rows in this date group */}
      {isExpanded &&
        rows.map((row) => (
          <LabResultRow key={`${date}-${row.test}`} row={row} maxPriority={maxPriority} />
        ))}
    </>
  );
}
