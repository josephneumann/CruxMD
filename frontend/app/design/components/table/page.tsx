"use client";

import React, { useState } from "react";
import { useTheme } from "next-themes";
import { FlaskConical, Pill, ChevronDown, ChevronRight } from "lucide-react";
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

// Panel group: a named set of component results (e.g. CBC)
interface LabPanel {
  type: "panel";
  name: string;
  results: LabResult[];
}

// Standalone result: a single test not part of a panel
interface StandaloneResult {
  type: "standalone";
  result: LabResult;
}

type LabEntry = LabPanel | StandaloneResult;

const labEntries: LabEntry[] = [
  {
    type: "standalone",
    result: {
      test: "Hemoglobin A1c",
      value: 6.8,
      unit: "%",
      rangeLow: 4.0,
      rangeHigh: 5.6,
      interpretation: "H",
      date: "01/25/2026",
      history: [
        { value: 7.4, date: "08/12/2025" },
        { value: 7.1, date: "09/15/2025" },
        { value: 7.0, date: "10/14/2025" },
        { value: 6.9, date: "11/11/2025" },
        { value: 6.8, date: "12/16/2025" },
        { value: 6.8, date: "01/25/2026" },
      ],
    },
  },
  {
    type: "panel",
    name: "Complete Blood Count (CBC)",
    results: [
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
    ],
  },
];

// Mirrors MedicationRequest FHIR structure:
// - medication: from medicationCodeableConcept.text (includes drug + dose + form)
// - frequency: derived from dosageInstruction[].timing.repeat or .text
// - reason: from reasonReference[].display or reasonCode[].text
// - status: "active" | "completed" (FHIR values, not "discontinued")
// - authoredOn: from authoredOn (ISO 8601)
// - requester: from requester.display

interface MedicationRow {
  medication: string;
  frequency: string | null;
  reason: string;
  status: "active" | "completed";
  authoredOn: string;
  requester: string;
}

const medications: MedicationRow[] = [
  { medication: "Lisinopril 10 MG Oral Tablet", frequency: "1x daily", reason: "Hypertension", status: "active", authoredOn: "01/15/2025", requester: "Dr. Terri Gutmann" },
  { medication: "Metformin hydrochloride 500 MG Oral Tablet", frequency: "2x daily", reason: "Diabetes mellitus type 2", status: "active", authoredOn: "03/20/2025", requester: "Dr. Terri Gutmann" },
  { medication: "Atorvastatin 20 MG Oral Tablet", frequency: "1x daily", reason: "Hyperlipidemia", status: "active", authoredOn: "06/10/2024", requester: "Dr. Maia Williams" },
  { medication: "Warfarin Sodium 5 MG Oral Tablet", frequency: "1x daily", reason: "Atrial fibrillation", status: "completed", authoredOn: "12/01/2024", requester: "Dr. Terri Gutmann" },
  { medication: "Ibuprofen 200 MG Oral Tablet", frequency: "As needed", reason: "Osteoarthritis of knee", status: "active", authoredOn: "09/14/2025", requester: "Dr. Maia Williams" },
];

// -- Components ---------------------------------------------------------------

