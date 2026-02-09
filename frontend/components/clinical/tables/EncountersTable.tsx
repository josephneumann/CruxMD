"use client";

import { CardContent } from "@/components/ui/card";
import {
  SortHeader,
  useSortState,
  sortRows,
  EncounterClassText,
} from "./table-primitives";

type EncSortKey = "type" | "encounterClass" | "date" | "provider" | "location" | "reason";

const cols: { key: EncSortKey; label: string }[] = [
  { key: "type", label: "Type" },
  { key: "encounterClass", label: "Class" },
  { key: "date", label: "Date" },
  { key: "provider", label: "Provider" },
  { key: "location", label: "Location" },
  { key: "reason", label: "Reason" },
];

export function EncountersTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<EncSortKey>();
  const sorted = sortRows(rows, sortKey, sortDir, (row, key) =>
    String(row[key] ?? ""),
  );

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
          {sorted.map((row, i) => (
            <tr key={`${row.type}-${i}`}>
              <td className="px-4 py-2 text-sm font-medium">{String(row.type ?? "")}</td>
              <td className="px-4 py-2">
                <EncounterClassText
                  encounterClass={(row.encounterClass as "AMB" | "EMER" | "IMP") ?? "AMB"}
                />
              </td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.date ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.provider ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{String(row.location ?? "")}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">
                {row.reason ? String(row.reason) : <span className="italic">&mdash;</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}
