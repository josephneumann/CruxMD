"use client";

import { useState, useRef, useEffect } from "react";
import { ArrowUp, Plus, Clock, ChevronDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";
import { MODEL_OPTIONS } from "@/lib/types";
import type { ModelId, ReasoningEffort } from "@/lib/types";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  model: ModelId;
  onModelChange: (model: ModelId) => void;
  reasoningEffort: ReasoningEffort;
  onReasoningEffortChange: (effort: ReasoningEffort) => void;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading = false,
  disabled = false,
  model,
  onModelChange,
  reasoningEffort,
  onReasoningEffortChange,
}: ChatInputProps) {
  const [showModelMenu, setShowModelMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!showModelMenu) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowModelMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showModelMenu]);

  const selectedModel = MODEL_OPTIONS.find((m) => m.id === model) ?? MODEL_OPTIONS[0];

  const handleSubmit = () => {
    onSubmit();
    // Re-focus textarea after submit
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
    });
  };

  return (
    <div className="sticky bottom-0 border-t border-border bg-background p-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-card rounded-2xl border border-border shadow-sm overflow-visible">
          <div className="px-4 py-4">
            <AutoResizeTextarea
              ref={textareaRef}
              value={value}
              onChange={onChange}
              onSubmit={handleSubmit}
              placeholder="What can I help you with today?"
              disabled={disabled}
              autoFocus
            />
          </div>
          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer">
                    <Plus className="h-5 w-5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">Add files, connectors and more</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                    onClick={() => onReasoningEffortChange(reasoningEffort === "high" ? "medium" : "high")}
                  >
                    <Clock className={`h-5 w-5 ${reasoningEffort === "high" ? "text-primary" : ""}`} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">Extended thinking</TooltipContent>
              </Tooltip>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setShowModelMenu((v) => !v)}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg px-2 py-1 transition-colors cursor-pointer"
                >
                  {selectedModel.label}
                  <ChevronDown className="h-3 w-3" />
                </button>
                {showModelMenu && (
                  <div className="absolute bottom-full right-0 mb-2 w-56 rounded-lg border border-border bg-popover shadow-lg py-1 z-50">
                    {MODEL_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        onClick={() => {
                          onModelChange(option.id as ModelId);
                          setShowModelMenu(false);
                        }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left cursor-pointer rounded-md hover:bg-muted transition-colors"
                      >
                        <div className="w-4 flex-shrink-0">
                          {option.id === model && (
                            <Check className="h-4 w-4 text-primary" />
                          )}
                        </div>
                        <div>
                          <div className="text-sm font-medium">{option.label}</div>
                          <div className="text-xs text-muted-foreground">
                            {option.description}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Button
                size="icon"
                className="h-8 w-8 rounded-lg"
                disabled={!value.trim() || isLoading || disabled}
                onClick={handleSubmit}
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
