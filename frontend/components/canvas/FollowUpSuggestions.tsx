"use client";

import type { FollowUp } from "@/lib/types";

interface FollowUpSuggestionsProps {
  followUps: FollowUp[];
  onSelect: (question: string) => void;
}

export function FollowUpSuggestions({ followUps, onSelect }: FollowUpSuggestionsProps) {
  if (followUps.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {followUps.map((followUp, index) => (
        <button
          key={index}
          onClick={() => onSelect(followUp.question)}
          className="px-3 py-1.5 rounded-full border border-border bg-card text-sm text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
        >
          {followUp.question}
        </button>
      ))}
    </div>
  );
}
