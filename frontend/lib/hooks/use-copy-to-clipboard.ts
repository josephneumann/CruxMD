"use client";

import { useState, useCallback } from "react";

interface UseCopyToClipboardOptions {
  timeout?: number;
}

export function useCopyToClipboard({ timeout = 2000 }: UseCopyToClipboardOptions = {}) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), timeout);
  }, [timeout]);

  return { copied, copy };
}

/**
 * Variant that tracks which item was copied (for multiple copy buttons)
 */
export function useCopyToClipboardMulti<T extends string>({ timeout = 2000 }: UseCopyToClipboardOptions = {}) {
  const [copiedKey, setCopiedKey] = useState<T | null>(null);

  const copy = useCallback(async (text: string, key: T) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), timeout);
  }, [timeout]);

  return { copiedKey, copy };
}
