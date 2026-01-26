"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CodeBlock } from "@/components/design-system/CodeBlock";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color?: string;
    payload?: { event?: string };
  }>;
  label?: string;
}

const hba1cData = [
  { date: "Jan 24", value: 8.2 },
  { date: "Apr 24", value: 7.9 },
  { date: "Jul 24", value: 7.8 },
  { date: "Oct 24", value: 7.5 },
  { date: "Jan 25", value: 7.2 },
];

const bpData = [
  { date: "Oct 15", systolic: 142, diastolic: 92, event: null },
  { date: "Nov 1", systolic: 138, diastolic: 88, event: "Started Lisinopril 10mg" },
  { date: "Nov 15", systolic: 134, diastolic: 86, event: null },
  { date: "Dec 1", systolic: 136, diastolic: 88, event: null },
  { date: "Dec 15", systolic: 130, diastolic: 84, event: "Increased to 20mg" },
  { date: "Jan 1", systolic: 128, diastolic: 82, event: null },
  { date: "Jan 15", systolic: 124, diastolic: 80, event: null },
];

function CustomTooltip({ active, payload, label }: ChartTooltipProps) {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border bg-card p-3 shadow-md">
        <p className="text-sm font-medium">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
            {entry.name === "HbA1c" ? "%" : " mmHg"}
          </p>
        ))}
        {payload[0]?.payload?.event && (
          <p className="text-xs text-primary mt-1 border-t pt-1">
            {payload[0].payload.event}
          </p>
        )}
      </div>
    );
  }
  return null;
}

export default function ChartPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Chart</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Clinical data visualizations using Recharts. Charts use the design system
          color palette and follow the minimal, data-forward aesthetic.
        </p>
      </div>

      {/* HbA1c Trend */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Lab Trend</h2>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>HbA1c Trend</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">12-month glycemic control</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">7.2%</p>
              <Badge variant="positive" size="sm">On Target</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hba1cData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="hba1cGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7D8B6F" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#7D8B6F" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#666663", fontSize: 12 }}
                  />
                  <YAxis
                    domain={[6, 9]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#666663", fontSize: 12 }}
                    tickFormatter={(value) => `${value}%`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine
                    y={7}
                    stroke="#7D8B6F"
                    strokeDasharray="5 5"
                    label={{ value: "Target <7%", position: "right", fill: "#7D8B6F", fontSize: 11 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name="HbA1c"
                    stroke="#7D8B6F"
                    strokeWidth={2}
                    fill="url(#hba1cGradient)"
                    dot={{ fill: "#7D8B6F", strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: "#7D8B6F", strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Blood Pressure Intensification */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Clinical Intensification</h2>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Blood Pressure Control</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">Treatment response over 3 months</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold">124/80</p>
              <Badge variant="positive" size="sm">Controlled</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={bpData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#666663", fontSize: 12 }}
                  />
                  <YAxis
                    domain={[70, 150]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#666663", fontSize: 12 }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine
                    y={130}
                    stroke="#D4A27F"
                    strokeDasharray="5 5"
                    label={{ value: "SBP Goal", position: "right", fill: "#D4A27F", fontSize: 11 }}
                  />
                  <ReferenceLine
                    y={80}
                    stroke="#8B8FC7"
                    strokeDasharray="5 5"
                    label={{ value: "DBP Goal", position: "right", fill: "#8B8FC7", fontSize: 11 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="systolic"
                    name="Systolic"
                    stroke="#CC785C"
                    strokeWidth={2}
                    dot={{ fill: "#CC785C", strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: "#CC785C", strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    name="Diastolic"
                    stroke="#8B8FC7"
                    strokeWidth={2}
                    dot={{ fill: "#8B8FC7", strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: "#8B8FC7", strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-4 text-sm">
              <span className="flex items-center gap-2">
                <span className="size-3 rounded-full bg-[#CC785C]" />
                Systolic
              </span>
              <span className="flex items-center gap-2">
                <span className="size-3 rounded-full bg-[#8B8FC7]" />
                Diastolic
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

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
            <h3 className="font-medium text-sm mb-2">Direct Labeling</h3>
            <p className="text-sm text-muted-foreground">
              Label data points directly when possible. Prefer inline labels over legends.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Subtle Grid</h3>
            <p className="text-sm text-muted-foreground">
              Horizontal gridlines only, dashed, using Cloud Light (#E5E4DF). No vertical gridlines.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium text-sm mb-2">Purposeful Color</h3>
            <p className="text-sm text-muted-foreground">
              Color encodes meaning, not decoration. Use clinical insight colors for thresholds.
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
            { name: "Chart 1", color: "#CC785C", use: "Primary data" },
            { name: "Chart 2", color: "#7D8B6F", use: "Positive/target" },
            { name: "Chart 3", color: "#8B8FC7", use: "Secondary data" },
            { name: "Chart 4", color: "#D4A27F", use: "Warning/threshold" },
            { name: "Chart 5", color: "#61AAF2", use: "Info/reference" },
          ].map((item) => (
            <div
              key={item.name}
              className="flex items-center gap-3 rounded-lg border p-3"
            >
              <span
                className="size-4 rounded-full shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{item.name}</p>
                <p className="text-xs text-muted-foreground truncate">{item.use}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Usage */}
      <CodeBlock
        collapsible
        label="View Code"
        code={`import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

const data = [
  { date: "Jan", value: 8.2 },
  { date: "Apr", value: 7.9 },
];

<ResponsiveContainer width="100%" height={256}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" stroke="#E5E4DF" />
    <XAxis dataKey="date" />
    <YAxis />
    <Tooltip />
    <Line
      type="monotone"
      dataKey="value"
      stroke="#7D8B6F"
      strokeWidth={2}
    />
  </LineChart>
</ResponsiveContainer>`}
      />
    </div>
  );
}
