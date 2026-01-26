"use client";

import { useState } from "react";
import { Code, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "./CodeBlock";
import { cn } from "@/lib/utils";

interface ComponentPreviewProps {
  children: React.ReactNode;
  code: string;
  title?: string;
  description?: string;
  className?: string;
}

export function ComponentPreview({
  children,
  code,
  title,
  description,
  className,
}: ComponentPreviewProps) {
  const [showCode, setShowCode] = useState(false);

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      {(title || description) && (
        <div className="border-b px-4 py-3">
          {title && <h3 className="font-semibold">{title}</h3>}
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
        </div>
      )}
      <div className="p-6 bg-background/50 flex items-center justify-center min-h-[120px]">
        {children}
      </div>
      <div className="border-t">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowCode(!showCode)}
          className="w-full rounded-none justify-center gap-2 text-muted-foreground hover:text-foreground"
        >
          {showCode ? (
            <>
              <Eye className="size-4" />
              Hide Code
            </>
          ) : (
            <>
              <Code className="size-4" />
              View Code
            </>
          )}
        </Button>
        {showCode && <CodeBlock code={code} className="border-t rounded-none border-x-0 border-b-0" />}
      </div>
    </div>
  );
}

interface PreviewGridProps {
  children: React.ReactNode;
  cols?: 1 | 2 | 3 | 4;
}

export function PreviewGrid({ children, cols = 2 }: PreviewGridProps) {
  return (
    <div
      className={cn(
        "grid gap-6",
        cols === 1 && "grid-cols-1",
        cols === 2 && "grid-cols-1 md:grid-cols-2",
        cols === 3 && "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
        cols === 4 && "grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
      )}
    >
      {children}
    </div>
  );
}
