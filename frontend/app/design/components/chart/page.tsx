"use client";

import { useTheme } from "next-themes";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CodeBlock } from "@/components/design-system/CodeBlock";
import { HeartPulse, FlaskConical, Droplet } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Area,
  AreaChart,
} from "recharts";

// -- Types ----------------------------------------------------------------

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color?: string;
    payload?: Record<string, unknown>;
  }>;
  label?: string;
}

// -- Theme-aware colors ---------------------------------------------------

function useChartColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return {
    grid: isDark ? "#4A4A48" : "#E5E4DF",
    tick: isDark ? "#BFBFBA" : "#666663",
    chart1: isDark ? "#4A9A88" : "#2F5E52",
    chart4: isDark ? "#749BB0" : "#4A7A8C",
    chart5: isDark ? "#66BB6A" : "#388E3C",
    warning: isDark ? "#EBC47C" : "#D9A036",
    critical: isDark ? "#D46F65" : "#C24E42",
    gradientFrom: isDark ? 0.45 : 0.3,
    gradientTo: isDark ? 0.05 : 0,
    bandSubtle: isDark ? 0.12 : 0.08,
    bandMedium: isDark ? 0.18 : 0.12,
  };
}

// -- Data -----------------------------------------------------------------

// Basic trend: simple line chart, no reference ranges
const basicTrendData = [
  { date: "Jul", value: 198 },
  { date: "Aug", value: 205 },
  { date: "Sep", value: 195 },
  { date: "Oct", value: 188 },
  { date: "Nov", value: 192 },
  { date: "Dec", value: 184 },
  { date: "Jan", value: 178 },
];

// General pattern: reference range bands
const rangeBandData = [
  { month: "Jan", value: 7.2 },
  { month: "Feb", value: 6.8 },
  { month: "Mar", value: 6.5 },
  { month: "Apr", value: 6.1 },
  { month: "May", value: 5.7 },
  { month: "Jun", value: 5.2 },
];

// Sparkline metrics
const sparklineMetrics = [
  {
    name: "Glucose",
    current: "95 mg/dL",
    data: [{ v: 102 }, { v: 98 }, { v: 110 }, { v: 95 }, { v: 88 }, { v: 95 }],
    range: [70, 100] as [number, number],
    domain: [60, 120] as [number, number],
    status: "normal" as const,
  },
  {
    name: "Cholesterol",
    current: "215 mg/dL",
    data: [{ v: 240 }, { v: 232 }, { v: 225 }, { v: 220 }, { v: 218 }, { v: 215 }],
    range: [0, 200] as [number, number],
    domain: [150, 260] as [number, number],
    status: "warning" as const,
  },
  {
    name: "Creatinine",
    current: "1.1 mg/dL",
    data: [{ v: 1.0 }, { v: 1.05 }, { v: 1.1 }, { v: 1.08 }, { v: 1.12 }, { v: 1.1 }],
    range: [0.6, 1.2] as [number, number],
    domain: [0.4, 1.6] as [number, number],
    status: "normal" as const,
  },
  {
    name: "Potassium",
    current: "4.2 mEq/L",
    data: [{ v: 4.0 }, { v: 4.1 }, { v: 4.3 }, { v: 4.5 }, { v: 4.3 }, { v: 4.2 }],
    range: [3.5, 5.0] as [number, number],
    domain: [3.0, 5.5] as [number, number],
    status: "normal" as const,
  },
];

// Diabetes: HbA1c (higher starting point, showing treatment response)
const hba1cData = [
  { date: "Jan 24", value: 9.1 },
  { date: "Apr 24", value: 8.4 },
  { date: "Jul 24", value: 7.8 },
  { date: "Oct 24", value: 7.5 },
  { date: "Jan 25", value: 7.2 },
];

// CKD: eGFR decline over 2 years
const egfrData = [
  { date: "Jan 23", value: 68 },
  { date: "Jul 23", value: 62 },
  { date: "Jan 24", value: 54 },
  { date: "Jul 24", value: 47 },
  { date: "Jan 25", value: 38 },
];

