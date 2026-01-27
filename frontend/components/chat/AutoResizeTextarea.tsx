"use client";

import { useRef, useCallback } from "react";
import { cn } from "@/lib/utils";

interface AutoResizeTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Textarea that auto-resizes based on content and submits on Enter
 */
export function AutoResizeTextarea({
  value,
  onChange,
  onSubmit,
  placeholder = "Type a message...",
  disabled = false,
  className,
}: AutoResizeTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSubmit();
      }
    },
    [onSubmit]
  );

  return (
    <textarea
      ref={textareaRef}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onInput={handleInput}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      rows={1}
      className={cn(
        "w-full bg-transparent text-foreground placeholder:text-muted-foreground",
        "resize-none outline-none text-base min-h-[24px] max-h-[200px]",
        className
      )}
    />
  );
}
