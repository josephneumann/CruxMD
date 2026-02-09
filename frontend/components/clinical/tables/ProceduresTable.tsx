"use client";

import type { ReactNode } from "react";
import { CardContent } from "@/components/ui/card";
import { SortHeader, useSortState, sortRows, columnHasData } from "./table-primitives";

type ProcSortKey = "procedure" | "date" | "location" | "reason";

interface ColDef {
  key: ProcSortKey;
  label: string;
  required?: boolean;
  render: (row: Record<string, unknown>) => ReactNode;
}

const allCols: ColDef[] = [
  {
    key: "procedure",
    label: "Procedure",
    required: true,
    render: (row) => (
      <td className="px-3 py-2 text-sm font-medium">{String(row.procedure ?? "")}</td>
    ),
  },
  {
    key: "date",
    label: "Date",
    required: true,
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.date ?? "")}</td>
    ),
  },
  {
    key: "location",
    label: "Location",
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.location ?? "")}</td>
    ),
  },
  {
    key: "reason",
    label: "Reason",
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">
        {row.reason ? String(row.reason) : <span className="italic">&mdash;</span>}
      </td>
    ),
  },
];

function ProcCell({ col, row }: { col: ColDef; row: Record<string, unknown> }) {
  return <>{col.render(row)}</>;
}

export function ProceduresTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<ProcSortKey>();
  const visibleCols = allCols.filter(
    (col) => col.required || columnHasData(rows, col.key),
  );
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            {visibleCols.map((col) => (
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
              {visibleCols.map((col) => (
                <ProcCell key={col.key} col={col} row={row} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
