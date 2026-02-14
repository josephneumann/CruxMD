"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  CriticalityText,
  AllergyStatusText,
  useResponsiveColumns,
  tableClass,
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
      <table className={tableClass(maxPriority)}>
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Allergen"
              active={sortKey === "allergen"}
              direction={sortKey === "allergen" ? sortDir : null}
              onClick={() => toggle("allergen")}
            />
            <SortHeader
              label="Criticality"
              active={sortKey === "criticality"}
              direction={sortKey === "criticality" ? sortDir : null}
              onClick={() => toggle("criticality")}
            />
            {maxPriority >= 2 && (
              <SortHeader
                label="Category"
                active={sortKey === "category"}
                direction={sortKey === "category" ? sortDir : null}
                onClick={() => toggle("category")}
              />
            )}
            {maxPriority >= 3 && (
              <SortHeader
                label="Status"
                active={sortKey === "clinicalStatus"}
                direction={sortKey === "clinicalStatus" ? sortDir : null}
                onClick={() => toggle("clinicalStatus")}
              />
            )}
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
              <td className="font-medium">{String(row.allergen ?? "")}</td>
              <td>
                <CriticalityText criticality={(row.criticality as "high" | "low") ?? "low"} />
              </td>
              {maxPriority >= 2 && (
                <td className="text-muted-foreground capitalize">
                  {String(row.category ?? "")}
                </td>
              )}
              {maxPriority >= 3 && (
                <td>
                  <AllergyStatusText status={(row.clinicalStatus as "active" | "inactive") ?? "active"} />
                </td>
              )}
              {maxPriority >= 3 && (
                <td className="text-muted-foreground">{String(row.onsetDate ?? "")}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
