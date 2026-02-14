"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  columnHasData,
  useResponsiveColumns,
  tableClass,
  type ColumnPriority,
} from "./table-primitives";

type ProcSortKey = "procedure" | "date" | "location" | "reason";

export function ProceduresTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ProcSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const showLocation = maxPriority >= 3 && columnHasData(rows, "location");
  const showReason = maxPriority >= 3 && columnHasData(rows, "reason");

  let colCount = 2; // procedure + date always
  if (showLocation) colCount++;
  if (showReason) colCount++;

  // Group by year — extract from formatted date like "Sep 17, 2025"
  const yearMap = new Map<string, Record<string, unknown>[]>();
  for (const row of rows) {
    const date = String(row.date ?? "");
    const yearMatch = date.match(/\d{4}/);
    const year = yearMatch ? yearMatch[0] : "Unknown";
    if (!yearMap.has(year)) yearMap.set(year, []);
    yearMap.get(year)!.push(row);
  }

  const sortedYears = [...yearMap.keys()].sort((a, b) => b.localeCompare(a));

  const sortedGroups = sortedYears.map((year) => ({
    year,
    rows: sortRows(yearMap.get(year)!, sortKey, sortDir, (row, key) =>
      String(row[key] ?? ""),
    ),
  }));

  // Most recent year expanded, rest collapsed
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(sortedYears.length > 0 ? [sortedYears[0]] : []),
  );
  const toggleGroup = (group: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className={tableClass(maxPriority)}>
        <colgroup>
          <col className="w-[35%]" />
          <col />
          {showLocation && <col className="w-[25%]" />}
          {showReason && <col className="w-[25%]" />}
        </colgroup>
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Procedure"
              active={sortKey === "procedure"}
              direction={sortKey === "procedure" ? sortDir : null}
              onClick={() => toggle("procedure")}
            />
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
            {showLocation && (
              <SortHeader
                label="Location"
                active={sortKey === "location"}
                direction={sortKey === "location" ? sortDir : null}
                onClick={() => toggle("location")}
              />
            )}
            {showReason && (
              <SortHeader
                label="Reason"
                active={sortKey === "reason"}
                direction={sortKey === "reason" ? sortDir : null}
                onClick={() => toggle("reason")}
              />
            )}
          </tr>
        </thead>
        <tbody>
          {sortedGroups.map(({ year, rows: groupRows }) => (
            <YearGroup
              key={year}
              year={year}
              rows={groupRows}
              colCount={colCount}
              showLocation={showLocation}
              showReason={showReason}
              isExpanded={expanded.has(year)}
              onToggle={() => toggleGroup(year)}
            />
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

function YearGroup({
  year,
  rows,
  colCount,
  showLocation,
  showReason,
  isExpanded,
  onToggle,
}: {
  year: string;
  rows: Record<string, unknown>[];
  colCount: number;
  showLocation: boolean;
  showReason: boolean;
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
              {year}
            </span>
            <span className="text-xs text-muted-foreground/60">({rows.length})</span>
          </div>
        </td>
      </tr>
      {isExpanded &&
        rows.map((row, i) => (
          <tr key={`${year}-${i}`}>
            <td className="font-medium">{String(row.procedure ?? "")}</td>
            <td className="text-muted-foreground whitespace-nowrap">
              {String(row.date ?? "")}
            </td>
            {showLocation && (
              <td className="text-muted-foreground">{String(row.location ?? "")}</td>
            )}
            {showReason && (
              <td className="text-muted-foreground">
                {row.reason ? String(row.reason) : <span className="italic">&mdash;</span>}
              </td>
            )}
          </tr>
        ))}
    </>
  );
}
