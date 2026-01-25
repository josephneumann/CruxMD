"use client";

import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import type { Insight, InsightType } from "@/lib/types";
import { INSIGHT_TYPES } from "@/lib/types";
import { Info, AlertTriangle, AlertCircle, CheckCircle } from "lucide-react";

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
 * Uses the semantic insight color tokens from globals.css.
 */
const INSIGHT_STYLES: Record<InsightType, string> = {
  info: "border-insight-info bg-insight-info/10 text-insight-info [&>svg]:text-insight-info",
  warning: "border-insight-warning bg-insight-warning/10 text-insight-warning-foreground [&>svg]:text-insight-warning",
  critical: "border-insight-critical bg-insight-critical/10 text-insight-critical [&>svg]:text-insight-critical",
  positive: "border-insight-positive bg-insight-positive/10 text-insight-positive [&>svg]:text-insight-positive",
};

export interface InsightCardProps {
  /** The insight data to render */
  insight: Insight;
  /** Additional CSS classes */
  className?: string;
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
export function InsightCard({ insight, className }: InsightCardProps) {
  const { type, title, content, citations } = insight;

  // Validate type at runtime (in case of malformed data from API)
  const validType = INSIGHT_TYPES.includes(type) ? type : "info";
  const Icon = INSIGHT_ICONS[validType];
  const styles = INSIGHT_STYLES[validType];

  return (
    <Alert className={cn(styles, className)}>
      <Icon className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{content}</p>
        {citations && citations.length > 0 && (
          <div className="mt-2 text-xs opacity-75">
            {citations.map((citation, index) => (
              <span key={index} className="mr-2">
                [{citation}]
              </span>
            ))}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}

export default InsightCard;
