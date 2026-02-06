"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { designSystemNav } from "@/lib/design-system-nav";
import { Button } from "@/components/ui/button";
import {
  Palette,
  Type,
  Component,
  Smile,
  Home,
  Image as ImageIcon,
  BookOpen,
  LayoutGrid,
  PanelLeft,
  PanelLeftClose,
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
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile sidebar on route change
  // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on navigation
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 h-14">
        <Link href="/" className="flex items-center" onClick={closeMobile}>
          <Image
            src="/brand/logos/wordmark-primary.svg"
            alt="CruxMD"
            width={120}
            height={28}
            className="dark:hidden"
            priority
          />
          <Image
            src="/brand/logos/wordmark-reversed.svg"
            alt="CruxMD"
            width={120}
            height={28}
            className="hidden dark:block"
            priority
          />
        </Link>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-foreground md:hidden"
          onClick={closeMobile}
          aria-label="Close sidebar"
        >
          <PanelLeftClose className="h-5 w-5" />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="space-y-1 px-3 py-2 overflow-y-auto flex-1">
        {designSystemNav.map((item) => {
          const isActive = pathname === item.href;
          const isParentActive = item.children?.some((child) => pathname === child.href);
          const Icon = iconMap[item.icon];

          return (
            <div key={item.href}>
              <Link
                href={item.href}
                title={item.title}
                onClick={closeMobile}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive || isParentActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                {Icon && <Icon className="size-4 flex-shrink-0" />}
                <span>{item.title}</span>
              </Link>
              {item.children && (
                <div className="ml-7 mt-1 space-y-1 border-l pl-3">
                  {item.children.map((child) => {
                    const isChildActive = pathname === child.href;
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        onClick={closeMobile}
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
    </>
  );

  return (
    <>
      {/* Mobile: floating toggle button */}
      {!mobileOpen && (
        <Button
          variant="ghost"
          size="icon"
          className="fixed top-3 left-3 z-40 h-8 w-8 text-muted-foreground hover:text-foreground md:hidden"
          onClick={() => setMobileOpen(true)}
          aria-label="Open sidebar"
        >
          <PanelLeft className="h-5 w-5" />
        </Button>
      )}

      {/* Mobile: backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={closeMobile}
        />
      )}

      {/* Mobile sidebar: overlay, slides in from left */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col w-64 border-r border-border bg-background transition-transform duration-300 ease-in-out md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar: static */}
      <aside className="hidden md:flex flex-col w-64 border-r bg-muted/30 flex-shrink-0">
        {sidebarContent}
      </aside>
    </>
  );
}
