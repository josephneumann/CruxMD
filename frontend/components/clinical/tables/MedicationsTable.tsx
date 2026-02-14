"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
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

type MedSortKey = "medication" | "status" | "frequency" | "authoredOn" | "requester";

function medAccessor(row: Record<string, unknown>, key: string): string {
  return String(row[key] ?? "");
}

function MedRow({
  row,
  maxPriority,
  showFrequency,
  showAuthoredOn,
  showRequester,
}: {
  row: Record<string, unknown>;
  maxPriority: ColumnPriority;
  showFrequency: boolean;
  showAuthoredOn: boolean;
  showRequester: boolean;
}) {
  const status = String(row.status ?? "");
  return (
    <tr>
      <td className="font-medium">{String(row.medication ?? "")}</td>
      {maxPriority >= 2 && (
        <td>
          <span
            className={
              status === "active"
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-muted-foreground"
            }
          >
            {status || "\u2014"}
          </span>
        </td>
      )}
      {maxPriority >= 2 && showFrequency && (
        <td>
          {row.frequency ? String(row.frequency) : <span className="text-muted-foreground italic">&mdash;</span>}
        </td>
      )}
      {maxPriority >= 3 && showAuthoredOn && (
        <td className="text-muted-foreground whitespace-nowrap">{String(row.authoredOn ?? "")}</td>
      )}
      {maxPriority >= 3 && showRequester && (
        <td className="text-muted-foreground">{String(row.requester ?? "")}</td>
      )}
    </tr>
  );
}

export function MedicationsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<MedSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const showFrequency = columnHasData(rows, "frequency");
  const showAuthoredOn = columnHasData(rows, "authoredOn");
  const showRequester = columnHasData(rows, "requester");

  // Count visible columns for colSpan
  let colCount = 1; // medication always
  if (maxPriority >= 2) {
    colCount++; // status
    if (showFrequency) colCount++;
  }
  if (maxPriority >= 3) {
    if (showAuthoredOn) colCount++;
    if (showRequester) colCount++;
  }

  // Group by reason
  const reasonMap = new Map<string, Record<string, unknown>[]>();
  for (const row of rows) {
    const reason = row.reason ? String(row.reason) : "Other";
    if (!reasonMap.has(reason)) reasonMap.set(reason, []);
    reasonMap.get(reason)!.push(row);
  }

  // Sort groups alphabetically, but put "Other" last
  const groupKeys = [...reasonMap.keys()].sort((a, b) => {
    if (a === "Other") return 1;
    if (b === "Other") return -1;
    return a.localeCompare(b);
  });

  // Sort rows within each group
  const sortedGroups = groupKeys.map((reason) => ({
    reason,
    rows: sortRows(reasonMap.get(reason)!, sortKey, sortDir, medAccessor),
  }));

  // All groups expanded by default
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(groupKeys),
  );
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
              label="Medication"
              active={sortKey === "medication"}
              direction={sortKey === "medication" ? sortDir : null}
              onClick={() => toggle("medication")}
            />
            {maxPriority >= 2 && (
              <SortHeader
                label="Status"
                active={sortKey === "status"}
                direction={sortKey === "status" ? sortDir : null}
                onClick={() => toggle("status")}
              />
            )}
            {maxPriority >= 2 && showFrequency && (
              <SortHeader
                label="Frequency"
                active={sortKey === "frequency"}
                direction={sortKey === "frequency" ? sortDir : null}
                onClick={() => toggle("frequency")}
              />
            )}
            {maxPriority >= 3 && showAuthoredOn && (
              <SortHeader
                label="Prescribed"
                active={sortKey === "authoredOn"}
                direction={sortKey === "authoredOn" ? sortDir : null}
                onClick={() => toggle("authoredOn")}
              />
            )}
            {maxPriority >= 3 && showRequester && (
              <SortHeader
                label="Requester"
                active={sortKey === "requester"}
                direction={sortKey === "requester" ? sortDir : null}
                onClick={() => toggle("requester")}
              />
            )}
          </tr>
        </thead>
        <tbody>
          {sortedGroups.map(({ reason, rows: groupRows }) => (
            <ReasonGroup
              key={reason}
              reason={reason}
              rows={groupRows}
              colCount={colCount}
              maxPriority={maxPriority}
              showFrequency={showFrequency}
              showAuthoredOn={showAuthoredOn}
              showRequester={showRequester}
              isExpanded={expanded.has(reason)}
              onToggle={() => toggleGroup(reason)}
            />
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

function ReasonGroup({
  reason,
  rows,
  colCount,
  maxPriority,
  showFrequency,
  showAuthoredOn,
  showRequester,
  isExpanded,
  onToggle,
}: {
  reason: string;
  rows: Record<string, unknown>[];
  colCount: number;
  maxPriority: ColumnPriority;
  showFrequency: boolean;
  showAuthoredOn: boolean;
  showRequester: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Chevron = isExpanded ? ChevronDown : ChevronRight;
  return (
    <>
      <tr className="bg-muted/20 cursor-pointer hover:bg-muted/40" onClick={onToggle}>
        <td colSpan={colCount}>
          <div className="flex items-center gap-1.5">
            <Chevron className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {reason}
            </span>
            <span className="text-xs text-muted-foreground/60">({rows.length})</span>
          </div>
        </td>
      </tr>
      {isExpanded &&
        rows.map((row, i) => (
          <MedRow
            key={`${reason}-${i}`}
            row={row}
            maxPriority={maxPriority}
            showFrequency={showFrequency}
            showAuthoredOn={showAuthoredOn}
            showRequester={showRequester}
          />
        ))}
    </>
  );
}
