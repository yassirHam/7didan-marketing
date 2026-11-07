"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { LIMITS } from "@/lib/validation";
import { cx, Spinner } from "../ui";

export function Composer({
  onSend,
  busy,
  initial = "",
}: {
  onSend: (text: string) => void;
  busy: boolean;
  initial?: string;
}) {
  const [text, setText] = useState(initial);
  const ref = useRef<HTMLTextAreaElement>(null);
  const tooLong = text.length > LIMITS.message;
  const canSend = !busy && text.trim().length > 0 && !tooLong;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!canSend) return;
    onSend(text);
    setText("");
    ref.current?.focus();
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e);
  };

  return (
    <form
      onSubmit={submit}
      className="flex items-end gap-3 rounded-2xl border border-line bg-canvas-card p-2.5 pl-5 shadow-sm transition-colors focus-within:border-tangerine focus-within:ring-2 focus-within:ring-tangerine/15"
    >
      <label htmlFor="composer" className="sr-only">Your question</label>
      <textarea
        id="composer"
        ref={ref}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        placeholder="Ask in Darija, French or English (e.g. Bghit n3ref offre fibre 20 personnes)…"
        aria-invalid={tooLong || undefined}
        aria-describedby={tooLong ? "composer-error" : undefined}
        className="max-h-40 min-h-11 flex-1 resize-none bg-transparent py-2.5 text-[15px] text-ink placeholder:text-ash/60 focus:outline-none"
      />

      {tooLong && (
        <span id="composer-error" className="self-center font-mono text-xs text-danger">
          {text.length}/{LIMITS.message}
        </span>
      )}

      <button
        type="submit"
        disabled={!canSend}
        aria-label="Send"
        className={cx(
          "grid size-11 shrink-0 place-items-center rounded-xl font-mono transition-all",
          canSend
            ? "bg-tangerine text-white hover:bg-ink active:scale-95 shadow-sm"
            : "bg-canvas-subtle text-ash/40"
        )}
      >
        {busy ? (
          <Spinner className="size-5" />
        ) : (
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        )}
      </button>
    </form>
  );
}
