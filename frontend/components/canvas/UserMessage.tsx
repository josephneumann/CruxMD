"use client";

import type { DisplayMessage } from "@/hooks";

interface UserMessageProps {
  message: DisplayMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="mb-8">
      <div className="flex justify-end">
        <div className="bg-muted rounded-2xl px-4 py-3 max-w-[80%]">
          <p className="text-foreground whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  );
}
