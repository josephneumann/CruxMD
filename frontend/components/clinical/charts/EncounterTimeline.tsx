"use client";

import type { ClinicalVisualization, TimelineEvent } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CalendarDays, Calendar, AlertCircle, Bed } from "lucide-react";

function eventStyle(category?: string) {
  const cat = (category ?? "").toUpperCase();
  if (cat === "EMER") {
    return { Icon: AlertCircle, color: "text-destructive", bg: "bg-destructive/20", ring: "ring-destructive/30" };
  }
  if (cat === "IMP") {
    return { Icon: Bed, color: "text-amber-500", bg: "bg-amber-500/20", ring: "ring-amber-500/30" };
  }
  // AMB or default
  return { Icon: Calendar, color: "text-muted-foreground", bg: "bg-muted", ring: "ring-border" };
}

function TimelineItem({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const { Icon, color, bg, ring } = eventStyle(event.category);
  return (
    <div className="relative flex gap-4">
      {/* Vertical line + dot */}
      <div className="flex flex-col items-center">
        <div className={`flex size-8 shrink-0 items-center justify-center rounded-full ring-2 ${bg} ${ring}`}>
          <Icon className={`size-4 ${color}`} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-border" />}
      </div>
      {/* Content */}
      <div className="pb-6">
        <p className="text-xs text-muted-foreground">{event.date}</p>
        <p className="text-sm font-medium mt-0.5">{event.title}</p>
        {event.detail && (
          <p className="text-sm text-muted-foreground mt-0.5">{event.detail}</p>
        )}
      </div>
    </div>
  );
}

export function EncounterTimeline({ viz }: { viz: ClinicalVisualization }) {
  const events = viz.events ?? [];
  if (events.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarDays className="size-5 text-muted-foreground" />
          {viz.title}
        </CardTitle>
        {viz.subtitle && (
          <p className="text-sm text-muted-foreground">{viz.subtitle}</p>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {events.map((event, i) => (
            <TimelineItem key={i} event={event} isLast={i === events.length - 1} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
