"use client";

import { CardContent } from "@/components/ui/card";
import { SortHeader, useSortState, sortRows, useResponsiveColumns } from "./table-primitives";

type ImmSortKey = "vaccine" | "date" | "location";

export function ImmunizationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ImmSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            {/* P1: Vaccine */}
            <SortHeader
              label="Vaccine"
              active={sortKey === "vaccine"}
              direction={sortKey === "vaccine" ? sortDir : null}
              onClick={() => toggle("vaccine")}
            />
            {/* P1: Date */}
            <SortHeader
              label="Date"
              active={sortKey === "date"}
              direction={sortKey === "date" ? sortDir : null}
              onClick={() => toggle("date")}
            />
            {/* P2: Location */}
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
        <tbody className="divide-y">
          {sorted.map((row, i) => (
            <tr key={`${row.vaccine}-${i}`}>
              <td className="px-3 py-2 text-sm font-medium">{String(row.vaccine ?? "")}</td>
              <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.date ?? "")}</td>
              {maxPriority >= 2 && (
                <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.location ?? "")}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
