"use client";

import { useState } from "react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import type { Insight, InsightType } from "@/lib/types";
import { INSIGHT_TYPES } from "@/lib/types";
import {
  Info,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  TestTube,
  Calendar,
  Pill,
  FileText,
  Stethoscope,
  ChevronDown,
} from "lucide-react";

/**
 * Maps insight types to their corresponding icons.
 */
const INSIGHT_ICONS: Record<InsightType, React.ComponentType<{ className?: string }>> = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
  positive: CheckCircle,
};

/**
 * Maps insight types to their Tailwind color classes.
 * Uses left accent bar pattern for clean, modern aesthetic.
 * No top/right/bottom borders - only a bold left edge for severity indication.
 */
const INSIGHT_STYLES: Record<InsightType, string> = {
  info: "border-0 border-l-4 border-l-insight-info bg-insight-info/15 dark:bg-insight-info/20 text-foreground [&>svg]:text-insight-info",
  warning: "border-0 border-l-4 border-l-insight-warning bg-insight-warning/15 dark:bg-insight-warning/20 text-foreground [&>svg]:text-insight-warning",
  critical: "border-0 border-l-4 border-l-insight-critical bg-insight-critical/15 dark:bg-insight-critical/20 text-foreground [&>svg]:text-insight-critical",
  positive: "border-0 border-l-4 border-l-insight-positive bg-insight-positive/15 dark:bg-insight-positive/20 text-foreground [&>svg]:text-insight-positive",
};

/**
 * Citation type detection and icon mapping.
 */
type CitationType = "labs" | "encounter" | "medications" | "notes" | "vitals" | "other";

const CITATION_ICONS: Record<CitationType, React.ComponentType<{ className?: string }>> = {
  labs: TestTube,
  encounter: Calendar,
  medications: Pill,
  notes: FileText,
  vitals: Stethoscope,
  other: FileText,
};

/**
 * Detect citation type from citation text.
 */
function detectCitationType(citation: string): CitationType {
  const lower = citation.toLowerCase();
  if (lower.includes("lab") || lower.includes("metabolic") || lower.includes("cbc") || lower.includes("panel")) {
    return "labs";
  }
  if (lower.includes("encounter") || lower.includes("visit") || lower.includes("appointment")) {
    return "encounter";
  }
  if (lower.includes("medication") || lower.includes("drug") || lower.includes("prescription")) {
    return "medications";
  }
  if (lower.includes("note") || lower.includes("documentation")) {
    return "notes";
  }
  if (lower.includes("vital") || lower.includes("bp") || lower.includes("heart rate")) {
    return "vitals";
  }
  return "other";
}

export interface InsightCardProps {
  /** The insight data to render */
  insight: Insight;
  /** Additional CSS classes */
  className?: string;
  /** Start expanded (default: false) */
  defaultExpanded?: boolean;
}

/**
 * InsightCard renders a clinical insight with color-coded severity.
 *
 * Uses shadcn/ui Alert as base, with custom styling for each insight type:
 * - info (blue): General information
 * - warning (yellow/amber): Caution indicators
 * - critical (red): Urgent clinical alerts
 * - positive (green): Favorable findings
 */
export function InsightCard({ insight, className, defaultExpanded = false }: InsightCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { type, title, content, citations } = insight;

  // Validate type at runtime (in case of malformed data from API)
  const validType = INSIGHT_TYPES.includes(type) ? type : "info";
  const Icon = INSIGHT_ICONS[validType];
  const styles = INSIGHT_STYLES[validType];

  return (
    <Alert className={cn(styles, "relative", className)}>
      <Icon className="h-4 w-4" />
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <AlertTitle className="cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
            {title}
          </AlertTitle>
          {expanded && (
            <AlertDescription>
              <p>{content}</p>
              {citations && citations.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {citations.map((citation, index) => {
                    const citationType = detectCitationType(citation);
                    const CitationIcon = CITATION_ICONS[citationType];
                    return (
                      <span
                        key={index}
                        className="inline-flex items-center gap-1.5 rounded-md bg-background/50 dark:bg-background/30 px-2 py-1 text-xs text-muted-foreground"
                      >
                        <CitationIcon className="size-3" />
                        {citation}
                      </span>
                    );
                  })}
                </div>
              )}
            </AlertDescription>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 p-0.5 rounded text-muted-foreground hover:text-foreground transition-transform cursor-pointer"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", expanded && "rotate-180")} />
        </button>
      </div>
    </Alert>
  );
}

export default InsightCard;
