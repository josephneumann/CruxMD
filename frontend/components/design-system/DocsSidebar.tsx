"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { designSystemNav } from "@/lib/design-system-nav";
import {
  Palette,
  Type,
  Component,
  Smile,
  Home,
  Image as ImageIcon,
  BookOpen,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  home: Home,
  book: BookOpen,
  image: ImageIcon,
  palette: Palette,
  type: Type,
  layout: LayoutGrid,
  component: Component,
  smile: Smile,
};

export function DocsSidebar() {
  const pathname = usePathname();
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const wordmarkSrc = mounted && resolvedTheme === "dark"
    ? "/brand/wordmark-reversed.svg"
    : "/brand/wordmark-primary.svg";

  return (
    <aside className="w-64 border-r bg-muted/30 p-6 overflow-y-auto">
      <div className="mb-8 px-3">
        <Link href="/design" className="flex items-center">
          <Image
            src={wordmarkSrc}
            alt="CruxMD"
            width={100}
            height={24}
            priority
          />
        </Link>
        <p className="text-sm text-muted-foreground mt-1">Design System</p>
      </div>
      <nav className="space-y-1">
        {designSystemNav.map((item) => {
          const isActive = pathname === item.href;
          const isParentActive = item.children?.some((child) => pathname === child.href);
          const Icon = iconMap[item.icon];

          return (
            <div key={item.href}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive || isParentActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                {Icon && <Icon className="size-4" />}
                {item.title}
              </Link>
              {item.children && (
                <div className="ml-7 mt-1 space-y-1 border-l pl-3">
                  {item.children.map((child) => {
                    const isChildActive = pathname === child.href;
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={cn(
                          "block rounded-md px-3 py-1.5 text-sm transition-colors",
                          isChildActive
                            ? "text-primary font-medium"
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {child.title}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
