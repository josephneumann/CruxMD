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

type CondSortKey = "condition" | "verificationStatus" | "onsetDate" | "abatementDate";

function condAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

const VERIFICATION_COLORS: Record<string, string> = {
  confirmed: "text-emerald-600 dark:text-emerald-400",
  unconfirmed: "text-amber-600 dark:text-amber-400",
  provisional: "text-amber-600 dark:text-amber-400",
  differential: "text-sky-600 dark:text-sky-400",
  refuted: "text-muted-foreground line-through",
  "entered-in-error": "text-muted-foreground line-through",
};

function CondRow({
  row,
  maxPriority,
}: {
  row: Record<string, unknown>;
  maxPriority: ColumnPriority;
}) {
  const verification = String(row.verificationStatus ?? "");
  const colorClass = VERIFICATION_COLORS[verification] ?? "text-muted-foreground";
  return (
    <tr>
      <td className="font-medium">{String(row.condition ?? "")}</td>
      {maxPriority >= 2 && (
        <td>
          <span className={colorClass}>{verification || "\u2014"}</span>
        </td>
      )}
      {maxPriority >= 2 && (
        <td className="text-muted-foreground whitespace-nowrap">{String(row.onsetDate ?? "")}</td>
      )}
      {maxPriority >= 3 && (
        <td className="text-muted-foreground whitespace-nowrap">
          {row.abatementDate ? String(row.abatementDate) : <span className="italic">&mdash;</span>}
        </td>
      )}
    </tr>
  );
}

export function ConditionsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<CondSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const colCount =
    1 +
    (maxPriority >= 2 ? 2 : 0) + // verification + onset
    (maxPriority >= 3 ? 1 : 0);  // abatement

  const activeConds = rows.filter((c) => c.clinicalStatus === "active");
  const resolvedConds = rows.filter((c) => c.clinicalStatus === "resolved");
  const sortedActive = sortRows(activeConds, sortKey, sortDir, condAccessor);
  const sortedResolved = sortRows(resolvedConds, sortKey, sortDir, condAccessor);

  // Active expanded by default, resolved collapsed
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(["active"]));
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
              label="Condition"
              active={sortKey === "condition"}
              direction={sortKey === "condition" ? sortDir : null}
              onClick={() => toggle("condition")}
            />
            {maxPriority >= 2 && (
              <SortHeader
                label="Verification"
                active={sortKey === "verificationStatus"}
                direction={sortKey === "verificationStatus" ? sortDir : null}
                onClick={() => toggle("verificationStatus")}
              />
            )}
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
        <tbody>
          {sortedActive.length > 0 && (
            <StatusGroup
              label="Active"
              count={sortedActive.length}
              colCount={colCount}
              isExpanded={expanded.has("active")}
              onToggle={() => toggleGroup("active")}
            />
          )}
          {expanded.has("active") &&
            sortedActive.map((row, i) => (
              <CondRow key={`active-${i}`} row={row} maxPriority={maxPriority} />
            ))}
          {sortedResolved.length > 0 && (
            <StatusGroup
              label="Resolved"
              count={sortedResolved.length}
              colCount={colCount}
              isExpanded={expanded.has("resolved")}
              onToggle={() => toggleGroup("resolved")}
            />
          )}
          {expanded.has("resolved") &&
            sortedResolved.map((row, i) => (
              <CondRow key={`resolved-${i}`} row={row} maxPriority={maxPriority} />
            ))}
        </tbody>
      </table>
    </CardContent>
  );
}

function StatusGroup({
  label,
  count,
  colCount,
  isExpanded,
  onToggle,
}: {
  label: string;
  count: number;
  colCount: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Chevron = isExpanded ? ChevronDown : ChevronRight;
  return (
    <tr className="bg-muted/20 cursor-pointer hover:bg-muted/40" onClick={onToggle}>
      <td colSpan={colCount}>
        <div className="flex items-center gap-1.5">
          <Chevron className="size-3.5 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {label}
          </span>
          <span className="text-xs text-muted-foreground/60">({count})</span>
        </div>
      </td>
    </tr>
  );
}
