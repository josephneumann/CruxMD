"use client";

import { useState } from "react";
import { Check, Copy, ChevronDown, ChevronRight, Code } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CodeBlockProps {
  code: string;
  language?: string;
  className?: string;
  /** If true, code is hidden behind a "View Code" toggle */
  collapsible?: boolean;
  /** Custom label for the toggle button (default: "View Code") */
  label?: string;
  /** If collapsible, whether to start expanded */
  defaultExpanded?: boolean;
}

export function CodeBlock({
  code,
  language = "tsx",
  className,
  collapsible = false,
  label = "View Code",
  defaultExpanded = false,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (collapsible) {
    return (
      <div className={cn("rounded-lg border", className)}>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Code className="size-4 text-muted-foreground" />
            {label}
          </span>
          {expanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </button>
        {expanded && (
          <div className="border-t bg-muted">
            <div className="flex items-center justify-between border-b px-4 py-2">
              <span className="text-xs font-mono text-muted-foreground">{language}</span>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={handleCopy}
                className="text-muted-foreground hover:text-foreground"
              >
                {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
              </Button>
            </div>
            <pre className="overflow-x-auto p-4">
              <code className="text-sm font-mono">{code}</code>
            </pre>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={cn("relative rounded-lg border bg-muted", className)}>
      <div className="flex items-center justify-between border-b px-4 py-2">
        <span className="text-xs font-mono text-muted-foreground">{language}</span>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={handleCopy}
          className="text-muted-foreground hover:text-foreground"
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
        </Button>
      </div>
      <pre className="overflow-x-auto p-4">
        <code className="text-sm font-mono">{code}</code>
      </pre>
    </div>
  );
}
