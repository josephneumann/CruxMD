"use client";

import type { ClinicalVisualization } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FlaskConical, HeartPulse } from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine as RechartReferenceLine,
  ReferenceArea,
} from "recharts";
import { useChartColors, CHART_MARGIN, ChartTooltip, MultiMedTimeline } from "./chart-utils";

// Map severity to chart color token
function bandColor(severity: string, c: ReturnType<typeof useChartColors>) {
  if (severity === "normal") return c.chart5;
  if (severity === "warning") return c.warning;
  return c.critical;
}

// Pick icon based on series names
function ChartIcon({ names }: { names: string[] }) {
  const lower = names.map((n) => n.toLowerCase()).join(" ");
  const isVital = /heart|pulse|bp|blood pressure|systolic|diastolic|rate/.test(lower);
  const Icon = isVital ? HeartPulse : FlaskConical;
  return <Icon className="size-5 text-muted-foreground" />;
}

export function TrendChart({ viz }: { viz: ClinicalVisualization }) {
  const c = useChartColors();
  const series = viz.series ?? [];
  const rangeBands = viz.range_bands ?? [];
  const referenceLines = viz.reference_lines ?? [];

  if (series.length === 0) return null;

  const isMulti = series.length > 1;
  const hasRangeBands = rangeBands.length > 0;
  const seriesNames = series.map((s) => s.name);

  // Build unified data array keyed by date
  const dataMap = new Map<string, Record<string, unknown>>();
  for (const s of series) {
    for (const pt of s.data_points) {
      const existing = dataMap.get(pt.date) ?? { date: pt.date };
      if (isMulti) {
        existing[s.name] = pt.value;
      } else {
        existing.value = pt.value;
      }
      if (pt.label) existing.event = pt.label;
      dataMap.set(pt.date, existing);
    }
  }
  const data = Array.from(dataMap.values());

  const multiColors = [c.chart1, c.chart4];
  const containerHeight = hasRangeBands || isMulti ? "h-64" : "h-56";

  const badgeVariant = viz.trend_status ?? "neutral";

  // Unique gradient ID
  const gradId = `grad-${viz.title.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <ChartIcon names={seriesNames} />
            {viz.title}
          </CardTitle>
          {viz.subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{viz.subtitle}</p>
          )}
        </div>
        {(viz.current_value || viz.trend_summary) && (
          <div className="text-right">
            {viz.current_value && (
              <p className="text-2xl font-semibold">{viz.current_value}</p>
            )}
            {viz.trend_summary && (
              <Badge variant={badgeVariant} size="sm">{viz.trend_summary}</Badge>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className={containerHeight}>
          <ResponsiveContainer width="100%" height="100%">
            {/* Variant A: basic single series, no range bands */}
            {!isMulti && !hasRangeBands ? (
              <AreaChart data={data} margin={CHART_MARGIN}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={c.line} stopOpacity={c.gradientFrom} />
                    <stop offset="95%" stopColor={c.line} stopOpacity={c.gradientTo} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  name={series[0].name}
                  unit={series[0].unit ? ` ${series[0].unit}` : undefined}
                  stroke={c.line}
                  strokeWidth={2}
                  fill={`url(#${gradId})`}
                  dot={{ fill: c.line, strokeWidth: 0, r: 4 }}
                  activeDot={{ fill: c.line, strokeWidth: 2, stroke: "#fff", r: 6 }}
                />
              </AreaChart>
            ) : (
              <LineChart data={data} margin={CHART_MARGIN}>
                {/* Range bands */}
                {rangeBands.map((band, i) => (
                  <ReferenceArea
                    key={`band-${i}`}
                    y1={band.y1}
                    y2={band.y2}
                    fill={bandColor(band.severity, c)}
                    fillOpacity={band.severity === "normal" ? c.bandSubtle : c.bandMedium}
                    label={band.label ? {
                      value: band.label,
                      position: "insideTopRight" as const,
                      fontSize: 10,
                      fill: c.tick,
                    } : undefined}
                  />
                ))}
                <CartesianGrid strokeDasharray="6 4" stroke={c.grid} vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: c.tick, fontSize: 12 }} />
                <Tooltip content={<ChartTooltip />} />
                {/* Reference lines */}
                {referenceLines.map((rl, i) => (
                  <RechartReferenceLine
                    key={`ref-${i}`}
                    y={rl.value}
                    stroke={c.chart5}
                    strokeDasharray="6 4"
                    label={{ value: rl.label, position: "insideTopRight" as const, fill: c.chart5, fontSize: 11 }}
                  />
                ))}
                {/* Data lines */}
                {isMulti ? (
                  series.map((s, i) => (
                    <Line
                      key={s.name}
                      type="monotone"
                      dataKey={s.name}
                      name={s.name}
                      unit={s.unit ? ` ${s.unit}` : undefined}
                      stroke={multiColors[i % multiColors.length]}
                      strokeWidth={2}
                      dot={{ fill: multiColors[i % multiColors.length], strokeWidth: 0, r: 4 }}
                      activeDot={{ fill: multiColors[i % multiColors.length], strokeWidth: 2, stroke: "#fff", r: 6 }}
                    />
                  ))
                ) : (
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={series[0].name}
                    unit={series[0].unit ? ` ${series[0].unit}` : undefined}
                    stroke={c.line}
                    strokeWidth={2}
                    dot={{ fill: c.line, strokeWidth: 0, r: 4 }}
                    activeDot={{ fill: c.line, strokeWidth: 2, stroke: "#fff", r: 6 }}
                  />
                )}
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
        {/* Multi-series legend */}
        {isMulti && (
          <div className="flex items-center justify-center gap-6 mt-2 text-sm">
            {series.map((s, i) => (
              <span key={s.name} className="flex items-center gap-2">
                <span className="size-3 rounded-full" style={{ backgroundColor: multiColors[i % multiColors.length] }} />
                {s.name}
              </span>
            ))}
          </div>
        )}
        {/* Medication timeline */}
        {viz.medications && viz.medications.length > 0 && (
          <MultiMedTimeline rows={viz.medications} />
        )}
      </CardContent>
    </Card>
  );
}
