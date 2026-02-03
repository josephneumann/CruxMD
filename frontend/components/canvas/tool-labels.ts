import type { LucideIcon } from "lucide-react";
import { FlaskConical, Search, CalendarClock, Network, Stethoscope } from "lucide-react";

interface ToolConfig {
  icon: LucideIcon;
  /** Present-tense label for in-flight display */
  activeLabel: string;
  /** Past-tense label for completed log */
  doneLabel: string;
}

const TOOL_CONFIG: Record<string, ToolConfig> = {
  search_patient_data: { icon: Search, activeLabel: "Searching", doneLabel: "Searched patient data" },
  get_encounter_details: { icon: Stethoscope, activeLabel: "Retrieving encounter", doneLabel: "Retrieved encounter details" },
  get_lab_history: { icon: FlaskConical, activeLabel: "Looking up labs", doneLabel: "Looked up lab history" },
  find_related_resources: { icon: Network, activeLabel: "Finding related resources", doneLabel: "Found related resources" },
  get_patient_timeline: { icon: CalendarClock, activeLabel: "Getting timeline", doneLabel: "Retrieved patient timeline" },
};

const DEFAULT_CONFIG: ToolConfig = { icon: Search, activeLabel: "Running tool", doneLabel: "Ran tool" };

/**
 * Extract the human-readable search term from a tool call's arguments JSON.
 * Returns null if no meaningful term can be extracted.
 */
function extractSearchTerm(name: string, argumentsJson: string): string | null {
  try {
    const args = JSON.parse(argumentsJson);

    switch (name) {
      case "search_patient_data":
        return args.query ?? null;
      case "get_lab_history":
        return args.lab_name ?? null;
      case "get_encounter_details":
        return args.encounter_fhir_id ?? null;
      case "find_related_resources":
        return args.resource_type ?? null;
      case "get_patient_timeline": {
        const parts: string[] = [];
        if (args.start_date) parts.push(args.start_date);
        if (args.end_date) parts.push(args.end_date);
        return parts.length > 0 ? parts.join(" to ") : null;
      }
      default:
        return null;
    }
  } catch {
    return null;
  }
}

/** Format a tool call for the in-flight spinner status line. */
export function formatToolActive(name: string, argumentsJson: string): string {
  const config = TOOL_CONFIG[name] ?? DEFAULT_CONFIG;
  const term = extractSearchTerm(name, argumentsJson);
  return term ? `${config.activeLabel} — ${term}` : config.activeLabel;
}

/** Format a tool call for the completed log (past tense). */
export function formatToolDone(name: string, argumentsJson: string): string {
  const config = TOOL_CONFIG[name] ?? DEFAULT_CONFIG;
  const term = extractSearchTerm(name, argumentsJson);
  return term ? `${config.doneLabel} — ${term}` : config.doneLabel;
}

/** Get the icon for a tool name. */
export function getToolIcon(name: string): LucideIcon {
  return (TOOL_CONFIG[name] ?? DEFAULT_CONFIG).icon;
}
