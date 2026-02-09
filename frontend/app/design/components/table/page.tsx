"use client";

import { useTheme } from "next-themes";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CodeBlock } from "@/components/design-system/CodeBlock";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  YAxis,
  Tooltip,
} from "recharts";

// -- Theme-aware colors (matches chart page) ----------------------------------

function useTableColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return {
    chart1: isDark ? "#4A9A88" : "#2F5E52",
    warning: isDark ? "#EBC47C" : "#D9A036",
    critical: isDark ? "#D46F65" : "#C24E42",
    rangeBg: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
    rangeNormal: isDark ? "#66BB6A" : "#388E3C",
    rangeWarning: isDark ? "#EBC47C" : "#D9A036",
    rangeCritical: isDark ? "#D46F65" : "#C24E42",
  };
}

// -- HL7 FHIR Observation Interpretation Codes --------------------------------
// N = Normal, H = High, L = Low, HH = Critically High, LL = Critically Low

type HL7Interpretation = "N" | "H" | "L" | "HH" | "LL";

interface HistoryPoint {
  value: number;
  date: string;
}

interface LabResult {
  test: string;
  value: number;
  unit: string;
  rangeLow: number;
  rangeHigh: number;
  interpretation: HL7Interpretation;
  date: string;
  history: HistoryPoint[];
}

const labResults: LabResult[] = [
  {
    test: "White Blood Cells",
    value: 7.5,
    unit: "K/uL",
    rangeLow: 4.5,
    rangeHigh: 11.0,
    interpretation: "N",
    date: "01/25/2026",
    history: [
      { value: 6.8, date: "08/12/2025" },
      { value: 7.2, date: "09/15/2025" },
      { value: 7.0, date: "10/14/2025" },
      { value: 7.3, date: "11/11/2025" },
      { value: 7.1, date: "12/16/2025" },
      { value: 7.5, date: "01/25/2026" },
    ],
  },
  {
    test: "Hemoglobin",
    value: 15.2,
    unit: "g/dL",
    rangeLow: 13.5,
    rangeHigh: 17.5,
    interpretation: "N",
    date: "01/25/2026",
    history: [
      { value: 14.8, date: "08/12/2025" },
      { value: 15.0, date: "09/15/2025" },
      { value: 14.9, date: "10/14/2025" },
      { value: 15.1, date: "11/11/2025" },
      { value: 15.0, date: "12/16/2025" },
      { value: 15.2, date: "01/25/2026" },
    ],
  },
  {
    test: "Platelets",
    value: 425,
    unit: "K/uL",
    rangeLow: 150,
    rangeHigh: 400,
    interpretation: "H",
    date: "01/25/2026",
    history: [
      { value: 380, date: "08/12/2025" },
      { value: 395, date: "09/15/2025" },
      { value: 400, date: "10/14/2025" },
      { value: 410, date: "11/11/2025" },
      { value: 418, date: "12/16/2025" },
      { value: 425, date: "01/25/2026" },
    ],
  },
  {
    test: "Potassium",
    value: 6.2,
    unit: "mEq/L",
    rangeLow: 3.5,
    rangeHigh: 5.0,
    interpretation: "HH",
    date: "01/25/2026",
    history: [
      { value: 4.2, date: "08/12/2025" },
      { value: 4.5, date: "09/15/2025" },
      { value: 4.8, date: "10/14/2025" },
      { value: 5.1, date: "11/11/2025" },
      { value: 5.8, date: "12/16/2025" },
      { value: 6.2, date: "01/25/2026" },
    ],
  },
];

