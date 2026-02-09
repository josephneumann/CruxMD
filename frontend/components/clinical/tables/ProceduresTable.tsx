"use client";

import { CardContent } from "@/components/ui/card";
import { SortHeader, useSortState, sortRows } from "./table-primitives";

type ProcSortKey = "procedure" | "date" | "location" | "reason";

const cols: { key: ProcSortKey; label: string }[] = [
  { key: "procedure", label: "Procedure" },
  { key: "date", label: "Date" },
  { key: "location", label: "Location" },
  { key: "reason", label: "Reason" },
];

export function ProceduresTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ProcSortKey>();
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0">
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
            <tr key={`${row.procedure}-${i}`}>
              <td className="px-4 py-2 text-sm font-medium">{String(row.procedure ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.date ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.location ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">
                {row.reason ? String(row.reason) : <span className="italic">&mdash;</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
