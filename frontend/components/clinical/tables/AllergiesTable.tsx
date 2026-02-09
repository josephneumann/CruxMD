"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  CriticalityText,
  AllergyStatusText,
} from "./table-primitives";

type AllergySortKey = "allergen" | "category" | "criticality" | "clinicalStatus" | "onsetDate";

const cols: { key: AllergySortKey; label: string }[] = [
  { key: "allergen", label: "Allergen" },
  { key: "category", label: "Category" },
  { key: "criticality", label: "Criticality" },
  { key: "clinicalStatus", label: "Status" },
  { key: "onsetDate", label: "Onset" },
];

export function AllergiesTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<AllergySortKey>();
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

  return (
    <CardContent className="p-0 overflow-x-auto">
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
          {sorted.map((row, i) => (
            <tr key={`${row.allergen}-${i}`}>
              <td className="px-3 py-2 text-sm font-medium">{String(row.allergen ?? "")}</td>
              <td className="px-3 py-2 text-sm text-muted-foreground capitalize">
                {String(row.category ?? "")}
              </td>
              <td className="px-3 py-2">
                <CriticalityText criticality={(row.criticality as "high" | "low") ?? "low"} />
              </td>
              <td className="px-3 py-2">
                <AllergyStatusText status={(row.clinicalStatus as "active" | "inactive") ?? "active"} />
              </td>
              <td className="px-3 py-2 text-sm text-muted-foreground">{String(row.onsetDate ?? "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
