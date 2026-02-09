"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  ConditionStatusText,
} from "./table-primitives";

type CondSortKey = "condition" | "clinicalStatus" | "onsetDate" | "abatementDate";

const cols: { key: CondSortKey; label: string }[] = [
  { key: "condition", label: "Condition" },
  { key: "clinicalStatus", label: "Status" },
  { key: "onsetDate", label: "Onset" },
  { key: "abatementDate", label: "Resolved" },
];

function condAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

function CondRow({ row }: { row: Record<string, unknown> }) {
  return (
    <tr>
      <td className="px-4 py-2 text-sm font-medium">{String(row.condition ?? "")}</td>
      <td className="px-4 py-2">
        <ConditionStatusText status={(row.clinicalStatus as "active" | "resolved") ?? "active"} />
      </td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.onsetDate ?? "")}</td>
      <td className="px-4 py-2 text-sm text-muted-foreground">
        {row.abatementDate ? String(row.abatementDate) : <span className="italic">&mdash;</span>}
      </td>
    </tr>
  );
}

export function ConditionsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<CondSortKey>();

  const activeConds = rows.filter((c) => c.clinicalStatus === "active");
  const resolvedConds = rows.filter((c) => c.clinicalStatus === "resolved");
  const sortedActive = sortRows(activeConds, sortKey, sortDir, condAccessor);
  const sortedResolved = sortRows(resolvedConds, sortKey, sortDir, condAccessor);

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
            <CondRow key={`active-${i}`} row={row} />
          ))}
        </tbody>
        {sortedResolved.length > 0 && (
          <tbody className="divide-y">
            <tr>
              <td colSpan={4} className="px-4 py-1.5 bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Resolved
                </span>
              </td>
            </tr>
            {sortedResolved.map((row, i) => (
              <CondRow key={`resolved-${i}`} row={row} />
            ))}
          </tbody>
        )}
      </table>
    </CardContent>
  );
}
