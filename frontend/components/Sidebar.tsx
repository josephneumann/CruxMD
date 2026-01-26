"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  PanelLeftClose,
  PanelLeft,
  Plus,
  Search,
  Users,
  CheckSquare,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface SidebarProps {
  className?: string;
}

// Recent sessions with fixture patients (dummy time data)
const RECENT_SESSIONS = [
  { id: "session-1", patientId: "5c9f20d5-8361-b331-9267-5303ca5b136a", patientName: "Andrés Olivo", timeAgo: "10 minutes ago" },
  { id: "session-2", patientId: "d545798e-09a4-ef89-abc5-9f62dc5a5095", patientName: "Ash Brekke", timeAgo: "30 minutes ago" },
  { id: "session-3", patientId: "eed8a921-eac8-0778-4113-255f4e35506a", patientName: "Kimi Wyman", timeAgo: "2 hours ago" },
  { id: "session-4", patientId: "3c4b499b-090b-c6fa-28d7-b56c6056d0a2", patientName: "Lou Russel", timeAgo: "Yesterday" },
  { id: "session-5", patientId: "5393ea7f-1fea-4064-9df4-460a2f662d07", patientName: "Miguel Bashirian", timeAgo: "2 days ago" },
];

// Navigation items
const NAV_ITEMS = [
  { icon: Plus, label: "New chat", href: "/chat" },
  { icon: Search, label: "Search", href: "#" },
  { icon: Users, label: "Patients", href: "#" },
  { icon: CheckSquare, label: "Tasks", href: "/tasks" },
];

export function Sidebar({ className }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRecentsExpanded, setIsRecentsExpanded] = useState(true);

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r border-border bg-background transition-all duration-300 ease-in-out",
        isExpanded ? "w-64" : "w-14",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 h-14">
        {isExpanded ? (
          <Link href="/" className="flex items-center">
            <Image
              src="/brand/wordmark-primary.svg"
              alt="CruxMD"
              width={100}
              height={24}
              priority
            />
          </Link>
        ) : (
          <div className="w-8" /> // Spacer when collapsed
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
        >
          {isExpanded ? (
            <PanelLeftClose className="h-5 w-5" />
          ) : (
            <PanelLeft className="h-5 w-5" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 px-2 py-2">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors",
              !isExpanded && "justify-center px-0"
            )}
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {isExpanded && <span>{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Recent Sessions Section */}
      {isExpanded && (
        <div className="flex-1 flex flex-col min-h-0 px-2 py-2">
          {/* Section Header */}
          <button
            onClick={() => setIsRecentsExpanded(!isRecentsExpanded)}
            className="flex items-center justify-between px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            <span>Recent Sessions</span>
            {isRecentsExpanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>

          {/* Sessions List */}
          {isRecentsExpanded && (
            <div className="flex-1 overflow-y-auto">
              <div className="flex flex-col gap-1 py-1">
                {RECENT_SESSIONS.map((session) => (
                  <Link
                    key={session.id}
                    href={`/chat?patient=${session.patientId}&session=${session.id}`}
                    className="group flex flex-col rounded-lg px-3 py-2 transition-all hover:bg-card hover:shadow-md hover:border hover:border-border/50"
                  >
                    <span className="truncate text-sm text-foreground group-hover:text-foreground">
                      {session.patientName}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {session.timeAgo}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Collapsed state - show icons only for recents */}
      {!isExpanded && (
        <div className="flex-1 flex flex-col items-center gap-1 py-2">
          {/* Could show mini avatars or patient icons here */}
        </div>
      )}

      {/* Footer - User Profile */}
      <div className="mt-auto border-t border-border">
        <button
          className={cn(
            "flex items-center gap-3 w-full px-3 py-3 hover:bg-muted transition-colors",
            !isExpanded && "justify-center"
          )}
        >
          {/* Avatar */}
          <div className="h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center text-sm font-medium shrink-0">
            JN
          </div>
          {isExpanded && (
            <div className="flex-1 flex items-center justify-between min-w-0">
              <div className="flex flex-col items-start min-w-0">
                <span className="text-sm font-medium text-foreground truncate">
                  Dr. Neumann
                </span>
                <span className="text-xs text-muted-foreground">
                  Internal Medicine
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
            </div>
          )}
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
