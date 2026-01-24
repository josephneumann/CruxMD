"use client";

/**
 * Patient selector dropdown component.
 *
 * Allows users to select a patient from a list. Uses shadcn/ui Select
 * for a consistent, accessible dropdown experience.
 */

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getPatientDisplayName, formatFhirDate } from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface PatientSelectorProps {
  patients: PatientListItem[];
  selectedPatientId: string | null;
  onPatientChange: (patientId: string) => void;
  disabled?: boolean;
}

export function PatientSelector({
  patients,
  selectedPatientId,
  onPatientChange,
  disabled = false,
}: PatientSelectorProps) {
  return (
    <Select
      value={selectedPatientId || undefined}
      onValueChange={onPatientChange}
      disabled={disabled || patients.length === 0}
    >
      <SelectTrigger className="w-[300px]">
        <SelectValue placeholder="Select a patient..." />
      </SelectTrigger>
      <SelectContent>
        {patients.map((patient) => (
          <SelectItem key={patient.id} value={patient.id}>
            <span className="font-medium">
              {getPatientDisplayName(patient.data)}
            </span>
            {patient.data.birthDate && (
              <span className="ml-2 text-muted-foreground">
                ({formatFhirDate(patient.data.birthDate)})
              </span>
            )}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
