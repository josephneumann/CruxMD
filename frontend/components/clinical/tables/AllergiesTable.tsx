"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  CriticalityText,
  AllergyStatusText,
  useResponsiveColumns,
} from "./table-primitives";

type AllergySortKey = "allergen" | "category" | "criticality" | "clinicalStatus" | "onsetDate";

export function AllergiesTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<AllergySortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            {/* P1: Allergen */}
            <SortHeader
              label="Allergen"
              active={sortKey === "allergen"}
              direction={sortKey === "allergen" ? sortDir : null}
              onClick={() => toggle("allergen")}
            />
            {/* P1: Criticality */}
            <SortHeader
              label="Criticality"
              active={sortKey === "criticality"}
              direction={sortKey === "criticality" ? sortDir : null}
              onClick={() => toggle("criticality")}
            />
            {/* P2: Category */}
            {maxPriority >= 2 && (
              <SortHeader
                label="Category"
                active={sortKey === "category"}
                direction={sortKey === "category" ? sortDir : null}
                onClick={() => toggle("category")}
              />
            )}
            {/* P3: Status */}
            {maxPriority >= 3 && (
              <SortHeader
                label="Status"
                active={sortKey === "clinicalStatus"}
                direction={sortKey === "clinicalStatus" ? sortDir : null}
                onClick={() => toggle("clinicalStatus")}
              />
            )}
            {/* P3: Onset */}
            {maxPriority >= 3 && (
              <SortHeader
                label="Onset"
                active={sortKey === "onsetDate"}
                direction={sortKey === "onsetDate" ? sortDir : null}
                onClick={() => toggle("onsetDate")}
              />
            )}
          </tr>
        </thead>
        <tbody className="divide-y">
          {sorted.map((row, i) => (
            <tr key={`${row.allergen}-${i}`}>
              <td className="px-3 py-2 text-sm font-medium">{String(row.allergen ?? "")}</td>
              <td className="px-3 py-2">
                <CriticalityText criticality={(row.criticality as "high" | "low") ?? "low"} />
              </td>
              {maxPriority >= 2 && (
                <td className="px-3 py-2 text-sm text-muted-foreground capitalize">
                  {String(row.category ?? "")}
                </td>
              )}
              {maxPriority >= 3 && (
                <td className="px-3 py-2">
                  <AllergyStatusText status={(row.clinicalStatus as "active" | "inactive") ?? "active"} />
                </td>
              )}
              {maxPriority >= 3 && (
                <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.onsetDate ?? "")}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
