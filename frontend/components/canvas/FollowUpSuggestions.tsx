"use client";

import { ChevronRight } from "lucide-react";
import type { FollowUp } from "@/lib/types";

interface FollowUpSuggestionsProps {
  followUps: FollowUp[];
  onSelect: (question: string) => void;
}

export function FollowUpSuggestions({ followUps, onSelect }: FollowUpSuggestionsProps) {
  if (followUps.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 mt-3">
      {followUps.map((followUp, index) => (
        <button
          key={index}
          onClick={() => onSelect(followUp.question)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors text-left cursor-pointer"
        >
          <span className="flex-1">{followUp.question}</span>
          <ChevronRight className="h-4 w-4 shrink-0" />
        </button>
      ))}
    </div>
  );
}
