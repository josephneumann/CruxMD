"use client";

import { useTheme } from "next-themes";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CodeBlock } from "@/components/design-system/CodeBlock";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  ReferenceArea,
  YAxis,
} from "recharts";

// -- Theme-aware colors (matches chart page) ----------------------------------

function useTableColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return {
    chart1: isDark ? "#4A9A88" : "#2F5E52",
    chart5: isDark ? "#66BB6A" : "#388E3C",
    warning: isDark ? "#EBC47C" : "#D9A036",
    critical: isDark ? "#D46F65" : "#C24E42",
    rangeBg: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
    rangeNormal: isDark ? "#66BB6A" : "#388E3C",
    rangeWarning: isDark ? "#EBC47C" : "#D9A036",
    rangeCritical: isDark ? "#D46F65" : "#C24E42",
    bandSubtle: isDark ? 0.12 : 0.08,
  };
}

// -- Data ---------------------------------------------------------------------

interface LabResult {
  test: string;
  value: number;
  unit: string;
  rangeLow: number;
  rangeHigh: number;
  status: "normal" | "high" | "low" | "critical";
  date: string;
  history: number[];
}

const labResults: LabResult[] = [
  {
    test: "White Blood Cells",
    value: 7.5,
    unit: "K/uL",
    rangeLow: 4.5,
    rangeHigh: 11.0,
    status: "normal",
    date: "01/25/2026",
    history: [6.8, 7.2, 7.0, 7.3, 7.1, 7.5],
  },
  {
    test: "Hemoglobin",
    value: 15.2,
    unit: "g/dL",
    rangeLow: 13.5,
    rangeHigh: 17.5,
    status: "normal",
    date: "01/25/2026",
    history: [14.8, 15.0, 14.9, 15.1, 15.0, 15.2],
  },
  {
    test: "Platelets",
    value: 425,
    unit: "K/uL",
    rangeLow: 150,
    rangeHigh: 400,
    status: "high",
    date: "01/25/2026",
    history: [380, 395, 400, 410, 418, 425],
  },
  {
    test: "Potassium",
    value: 6.2,
    unit: "mEq/L",
    rangeLow: 3.5,
    rangeHigh: 5.0,
    status: "critical",
    date: "01/25/2026",
    history: [4.2, 4.5, 4.8, 5.1, 5.8, 6.2],
  },
];

