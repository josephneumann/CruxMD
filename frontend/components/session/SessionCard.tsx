"use client";

import { useCallback, useState } from "react";
import { Trash2, User, Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { SessionResponse, PatientListItem } from "@/lib/types";

interface SessionCardProps {
  session: SessionResponse;
  patient?: PatientListItem;
  onOpen: (sessionId: string) => void;
  onDelete: (sessionId: string) => Promise<void>;
}

/**
 * Format a relative time string (e.g., "5 minutes ago", "2 hours ago")
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
}

/**
 * Get the last message excerpt from session messages
 */
function getLastMessageExcerpt(session: SessionResponse, maxLength = 100): string {
  if (!session.messages || session.messages.length === 0) {
    return session.summary || "No messages yet";
  }

  const lastMessage = session.messages[session.messages.length - 1];
  const content = lastMessage.content;

  if (content.length <= maxLength) return content;
  return content.substring(0, maxLength).trim() + "...";
}

/**
 * Get patient display name from FHIR data
 */
function getPatientName(patient?: PatientListItem): string {
  if (!patient?.data?.name?.[0]) return "Unknown Patient";

  const name = patient.data.name[0];
  const given = name.given?.join(" ") || "";
  const family = name.family || "";

  return `${given} ${family}`.trim() || "Unknown Patient";
}

/**
 * SessionCard - Display a single session with open and delete capability
 */
export function SessionCard({ session, patient, onOpen, onDelete }: SessionCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleCardClick = useCallback(() => {
    onOpen(session.id);
  }, [session.id, onOpen]);

  const handleDelete = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    setIsDeleting(true);
    try {
      await onDelete(session.id);
    } finally {
      setIsDeleting(false);
    }
  }, [session.id, onDelete]);

  const patientName = getPatientName(patient);
  const excerpt = getLastMessageExcerpt(session);
  const timeAgo = formatRelativeTime(session.last_active_at);

  return (
    <Card
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={handleCardClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">{patientName}</CardTitle>
          </div>
        </div>
      </CardHeader>

      <CardContent className="py-2">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {excerpt}
        </p>
      </CardContent>

      <CardFooter className="pt-2 flex items-center justify-between">
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{timeAgo}</span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleDelete}
          disabled={isDeleting}
          className="gap-1 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-3 w-3" />
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </CardFooter>
    </Card>
  );
}

export default SessionCard;
