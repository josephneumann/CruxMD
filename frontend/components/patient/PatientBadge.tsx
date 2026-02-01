"use client";

/**
 * Patient selector — read-only display of the currently selected patient.
 */

import { getPatientDisplayName, formatFhirDate } from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface PatientBadgeProps {
  patient: PatientListItem | null;
}

export function PatientBadge({ patient }: PatientBadgeProps) {
  if (!patient) {
    return (
      <div className="text-sm text-muted-foreground">No patient selected</div>
    );
  }

  const name = getPatientDisplayName(patient.data);
  const dob = patient.data.birthDate ? formatFhirDate(patient.data.birthDate) : null;

  return (
    <div className="text-sm text-muted-foreground">
      <span className="font-medium text-foreground">{name}</span>
      {dob && <span> · DOB: {dob}</span>}
    </div>
  );
}
