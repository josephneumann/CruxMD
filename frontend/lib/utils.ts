import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * FHIR HumanName type for patient display helpers.
 */
interface FhirHumanName {
  text?: string;
  given?: string[];
  family?: string;
}

/**
 * Minimal FHIR Patient type for display helpers.
 */
interface FhirPatientLike {
  name?: FhirHumanName[];
}

/**
 * Extract display name from a FHIR Patient resource.
 */
export function getPatientDisplayName(patient: FhirPatientLike): string {
  const name = patient.name?.[0];
  if (!name) return "Unknown";

  if (name.text) return name.text;

  const given = name.given?.join(" ") || "";
  const family = name.family || "";
  return `${given} ${family}`.trim() || "Unknown";
}
