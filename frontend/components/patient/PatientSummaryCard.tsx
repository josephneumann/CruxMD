"use client";

/**
 * Patient Summary Card — reusable card for displaying patient info at a glance.
 *
 * Used on the Patients list page and referenced in the design system.
 */

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import {
  getPatientDisplayName,
  getPatientInitials,
  getPatientAvatarUrl,
  formatFhirDate,
  calculateAge,
  cn,
} from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface PatientSummaryCardProps {
  patient: PatientListItem;
  onClick?: () => void;
  className?: string;
}

export function PatientSummaryCard({ patient, onClick, className }: PatientSummaryCardProps) {
  const { data } = patient;
  const name = getPatientDisplayName(data);
  const initials = getPatientInitials(data);
  const avatarSrc = getPatientAvatarUrl(data);
  const age = calculateAge(data.birthDate);
  const dob = data.birthDate ? formatFhirDate(data.birthDate) : null;
  const card = (
    <Card
      className={cn(
        "p-5 transition-all duration-150",
        onClick && "cursor-pointer hover:bg-muted/50 hover:border-transparent dark:hover:bg-white/[0.04] dark:hover:border-transparent hover:-translate-y-0.5",
        className,
      )}
    >
      <div className="flex items-start gap-4">
        <Avatar className="size-12 bg-primary/20">
          <AvatarImage src={avatarSrc} alt={name} className="object-cover" />
          <AvatarFallback className="bg-primary/20 text-primary font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0 text-left">
          <h3 className="font-semibold truncate">{name}</h3>
          <div className="mt-1 text-sm text-muted-foreground space-y-0.5">
            {(age !== null || data.gender) && (
              <p>
                {age !== null && `${age}y`}
                {age !== null && data.gender && ", "}
                {data.gender && <span className="capitalize">{data.gender}</span>}
                {dob && ` • DOB: ${dob}`}
              </p>
            )}
          </div>
        </div>
      </div>
    </Card>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="text-left w-full">
        {card}
      </button>
    );
  }

  return card;
}