const medications = [
  { name: "Lisinopril", dosage: "10 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "01/15/2025", status: "active" },
  { name: "Metformin", dosage: "500 mg", frequency: "Twice daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "03/20/2025", status: "active" },
  { name: "Atorvastatin", dosage: "20 mg", frequency: "Once daily at bedtime", route: "Oral", prescriber: "Dr. Williams", startDate: "06/10/2024", status: "active" },
  { name: "Warfarin", dosage: "5 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "12/01/2024", status: "discontinued" },
];

// -- Components ---------------------------------------------------------------

function StatusFlag({ status }: { status: string }) {
  if (status === "high") return <Badge variant="warning" size="sm" className="ml-2 text-[10px] px-1.5">H</Badge>;
  if (status === "low") return <Badge variant="warning" size="sm" className="ml-2 text-[10px] px-1.5">L</Badge>;
  if (status === "critical") return <Badge variant="critical" size="sm" className="ml-2 text-[10px] px-1.5">CRIT</Badge>;
  return null;
}

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
function RangeBar({ value, low, high, status }: {
  value: number;
  low: number;
  high: number;
  status: string;
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

  const markerColor =
    status === "critical" ? c.rangeCritical
    : status === "high" || status === "low" ? c.rangeWarning
    : c.rangeNormal;

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
 * Tiny inline sparkline showing last 6 readings.
 * Color matches the status: green for normal, amber for high/low, red for critical.
 * Subtle reference range band provides context.
 */
function Sparkline({ data, status, rangeLow, rangeHigh }: {
  data: number[];
  status: string;
  rangeLow: number;
  rangeHigh: number;
}) {
  const c = useTableColors();
  const chartData = data.map((v) => ({ v }));

  const min = Math.min(...data, rangeLow);
  const max = Math.max(...data, rangeHigh);
  const pad = (max - min) * 0.15 || 0.5;
  const domain: [number, number] = [min - pad, max + pad];

  const strokeColor =
    status === "critical" ? c.critical
    : status === "high" || status === "low" ? c.warning
    : c.chart1;

  return (
    <div className="w-[72px] h-[28px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <ReferenceArea y1={rangeLow} y2={rangeHigh} fill={c.chart5} fillOpacity={c.bandSubtle} />
          <YAxis domain={domain} hide />
          <Line
            type="monotone"
            dataKey="v"
            stroke={strokeColor}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
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
          The lab results table consolidates status into a single flag badge next to the test
          name. Inline sparklines show recent trend history, and reference range interval bars
          give immediate visual context for where the current value sits.
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
                  <th className={TH}>Trend</th>
                  <th className={TH}>Reference Range</th>
                  <th className={TH}>Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {labResults.map((row) => {
                  const isAbnormal = row.status !== "normal";
                  return (
                    <tr key={row.test} className={row.status === "critical" ? "bg-[#C24E42]/5" : ""}>
                      <td className="p-4 font-medium">
                        {row.test}
                        <StatusFlag status={row.status} />
                      </td>
                      <td className="p-4">
                        <span className={isAbnormal ? "text-[#C24E42] font-medium tabular-nums" : "tabular-nums"}>
                          {row.value} <span className="text-muted-foreground font-normal">{row.unit}</span>
                        </span>
                      </td>
                      <td className="p-4">
                        <Sparkline
                          data={row.history}
                          status={row.status}
                          rangeLow={row.rangeLow}
                          rangeHigh={row.rangeHigh}
                        />
                      </td>
                      <td className="p-4">
                        <RangeBar
                          value={row.value}
                          low={row.rangeLow}
                          high={row.rangeHigh}
                          status={row.status}
                        />
                      </td>
                      <td className="p-4 text-muted-foreground">{row.date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {/* Legend */}
            <div className="flex items-center gap-6 px-4 py-3 border-t text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-[#388E3C]" />
                Normal
              </span>
              <span className="flex items-center gap-1.5">
                <Badge variant="warning" size="sm" className="text-[10px] px-1.5">H</Badge>
                Above Range
              </span>
              <span className="flex items-center gap-1.5">
                <Badge variant="warning" size="sm" className="text-[10px] px-1.5">L</Badge>
                Below Range
              </span>
              <span className="flex items-center gap-1.5">
                <Badge variant="critical" size="sm" className="text-[10px] px-1.5">CRIT</Badge>
                Critical
              </span>
              <span className="flex items-center gap-1.5 ml-2 border-l pl-4">
                <div className="w-8 h-1.5 rounded-full bg-muted relative">
                  <div className="absolute left-1/4 w-1/2 h-full rounded-full bg-[#388E3C]/20" />
                  <div className="absolute left-[60%] top-1/2 -translate-y-1/2 size-1.5 rounded-full bg-[#388E3C]" />
                </div>
                Value in Range
              </span>
            </div>
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
        code={`// Lab results with sparklines and range bars
interface LabResult {
  test: string;
  value: number;
  unit: string;
  rangeLow: number;
  rangeHigh: number;
  status: "normal" | "high" | "low" | "critical";
  date: string;
  history: number[];  // last 6 readings
}

// Status flag inline with test name
<td className="p-4 font-medium">
  {row.test}
  <StatusFlag status={row.status} />
</td>

// Inline sparkline with reference range band
<Sparkline
  data={row.history}
  status={row.status}
  rangeLow={row.rangeLow}
  rangeHigh={row.rangeHigh}
/>

// Visual reference range interval bar
<RangeBar
  value={row.value}
  low={row.rangeLow}
  high={row.rangeHigh}
  status={row.status}
/>`}
      />
    </div>
  );
}
