"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { toAnswers, useConversation } from "@/hooks/useConversation";
import { Disclaimer } from "../SiteChrome";
import { Alert, Button, Logo, Mark } from "../ui";
import { Composer } from "./Composer";
import { ContactStep } from "./ContactStep";
import { MessageBubble, Typing } from "./MessageBubble";
import { NeedStep, RequirementsStep, Stepper, TimelineStep } from "./Qualification";
import { ResultCard } from "./ResultCard";

const STARTERS = [
  "Salam! Bghit n3ref chno l'offre li kaynasb charika dyali?",
  "Which internet option fits a 20-person office?",
  "What is the exact price for 500 mobile lines?",
  "Quelles solutions cloud proposez-vous pour héberger notre ERP ?",
];

function Welcome({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl py-12 text-center animate-rise">
      <div className="inline-block p-3">
        <Mark className="mx-auto size-14 drop-shadow-[0_4px_20px_rgba(255,107,26,0.25)]" />
      </div>

      <p className="t-label mt-4 text-tangerine">7DIDAN // ENTERPRISE CONVERSATION</p>
      <h1 className="t-title mt-2 text-ink">
        Ask the Business Catalogue.
      </h1>

      <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-ink-soft">
        Direct quotes from official catalogue documents in Moroccan Darija, French or English.
        Honest abstention on unlisted conditions.
      </p>

      <div className="mt-8 grid gap-2.5 sm:grid-cols-2 text-left">
        {STARTERS.map((q, i) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="group flex flex-col justify-between rounded-xl border border-line bg-canvas-card p-4 shadow-sm transition-all hover:border-tangerine hover:shadow-md active:scale-[0.98]"
          >
            <span className="font-mono text-[10px] text-ash">PROMPT 0{i + 1}</span>
            <span className="mt-2 text-xs font-medium leading-snug text-ink-soft group-hover:text-ink">
              &quot;{q}&quot;
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatApp() {
  const c = useConversation();
  const { state: s } = c;
  const initial = useSearchParams().get("q")?.slice(0, 2000) ?? "";
  const bottom = useRef<HTMLDivElement>(null);
  const qualifying = s.phase !== "chat";

  const lastAssistant = [...s.messages].reverse().find((m) => m.role === "assistant");

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [s.messages.length, s.thinking, s.phase, s.chatError]);

  const stepProps = {
    draft: s.draft,
    errors: s.errors,
    setDraft: c.setDraft,
    next: c.next,
    back: c.back,
    cancel: c.cancel,
  };

  return (
    <div className="flex h-dvh flex-col bg-canvas text-ink">
      {/* ── App Bar ── */}
      <header className="z-30 border-b border-line bg-canvas/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between gap-4 px-6">
          <Link href="/" aria-label="Back to 7didan home">
            <Logo className="text-lg" />
          </Link>

          <div className="flex items-center gap-3">
            {s.mode === "demo" && (
              <span
                className="rounded border border-sun bg-sun/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink"
                title="Synthetic business catalogue answers"
              >
                Demo Environment
              </span>
            )}

            {!qualifying && (
              <Button
                variant="secondary"
                className="min-h-9 px-4 text-[10px]"
                onClick={() => c.startQualification(lastAssistant?.suggested)}
              >
                <span>Talk to Advisor</span>
                <span aria-hidden="true">→</span>
              </Button>
            )}

            {s.messages.length > 0 && !qualifying && (
              <Button
                variant="ghost"
                className="min-h-9 px-3 text-[10px]"
                onClick={c.reset}
                aria-label="Start a new conversation"
              >
                Reset
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* ── Messages Stream ── */}
      <main className="flex-1 overflow-y-auto" aria-label="Conversation Feed">
        <div
          className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8"
          aria-live="polite"
          aria-relevant="additions"
        >
          {s.messages.length === 0 && !qualifying && <Welcome onPick={c.send} />}

          {s.messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              onQualify={
                !qualifying && m === lastAssistant && m.offer
                  ? () => c.startQualification(m.suggested)
                  : undefined
              }
            />
          ))}

          {s.thinking && <Typing />}

          {s.chatError && (
            <Alert
              tone="error"
              title="Assistant Pipeline Unreachable"
              action={
                <Button variant="secondary" onClick={c.retryChat}>
                  Retry Query
                </Button>
              }
            >
              {s.chatError.text}
            </Alert>
          )}

          {s.phase === "result" && s.outcome && (
            <ResultCard outcome={s.outcome} onContinue={c.finishEnquiry} />
          )}

          <div ref={bottom} />
        </div>
      </main>

      {/* ── Bottom Interactive Zone: Stepper Drawer or Composer ── */}
      <div className="border-t border-line bg-canvas/90 backdrop-blur-md">
        <div className="mx-auto max-w-4xl px-6 pb-[max(env(safe-area-inset-bottom),1rem)] pt-4">
          {s.phase === "chat" && (
            <>
              <Composer onSend={c.send} busy={s.thinking} initial={initial} />
              <Disclaimer className="mt-3 text-center font-mono text-[10px] uppercase tracking-wider text-ash" />
            </>
          )}

          {qualifying && s.phase !== "result" && (
            <div className="flex max-h-[75dvh] flex-col gap-4 overflow-y-auto pb-2">
              <Stepper phase={s.phase} />
              {s.phase === "need" && <NeedStep {...stepProps} />}
              {s.phase === "requirements" && <RequirementsStep {...stepProps} />}
              {s.phase === "timeline" && <TimelineStep {...stepProps} />}
              {s.phase === "contact" && (
                <ContactStep
                  answers={toAnswers(s.draft)}
                  contact={s.contact}
                  consent={s.consent}
                  errors={s.errors}
                  sending={s.sending}
                  outcome={s.outcome}
                  setContact={c.setContact}
                  setConsent={c.setConsent}
                  submit={c.submit}
                  decline={c.decline}
                  back={c.back}
                  editAnswers={c.editAnswers}
                  cancel={c.cancel}
                />
              )}
            </div>
          )}

          {s.phase === "result" && (
            <p className="py-2 text-center font-mono text-xs text-ash">
              Enquiry cycle concluded. Select &quot;Ask Another Question&quot; above to reset stream.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