const medications = [
  { name: "Lisinopril", dosage: "10 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "01/15/2025", status: "active" },
  { name: "Metformin", dosage: "500 mg", frequency: "Twice daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "03/20/2025", status: "active" },
  { name: "Atorvastatin", dosage: "20 mg", frequency: "Once daily at bedtime", route: "Oral", prescriber: "Dr. Williams", startDate: "06/10/2024", status: "active" },
  { name: "Warfarin", dosage: "5 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "12/01/2024", status: "discontinued" },
];

// -- Components ---------------------------------------------------------------

function MedStatusBadge({ status }: { status: string }) {
  const variants: Record<string, "positive" | "neutral"> = {
    active: "positive",
    discontinued: "neutral",
  };
  const labels: Record<string, string> = {
    active: "Active",
    discontinued: "Discontinued",
  };
  return <Badge variant={variants[status]} size="sm">{labels[status]}</Badge>;
}

/**
 * Compact reference range interval bar.
 * Shows the normal range as a highlighted zone within a track,
 * with a dot marker showing where the current value sits.
 */
function RangeBar({ value, low, high, interpretation }: {
  value: number;
  low: number;
  high: number;
  interpretation: HL7Interpretation;
}) {
  const c = useTableColors();

  // Extend display 30% beyond range on each side
  const rangeSpan = high - low;
  const padding = rangeSpan * 0.3;
  const displayLow = low - padding;
  const displayHigh = high + padding;
  const displaySpan = displayHigh - displayLow;

  // Position of current value as percentage
  const position = Math.max(3, Math.min(97, ((value - displayLow) / displaySpan) * 100));

  // Normal range zone position
  const rangeStart = ((low - displayLow) / displaySpan) * 100;
  const rangeWidth = ((high - low) / displaySpan) * 100;

  const isCritical = interpretation === "HH" || interpretation === "LL";
  const isAbnormal = interpretation === "H" || interpretation === "L";
  const markerColor = isCritical ? c.rangeCritical : isAbnormal ? c.rangeWarning : c.rangeNormal;

  return (
    <div className="flex items-center gap-2.5 min-w-[160px]">
      <div className="relative flex-1 h-2">
        {/* Track background */}
        <div className="absolute inset-0 rounded-full" style={{ backgroundColor: c.rangeBg }} />
        {/* Normal range zone */}
        <div
          className="absolute top-0 h-full rounded-full"
          style={{
            left: `${rangeStart}%`,
            width: `${rangeWidth}%`,
            backgroundColor: c.rangeNormal,
            opacity: 0.2,
          }}
        />
        {/* Position marker */}
        <div
          className="absolute top-1/2 size-2.5 rounded-full border-2 border-background"
          style={{
            left: `${position}%`,
            transform: "translate(-50%, -50%)",
            backgroundColor: markerColor,
          }}
        />
      </div>
      <span className="text-[11px] text-muted-foreground tabular-nums whitespace-nowrap">
        {low}–{high}
      </span>
    </div>
  );
}

/**
 * Compact tooltip for sparklines — shows value and date.
 */
function SparklineTooltip({ active, payload }: {
  active?: boolean;
  payload?: Array<{ payload?: { value: number; date: string } }>;
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const { value, date } = payload[0].payload;
  return (
    <div className="rounded border bg-card px-2 py-1 shadow-md text-[11px] leading-snug">
      <p className="font-medium tabular-nums">{value}</p>
      <p className="text-muted-foreground">{date}</p>
    </div>
  );
}

/**
 * Inline sparkline with % change annotation and "since" date.
 * Color matches interpretation: green for N, amber for H/L, red for HH/LL.
 * Hover reveals value/date tooltip on each data point.
 */
function SparklineWithDelta({ data, interpretation, unit }: {
  data: HistoryPoint[];
  interpretation: HL7Interpretation;
  unit: string;
}) {
  const c = useTableColors();

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || 0.5;
  const domain: [number, number] = [min - pad, max + pad];

  const isCritical = interpretation === "HH" || interpretation === "LL";
  const isAbnormal = interpretation === "H" || interpretation === "L";
  const strokeColor = isCritical ? c.critical : isAbnormal ? c.warning : c.chart1;

  // Calculate % change from first to last reading
  const first = values[0];
  const last = values[values.length - 1];
  const pctChange = first !== 0 ? Math.round(((last - first) / first) * 100) : 0;
  const arrow = pctChange > 0 ? "↑" : pctChange < 0 ? "↓" : "→";
  const deltaColor = isCritical ? "text-[#C24E42]" : isAbnormal ? "text-[#D9A036]" : "text-muted-foreground";

  // Derive "since" from first history point
  const sinceDate = data[0].date;

  return (
    <div className="flex items-center gap-2">
      <div className="w-[72px] h-[28px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
            <YAxis domain={domain} hide />
            <Tooltip
              content={<SparklineTooltip />}
              cursor={false}
              position={{ y: -38 }}
              allowEscapeViewBox={{ x: true, y: true }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3, fill: strokeColor, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-[11px] leading-tight whitespace-nowrap">
        <span className={`font-medium ${deltaColor}`}>{arrow} {Math.abs(pctChange)}%</span>
        <br />
        <span className="text-muted-foreground">since {sinceDate}</span>
      </div>
    </div>
  );
}

// -- Table header cell helper -------------------------------------------------

const TH = "text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider";

// -- Page ---------------------------------------------------------------------

export default function TablePage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Table</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Tables display structured clinical data with inline sparklines, visual reference
          range bars, and status-coded values. Wrap in Card for grouped presentation.
        </p>
      </div>

      {/* Laboratory Results */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Laboratory Results</h2>
        <p className="text-muted-foreground max-w-2xl">
          Columns follow clinical reading order: identify the test, read the value, check if
          it&apos;s in range (via the range bar marker color), then assess the trend. The range bar
          encodes interpretation through marker color — green for normal, amber for high/low,
          red for critical — eliminating the need for separate status badges.
        </p>
        <Card>
          <CardHeader>
            <CardTitle>Complete Blood Count (CBC)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className={TH}>Test</th>
                  <th className={TH}>Result</th>
                  <th className={TH}>Reference Range</th>
                  <th className={TH}>Trend</th>
                  <th className={TH}>Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {labResults.map((row) => {
                  const isCritical = row.interpretation === "HH" || row.interpretation === "LL";
                  const isAbnormal = row.interpretation !== "N";
                  return (
                    <tr key={row.test} className={isCritical ? "bg-[#C24E42]/5" : ""}>
                      <td className="p-4 font-medium">{row.test}</td>
                      <td className="p-4">
                        <span className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}>
                          {row.value} <span className="text-muted-foreground font-normal">{row.unit}</span>
                        </span>
                      </td>
                      <td className="p-4">
                        <RangeBar
                          value={row.value}
                          low={row.rangeLow}
                          high={row.rangeHigh}
                          interpretation={row.interpretation}
                        />
                      </td>
                      <td className="p-4">
                        <SparklineWithDelta
                          data={row.history}
                          interpretation={row.interpretation}
                          unit={row.unit}
                        />
                      </td>
                      <td className="p-4 text-muted-foreground">{row.date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Current Medications */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Current Medications</h2>
        <Card>
          <CardHeader>
            <CardTitle>Current Medications</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className={TH}>Medication</th>
                  <th className={TH}>Dosage</th>
                  <th className={TH}>Frequency</th>
                  <th className={TH}>Route</th>
                  <th className={TH}>Prescriber</th>
                  <th className={TH}>Start Date</th>
                  <th className={TH}>Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {medications.map((row) => (
                  <tr key={row.name}>
                    <td className="p-4 font-medium">{row.name}</td>
                    <td className="p-4">{row.dosage}</td>
                    <td className="p-4">{row.frequency}</td>
                    <td className="p-4">{row.route}</td>
                    <td className="p-4">{row.prescriber}</td>
                    <td className="p-4 text-muted-foreground">{row.startDate}</td>
                    <td className="p-4"><MedStatusBadge status={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Basic Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Table</h2>
        <p className="text-muted-foreground">
          Minimal table styling without card wrapper.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 text-sm font-medium">Name</th>
                <th className="text-left p-3 text-sm font-medium">Type</th>
                <th className="text-left p-3 text-sm font-medium">Default</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="p-3 font-mono text-sm">variant</td>
                <td className="p-3 text-sm text-muted-foreground">string</td>
                <td className="p-3 font-mono text-sm">&quot;default&quot;</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-sm">size</td>
                <td className="p-3 text-sm text-muted-foreground">string</td>
                <td className="p-3 font-mono text-sm">&quot;md&quot;</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Usage */}
      <CodeBlock
        collapsible
        label="View Code"
        code={`// HL7 FHIR Observation Interpretation Codes
// N = Normal, H = High, L = Low, HH = Critically High, LL = Critically Low
type HL7Interpretation = "N" | "H" | "L" | "HH" | "LL";

interface LabResult {
  test: string;
  value: number;
  unit: string;
  rangeLow: number;
  rangeHigh: number;
  interpretation: HL7Interpretation;
  date: string;
  history: { value: number; date: string }[];  // last 6 readings
}

// Column order follows clinical reading flow:
// Test → Result → Range Bar → Trend → Date
//
// The range bar marker color encodes interpretation:
//   green = N (normal), amber = H/L, red = HH/LL
// No separate status badge needed — color does the work.

<RangeBar
  value={row.value}
  low={row.rangeLow}
  high={row.rangeHigh}
  interpretation={row.interpretation}
/>

<SparklineWithDelta
  data={row.history}
  interpretation={row.interpretation}
  unit={row.unit}
/>`}
      />
    </div>
  );
}
