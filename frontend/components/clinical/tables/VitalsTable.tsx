"use client";

import {
  Activity,
  HeartPulse,
  Wind,
  Thermometer,
  Scale,
  Ruler,
  Calculator,
  Frown,
} from "lucide-react";
import { CardContent } from "@/components/ui/card";
import type { HL7Interpretation, HistoryPoint } from "@/lib/types";
import {
  TH,
  SortHeader,
  useSortState,
  sortRows,
  RangeBar,
  SparklineWithDelta,
  useResponsiveColumns,
  tableClass,
} from "./table-primitives";

type VitalSortKey = "vital" | "value" | "date";

const vitalIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  "Blood Pressure": Activity,
  "Heart Rate": HeartPulse,
  "Respiratory Rate": Wind,
  "Body Temperature": Thermometer,
  "Body Weight": Scale,
  "Body Height": Ruler,
  "BMI": Calculator,
  "Pain Severity": Frown,
};

export function VitalsTable({ rows }: { rows: Record<string, unknown>[] }) {
  const { sortKey, sortDir, toggle } = useSortState<VitalSortKey>();
  const { containerRef, maxPriority } = useResponsiveColumns();

  const sorted = sortRows(rows, sortKey, sortDir, (row, key) => {
    if (key === "value") return Number(row.numericValue ?? 0);
    return String(row[key] ?? "");
  });

  return (
    <CardContent className="p-0 overflow-x-auto" ref={containerRef}>
      <table className={tableClass(maxPriority)}>
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader
              label="Vital Sign"
              active={sortKey === "vital"}
              direction={sortKey === "vital" ? sortDir : null}
              onClick={() => toggle("vital")}
            />
            <SortHeader
              label="Value"
              active={sortKey === "value"}
              direction={sortKey === "value" ? sortDir : null}
              onClick={() => toggle("value")}
            />
            {maxPriority >= 2 && <th className={TH}>Reference Range</th>}
            {maxPriority >= 3 && <th className={TH}>Trend</th>}
            {maxPriority >= 3 && (
              <SortHeader
                label="Date"
                active={sortKey === "date"}
                direction={sortKey === "date" ? sortDir : null}
                onClick={() => toggle("date")}
              />
            )}
          </tr>
        </thead>
        <tbody className="divide-y">
          {sorted.map((row, i) => {
            const vital = String(row.vital ?? "");
            const VitalIcon = vitalIcons[vital];
            const interpretation = row.interpretation as HL7Interpretation | undefined;
            const isCritical = interpretation === "HH" || interpretation === "LL";
            const isAbnormal = interpretation && interpretation !== "N";
            const hasRange =
              row.rangeLow != null &&
              row.rangeHigh != null &&
              interpretation != null;
            const hasHistory =
              Array.isArray(row.history) &&
              row.history.length > 0 &&
              interpretation != null;

            return (
              <tr key={`${vital}-${i}`}>
                <td className="font-medium">
                  <div className="flex items-center gap-2">
                    {VitalIcon && (
                      <VitalIcon className="size-3.5 text-muted-foreground" />
                    )}
                    {vital}
                  </div>
                </td>
                <td className="whitespace-nowrap">
                  <span
                    className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}
                  >
                    {String(row.value ?? "")}{" "}
                    <span className="text-muted-foreground font-normal">
                      {String(row.unit ?? "")}
                    </span>
                  </span>
                </td>
                {maxPriority >= 2 && (
                  <td>
                    {hasRange && (
                      <RangeBar
                        value={Number(row.numericValue ?? 0)}
                        low={Number(row.rangeLow)}
                        high={Number(row.rangeHigh)}
                        interpretation={interpretation!}
                      />
                    )}
                  </td>
                )}
                {maxPriority >= 3 && (
                  <td>
                    {hasHistory && (
                      <SparklineWithDelta
                        data={row.history as HistoryPoint[]}
                        interpretation={interpretation!}
                        unit={String(row.unit ?? "")}
                      />
                    )}
                  </td>
                )}
                {maxPriority >= 3 && (
                  <td className="text-muted-foreground">
                    {String(row.date ?? "")}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </CardContent>
  );
}
