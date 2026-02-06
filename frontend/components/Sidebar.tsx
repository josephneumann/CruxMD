"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  PanelLeftClose,
  PanelLeft,
  Search,
  Users,
  Folders,
  ChevronUp,
  Sun,
  Moon,
  Monitor,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useSession, signOut } from "@/lib/auth-client";

interface SidebarProps {
  className?: string;
}

// Navigation items
const NAV_ITEMS = [
  { icon: Search, label: "Search", href: "#" },
  { icon: Users, label: "Patients", href: "/patients" },
  { icon: Folders, label: "Sessions", href: "/sessions" },
];

export function Sidebar({ className }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { data: session } = useSession();
  const pathname = usePathname();
  const isOnChat = pathname?.startsWith("/chat");

  const userName = session?.user?.name || "User";

  // Avoid hydration mismatch by only rendering theme-dependent content after mount
  // eslint-disable-next-line react-hooks/set-state-in-effect -- standard hydration pattern
  useEffect(() => { setMounted(true); }, []);

  // Close mobile sidebar on route change
  // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on navigation
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Close user menu on outside click
  useEffect(() => {
    if (!showUserMenu) return;
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showUserMenu]);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const wordmarkSrc = mounted && resolvedTheme === "dark"
    ? "/brand/logos/wordmark-reversed.png"
    : "/brand/logos/wordmark-primary.png";

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 h-14">
        {isExpanded || mobileOpen ? (
          <Link href="/" className="flex items-center" onClick={closeMobile}>
            <Image
              src={wordmarkSrc}
              alt="CruxMD"
              width={200}
              height={67}
              className="h-7 w-auto"
              unoptimized
              priority
            />
          </Link>
        ) : (
          <div className="w-8" />
        )}
        {/* Desktop toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-foreground hidden md:flex"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
        >
          {isExpanded ? (
            <PanelLeftClose className="h-5 w-5" />
          ) : (
            <PanelLeft className="h-5 w-5" />
          )}
        </Button>
        {/* Mobile close */}
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
      <nav className="flex flex-col gap-1 px-2 py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href !== "#" && pathname?.startsWith(item.href);
          const navLink = (
            <Link
              key={item.label}
              href={item.href}
              onClick={closeMobile}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                !isExpanded && !mobileOpen && "justify-center px-0"
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {(isExpanded || mobileOpen) && <span>{item.label}</span>}
            </Link>
          );
          return !isExpanded && !mobileOpen ? (
            <Tooltip key={item.label}>
              <TooltipTrigger asChild>{navLink}</TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          ) : (
            navLink
          );
        })}
        {/* CruxMD Mark */}
        {(() => {
          const chatLink = (
            <Link
              href="/chat"
              onClick={closeMobile}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isOnChat
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                !isExpanded && !mobileOpen && "justify-center px-0"
              )}
              aria-label="CruxMD Chat"
            >
              <span className="relative flex items-center justify-center h-5 w-5 shrink-0">
                {mounted && (
                  <Image
                    src={resolvedTheme === "dark" ? "/brand/logos/mark-reversed.svg" : "/brand/logos/mark-primary.svg"}
                    alt="CruxMD"
                    width={20}
                    height={20}
                    className="h-5 w-5"
                  />
                )}
              </span>
              {(isExpanded || mobileOpen) && <span>Chat</span>}
            </Link>
          );
          return !isExpanded && !mobileOpen ? (
            <Tooltip>
              <TooltipTrigger asChild>{chatLink}</TooltipTrigger>
              <TooltipContent side="right">Chat</TooltipContent>
            </Tooltip>
          ) : (
            chatLink
          );
        })()}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Theme Toggle */}
      <div className="px-2 py-2">
        <button
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors w-full",
            !isExpanded && !mobileOpen && "justify-center px-0"
          )}
          onClick={() => {
            if (theme === "light") setTheme("dark");
            else if (theme === "dark") setTheme("system");
            else setTheme("light");
          }}
          aria-label="Toggle theme"
        >
          {mounted && (
            <>
              {theme === "light" && <Sun className="h-5 w-5 shrink-0" />}
              {theme === "dark" && <Moon className="h-5 w-5 shrink-0" />}
              {theme === "system" && <Monitor className="h-5 w-5 shrink-0" />}
            </>
          )}
          {(isExpanded || mobileOpen) && mounted && (
            <span>
              {theme === "light" && "Light"}
              {theme === "dark" && "Dark"}
              {theme === "system" && "System"}
            </span>
          )}
        </button>
      </div>

      {/* Footer - User Profile */}
      <div ref={userMenuRef} className="relative border-t border-border">
        {showUserMenu && (
          <div className="fixed inset-0 z-60 flex items-end justify-start p-4">
            <div
              className="absolute inset-0 bg-black/20"
              onClick={() => setShowUserMenu(false)}
            />
            <div className="relative ml-1 mb-14 w-56 rounded-xl border border-border bg-popover p-1.5 shadow-xl animate-in fade-in slide-in-from-bottom-2 duration-150">
              <div className="px-3 py-2 border-b border-border mb-1">
                <p className="text-sm font-medium text-foreground truncate">{userName}</p>
                <p className="text-xs text-muted-foreground truncate">{session?.user?.email}</p>
              </div>
              <button
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                onClick={() => {
                  setShowUserMenu(false);
                  signOut({ fetchOptions: { onSuccess: () => { window.location.href = "/login"; } } });
                }}
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        )}
        <div
          className={cn(
            "flex items-center gap-3 w-full px-3 py-3",
            !isExpanded && !mobileOpen && "justify-center"
          )}
        >
          <button
            className="h-8 w-8 rounded-full overflow-hidden shrink-0 hover:opacity-80 transition-opacity"
            onClick={() => setShowUserMenu(!showUserMenu)}
            aria-label="User menu"
          >
            <Image
              src="/brand/avatars/admin-avatar-right-facing.png"
              alt={userName}
              width={32}
              height={32}
              className="h-full w-full object-cover"
            />
          </button>
          {(isExpanded || mobileOpen) && (
            <button
              className="flex-1 flex items-center justify-between min-w-0 hover:opacity-80 transition-opacity"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <span className="text-sm font-medium text-foreground truncate">
                {userName}
              </span>
              <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
            </button>
          )}
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile: floating toggle button (visible when sidebar is closed) */}
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
          className,
        )}
      >
        {sidebarContent}
      </aside>

      {/* Desktop sidebar: static, collapsible */}
      <aside
        className={cn(
          "hidden md:flex flex-col h-screen sticky top-0 z-50 border-r border-border bg-background transition-all duration-300 ease-in-out",
          isExpanded ? "w-64" : "w-14",
          className
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}

export default Sidebar;
