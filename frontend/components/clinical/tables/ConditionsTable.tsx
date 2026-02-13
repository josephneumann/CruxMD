"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  ConditionStatusText,
  useResponsiveColumns,
} from "./table-primitives";

type CondSortKey = "condition" | "clinicalStatus" | "onsetDate" | "abatementDate";

function condAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

function CondRow({
  row,
  maxPriority,
}: {
  row: Record<string, unknown>;
  maxPriority: 1 | 2 | 3;
}) {
  return (
    <tr>
      {/* P1: Condition name */}
      <td className="px-3 py-2 text-sm font-medium">{String(row.condition ?? "")}</td>
      {/* P1: Status */}
      <td className="px-3 py-2">
        <ConditionStatusText status={(row.clinicalStatus as "active" | "resolved") ?? "active"} />
      </td>
      {/* P2: Onset date */}
      {maxPriority >= 2 && (
        <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.onsetDate ?? "")}</td>
      )}
      {/* P3: Resolved date */}
      {maxPriority >= 3 && (
        <td className="px-3 py-2 text-sm text-muted-foreground">
          {row.abatementDate ? String(row.abatementDate) : <span className="italic">&mdash;</span>}
        </td>
      )}
    </tr>
  );
}

export function ConditionsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<CondSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const colCount = 2 + (maxPriority >= 2 ? 1 : 0) + (maxPriority >= 3 ? 1 : 0);

  const activeConds = rows.filter((c) => c.clinicalStatus === "active");
  const resolvedConds = rows.filter((c) => c.clinicalStatus === "resolved");
  const sortedActive = sortRows(activeConds, sortKey, sortDir, condAccessor);
  const sortedResolved = sortRows(resolvedConds, sortKey, sortDir, condAccessor);

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Condition"
              active={sortKey === "condition"}
              direction={sortKey === "condition" ? sortDir : null}
              onClick={() => toggle("condition")}
            />
            <SortHeader
              label="Status"
              active={sortKey === "clinicalStatus"}
              direction={sortKey === "clinicalStatus" ? sortDir : null}
              onClick={() => toggle("clinicalStatus")}
            />
            {maxPriority >= 2 && (
              <SortHeader
                label="Onset"
                active={sortKey === "onsetDate"}
                direction={sortKey === "onsetDate" ? sortDir : null}
                onClick={() => toggle("onsetDate")}
              />
            )}
            {maxPriority >= 3 && (
              <SortHeader
                label="Resolved"
                active={sortKey === "abatementDate"}
                direction={sortKey === "abatementDate" ? sortDir : null}
                onClick={() => toggle("abatementDate")}
              />
            )}
          </tr>
        </thead>
        <tbody className="divide-y">
          {sortedActive.map((row, i) => (
            <CondRow key={`active-${i}`} row={row} maxPriority={maxPriority} />
          ))}
        </tbody>
        {sortedResolved.length > 0 && (
          <tbody className="divide-y">
            <tr>
              <td colSpan={colCount} className="px-3 py-1.5 bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Resolved
                </span>
              </td>
            </tr>
            {sortedResolved.map((row, i) => (
              <CondRow key={`resolved-${i}`} row={row} maxPriority={maxPriority} />
            ))}
          </tbody>
        )}
      </table>
    </CardContent>
  );
}
