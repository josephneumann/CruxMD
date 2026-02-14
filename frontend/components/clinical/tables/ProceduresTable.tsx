"use client";

import type { ReactNode } from "react";
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

interface ColDef {
  key: ProcSortKey;
  label: string;
  required?: boolean;
  priority: ColumnPriority;
  render: (row: Record<string, unknown>) => ReactNode;
}

const allCols: ColDef[] = [
  {
    key: "procedure",
    label: "Procedure",
    required: true,
    priority: 1,
    render: (row) => (
      <td className="font-medium">{String(row.procedure ?? "")}</td>
    ),
  },
  {
    key: "date",
    label: "Date",
    required: true,
    priority: 1,
    render: (row) => (
      <td className="text-muted-foreground">{String(row.date ?? "")}</td>
    ),
  },
  {
    key: "location",
    label: "Location",
    priority: 3,
    render: (row) => (
      <td className="text-muted-foreground">{String(row.location ?? "")}</td>
    ),
  },
  {
    key: "reason",
    label: "Reason",
    priority: 3,
    render: (row) => (
      <td className="text-muted-foreground">
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
  const { containerRef, maxPriority } = useResponsiveColumns();

  const visibleCols = allCols.filter(
    (col) => col.priority <= maxPriority && (col.required || columnHasData(rows, col.key)),
  );
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className={tableClass(maxPriority)}>
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
