"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  useResponsiveColumns,
  tableClass,
  type ColumnPriority,
} from "./table-primitives";

type ImmSortKey = "vaccine" | "date" | "location";

export function ImmunizationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ImmSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const colCount =
    2 + // vaccine + date always
    (maxPriority >= 2 ? 1 : 0); // location

  // Group by vaccine name
  const vaccineMap = new Map<string, Record<string, unknown>[]>();
  for (const row of rows) {
    const name = String(row.vaccine ?? "Unknown");
    if (!vaccineMap.has(name)) vaccineMap.set(name, []);
    vaccineMap.get(name)!.push(row);
  }

  // Sort groups alphabetically
  const groupKeys = [...vaccineMap.keys()].sort((a, b) => a.localeCompare(b));

  // Sort rows within each group by date descending (most recent first)
  const sortedGroups = groupKeys.map((name) => {
    const groupRows = vaccineMap.get(name)!;
    const sorted = sortKey
      ? sortRows(groupRows, sortKey, sortDir, (row, key) => String(row[key] ?? ""))
      : [...groupRows].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")));
    return { name, rows: sorted };
  });

  // All groups expanded by default
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(groupKeys));
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
              label="Vaccine"
              active={sortKey === "vaccine"}
              direction={sortKey === "vaccine" ? sortDir : null}
              onClick={() => toggle("vaccine")}
            />
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
            {maxPriority >= 2 && (
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
          {sortedGroups.map(({ name, rows: groupRows }) => (
            <VaccineGroup
              key={name}
              name={name}
              rows={groupRows}
              colCount={colCount}
              maxPriority={maxPriority}
              isExpanded={expanded.has(name)}
              onToggle={() => toggleGroup(name)}
            />
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

function VaccineGroup({
  name,
  rows,
  colCount,
  maxPriority,
  isExpanded,
  onToggle,
}: {
  name: string;
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
              {name}
            </span>
            <span className="text-xs text-muted-foreground/60">({rows.length})</span>
          </div>
        </td>
      </tr>
      {isExpanded &&
        rows.map((row, i) => (
          <tr key={`${name}-${i}`}>
            <td className="font-medium">{String(row.vaccine ?? "")}</td>
            <td className="text-muted-foreground">{String(row.date ?? "")}</td>
            {maxPriority >= 2 && (
              <td className="text-muted-foreground">{String(row.location ?? "")}</td>
            )}
          </tr>
        ))}
    </>
  );
}