function MedStatusBadge({ status }: { status: MedicationRow["status"] }) {
  if (status === "active") return <Badge variant="positive" size="sm">Active</Badge>;
  return <Badge variant="neutral" size="sm">Completed</Badge>;
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

// -- Lab result row -----------------------------------------------------------

function LabResultRow({ row, indented }: { row: LabResult; indented?: boolean }) {
  const isCritical = row.interpretation === "HH" || row.interpretation === "LL";
  const isAbnormal = row.interpretation !== "N";
  const textSize = indented ? "text-[13px]" : "";
  return (
    <tr key={row.test} className={isCritical ? "bg-[#C24E42]/5" : ""}>
      <td className={`px-4 py-2.5 font-medium ${textSize} ${indented ? "pl-8" : ""}`}>{row.test}</td>
      <td className={`px-4 py-2.5 ${textSize}`}>
        <span className={`tabular-nums ${isCritical ? "text-[#C24E42] font-medium" : isAbnormal ? "text-[#D9A036] font-medium" : ""}`}>
          {row.value} <span className="text-muted-foreground font-normal">{row.unit}</span>
        </span>
      </td>
      <td className="px-4 py-2.5">
        <RangeBar
          value={row.value}
          low={row.rangeLow}
          high={row.rangeHigh}
          interpretation={row.interpretation}
        />
      </td>
      <td className="px-4 py-2.5">
        <SparklineWithDelta
          data={row.history}
          interpretation={row.interpretation}
          unit={row.unit}
        />
      </td>
      <td className="px-4 py-2.5 text-muted-foreground">{row.date}</td>
    </tr>
  );
}

// -- Table header cell helper -------------------------------------------------

const TH = "text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider";

// -- Page ---------------------------------------------------------------------

export default function TablePage() {
  const [expandedPanels, setExpandedPanels] = useState<Record<string, boolean>>({
    "Complete Blood Count (CBC)": true,
  });

  const togglePanel = (name: string) => {
    setExpandedPanels((prev) => ({ ...prev, [name]: !prev[name] }));
  };

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
          it&apos;s in range (via the range bar marker color), then assess the trend. Panel groups
          (like CBC) are collapsible; standalone results sit alongside them in the same table.
        </p>
        <Card className="py-0 gap-0">
          <div className="flex items-center gap-2 px-4 py-2 border-b">
            <FlaskConical className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">Lab Results</span>
          </div>
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
                {labEntries.map((entry) => {
                  if (entry.type === "panel") {
                    const isExpanded = expandedPanels[entry.name] ?? false;
                    const Chevron = isExpanded ? ChevronDown : ChevronRight;
                    return (
                      <React.Fragment key={entry.name}>
                        <tr
                          className="bg-muted/20 cursor-pointer select-none hover:bg-muted/40 transition-colors"
                          onClick={() => togglePanel(entry.name)}
                        >
                          <td colSpan={5} className="px-4 py-2.5">
                            <div className="flex items-center justify-between font-medium">
                              <div className="flex items-center gap-2">
                                {entry.name}
                                <span className="text-xs text-muted-foreground font-normal">
                                  ({entry.results.length} components)
                                </span>
                              </div>
                              <Chevron className="size-4 text-muted-foreground" />
                            </div>
                          </td>
                        </tr>
                        {isExpanded && entry.results.map((row) => (
                          <LabResultRow key={row.test} row={row} indented />
                        ))}
                      </React.Fragment>
                    );
                  }
                  return <LabResultRow key={entry.result.test} row={entry.result} />;
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Design documentation */}
        <div className="space-y-4 text-sm text-muted-foreground">
          <h3 className="text-lg font-medium text-foreground">Design Notes</h3>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Column Order — Clinical Reading Flow</p>
            <p>
              Columns are ordered to match how clinicians scan lab results: <strong className="text-foreground">Test → Result → Reference Range → Trend → Date</strong>.
              The eye identifies the test name, reads the numeric value, checks whether it falls
              within range (via the range bar), assesses the trend direction, then notes recency.
              This left-to-right flow mirrors the cognitive priority of clinical decision-making.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Range Bar — Interpretation Without Labels</p>
            <p>
              The reference range bar replaces text-based status badges entirely. A horizontal track
              shows the normal zone as a shaded region, with a colored dot marker indicating where
              the current value sits. Marker color encodes HL7 interpretation: <span className="text-[#388E3C]">green</span> for
              Normal (N), <span className="text-[#D9A036]">amber</span> for High/Low (H/L),
              and <span className="text-[#C24E42]">red</span> for Critically High/Low (HH/LL).
              This removes the need for separate badge components or a legend — the color is
              the interpretation, visible at a glance.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Result Value Color</p>
            <p>
              Result numbers use a three-tier color system matching the range bar marker:
              default text for normal values, amber for abnormal (H/L), and red for critical
              (HH/LL). This reinforces the range bar without requiring the user to look across
              to the bar for every row.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Sparkline Trends</p>
            <p>
              Each row includes a 72px inline sparkline showing the last 6 readings. The line
              color matches the current interpretation tier. A percentage-change annotation
              (e.g. &ldquo;↑ 12%&rdquo;) and &ldquo;since&rdquo; date are displayed alongside to give
              immediate context on trajectory and timeframe. Hovering over the sparkline reveals
              a tooltip with the exact value and date for each data point, positioned above the
              chart to avoid obscuring the line.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Panel Groups &amp; Standalone Results</p>
            <p>
              Lab results can appear as collapsible panel groups (e.g. CBC with 4 components) or
              standalone rows (e.g. HbA1c). Panel headers span the full table width with a chevron
              toggle on the right edge. Component rows within a panel are slightly indented and
              use a smaller font size to establish visual hierarchy. Standalone results render at
              the same level as panel headers. This structure mirrors how lab panels are ordered
              in clinical systems.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Compact Card Layout</p>
            <p>
              The card uses zero internal padding (<code className="text-xs bg-muted px-1 py-0.5 rounded">py-0 gap-0</code> overrides)
              with a slim title bar separated by a border. Column headers use reduced vertical
              padding. Data rows use <code className="text-xs bg-muted px-1 py-0.5 rounded">py-2.5</code> for
              density without sacrificing readability. Critical rows receive a subtle red background
              tint to draw attention without overwhelming the table.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">HL7 FHIR Interpretation Codes</p>
            <p>
              Values follow the HL7 FHIR Observation Interpretation code system:
              N (Normal), H (High), L (Low), HH (Critically High), LL (Critically Low).
              Note that Synthea fixture data does not include <code className="text-xs bg-muted px-1 py-0.5 rounded">interpretation</code> or <code className="text-xs bg-muted px-1 py-0.5 rounded">referenceRange</code> fields
              on Observations — interpretation must be derived at display time using LOINC-based
              reference ranges.
            </p>
          </div>
        </div>
      </div>

      {/* Medications */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Medications</h2>
        <p className="text-muted-foreground max-w-2xl">
          Data mirrors FHIR MedicationRequest structure. The medication column contains the full
          RxNorm display string (drug + dose + form) from <code className="text-xs bg-muted px-1 py-0.5 rounded">medicationCodeableConcept.text</code>.
          Frequency is derived from <code className="text-xs bg-muted px-1 py-0.5 rounded">dosageInstruction</code> timing
          data. Reason comes from <code className="text-xs bg-muted px-1 py-0.5 rounded">reasonReference.display</code>.
          Separate dosage and route columns are unnecessary — both are embedded in the medication name.
        </p>
        <Card className="py-0 gap-0">
          <div className="flex items-center gap-2 px-4 py-2 border-b">
            <Pill className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">Medications</span>
          </div>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className={TH}>Medication</th>
                  <th className={TH}>Frequency</th>
                  <th className={TH}>Reason</th>
                  <th className={TH}>Status</th>
                  <th className={TH}>Prescribed</th>
                  <th className={TH}>Requester</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {medications.map((row) => (
                  <tr key={row.medication}>
                    <td className="px-4 py-2 text-sm font-medium">{row.medication}</td>
                    <td className="px-4 py-2 text-sm">{row.frequency ?? <span className="text-muted-foreground italic">—</span>}</td>
                    <td className="px-4 py-2 text-sm text-muted-foreground">{row.reason}</td>
                    <td className="px-4 py-2"><MedStatusBadge status={row.status} /></td>
                    <td className="px-4 py-2 text-sm text-muted-foreground">{row.authoredOn}</td>
                    <td className="px-4 py-2 text-sm text-muted-foreground">{row.requester}</td>
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
          Simple key-value or props reference table using the shared compact card wrapper
          and consistent column header styling.
        </p>
        <Card className="py-0 gap-0">
          <div className="flex items-center gap-2 px-4 py-2 border-b">
            <span className="text-sm font-medium">Props API</span>
          </div>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className={TH}>Name</th>
                  <th className={TH}>Type</th>
                  <th className={TH}>Default</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <tr>
                  <td className="px-4 py-2.5 font-mono text-sm">variant</td>
                  <td className="px-4 py-2.5 text-sm text-muted-foreground">string</td>
                  <td className="px-4 py-2.5 font-mono text-sm">&quot;default&quot;</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono text-sm">size</td>
                  <td className="px-4 py-2.5 text-sm text-muted-foreground">string</td>
                  <td className="px-4 py-2.5 font-mono text-sm">&quot;md&quot;</td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Shared styling documentation */}
        <div className="space-y-4 text-sm text-muted-foreground">
          <h3 className="text-lg font-medium text-foreground">Shared Table Styling</h3>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Card Wrapper</p>
            <p>
              All tables use <code className="text-xs bg-muted px-1 py-0.5 rounded">Card</code> with <code className="text-xs bg-muted px-1 py-0.5 rounded">py-0 gap-0</code> overrides
              to eliminate the default vertical padding and gap. A slim title bar sits at the top,
              separated from the table by a border. This keeps the card chrome minimal so the data
              is the focus.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Column Headers</p>
            <p>
              All column headers share the same class: uppercase, <code className="text-xs bg-muted px-1 py-0.5 rounded">text-xs</code>,
              muted foreground color, with <code className="text-xs bg-muted px-1 py-0.5 rounded">px-4 py-2</code> padding
              and a <code className="text-xs bg-muted px-1 py-0.5 rounded">bg-muted/30</code> background. This creates a
              consistent, unobtrusive header row across all table variants.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Data Rows</p>
            <p>
              Data cells use <code className="text-xs bg-muted px-1 py-0.5 rounded">px-4 py-2</code> to <code className="text-xs bg-muted px-1 py-0.5 rounded">py-2.5</code> padding
              depending on content density, with <code className="text-xs bg-muted px-1 py-0.5 rounded">text-sm</code> font
              sizing. Rows are separated by <code className="text-xs bg-muted px-1 py-0.5 rounded">divide-y</code> borders.
              The first column is typically <code className="text-xs bg-muted px-1 py-0.5 rounded">font-medium</code> to
              anchor the eye, while secondary columns like dates use <code className="text-xs bg-muted px-1 py-0.5 rounded">text-muted-foreground</code>.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Status Badges</p>
            <p>
              Status indicators use the <code className="text-xs bg-muted px-1 py-0.5 rounded">Badge</code> component
              at <code className="text-xs bg-muted px-1 py-0.5 rounded">sm</code> size. The <code className="text-xs bg-muted px-1 py-0.5 rounded">positive</code> variant
              (green) is used for active states, and <code className="text-xs bg-muted px-1 py-0.5 rounded">neutral</code> (gray)
              for inactive or discontinued states. Badges are placed in the final column as a
              scannable status indicator.
            </p>
          </div>
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
