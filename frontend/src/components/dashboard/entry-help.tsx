"use client";

import type { ReactNode } from "react";
import { CircleHelp } from "lucide-react";

/**
 * Small, reusable Entry guidance disclosure.
 *
 * Native details/summary provides keyboard and touch toggle without JS state.
 * CSS also reveals the explanation when a pointer hovers over the icon.
 * Never use this for errors, validation results or action-critical messages.
 */
export function EntryHelp({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <details className="entry-help">
      <summary aria-label={`${label} — more information`} title={label}>
        <CircleHelp size={16} aria-hidden="true" />
      </summary>
      <div className="entry-help-content" role="note">
        {children}
      </div>
    </details>
  );
}
