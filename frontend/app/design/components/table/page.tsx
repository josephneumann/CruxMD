"use client";

import React, { useState } from "react";
import { useTheme } from "next-themes";
import { FlaskConical, Pill, Syringe, HeartPulse, ShieldAlert, Stethoscope, CalendarDays, ChevronDown, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
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

// Mirrors FHIR Immunization structure:
// - vaccine: from vaccineCode.text (CVX display string)
// - date: from occurrenceDateTime
// - location: from location.display
// - status: always "completed" in Synthea fixtures

interface ImmunizationRow {
  vaccine: string;
  date: string;
  location: string;
  status: "completed";
}

const immunizations: ImmunizationRow[] = [
  { vaccine: "Influenza, seasonal, injectable, preservative free", date: "10/15/2025", location: "River's Edge Primary Care LLC", status: "completed" },
  { vaccine: "Influenza, seasonal, injectable, preservative free", date: "10/22/2024", location: "River's Edge Primary Care LLC", status: "completed" },
  { vaccine: "COVID-19, mRNA, LNP-S, PF, 100 mcg/0.5mL dose", date: "06/02/2024", location: "University of MA Med Ctr", status: "completed" },
  { vaccine: "COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose", date: "01/15/2024", location: "University of MA Med Ctr", status: "completed" },
  { vaccine: "Td (adult), 5 Lf tetanus toxoid, preservative free, adsorbed", date: "08/09/2023", location: "River's Edge Primary Care LLC", status: "completed" },
  { vaccine: "Zoster vaccine, live", date: "03/14/2023", location: "River's Edge Primary Care LLC", status: "completed" },
  { vaccine: "Hep B, adult", date: "11/20/2022", location: "University of MA Med Ctr", status: "completed" },
];

// Mirrors FHIR Observation (vital-signs category) structure:
// - vital: from code.text (LOINC display string)
// - value: from valueQuantity.value (or component[] for BP)
// - unit: from valueQuantity.unit
// - loinc: from code.coding[0].code
// - date: from effectiveDateTime

interface VitalSignRow {
  vital: string;
  value: string;
  unit: string;
  loinc: string;
  date: string;
}

const vitalSigns: VitalSignRow[] = [
  { vital: "Blood Pressure", value: "128/82", unit: "mmHg", loinc: "85354-9", date: "01/25/2026" },
  { vital: "Heart Rate", value: "72", unit: "/min", loinc: "8867-4", date: "01/25/2026" },
  { vital: "Respiratory Rate", value: "16", unit: "/min", loinc: "9279-1", date: "01/25/2026" },
  { vital: "Body Temperature", value: "37.1", unit: "°C", loinc: "8310-5", date: "01/25/2026" },
  { vital: "Body Weight", value: "91.8", unit: "kg", loinc: "29463-7", date: "01/25/2026" },
  { vital: "Body Height", value: "170.2", unit: "cm", loinc: "8302-2", date: "01/25/2026" },
  { vital: "BMI", value: "31.7", unit: "kg/m²", loinc: "39156-5", date: "01/25/2026" },
  { vital: "Pain Severity", value: "3", unit: "/10", loinc: "72514-3", date: "01/25/2026" },
];

// Mirrors FHIR AllergyIntolerance structure:
// - allergen: from code.coding[0].display (SNOMED)
// - category: from category[0] ("medication" | "food" | "environment")
// - criticality: from criticality ("high" | "low")
// - clinicalStatus: from clinicalStatus.coding[0].code
// - onsetDate: from onsetDateTime
// NOTE: 0 AllergyIntolerance resources exist in Synthea fixtures.
// Mock data shown for design reference.

interface AllergyRow {
  allergen: string;
  category: "medication" | "food" | "environment";
  criticality: "high" | "low";
  clinicalStatus: "active" | "inactive";
  onsetDate: string;
}

const allergies: AllergyRow[] = [
  { allergen: "Penicillin", category: "medication", criticality: "high", clinicalStatus: "active", onsetDate: "03/15/2018" },
  { allergen: "Shellfish", category: "food", criticality: "high", clinicalStatus: "active", onsetDate: "06/20/2010" },
  { allergen: "Latex", category: "environment", criticality: "low", clinicalStatus: "active", onsetDate: "11/08/2020" },
  { allergen: "Sulfonamide", category: "medication", criticality: "low", clinicalStatus: "active", onsetDate: "09/03/2022" },
];

// Mirrors FHIR Procedure structure:
// - procedure: from code.text (SNOMED display)
// - date: from performedPeriod.start
// - location: from location.display
// - reason: from reasonReference[].display or reasonCode[].coding[0].display
// - status: always "completed" in Synthea (omitted from display)

interface ProcedureRow {
  procedure: string;
  date: string;
  location: string;
  reason: string | null;
}

const procedures: ProcedureRow[] = [
  { procedure: "Depression screening", date: "01/25/2026", location: "River's Edge Primary Care LLC", reason: null },
  { procedure: "Medication reconciliation", date: "01/15/2026", location: "River's Edge Primary Care LLC", reason: null },
  { procedure: "Spirometry", date: "08/15/2025", location: "River's Edge Primary Care LLC", reason: "Pulmonary emphysema" },
  { procedure: "Colonoscopy", date: "06/20/2024", location: "University of MA Med Ctr", reason: "Screening for occult blood" },
  { procedure: "Percutaneous coronary intervention", date: "03/30/2024", location: "Fitchburg Outpatient Clinic", reason: "Ischemic heart disease" },
  { procedure: "Physical therapy procedure", date: "11/05/2023", location: "River's Edge Primary Care LLC", reason: "Osteoarthritis of knee" },
  { procedure: "Dental care", date: "08/23/2023", location: "Shriners Hospital for Children", reason: "Patient referral for dental care" },
];

// Mirrors FHIR Encounter structure:
// - type: from type[0].coding[0].display (SNOMED)
// - encounterClass: from class.code (v3-ActCode: AMB, EMER, IMP)
// - date: from period.start
// - provider: from participant[0].individual.display
// - location: from location[0].location.display
// - reason: from reasonCode[0].coding[0].display (56% populated)

interface EncounterRow {
  type: string;
  encounterClass: "AMB" | "EMER" | "IMP";
  date: string;
  provider: string;
  location: string;
  reason: string | null;
}

const encounters: EncounterRow[] = [
  { type: "General examination of patient", encounterClass: "AMB", date: "01/25/2026", provider: "Dr. Quentin Fritsch", location: "River's Edge Primary Care LLC", reason: null },
  { type: "Encounter for problem", encounterClass: "AMB", date: "11/15/2025", provider: "Dr. Terri Gutmann", location: "River's Edge Primary Care LLC", reason: "Hypertension" },
  { type: "Emergency room admission", encounterClass: "EMER", date: "07/14/2025", provider: "Dr. Olympia Ward", location: "Nurse on Call", reason: "Asthma" },
  { type: "Prenatal visit", encounterClass: "AMB", date: "05/10/2025", provider: "Dr. Terri Gutmann", location: "River's Edge Primary Care LLC", reason: null },
  { type: "Hospital admission", encounterClass: "IMP", date: "11/22/2024", provider: "Dr. Shayne Gutmann", location: "Windsor Nursing & Retirement Home", reason: "Patient transfer to SNF" },
  { type: "Urgent care clinic", encounterClass: "EMER", date: "09/03/2024", provider: "Dr. Maia Williams", location: "Fitchburg Outpatient Clinic", reason: "Acute bronchitis" },
  { type: "Well child visit", encounterClass: "AMB", date: "04/07/2024", provider: "Dr. Quentin Fritsch", location: "River's Edge Primary Care LLC", reason: null },
];

// -- Table header cell helper -------------------------------------------------

const TH = "text-left px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider";

// -- Components ---------------------------------------------------------------

function MedStatusBadge({ status }: { status: MedicationRow["status"] }) {
  if (status === "active") {
    return <span className="text-xs text-[#388E3C] dark:text-[#66BB6A]">Active</span>;
  }
  return <span className="text-xs text-muted-foreground">Completed</span>;
}

// -- Sortable column header ---------------------------------------------------

type SortDir = "asc" | "desc" | null;

function SortHeader({ label, active, direction, onClick }: {
  label: string;
  active: boolean;
  direction: SortDir;
  onClick: () => void;
}) {
  const Icon = active ? (direction === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th
      className={`${TH} cursor-pointer select-none hover:text-foreground transition-colors`}
      onClick={onClick}
    >
      <div className="flex items-center gap-1">
        {label}
        <Icon className={`size-3 ${active ? "text-foreground" : ""}`} />
      </div>
    </th>
  );
}

function useSortState<K extends string>(defaultKey?: K) {
  const [sortKey, setSortKey] = useState<K | null>(defaultKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const toggle = (key: K) => {
    if (sortKey === key) {
      if (sortDir === "asc") setSortDir("desc");
      else if (sortDir === "desc") { setSortKey(null); setSortDir(null); }
      else setSortDir("asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  return { sortKey, sortDir, toggle };
}

function sortRows<T>(rows: T[], key: string | null, dir: SortDir, accessor: (row: T, key: string) => string | number): T[] {
  if (!key || !dir) return rows;
  return [...rows].sort((a, b) => {
    const va = accessor(a, key);
    const vb = accessor(b, key);
    if (typeof va === "number" && typeof vb === "number") return dir === "asc" ? va - vb : vb - va;
    return dir === "asc" ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
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

// -- Medications table with sort + active/completed divider -------------------

type MedSortKey = "medication" | "frequency" | "reason" | "status" | "authoredOn" | "requester";

function medAccessor(row: MedicationRow, key: string): string {
  return String(row[key as keyof MedicationRow] ?? "");
}

function MedRow({ row }: { row: MedicationRow }) {
  return (
    <tr key={row.medication}>
      <td className="px-4 py-2 text-sm font-medium">{row.medication}</td>
      <td className="px-4 py-2 text-sm">{row.frequency ?? <span className="text-muted-foreground italic">—</span>}</td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{row.reason}</td>
      <td className="px-4 py-2"><MedStatusBadge status={row.status} /></td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{row.authoredOn}</td>
      <td className="px-4 py-2 text-sm text-muted-foreground">{row.requester}</td>
    </tr>
  );
}

function MedicationsTable() {
  const { sortKey, sortDir, toggle } = useSortState<MedSortKey>();

  const activeMeds = medications.filter((m) => m.status === "active");
  const completedMeds = medications.filter((m) => m.status === "completed");
  const sortedActive = sortRows(activeMeds, sortKey, sortDir, medAccessor);
  const sortedCompleted = sortRows(completedMeds, sortKey, sortDir, medAccessor);

  const cols: { key: MedSortKey; label: string }[] = [
    { key: "medication", label: "Medication" },
    { key: "frequency", label: "Frequency" },
    { key: "reason", label: "Reason" },
    { key: "status", label: "Status" },
    { key: "authoredOn", label: "Prescribed" },
    { key: "requester", label: "Requester" },
  ];

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
          {sortedActive.map((row) => <MedRow key={row.medication} row={row} />)}
        </tbody>
        {sortedCompleted.length > 0 && (
          <tbody className="divide-y">
            <tr>
              <td colSpan={6} className="px-4 py-1.5 bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Completed</span>
              </td>
            </tr>
            {sortedCompleted.map((row) => <MedRow key={row.medication} row={row} />)}
          </tbody>
        )}
      </table>
    </CardContent>
  );
}

// -- Basic props table with sort -----------------------------------------------

interface PropRow { name: string; type: string; defaultVal: string }
const propRows: PropRow[] = [
  { name: "variant", type: "string", defaultVal: '"default"' },
  { name: "size", type: "string", defaultVal: '"md"' },
];

type PropSortKey = "name" | "type" | "defaultVal";

function BasicPropsTable() {
  const { sortKey, sortDir, toggle } = useSortState<PropSortKey>();
  const sorted = sortRows(propRows, sortKey, sortDir, (row, key) => row[key as keyof PropRow]);

  return (
    <CardContent className="p-0">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/30">
            <SortHeader label="Name" active={sortKey === "name"} direction={sortKey === "name" ? sortDir : null} onClick={() => toggle("name")} />
            <SortHeader label="Type" active={sortKey === "type"} direction={sortKey === "type" ? sortDir : null} onClick={() => toggle("type")} />
            <SortHeader label="Default" active={sortKey === "defaultVal"} direction={sortKey === "defaultVal" ? sortDir : null} onClick={() => toggle("defaultVal")} />
          </tr>
        </thead>
        <tbody className="divide-y">
          {sorted.map((row) => (
            <tr key={row.name}>
              <td className="px-4 py-2.5 font-mono text-sm">{row.name}</td>
              <td className="px-4 py-2.5 text-sm text-muted-foreground">{row.type}</td>
              <td className="px-4 py-2.5 font-mono text-sm">{row.defaultVal}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Immunizations table with sort ---------------------------------------------

type ImmSortKey = "vaccine" | "date" | "location";

function ImmunizationsTable() {
  const { sortKey, sortDir, toggle } = useSortState<ImmSortKey>();
  const sorted = sortRows(immunizations, sortKey, sortDir, (row, key) => row[key as keyof ImmunizationRow]);

  const cols: { key: ImmSortKey; label: string }[] = [
    { key: "vaccine", label: "Vaccine" },
    { key: "date", label: "Date" },
    { key: "location", label: "Location" },
  ];

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
            <tr key={`${row.vaccine}-${row.date}-${i}`}>
              <td className="px-4 py-2 text-sm font-medium">{row.vaccine}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.date}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.location}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Vitals table with sort ---------------------------------------------------

type VitalSortKey = "vital" | "value" | "date";

function VitalsTable() {
  const { sortKey, sortDir, toggle } = useSortState<VitalSortKey>();
  const sorted = sortRows(vitalSigns, sortKey, sortDir, (row, key) => {
    if (key === "value") return parseFloat(row.value) || 0;
    return row[key as keyof VitalSignRow];
  });

  const cols: { key: VitalSortKey; label: string }[] = [
    { key: "vital", label: "Vital Sign" },
    { key: "value", label: "Value" },
    { key: "date", label: "Date" },
  ];

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
          {sorted.map((row) => (
            <tr key={row.loinc}>
              <td className="px-4 py-2 text-sm font-medium">{row.vital}</td>
              <td className="px-4 py-2 text-sm tabular-nums">
                {row.value} <span className="text-muted-foreground">{row.unit}</span>
              </td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Allergies table with sort ------------------------------------------------

type AllergySortKey = "allergen" | "category" | "criticality" | "clinicalStatus" | "onsetDate";

function CriticalityText({ criticality }: { criticality: AllergyRow["criticality"] }) {
  if (criticality === "high") {
    return <span className="text-xs text-[#C24E42] dark:text-[#D46F65]">High</span>;
  }
  return <span className="text-xs text-muted-foreground">Low</span>;
}

function AllergyStatusText({ status }: { status: AllergyRow["clinicalStatus"] }) {
  if (status === "active") {
    return <span className="text-xs text-[#388E3C] dark:text-[#66BB6A]">Active</span>;
  }
  return <span className="text-xs text-muted-foreground">Inactive</span>;
}

function AllergiesTable() {
  const { sortKey, sortDir, toggle } = useSortState<AllergySortKey>();
  const sorted = sortRows(allergies, sortKey, sortDir, (row, key) => row[key as keyof AllergyRow]);

  const cols: { key: AllergySortKey; label: string }[] = [
    { key: "allergen", label: "Allergen" },
    { key: "category", label: "Category" },
    { key: "criticality", label: "Criticality" },
    { key: "clinicalStatus", label: "Status" },
    { key: "onsetDate", label: "Onset" },
  ];

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
          {sorted.map((row) => (
            <tr key={row.allergen}>
              <td className="px-4 py-2 text-sm font-medium">{row.allergen}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground capitalize">{row.category}</td>
              <td className="px-4 py-2"><CriticalityText criticality={row.criticality} /></td>
              <td className="px-4 py-2"><AllergyStatusText status={row.clinicalStatus} /></td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.onsetDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Procedures table with sort -----------------------------------------------

type ProcSortKey = "procedure" | "date" | "location" | "reason";

function ProceduresTable() {
  const { sortKey, sortDir, toggle } = useSortState<ProcSortKey>();
  const sorted = sortRows(procedures, sortKey, sortDir, (row, key) => row[key as keyof ProcedureRow] ?? "");

  const cols: { key: ProcSortKey; label: string }[] = [
    { key: "procedure", label: "Procedure" },
    { key: "date", label: "Date" },
    { key: "location", label: "Location" },
    { key: "reason", label: "Reason" },
  ];

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
          {sorted.map((row) => (
            <tr key={`${row.procedure}-${row.date}`}>
              <td className="px-4 py-2 text-sm font-medium">{row.procedure}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.date}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.location}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">
                {row.reason ?? <span className="italic">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Encounters table with sort -----------------------------------------------

type EncSortKey = "type" | "encounterClass" | "date" | "provider" | "location" | "reason";

function EncounterClassText({ encounterClass }: { encounterClass: EncounterRow["encounterClass"] }) {
  const styles: Record<string, string> = {
    AMB: "text-xs text-muted-foreground",
    EMER: "text-xs text-[#C24E42] dark:text-[#D46F65]",
    IMP: "text-xs text-[#D9A036] dark:text-[#EBC47C]",
  };
  const labels: Record<string, string> = { AMB: "Ambulatory", EMER: "Emergency", IMP: "Inpatient" };
  return <span className={styles[encounterClass]}>{labels[encounterClass]}</span>;
}

function EncountersTable() {
  const { sortKey, sortDir, toggle } = useSortState<EncSortKey>();
  const sorted = sortRows(encounters, sortKey, sortDir, (row, key) => row[key as keyof EncounterRow] ?? "");

  const cols: { key: EncSortKey; label: string }[] = [
    { key: "type", label: "Type" },
    { key: "encounterClass", label: "Class" },
    { key: "date", label: "Date" },
    { key: "provider", label: "Provider" },
    { key: "location", label: "Location" },
    { key: "reason", label: "Reason" },
  ];

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
            <tr key={`${row.type}-${row.date}-${i}`}>
              <td className="px-4 py-2 text-sm font-medium">{row.type}</td>
              <td className="px-4 py-2"><EncounterClassText encounterClass={row.encounterClass} /></td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.date}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.provider}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">{row.location}</td>
              <td className="px-4 py-2 text-sm text-muted-foreground">
                {row.reason ?? <span className="italic">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </CardContent>
  );
}

// -- Page ---------------------------------------------------------------------

export default function TablePage() {
  const [expandedPanels, setExpandedPanels] = useState<Record<string, boolean>>({
    "Complete Blood Count (CBC)": true,
  });

  const togglePanel = (name: string) => {
    setExpandedPanels((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  type LabSortKey = "test" | "value" | "date";
  const labSort = useSortState<LabSortKey>();

  // Flatten lab entries for sorting: extract all LabResults with their panel context
  const sortedLabEntries = React.useMemo(() => {
    if (!labSort.sortKey || !labSort.sortDir) return labEntries;

    return labEntries.map((entry) => {
      if (entry.type === "panel") {
        const sorted = sortRows(entry.results, labSort.sortKey, labSort.sortDir, (row, key) => {
          if (key === "test") return row.test;
          if (key === "value") return row.value;
          if (key === "date") return row.date;
          return "";
        });
        return { ...entry, results: sorted };
      }
      return entry;
    });
  }, [labSort.sortKey, labSort.sortDir]);

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
                  <SortHeader label="Test" active={labSort.sortKey === "test"} direction={labSort.sortKey === "test" ? labSort.sortDir : null} onClick={() => labSort.toggle("test")} />
                  <SortHeader label="Result" active={labSort.sortKey === "value"} direction={labSort.sortKey === "value" ? labSort.sortDir : null} onClick={() => labSort.toggle("value")} />
                  <th className={TH}>Reference Range</th>
                  <th className={TH}>Trend</th>
                  <SortHeader label="Date" active={labSort.sortKey === "date"} direction={labSort.sortKey === "date" ? labSort.sortDir : null} onClick={() => labSort.toggle("date")} />
                </tr>
              </thead>
              <tbody className="divide-y">
                {sortedLabEntries.map((entry) => {
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
          <MedicationsTable />
        </Card>

        {/* Medications design documentation */}
        <div className="space-y-4 text-sm text-muted-foreground">
          <h3 className="text-lg font-medium text-foreground">Design Notes</h3>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Column Order — Clinical Reading Flow</p>
            <p>
              Columns follow clinical scanning priority: <strong className="text-foreground">Medication → Frequency → Reason → Status → Prescribed → Requester</strong>.
              The clinician identifies the drug and dose, checks the schedule, understands why it was
              prescribed, confirms whether it&apos;s still active, then notes when it started and who
              ordered it. This mirrors the natural question flow when reviewing a medication list.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">FHIR Data Mapping</p>
            <p>
              All columns map directly to FHIR MedicationRequest fields. The medication name uses
              the full RxNorm display string from <code className="text-xs bg-muted px-1 py-0.5 rounded">medicationCodeableConcept.text</code> which
              includes drug name, dose, and form (e.g. &ldquo;Lisinopril 10 MG Oral Tablet&rdquo;). This
              eliminates the need for separate dosage and route columns — both are embedded in the
              medication name. Frequency is derived from <code className="text-xs bg-muted px-1 py-0.5 rounded">dosageInstruction[].timing.repeat</code> or
              falls back to <code className="text-xs bg-muted px-1 py-0.5 rounded">dosageInstruction[].text</code>. About 20% of
              MedicationRequests in Synthea fixtures lack dosageInstruction entirely.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Reason for Prescribing</p>
            <p>
              The reason column surfaces clinical intent from <code className="text-xs bg-muted px-1 py-0.5 rounded">reasonReference[].display</code> or <code className="text-xs bg-muted px-1 py-0.5 rounded">reasonCode[].text</code>.
              This connects the medication to the underlying condition (e.g. Lisinopril → Hypertension),
              giving context that a drug name alone cannot. In real workflows, this helps catch
              inappropriate prescriptions and supports medication reconciliation.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Status Values</p>
            <p>
              FHIR MedicationRequest uses <code className="text-xs bg-muted px-1 py-0.5 rounded">active</code> and <code className="text-xs bg-muted px-1 py-0.5 rounded">completed</code> —
              not &ldquo;discontinued&rdquo; as commonly seen in EHR interfaces. The <code className="text-xs bg-muted px-1 py-0.5 rounded">positive</code> badge
              variant (green) marks active medications, and <code className="text-xs bg-muted px-1 py-0.5 rounded">neutral</code> (gray)
              marks completed ones. Status is placed mid-table as a key scanning signal — the
              clinician needs to quickly distinguish current from historical medications.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Dropped Columns</p>
            <p>
              <strong className="text-foreground">Dosage</strong> and <strong className="text-foreground">Route</strong> are
              intentionally omitted. Synthea&apos;s RxNorm display strings embed both (e.g. &ldquo;500 MG Oral
              Tablet&rdquo;), making separate columns redundant. Route in particular has extremely low
              information density — nearly all outpatient medications are oral. Removing these
              columns reduces visual noise and lets the table focus on clinically actionable fields.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Requester vs Prescriber</p>
            <p>
              The column is labeled &ldquo;Requester&rdquo; to match the FHIR field name (<code className="text-xs bg-muted px-1 py-0.5 rounded">requester.display</code>).
              In FHIR, the requester is the practitioner who authored the medication order, sourced
              via NPI reference. This is placed last as the least-scanned column — clinicians
              prioritize what the drug is and whether it&apos;s active over who prescribed it.
            </p>
          </div>
        </div>
      </div>

      {/* Immunizations */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Immunizations</h2>
        <p className="text-muted-foreground max-w-2xl">
          Data mirrors FHIR Immunization resources. The vaccine column uses the CVX display
          string from <code className="text-xs bg-muted px-1 py-0.5 rounded">vaccineCode.text</code>.
          All Synthea immunizations have status &ldquo;completed&rdquo; — there are no pending or
          refused records in the fixtures.
        </p>
        <Card className="py-0 gap-0">
          <div className="flex items-center gap-2 px-4 py-2 border-b">
            <Syringe className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">Immunizations</span>
          </div>
          <ImmunizationsTable />
        </Card>

        {/* Immunizations design documentation */}
        <div className="space-y-4 text-sm text-muted-foreground">
          <h3 className="text-lg font-medium text-foreground">Design Notes</h3>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Column Order</p>
            <p>
              <strong className="text-foreground">Vaccine → Date → Location</strong>.
              The clinician identifies which vaccine was given, checks when it was administered,
              and notes where. Status is omitted as a column because all Synthea immunizations
              are &ldquo;completed&rdquo; — in a production system with pending/refused states,
              a status column would be added.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">FHIR Data Mapping</p>
            <p>
              The vaccine name comes from <code className="text-xs bg-muted px-1 py-0.5 rounded">vaccineCode.text</code>,
              which contains the CVX display string (e.g. &ldquo;Influenza, seasonal, injectable,
              preservative free&rdquo;). Date maps to <code className="text-xs bg-muted px-1 py-0.5 rounded">occurrenceDateTime</code> and
              location to <code className="text-xs bg-muted px-1 py-0.5 rounded">location.display</code>.
              The CVX code (<code className="text-xs bg-muted px-1 py-0.5 rounded">vaccineCode.coding[0].code</code>) is
              available in the FHIR data but omitted from display — the full vaccine name provides
              sufficient identification for clinical review.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Fixture Characteristics</p>
            <p>
              Synthea generates 73 immunization records across 5 patient bundles with 7 distinct
              vaccine types. Influenza dominates (50 of 73), followed by COVID-19 variants (10),
              tetanus (5), zoster (4), hepatitis B (3), and meningococcal (1). All records
              include <code className="text-xs bg-muted px-1 py-0.5 rounded">primarySource: true</code> and
              a location reference. No optional FHIR fields (site, route, doseQuantity, performer)
              are present in the Synthea data.
            </p>
          </div>

          <div className="space-y-3">
            <p className="font-medium text-foreground">Omitted Fields</p>
            <p>
              Several FHIR Immunization fields are absent from Synthea fixtures
              and therefore not displayed: <strong className="text-foreground">site</strong> (injection
              site), <strong className="text-foreground">route</strong> (administration
              route), <strong className="text-foreground">doseQuantity</strong>, <strong className="text-foreground">performer</strong> (administering
              practitioner), and <strong className="text-foreground">note</strong>. A production
              implementation would add columns for these if populated.
            </p>
          </div>
        </div>
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
          <BasicPropsTable />
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
