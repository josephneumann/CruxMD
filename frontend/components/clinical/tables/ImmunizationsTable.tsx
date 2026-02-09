"use client";

import { CardContent } from "@/components/ui/card";
import { SortHeader, useSortState, sortRows } from "./table-primitives";

type ImmSortKey = "vaccine" | "date" | "location";

const cols: { key: ImmSortKey; label: string }[] = [
  { key: "vaccine", label: "Vaccine" },
  { key: "date", label: "Date" },
  { key: "location", label: "Location" },
];

export function ImmunizationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ImmSortKey>();
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            {cols.map((col) => (
              <SortHeader
                key={col.key}
                label={col.label}
                active={sortKey === col.key}
                direction={sortKey === col.key ? sortDir : null}
                onClick={() => toggle(col.key)}
              />
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {sorted.map((row, i) => (
            <tr key={`${row.vaccine}-${i}`}>
              <td className="px-3 py-2 text-sm font-medium">{String(row.vaccine ?? "")}</td>
              <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.date ?? "")}</td>
              <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.location ?? "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
