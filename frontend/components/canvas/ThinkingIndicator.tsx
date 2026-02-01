"use client";

interface ThinkingIndicatorProps {
  reasoningText?: string;
}

export function ThinkingIndicator({ reasoningText }: ThinkingIndicatorProps) {
  const hasText = reasoningText && reasoningText.length > 0;

  return (
    <div className="mb-4">
      <div className="bg-muted/50 rounded-xl px-4 py-3 w-fit max-w-2xl">
        {hasText ? (
          <div className="max-h-32 overflow-y-auto text-sm text-muted-foreground whitespace-pre-wrap">
            {reasoningText}
            <span className="inline-block w-1.5 h-4 bg-muted-foreground/60 animate-pulse ml-0.5 align-text-bottom" />
          </div>
        ) : (
          <span className="text-sm text-muted-foreground animate-pulse">
            Thinking...
          </span>
        )}
      </div>
    </div>
  );
}