// Hypertension: BP with multi-drug therapy intensification
const bpData = [
  { date: "Sep 1", systolic: 152, diastolic: 96 },
  { date: "Sep 15", systolic: 148, diastolic: 94, event: "Started Lisinopril 10mg" },
  { date: "Oct 1", systolic: 144, diastolic: 90 },
  { date: "Oct 15", systolic: 142, diastolic: 88, event: "↑ Lisinopril 20mg" },
  { date: "Nov 1", systolic: 138, diastolic: 86 },
  { date: "Nov 15", systolic: 136, diastolic: 84, event: "+ Amlodipine 5mg" },
  { date: "Dec 1", systolic: 132, diastolic: 82 },
  { date: "Dec 15", systolic: 130, diastolic: 80, event: "↑ Amlodipine 10mg" },
  { date: "Jan 1", systolic: 126, diastolic: 78, event: "+ HCTZ 12.5mg" },
  { date: "Jan 15", systolic: 122, diastolic: 76 },
];

// -- Shared components ----------------------------------------------------

function CustomTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const unitMap: Record<string, string> = {
    HbA1c: "%", eGFR: " mL/min", Systolic: " mmHg", Diastolic: " mmHg",
  };
  return (
    <div className="rounded-lg border bg-card p-3 shadow-md">
      <p className="text-sm font-medium">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {entry.value}{unitMap[entry.name] ?? ""}
        </p>
      ))}
      {typeof payload[0]?.payload?.event === "string" && (
        <p className="text-xs text-primary mt-1 border-t pt-1">
          {payload[0].payload.event}
        </p>
      )}
    </div>
  );
}

interface MedSegment { label: string; flex: number; active: boolean }

