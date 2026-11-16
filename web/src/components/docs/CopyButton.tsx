"use client";

import { useState } from "react";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1600);
        } catch {
          /* clipboard blocked: nothing to do */
        }
      }}
      className="absolute right-2 top-2 border border-line-strong bg-ink px-2 py-1 font-mono text-[0.75rem] text-paper-dim transition-colors hover:border-paper hover:text-paper"
    >
      {copied ? "Copied" : "Copy"}
      <span className="sr-only" aria-live="polite">
        {copied ? " to clipboard" : ""}
      </span>
    </button>
  );
}
