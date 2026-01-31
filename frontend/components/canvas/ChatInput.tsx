"use client";

import { ArrowUp, Plus, Clock, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function ChatInput({ value, onChange, onSubmit, disabled = false }: ChatInputProps) {
  return (
    <div className="border-t border-border bg-background p-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-card rounded-2xl border border-border shadow-sm">
          <div className="px-4 py-4">
            <AutoResizeTextarea
              value={value}
              onChange={onChange}
              onSubmit={onSubmit}
              placeholder="What can I help you with today?"
              disabled={disabled}
              autoFocus
            />
          </div>
          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                <Plus className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                <Clock className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                Opus 4.5
                <ChevronDown className="h-3 w-3" />
              </button>
              <Button
                size="icon"
                className="h-8 w-8 rounded-lg"
                disabled={!value.trim() || disabled}
                onClick={onSubmit}
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