function MedicationTimeline({ segments }: { segments: MedSegment[] }) {
  const c = useChartColors();
  return (
    <div className="mt-3 ml-4 mr-8">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 font-medium">
        Medications
      </p>
      <div className="flex gap-0.5">
        {segments.map((seg, i) => (
          <div
            key={i}
            className="relative h-7 rounded text-[11px] flex items-center px-2 truncate overflow-hidden"
            style={{ flex: seg.flex }}
          >
            <div
              className="absolute inset-0 rounded"
              style={{
                backgroundColor: seg.active ? c.chart1 : c.grid,
                opacity: seg.active ? 0.2 : 0.4,
              }}
            />
            <span className="relative text-xs font-medium">{seg.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface MedRow { drug: string; segments: MedSegment[] }

function MultiMedTimeline({ rows }: { rows: MedRow[] }) {
  const c = useChartColors();
  return (
    <div className="mt-3 ml-4 mr-8">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 font-medium">
        Medications
      </p>
      <div className="space-y-px">
        {rows.map((row, ri) => (
          <div key={ri} className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground w-16 shrink-0 truncate text-right">
              {row.drug}
            </span>
            <div className="flex gap-px flex-1">
              {row.segments.map((seg, si) => (
                <div
                  key={si}
                  className="relative h-5 rounded-sm text-[10px] flex items-center px-1.5 truncate overflow-hidden"
                  style={{ flex: seg.flex }}
                >
                  {seg.active && (
                    <div
                      className="absolute inset-0 rounded-sm"
                      style={{ backgroundColor: c.chart1, opacity: 0.2 }}
                    />
                  )}
                  {seg.label && (
                    <span className="relative text-[10px] font-medium">{seg.label}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// -- Shared chart props ---------------------------------------------------

const CHART_MARGIN = { top: 10, right: 30, left: -10, bottom: 0 };

// -- Page -----------------------------------------------------------------

export default function ChartPage() {
  const c = useChartColors();

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Chart</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Clinical data visualizations using Recharts. Charts use the design system
          color palette, theme-aware colors, and evidence-based clinical visualization
          patterns.
        </p>
      </div>

      {/* ================================================================ */}
      {/*  GENERAL PATTERNS                                                */}
      {/* ================================================================ */}

      {/* Basic Lab Trend */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Lab Trend</h2>
        <p className="text-muted-foreground max-w-2xl">
          The default chart style for any lab value or vital sign. Clean line, horizontal
          gridlines, and an area fill. No reference ranges — use this when ranges aren&apos;t
          clinically meaningful or when showing a general trend.
        </p>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Total Cholesterol</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                6-month trend
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">178 mg/dL</p>
              <p className="text-xs text-muted-foreground">↓ 10% over 6mo</p>
              <Badge variant="positive" size="sm">Improving</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={basicTrendData} margin={CHART_MARGIN}>
                  <defs>
                    <linearGradient id="basicGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={c.chart1} stopOpacity={c.gradientFrom} />
                      <stop offset="95%" stopColor={c.chart1} stopOpacity={c.gradientTo} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                  <YAxis
                    domain={[150, 220]}
                    ticks={[160, 180, 200]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: c.tick, fontSize: 12 }}
                  />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke={c.chart1}
                    strokeWidth={2}
                    fill="url(#basicGrad)"
                    dot={{ fill: c.chart1, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart1, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Reference Range Bands */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Reference Range Bands</h2>
        <p className="text-muted-foreground max-w-2xl">
          Colored background zones communicate normal, borderline, and abnormal ranges
          instantly — more effective than reference lines alone. Bands use very low
          opacity so the data line remains the visual focus.
        </p>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Lab Value Trend</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                6-month trend with clinical range zones
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">5.2</p>
              <p className="text-xs text-muted-foreground">↓ 28% over 6mo</p>
              <Badge variant="positive" size="sm">Normal</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rangeBandData} margin={CHART_MARGIN}>
                  <ReferenceArea y1={4} y2={5.5} fill={c.chart5} fillOpacity={c.bandSubtle} />
                  <ReferenceArea y1={5.5} y2={6.5} fill={c.warning} fillOpacity={c.bandMedium} />
                  <ReferenceArea y1={6.5} y2={8} fill={c.critical} fillOpacity={c.bandSubtle} />
                  <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                  <YAxis
                    domain={[4, 8]}
                    ticks={[5, 6, 7]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: c.tick, fontSize: 12 }}
                  />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={c.chart1}
                    strokeWidth={2}
                    dot={{ fill: c.chart1, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart1, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sparklines */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sparklines</h2>
        <p className="text-muted-foreground max-w-2xl">
          Compact inline charts for multi-lab panel overviews. Each sparkline shows the
          trend with a subtle reference range band. Best for metabolic panels, CBC results,
          or any at-a-glance multi-metric view.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {sparklineMetrics.map((m) => (
            <div key={m.name} className="rounded-lg border p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">{m.name}</span>
                <span className="text-sm font-semibold">{m.current}</span>
              </div>
              <div className="h-10">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={m.data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                    <ReferenceArea
                      y1={m.range[0]}
                      y2={m.range[1]}
                      fill={c.chart5}
                      fillOpacity={c.bandSubtle}
                    />
                    <YAxis domain={m.domain} hide />
                    <Line
                      type="monotone"
                      dataKey="v"
                      stroke={m.status === "warning" ? c.warning : c.chart1}
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ================================================================ */}
      {/*  CLINICAL EXAMPLES                                               */}
      {/* ================================================================ */}

      <div className="space-y-4 pt-4">
        <h2 className="text-3xl font-medium">Disease-Specific Charts</h2>
        <p className="text-muted-foreground max-w-2xl">
          Most lab values and vitals use the <strong className="text-foreground">basic trend</strong> or{" "}
          <strong className="text-foreground">reference range band</strong> patterns above. For conditions
          where published clinical guidelines define specific staging, targets, or visualization
          best practices, we implement disease-specific charts with features like KDIGO staging
          bands, medication timelines, and clinically meaningful thresholds.
        </p>
        <div className="rounded-lg border bg-muted/50 p-4 max-w-2xl">
          <p className="text-sm text-muted-foreground">
            <strong className="text-foreground">When to use disease-specific charts:</strong> Only when a
            condition has evidence-based visualization patterns — e.g. KDIGO staging for CKD,
            ADA targets for diabetes, ACC/AHA thresholds for hypertension. All other values
            default to basic trend or reference range bands.
          </p>
        </div>
      </div>

      {/* Diabetes: HbA1c */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Diabetes — HbA1c Trend</h2>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Droplet className="size-5 text-muted-foreground" />
                HbA1c Trend
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">12-month glycemic control</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">7.2%</p>
              <p className="text-xs text-muted-foreground">↓ 21% over 12mo</p>
              <Badge variant="warning" size="sm">Above Target</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hba1cData} margin={CHART_MARGIN}>
                  {/* Clinical range bands: <7 on target, 7-8 above, 8-9 high, >9 very high */}
                  <ReferenceArea y1={5} y2={7} fill={c.chart5} fillOpacity={c.bandSubtle} />
                  <ReferenceArea y1={7} y2={8} fill={c.warning} fillOpacity={c.bandSubtle} />
                  <ReferenceArea y1={8} y2={10} fill={c.critical} fillOpacity={c.bandSubtle} />
                  <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                  <YAxis
                    domain={[5, 10]}
                    ticks={[6, 7, 8, 9]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: c.tick, fontSize: 12 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine
                    y={7}
                    stroke={c.chart5}
                    strokeDasharray="6 4"
                    label={{ value: "Target <7%", position: "insideTopRight", fill: c.chart5, fontSize: 11 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="HbA1c"
                    stroke={c.chart5}
                    strokeWidth={2}
                    dot={{ fill: c.chart5, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart5, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <MedicationTimeline
              segments={[
                { label: "Metformin 500mg", flex: 1, active: true },
                { label: "+ Jardiance 25mg", flex: 2, active: true },
                { label: "↑ Metformin 1000mg", flex: 1, active: true },
              ]}
            />
          </CardContent>
        </Card>
      </div>

      {/* CKD: eGFR with KDIGO staging */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">CKD — eGFR Staging</h2>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="size-5 text-muted-foreground" />
                Kidney Function Trend
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">2-year eGFR with KDIGO staging</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">38 mL/min</p>
              <p className="text-xs text-muted-foreground">↓ 44% over 2yr</p>
              <Badge variant="warning" size="sm">Stage G3b</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={egfrData} margin={CHART_MARGIN}>
                  {/* KDIGO staging bands */}
                  <ReferenceArea y1={90} y2={120} fill={c.chart5} fillOpacity={c.bandSubtle}
                    label={{ value: "G1", position: "insideTopRight", fontSize: 10, fill: c.tick }} />
                  <ReferenceArea y1={60} y2={90} fill={c.chart5} fillOpacity={0.05}
                    label={{ value: "G2", position: "insideTopRight", fontSize: 10, fill: c.tick }} />
                  <ReferenceArea y1={45} y2={60} fill={c.warning} fillOpacity={c.bandSubtle}
                    label={{ value: "G3a", position: "insideTopRight", fontSize: 10, fill: c.tick }} />
                  <ReferenceArea y1={30} y2={45} fill={c.warning} fillOpacity={c.bandMedium}
                    label={{ value: "G3b", position: "insideTopRight", fontSize: 10, fill: c.tick }} />
                  <ReferenceArea y1={15} y2={30} fill={c.critical} fillOpacity={c.bandSubtle}
                    label={{ value: "G4", position: "insideTopRight", fontSize: 10, fill: c.tick }} />
                  <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                  <YAxis
                    domain={[15, 120]}
                    ticks={[15, 30, 45, 60, 90]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: c.tick, fontSize: 12 }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="eGFR"
                    stroke={c.chart1}
                    strokeWidth={2}
                    dot={{ fill: c.chart1, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart1, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Hypertension: Blood Pressure */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Hypertension — Blood Pressure</h2>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <HeartPulse className="size-5 text-muted-foreground" />
                Blood Pressure Control
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">Medication therapy intensification over 5 months</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">122/76</p>
              <p className="text-xs text-muted-foreground">↓ 20% over 5mo</p>
              <Badge variant="positive" size="sm">At Goal</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={bpData} margin={CHART_MARGIN}>
                  {/* Goal zone: <130 systolic = controlled */}
                  <ReferenceArea y1={60} y2={130} fill={c.chart5} fillOpacity={c.bandSubtle} />
                  <ReferenceArea y1={130} y2={160} fill={c.critical} fillOpacity={c.bandSubtle} />
                  <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                  <YAxis
                    domain={[60, 160]}
                    ticks={[80, 100, 120, 140]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: c.tick, fontSize: 12 }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine
                    y={130}
                    stroke={c.warning}
                    strokeDasharray="6 4"
                    label={{ value: "SBP Goal", position: "insideTopRight", fill: c.warning, fontSize: 11 }}
                  />
                  <ReferenceLine
                    y={80}
                    stroke={c.chart4}
                    strokeDasharray="6 4"
                    label={{ value: "DBP Goal", position: "insideBottomRight", fill: c.chart4, fontSize: 11 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="systolic"
                    name="Systolic"
                    stroke={c.chart1}
                    strokeWidth={2}
                    dot={{ fill: c.chart1, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart1, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    name="Diastolic"
                    stroke={c.chart4}
                    strokeWidth={2}
                    dot={{ fill: c.chart4, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.chart4, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-2 text-sm">
              <span className="flex items-center gap-2">
                <span className="size-3 rounded-full" style={{ backgroundColor: c.chart1 }} />
                Systolic
              </span>
              <span className="flex items-center gap-2">
                <span className="size-3 rounded-full" style={{ backgroundColor: c.chart4 }} />
                Diastolic
              </span>
            </div>
            <MultiMedTimeline
              rows={[
                {
                  drug: "Lisinopril",
                  segments: [
                    { label: "", flex: 1, active: false },
                    { label: "10mg", flex: 2, active: true },
                    { label: "20mg", flex: 6, active: true },
                  ],
                },
                {
                  drug: "Amlodipine",
                  segments: [
                    { label: "", flex: 4, active: false },
                    { label: "5mg", flex: 2, active: true },
                    { label: "10mg", flex: 3, active: true },
                  ],
                },
                {
                  drug: "HCTZ",
                  segments: [
                    { label: "", flex: 8, active: false },
                    { label: "12.5mg", flex: 1, active: true },
                  ],
                },
              ]}
            />
          </CardContent>
        </Card>
      </div>

      {/* ================================================================ */}
      {/*  DESIGN GUIDANCE                                                 */}
      {/* ================================================================ */}

      {/* Design Principles */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Design Principles</h2>
        <p className="text-muted-foreground">
          Charts should embody clarity over decoration. Follow these principles:
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Data-Ink Ratio</h3>
            <p className="text-sm text-muted-foreground">
              Maximize data, minimize chrome. Every pixel should communicate information.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Clinical Range Bands</h3>
            <p className="text-sm text-muted-foreground">
              Use subtle background color zones to encode clinical meaning. Pre-attentive
              color processing lets users see normal/abnormal instantly without reading labels.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Subtle Grid</h3>
            <p className="text-sm text-muted-foreground">
              Horizontal gridlines only, dashed, theme-aware opacity. No vertical gridlines.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Medication Timeline</h3>
            <p className="text-sm text-muted-foreground">
              Align medication changes below the chart on the same time axis. Lets clinicians
              connect treatment changes to outcome trends at a glance.
            </p>
          </div>
        </div>
        <div className="rounded-lg border bg-muted/50 p-4">
          <h3 className="font-medium text-sm mb-2">Line & Point Specifications</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Stroke width:</span>
              <span className="ml-2 font-mono">2px</span>
            </div>
            <div>
              <span className="text-muted-foreground">Line caps:</span>
              <span className="ml-2 font-mono">round</span>
            </div>
            <div>
              <span className="text-muted-foreground">Data points:</span>
              <span className="ml-2 font-mono">4-6px</span>
            </div>
            <div>
              <span className="text-muted-foreground">Active dot:</span>
              <span className="ml-2 font-mono">6px + ring</span>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
          <h3 className="font-medium text-sm mb-2 text-destructive">Avoid</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>3D effects, bevels, or drop shadows on chart elements</li>
            <li>Bold gradients on bars (subtle area fills with opacity fade are acceptable)</li>
            <li>Decorative patterns or textures</li>
            <li>Animations beyond subtle transitions</li>
          </ul>
        </div>
      </div>

      {/* Color Reference */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Chart Colors</h2>
        <p className="text-muted-foreground">
          Use the design system palette for consistent data visualization.
        </p>
        <div className="grid grid-cols-5 gap-4">
          {[
            { name: "Chart 1", color: "#2F5E52", use: "Primary data" },
            { name: "Chart 2", color: "#D9A036", use: "Warning/threshold" },
            { name: "Chart 3", color: "#C24E42", use: "Critical/alert" },
            { name: "Chart 4", color: "#4A7A8C", use: "Info/reference" },
            { name: "Chart 5", color: "#388E3C", use: "Positive/target" },
          ].map((item) => (
            <div key={item.name} className="flex items-center gap-3 rounded-lg border p-3">
              <span className="size-4 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{item.name}</p>
                <p className="text-xs text-muted-foreground truncate">{item.use}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Code example */}
      <CodeBlock
        collapsible
        label="View Code — Reference Range Bands"
        code={`import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceArea,
} from "recharts";

// When reference range bands are present, use LineChart (no area fill).
// The bands provide the visual context — area fill would compete.
<ResponsiveContainer width="100%" height={256}>
  <LineChart data={data}>
    {/* Background range bands — render before data */}
    <ReferenceArea y1={0} y2={7} fill="#388E3C" fillOpacity={0.08} />
    <ReferenceArea y1={7} y2={8} fill="#D9A036" fillOpacity={0.1} />
    <ReferenceArea y1={8} y2={10} fill="#C24E42" fillOpacity={0.08} />

    <CartesianGrid strokeDasharray="6 4" stroke="#E5E4DF" vertical={false} />
    <XAxis dataKey="date" axisLine={false} tickLine={false} />
    <YAxis axisLine={false} tickLine={false} />
    <Tooltip />
    <Line
      type="monotone"
      dataKey="value"
      stroke="#388E3C"
      strokeWidth={2}
    />
  </LineChart>
</ResponsiveContainer>`}
      />
    </div>
  );
}
