"use client";

import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { getContrastTextClass } from "@/lib/color-utils";
import { useCopyToClipboard } from "@/lib/hooks/use-copy-to-clipboard";

interface ColorSwatchProps {
  name: string;
  value: string;
  description?: string;
  className?: string;
  large?: boolean;
}

export function ColorSwatch({
  name,
  value,
  description,
  className,
  large = false,
}: ColorSwatchProps) {
  const { copied, copy } = useCopyToClipboard();
  const textColor = getContrastTextClass(value);

  return (
    <button
      onClick={() => copy(value)}
      className={cn(
        "group relative flex flex-col rounded-lg border overflow-hidden transition-all hover:shadow-md hover:scale-[1.02] active:scale-100",
        large ? "h-32" : "h-24",
        className
      )}
    >
      <div
        className={cn("flex-1 flex items-center justify-center", textColor)}
        style={{ backgroundColor: value }}
      >
        <span
          className={cn(
            "text-xs font-mono opacity-0 group-hover:opacity-100 transition-opacity",
            copied && "opacity-100"
          )}
        >
          {copied ? (
            <span className="flex items-center gap-1">
              <Check className="size-3" /> Copied
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Copy className="size-3" /> {value}
            </span>
          )}
        </span>
      </div>
      <div className="bg-card px-3 py-2">
        <p className="text-sm font-medium text-left">{name}</p>
        {description && (
          <p className="text-xs text-muted-foreground text-left">{description}</p>
        )}
      </div>
    </button>
  );
}

interface ColorGroupProps {
  title: string;
  colors: Array<{ name: string; value: string; description?: string }>;
}

export function ColorGroup({ title, colors }: ColorGroupProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-medium">{title}</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {colors.map((color) => (
          <ColorSwatch
            key={color.name}
            name={color.name}
            value={color.value}
            description={color.description}
          />
        ))}
      </div>
    </div>
  );
}
