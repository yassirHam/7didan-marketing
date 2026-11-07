"use client";

import { useEffect, useRef } from "react";
import type { Outcome } from "@/lib/outcome";
import { Button, cx } from "../ui";

export function ResultCard({
  outcome,
  onContinue,
}: {
  outcome: Outcome;
  onContinue: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);

  const success = outcome.kind === "success";

  return (
    <section
      role="status"
      className={cx(
        "animate-rise overflow-hidden rounded-2xl border bg-canvas-card shadow-lg",
        success ? "border-success/40" : "border-line"
      )}
    >
      <div
        className={cx(
          "flex items-center gap-3.5 px-6 py-5 border-b border-line",
          success ? "bg-success/10 text-success" : "bg-canvas-subtle text-ink"
        )}
      >
        <span
          className={cx(
            "grid size-9 place-items-center rounded-full font-mono text-base font-bold",
            success ? "bg-success text-white" : "bg-canvas text-ink"
          )}
          aria-hidden="true"
        >
          {success ? "✓" : "—"}
        </span>
        <div>
          <p className="t-label text-ash">
            {success ? "ODOO CRM OPPORTUNITY VERIFIED" : "CONVERSATION DISENGAGED"}
          </p>
          <h2
            ref={heading}
            tabIndex={-1}
            className="mt-0.5 font-display text-lg font-bold text-ink focus:outline-none"
          >
            {outcome.title}
          </h2>
        </div>
      </div>

      <div className="space-y-4 px-6 py-5 text-sm">
        <p className="leading-relaxed text-ink-soft">{outcome.message}</p>

        {success && outcome.reference != null && (
          <div className="rounded-lg border border-line bg-canvas-subtle p-3 font-mono text-xs">
            <span className="text-ash">CRM_LEAD_RECORD_ID: </span>
            <span className="text-tangerine font-bold">#{outcome.reference}</span>
          </div>
        )}

        <div className="pt-2">
          <Button variant="secondary" onClick={onContinue}>
            ← Ask Another Question
          </Button>
        </div>
      </div>
    </section>
  );
}
