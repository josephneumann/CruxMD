"use client";

import {
  Pill,
  FlaskConical,
  HeartPulse,
  ClipboardList,
  ShieldAlert,
  Syringe,
  Stethoscope,
  CalendarDays,
} from "lucide-react";
import type { ClinicalTable as ClinicalTableData } from "@/lib/types";
import {
  CollapsibleTableCard,
  MedicationsTable,
  LabResultsTable,
  VitalsTable,
  ConditionsTable,
  AllergiesTable,
  ImmunizationsTable,
  ProceduresTable,
  EncountersTable,
} from "./tables";

const tableConfig: Record<
  ClinicalTableData["type"],
  {
    icon: React.ComponentType<{ className?: string }>;
    countLabel: string;
  }
> = {
  medications: { icon: Pill, countLabel: "medications" },
  lab_results: { icon: FlaskConical, countLabel: "results" },
  vitals: { icon: HeartPulse, countLabel: "vitals" },
  conditions: { icon: ClipboardList, countLabel: "conditions" },
  allergies: { icon: ShieldAlert, countLabel: "allergies" },
  immunizations: { icon: Syringe, countLabel: "immunizations" },
  procedures: { icon: Stethoscope, countLabel: "procedures" },
  encounters: { icon: CalendarDays, countLabel: "encounters" },
};

const tableRenderers: Record<
  ClinicalTableData["type"],
  React.ComponentType<{ rows: Record<string, unknown>[] }>
> = {
  medications: MedicationsTable,
  lab_results: LabResultsTable,
  vitals: VitalsTable,
  conditions: ConditionsTable,
  allergies: AllergiesTable,
  immunizations: ImmunizationsTable,
  procedures: ProceduresTable,
  encounters: EncountersTable,
};

function parseRows(rows: string | Record<string, unknown>[]): Record<string, unknown>[] {
  if (Array.isArray(rows)) return rows;
  try {
    const parsed = JSON.parse(rows);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function ClinicalTable({ table }: { table: ClinicalTableData }) {
  const config = tableConfig[table.type];
  const TableRenderer = tableRenderers[table.type];

  if (!config || !TableRenderer) return null;

  const rows = parseRows(table.rows);
  if (rows.length === 0) return null;

  return (
    <CollapsibleTableCard
      icon={config.icon}
      title={table.title}
      count={rows.length}
      countLabel={config.countLabel}
    >
      <TableRenderer rows={rows} />
    </CollapsibleTableCard>
  );
}
