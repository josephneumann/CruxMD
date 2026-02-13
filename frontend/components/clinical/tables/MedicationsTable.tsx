"use client";

import type { ReactNode } from "react";
import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  columnHasData,
  MedStatusBadge,
  useResponsiveColumns,
  type ColumnPriority,
} from "./table-primitives";

type MedSortKey = "medication" | "frequency" | "reason" | "status" | "authoredOn" | "requester";

interface ColDef {
  key: MedSortKey;
  label: string;
  /** Always show regardless of data presence */
  required?: boolean;
  /** Column priority: 1=always, 2=medium+, 3=wide only */
  priority: ColumnPriority;
  render: (row: Record<string, unknown>) => ReactNode;
}

const allCols: ColDef[] = [
  {
    key: "medication",
    label: "Medication",
    required: true,
    priority: 1,
    render: (row) => (
      <td className="px-3 py-2 text-sm font-medium">{String(row.medication ?? "")}</td>
    ),
  },
  {
    key: "status",
    label: "Status",
    required: true,
    priority: 1,
    render: (row) => (
      <td className="px-3 py-2">
        <MedStatusBadge status={(row.status as "active" | "completed") ?? "active"} />
      </td>
    ),
  },
  {
    key: "frequency",
    label: "Frequency",
    priority: 2,
    render: (row) => (
      <td className="px-3 py-2 text-sm">
        {row.frequency ? String(row.frequency) : <span className="text-muted-foreground italic">&mdash;</span>}
      </td>
    ),
  },
  {
    key: "reason",
    label: "Reason",
    priority: 2,
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.reason ?? "")}</td>
    ),
  },
  {
    key: "authoredOn",
    label: "Prescribed",
    priority: 3,
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.authoredOn ?? "")}</td>
    ),
  },
  {
    key: "requester",
    label: "Requester",
    priority: 3,
    render: (row) => (
      <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.requester ?? "")}</td>
    ),
  },
];

function MedCell({ col, row }: { col: ColDef; row: Record<string, unknown> }) {
  return <>{col.render(row)}</>;
}

function medAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

export function MedicationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<MedSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  // Only show columns that have data (or are required) AND fit the current width
  const visibleCols = allCols.filter(
    (col) => col.priority <= maxPriority && (col.required || columnHasData(rows, col.key)),
  );

  const activeMeds = rows.filter((m) => m.status === "active");
  const completedMeds = rows.filter((m) => m.status === "completed");
  const sortedActive = sortRows(activeMeds, sortKey, sortDir, medAccessor);
  const sortedCompleted = sortRows(completedMeds, sortKey, sortDir, medAccessor);

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
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
          {sortedActive.map((row, i) => (
            <tr key={`active-${i}`}>
              {visibleCols.map((col) => (
                <MedCell key={col.key} col={col} row={row} />
              ))}
            </tr>
          ))}
        </tbody>
        {sortedCompleted.length > 0 && (
          <tbody className="divide-y">
            <tr>
              <td colSpan={visibleCols.length} className="px-3 py-1.5 bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Completed
                </span>
              </td>
            </tr>
            {sortedCompleted.map((row, i) => (
              <tr key={`completed-${i}`}>
                {visibleCols.map((col) => (
                  <MedCell key={col.key} col={col} row={row} />
                ))}
              </tr>
            ))}
          </tbody>
        )}
      </table>
    </CardContent>
  );
}
