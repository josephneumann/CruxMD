"use client";

/**
 * Patient header component displaying selected patient information.
 *
 * Shows patient name, demographics, and key identifiers in a compact
 * header format suitable for the chat interface.
 */

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import {
  getPatientDisplayName,
  getPatientInitials,
  formatFhirDate,
  calculateAge,
  getPatientMRN,
} from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface PatientHeaderProps {
  patient: PatientListItem;
}

export function PatientHeader({ patient }: PatientHeaderProps) {
  const { data } = patient;
  const name = getPatientDisplayName(data);
  const initials = getPatientInitials(data);
  const age = calculateAge(data.birthDate);
  const mrn = getPatientMRN(data);

  return (
    <Card className="border-0 shadow-none bg-muted/50">
      <CardContent className="flex items-center gap-4 p-4">
        <Avatar className="h-12 w-12 border">
          <AvatarFallback className="bg-primary/10 text-primary font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-semibold truncate">{name}</h2>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            {age !== null && (
              <span>
                {age} y/o {data.gender && `(${data.gender})`}
              </span>
            )}
            {data.birthDate && <span>DOB: {formatFhirDate(data.birthDate)}</span>}
            {mrn && <span>MRN: {mrn}</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
