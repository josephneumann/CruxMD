"use client";

import { useState } from "react";
import { Building2, Cross, Hospital, ChevronDown, ChevronRight } from "lucide-react";
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

type EncSortKey = "type" | "date" | "provider" | "location";

const CLASS_CONFIG: Record<string, { icon: typeof Building2; style: string }> = {
  AMB: { icon: Building2, style: "text-muted-foreground" },
  EMER: { icon: Cross, style: "text-[#C24E42] dark:text-[#D46F65]" },
  IMP: { icon: Hospital, style: "text-[#D9A036] dark:text-[#EBC47C]" },
};

export function EncountersTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<EncSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const showProvider = columnHasData(rows, "provider");
  const showLocation = columnHasData(rows, "location");

  let colCount = 2; // date + type always
  if (maxPriority >= 2 && showProvider) colCount++;
  if (maxPriority >= 3 && showLocation) colCount++;

  // Group by year — anything >5 years old goes into "Older"
  const currentYear = new Date().getFullYear();
  const cutoff = currentYear - 5;
  const yearMap = new Map<string, Record<string, unknown>[]>();
  for (const row of rows) {
    const date = String(row.date ?? "");
    const yearMatch = date.match(/\d{4}/);
    const rawYear = yearMatch ? yearMatch[0] : "Unknown";
    const groupKey = rawYear !== "Unknown" && Number(rawYear) < cutoff ? "Older" : rawYear;
    if (!yearMap.has(groupKey)) yearMap.set(groupKey, []);
    yearMap.get(groupKey)!.push(row);
  }

  // Sort years descending, but "Older" always last
  const sortedYears = [...yearMap.keys()].sort((a, b) => {
    if (a === "Older") return 1;
    if (b === "Older") return -1;
    return b.localeCompare(a);
  });

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
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
            <SortHeader
              label="Type"
              active={sortKey === "type"}
              direction={sortKey === "type" ? sortDir : null}
              onClick={() => toggle("type")}
            />
            {maxPriority >= 2 && showProvider && (
              <SortHeader
                label="Provider"
                active={sortKey === "provider"}
                direction={sortKey === "provider" ? sortDir : null}
                onClick={() => toggle("provider")}
              />
            )}
            {maxPriority >= 3 && showLocation && (
              <SortHeader
                label="Location"
                active={sortKey === "location"}
                direction={sortKey === "location" ? sortDir : null}
                onClick={() => toggle("location")}
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
              maxPriority={maxPriority}
              showProvider={showProvider}
              showLocation={showLocation}
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
  maxPriority,
  showProvider,
  showLocation,
  isExpanded,
  onToggle,
}: {
  year: string;
  rows: Record<string, unknown>[];
  colCount: number;
  maxPriority: ColumnPriority;
  showProvider: boolean;
  showLocation: boolean;
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
        rows.map((row, i) => {
          const cls = String(row.encounterClass ?? "AMB");
          const config = CLASS_CONFIG[cls] ?? CLASS_CONFIG.AMB;
          const Icon = config.icon;
          return (
            <tr key={`${year}-${i}`}>
              <td className="text-muted-foreground whitespace-nowrap">
                {String(row.date ?? "")}
              </td>
              <td>
                <span className={`inline-flex items-center gap-1.5 font-medium ${config.style}`}>
                  <Icon className="size-3 shrink-0" />
                  {String(row.type ?? "")}
                </span>
              </td>
              {maxPriority >= 2 && showProvider && (
                <td className="text-muted-foreground">{String(row.provider ?? "")}</td>
              )}
              {maxPriority >= 3 && showLocation && (
                <td className="text-muted-foreground">{String(row.location ?? "")}</td>
              )}
            </tr>
          );
        })}
    </>
  );
}
