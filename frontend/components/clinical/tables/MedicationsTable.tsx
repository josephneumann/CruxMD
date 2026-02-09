"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  MedStatusBadge,
} from "./table-primitives";

type MedSortKey = "medication" | "frequency" | "reason" | "status" | "authoredOn" | "requester";

function medAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

function MedRow({ row }: { row: Record<string, unknown> }) {
  return (
    <tr>
      <td className="px-4 py-2 text-sm font-medium">{String(row.medication ?? "")}</td>
      <td className="px-4 py-2 text-sm">
        {row.frequency ? String(row.frequency) : <span className="text-muted-foreground italic">&mdash;</span>}
      </td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.reason ?? "")}</td>
      <td className="px-4 py-2">
        <MedStatusBadge status={(row.status as "active" | "completed") ?? "active"} />
      </td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.authoredOn ?? "")}</td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.requester ?? "")}</td>
    </tr>
  );
}

const cols: { key: MedSortKey; label: string }[] = [
  { key: "medication", label: "Medication" },
  { key: "frequency", label: "Frequency" },
  { key: "reason", label: "Reason" },
  { key: "status", label: "Status" },
  { key: "authoredOn", label: "Prescribed" },
  { key: "requester", label: "Requester" },
];

export function MedicationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<MedSortKey>();

  const activeMeds = rows.filter((m) => m.status === "active");
  const completedMeds = rows.filter((m) => m.status === "completed");
  const sortedActive = sortRows(activeMeds, sortKey, sortDir, medAccessor);
  const sortedCompleted = sortRows(completedMeds, sortKey, sortDir, medAccessor);

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
          {sortedActive.map((row, i) => (
            <MedRow key={`active-${i}`} row={row} />
          ))}
        </tbody>
        {sortedCompleted.length > 0 && (
          <tbody className="divide-y">
            <tr>
              <td colSpan={6} className="px-4 py-1.5 bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Completed
                </span>
              </td>
            </tr>
            {sortedCompleted.map((row, i) => (
              <MedRow key={`completed-${i}`} row={row} />
            ))}
          </tbody>
        )}
      </table>
    </CardContent>
  );
}
