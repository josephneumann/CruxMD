"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  Search,
  Trash2,
  MoreHorizontal,
  FolderOpen,
  CheckSquare,
  X,
  Minus,
  Pencil,
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useSessions } from "@/hooks";
import type { PatientListItem, SessionResponse } from "@/lib/types";
import { parsePatientList } from "@/lib/types";
import {
  getPatientDisplayName,
  getPatientInitials,
  getPatientAvatarUrl,
} from "@/lib/utils";

/**
 * Generate default session name from patient name and timestamp.
 * Format: PatientName-YYMMDD:HHMMSS
 */
function generateDefaultSessionName(patientName: string, startedAt: string): string {
  const date = new Date(startedAt);
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");

  // Clean patient name (replace spaces with hyphens, keep Unicode letters)
  const cleanName = patientName.trim().replace(/\s+/g, "-");

  return `${cleanName}-${yy}${mm}${dd}:${hh}${min}${ss}`;
}

export default function SessionsPage() {
  const router = useRouter();
  const { sessions, isLoading, error, deleteSession, updateSession } = useSessions();
  const [patients, setPatients] = useState<Map<string, PatientListItem>>(new Map());
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renamingSession, setRenamingSession] = useState<SessionResponse | null>(null);
  const [newName, setNewName] = useState("");

  // Fetch all patients to resolve names
  useEffect(() => {
    fetch("/api/patients?limit=1000")
      .then((res) => res.json())
      .then((data) => {
        const patientList = parsePatientList(data);
        const patientMap = new Map<string, PatientListItem>();
        for (const p of patientList) {
          patientMap.set(p.id, p);
        }
        setPatients(patientMap);
      })
      .catch((err) => {
        console.error("Failed to fetch patients:", err);
      })
      .finally(() => setPatientsLoading(false));
  }, []);

  // Filter sessions by patient name search, sort by timestamp desc
  const filteredSessions = sessions
    .filter((session) => {
      if (!search) return true;
      const patient = patients.get(session.patient_id);
      if (!patient) return false;
      const name = getPatientDisplayName(patient.data).toLowerCase();
      return name.includes(search.toLowerCase());
    })
    .sort((a, b) => {
      return new Date(b.last_active_at).getTime() - new Date(a.last_active_at).getTime();
    });

  const handleOpenSession = useCallback(
    (session: SessionResponse) => {
      router.push(`/chat/${session.id}?patient=${session.patient_id}`);
    },
    [router]
  );

  const handleDelete = useCallback(
    async (e: React.MouseEvent | null, sessionId: string) => {
      e?.stopPropagation();
      setDeletingIds((prev) => new Set(prev).add(sessionId));
      try {
        await deleteSession(sessionId);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(sessionId);
          return next;
        });
      } finally {
        setDeletingIds((prev) => {
          const next = new Set(prev);
          next.delete(sessionId);
          return next;
        });
      }
    },
    [deleteSession]
  );

  const handleDeleteSelected = useCallback(async () => {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      await handleDelete(null, id);
    }
  }, [selectedIds, handleDelete]);

  const toggleSelect = useCallback((e: React.MouseEvent | null, sessionId: string) => {
    e?.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedIds.size === filteredSessions.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredSessions.map((s) => s.id)));
    }
  }, [selectedIds.size, filteredSessions]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const openRenameDialog = useCallback((e: React.MouseEvent | null, session: SessionResponse) => {
    e?.stopPropagation();
    setRenamingSession(session);
    const patient = patients.get(session.patient_id);
    const patientName = patient ? getPatientDisplayName(patient.data) : "Unknown";
    const currentName = session.name || generateDefaultSessionName(patientName, session.started_at);
    setNewName(currentName);
    setRenameDialogOpen(true);
  }, [patients]);

  const handleRename = useCallback(async () => {
    if (!renamingSession || !newName.trim()) return;

    await updateSession(renamingSession.id, { name: newName.trim() });
    setRenameDialogOpen(false);
    setRenamingSession(null);
    setNewName("");
  }, [renamingSession, newName, updateSession]);

  const loading = isLoading || patientsLoading;

  const formatTimestamp = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const hasSelection = selectedIds.size > 0;
  const allSelected = filteredSessions.length > 0 && selectedIds.size === filteredSessions.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < filteredSessions.length;

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto w-full px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-semibold text-foreground pl-6 md:pl-0">Sessions</h1>
          </div>

          {/* Search bar */}
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search your sessions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-12 h-12 text-base bg-muted/50 border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>

          {error && (
            <div className="mb-4 p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
              {error.message}
            </div>
          )}

          {/* Session count or selection toolbar */}
          {!loading && filteredSessions.length > 0 && (
            <div className="flex items-center gap-2 mb-2 text-sm h-8">
              {hasSelection ? (
                <>
                  <button
                    onClick={handleSelectAll}
                    className="flex items-center justify-center w-5 h-5"
                  >
                    {allSelected ? (
                      <div className="w-4 h-4 rounded bg-primary flex items-center justify-center">
                        <CheckSquare className="h-3 w-3 text-primary-foreground" />
                      </div>
                    ) : someSelected ? (
                      <div className="w-4 h-4 rounded bg-primary flex items-center justify-center">
                        <Minus className="h-3 w-3 text-primary-foreground" />
                      </div>
                    ) : (
                      <div className="w-4 h-4 rounded border-2 border-muted-foreground" />
                    )}
                  </button>
                  <span className="text-muted-foreground">
                    {selectedIds.size} selected
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleDeleteSelected}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <div className="flex-1" />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={clearSelection}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <span className="text-muted-foreground">
                  {filteredSessions.length} session{filteredSessions.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}

          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 py-4 px-3 animate-pulse">
                  <div className="h-10 w-10 rounded-full bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 rounded bg-muted" />
                    <div className="h-3 w-48 rounded bg-muted" />
                  </div>
                  <div className="h-3 w-16 rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <MessageSquare className="h-10 w-10 mb-3" />
              <p className="text-sm">
                {search
                  ? "No sessions match your search."
                  : "No sessions yet. Start a conversation with a patient to create one."}
              </p>
            </div>
          ) : (
            <div className="space-y-0">
              {filteredSessions.map((session) => {
                const patient = patients.get(session.patient_id);
                const patientData = patient?.data;
                const patientName = patientData ? getPatientDisplayName(patientData) : "Unknown Patient";
                const initials = patientData ? getPatientInitials(patientData) : "?";
                const avatarSrc = patientData ? getPatientAvatarUrl(patientData) : undefined;
                const sessionName = session.name || generateDefaultSessionName(patientName, session.started_at);
                const isSelected = selectedIds.has(session.id);
                const isDeleting = deletingIds.has(session.id);

                return (
                  <div
                    key={session.id}
                    onClick={() => handleOpenSession(session)}
                    className={`flex items-center gap-3 py-3 px-3 rounded-lg cursor-pointer group transition-colors ${
                      isSelected ? "bg-muted" : "hover:bg-muted/50"
                    }`}
                  >
                    {/* Checkbox */}
                    <div className={`${isSelected || hasSelection ? "opacity-100" : "opacity-0 group-hover:opacity-100"} transition-opacity`}>
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleSelect(null, session.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>

                    {/* Avatar */}
                    <Avatar className="h-10 w-10 shrink-0">
                      <AvatarImage src={avatarSrc} alt={patientName} className="object-cover" />
                      <AvatarFallback className="bg-primary/10 text-primary text-sm font-medium">
                        {initials}
                      </AvatarFallback>
                    </Avatar>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-foreground truncate">{sessionName}</div>
                      <div className="text-sm text-muted-foreground">
                        {patientName} · Last message {formatTimestamp(session.last_active_at)}
                      </div>
                    </div>

                    {/* Actions */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => e.stopPropagation()}
                          disabled={isDeleting}
                          className="h-8 w-8 text-muted-foreground opacity-0 group-hover:opacity-100 focus:opacity-100 data-[state=open]:opacity-100"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem onClick={() => handleOpenSession(session)}>
                          <FolderOpen className="mr-2 h-4 w-4" />
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => toggleSelect(e as unknown as React.MouseEvent, session.id)}>
                          <CheckSquare className="mr-2 h-4 w-4" />
                          Select
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => openRenameDialog(e as unknown as React.MouseEvent, session)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => handleDelete(e as unknown as React.MouseEvent, session.id)}
                          variant="destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Session</DialogTitle>
          </DialogHeader>
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Session name"
            onKeyDown={(e) => e.key === "Enter" && handleRename()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRename} disabled={!newName.trim()}>
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
