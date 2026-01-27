import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-full font-medium transition-colors",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground",
        secondary: "bg-secondary-foreground text-secondary",
        jade: "bg-[#388E3C] text-white",
        teal: "bg-[#5A7D7C] text-white",
        pine: "bg-[#1B3A34] text-white",
        outline: "border border-primary text-primary bg-transparent",
        neutral: "bg-muted text-muted-foreground",
        // Clinical insight-aligned variants
        info: "bg-[#4A7A8C] text-white",
        warning: "bg-[#D9A036] text-white",
        critical: "bg-[#C24E42] text-white",
        positive: "bg-insight-positive text-insight-positive-foreground",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2.5 py-0.5 text-sm",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
