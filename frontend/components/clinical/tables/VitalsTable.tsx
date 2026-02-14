"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { CardContent } from "@/components/ui/card";
import type { HL7Interpretation, HistoryPoint } from "@/lib/types";
import {
  TH,
  CELL_PLACEHOLDER,
  SortHeader,
  useSortState,
  sortRows,
  RangeBar,
  SparklineWithDelta,
  useResponsiveColumns,
  tableClass,
  type ColumnPriority,
} from "./table-primitives";

type VitalSortKey = "vital" | "value" | "date";

interface ComponentRow {
  vital: string;
  value: string;
  numericValue: number | null;
  unit: string;
  rangeLow: number | null;
  rangeHigh: number | null;
  history: HistoryPoint[];
  interpretation: HL7Interpretation;
}

// Fixed ordering of vitals by LOINC code within each group
const VITAL_GROUPS: { label: string; loincs: string[] }[] = [
  {
    label: "Cardiac & Respiratory",
    loincs: [
      "85354-9", // Blood pressure
      "8867-4",  // Heart rate
      "9279-1",  // Respiratory rate
    ],
  },
  {
    label: "Body Composition",
    loincs: [
      "8302-2",  // Body height
      "29463-7", // Body weight
      "39156-5", // BMI
      "59576-9", // BMI percentile
    ],
  },
];

const _KNOWN_LOINCS = new Set(VITAL_GROUPS.flatMap((g) => g.loincs));

function VitalRow({
  row,
  maxPriority,
  indent,
}: {
  row: Record<string, unknown>;
  maxPriority: ColumnPriority;
  indent?: boolean;
}) {
  const vital = String(row.vital ?? "");
  const interpretation = row.interpretation as HL7Interpretation | undefined;
  const isCritical = interpretation === "HH" || interpretation === "LL";
  const isAbnormal = interpretation && interpretation !== "N";
  const hasRange =
    row.rangeLow != null &&
    row.rangeHigh != null &&
    interpretation != null;
  const hasHistory =
    Array.isArray(row.history) &&
    row.history.length > 0;

  return (
    <tr>
      <td className={indent ? "text-muted-foreground pl-10" : "font-medium"}>
        {indent && <span className="text-muted-foreground/40 mr-2">└</span>}
        {vital}
      </td>
      <td className="whitespace-nowrap">
        <span
          className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}
        >
          {String(row.value ?? "")}{" "}
          <span className="text-muted-foreground font-normal">
            {String(row.unit ?? "")}
          </span>
        </span>
      </td>
      {maxPriority >= 2 && (
        <td>
          {hasRange ? (
            <RangeBar
              value={Number(row.numericValue ?? 0)}
              low={Number(row.rangeLow)}
              high={Number(row.rangeHigh)}
              interpretation={interpretation!}
            />
          ) : (
            CELL_PLACEHOLDER
          )}
        </td>
      )}
      {maxPriority >= 3 && (
        <td>
          {hasHistory ? (
            <SparklineWithDelta
              data={row.history as HistoryPoint[]}
              interpretation={interpretation ?? "N"}
              unit={String(row.unit ?? "")}
            />
          ) : (
            CELL_PLACEHOLDER
          )}
        </td>
      )}
      <td className="text-muted-foreground whitespace-nowrap">
        {String(row.date ?? "")}
      </td>
    </tr>
  );
}

function VitalRowWithComponents({
  row,
  maxPriority,
}: {
  row: Record<string, unknown>;
  maxPriority: ColumnPriority;
}) {
  const components = row.components as ComponentRow[] | undefined;
  return (
    <>
      <VitalRow row={row} maxPriority={maxPriority} />
      {components?.map((comp) => (
        <VitalRow
          key={comp.vital}
          row={comp as unknown as Record<string, unknown>}
          maxPriority={maxPriority}
          indent
        />
      ))}
    </>
  );
}

export function VitalsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<VitalSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  // Index rows by LOINC for fixed ordering
  const byLoinc = new Map<string, Record<string, unknown>>();
  const otherRows: Record<string, unknown>[] = [];
  for (const row of rows) {
    const loinc = String(row.loinc ?? "");
    if (loinc && _KNOWN_LOINCS.has(loinc)) {
      byLoinc.set(loinc, row);
    } else {
      otherRows.push(row);
    }
  }

  // Build groups with only present vitals
  const groups: { label: string; rows: Record<string, unknown>[] }[] = [];
  for (const group of VITAL_GROUPS) {
    const groupRows: Record<string, unknown>[] = [];
    for (const loinc of group.loincs) {
      const row = byLoinc.get(loinc);
      if (row) groupRows.push(row);
    }
    if (groupRows.length > 0) {
      groups.push({ label: group.label, rows: groupRows });
    }
  }
  if (otherRows.length > 0) {
    groups.push({ label: "Other", rows: otherRows });
  }

  // Count columns for colSpan: vital + value + date always, +range at P2, +trend at P3
  const colCount =
    3 + (maxPriority >= 2 ? 1 : 0) + (maxPriority >= 3 ? 1 : 0);

  // All groups expanded by default
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(groups.map((g) => g.label)),
  );
  const toggleGroup = (label: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className={tableClass(maxPriority)}>
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Vital Sign"
              active={sortKey === "vital"}
              direction={sortKey === "vital" ? sortDir : null}
              onClick={() => toggle("vital")}
            />
            <SortHeader
              label="Value"
              active={sortKey === "value"}
              direction={sortKey === "value" ? sortDir : null}
              onClick={() => toggle("value")}
            />
            {maxPriority >= 2 && <th className={TH}>Reference Range</th>}
            {maxPriority >= 3 && <th className={TH}>Trend</th>}
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
          </tr>
        </thead>
        <tbody>
          {groups.map(({ label, rows: groupRows }) => {
            const sorted = sortKey
              ? sortRows(groupRows, sortKey, sortDir, (row, key) => {
                  if (key === "value") return Number(row.numericValue ?? 0);
                  return String(row[key] ?? "");
                })
              : groupRows;

            const Chevron = expanded.has(label) ? ChevronDown : ChevronRight;
            return (
              <VitalGroup
                key={label}
                label={label}
                rows={sorted}
                colCount={colCount}
                maxPriority={maxPriority}
                isExpanded={expanded.has(label)}
                onToggle={() => toggleGroup(label)}
              />
            );
          })}
        </tbody>
      </table>
    </CardContent>
  );
}

function VitalGroup({
  label,
  rows,
  colCount,
  maxPriority,
  isExpanded,
  onToggle,
}: {
  label: string;
  rows: Record<string, unknown>[];
  colCount: number;
  maxPriority: ColumnPriority;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Chevron = isExpanded ? ChevronDown : ChevronRight;
  return (
    <>
      <tr className="bg-muted/20 cursor-pointer hover:bg-muted/40" onClick={onToggle}>
        <td colSpan={colCount}>
          <div className="flex items-center gap-1.5">
            <Chevron className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {label}
            </span>
            <span className="text-xs text-muted-foreground/60">({rows.length})</span>
          </div>
        </td>
      </tr>
      {isExpanded &&
        rows.map((row, i) => (
          <VitalRowWithComponents
            key={`${label}-${i}`}
            row={row}
            maxPriority={maxPriority}
          />
        ))}
    </>
  );
}
