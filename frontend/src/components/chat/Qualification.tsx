"use client";

import { useEffect, useRef, type FormEvent, type ReactNode } from "react";
import { SERVICE_CATEGORIES, TIMELINE_CHOICES } from "@/lib/contract";
import { LIMITS, type FieldErrors } from "@/lib/validation";
import type { Draft, Phase } from "@/hooks/useConversation";
import { Button, cx, Field, TextArea, TextInput } from "../ui";

const STEP_LABELS = ["Scope & Need", "Budget & Specs", "Deployment Timeline", "CRM Contact"];
const stepIndex = (p: Phase) => ["need", "requirements", "timeline", "contact"].indexOf(p);

export function Stepper({ phase }: { phase: Phase }) {
  const current = stepIndex(phase);
  return (
    <ol className="flex items-center gap-2" aria-label="Qualification Progress">
      {STEP_LABELS.map((label, i) => {
        const state = i < current ? "done" : i === current ? "current" : "todo";
        return (
          <li
            key={label}
            className="flex flex-1 flex-col gap-1.5"
            aria-current={state === "current" ? "step" : undefined}
          >
            <div
              className={cx(
                "h-1 rounded-full transition-colors",
                state === "done" && "bg-tangerine",
                state === "current" && "bg-ink",
                state === "todo" && "bg-line"
              )}
            />
            <span
              className={cx(
                "hidden font-mono text-[10px] uppercase tracking-wider sm:block",
                state === "current" ? "text-ink font-semibold" : "text-ash"
              )}
            >
              0{i + 1} · {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function StepCard({
  step,
  title,
  intro,
  children,
  onBack,
  onCancel,
  footer,
  onSubmit,
}: {
  step: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
  onBack?: () => void;
  onCancel: () => void;
  footer: ReactNode;
  onSubmit: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [step]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      className="animate-rise rounded-2xl border border-line bg-canvas-card p-6 shadow-md sm:p-8"
    >
      <div className="flex items-start justify-between gap-4 border-b border-line pb-4">
        <div>
          <p className="t-label text-tangerine">{step}</p>
          <h2
            ref={heading}
            tabIndex={-1}
            className="mt-1 font-display text-xl font-bold text-ink focus:outline-none sm:text-2xl"
          >
            {title}
          </h2>
          {intro && <p className="mt-1 text-sm text-ink-soft">{intro}</p>}
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="font-mono text-xs uppercase tracking-wider text-ash transition-colors hover:text-ink"
        >
          Cancel
        </button>
      </div>

      <div className="mt-6 flex flex-col gap-5">{children}</div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            ← Back
          </Button>
        ) : (
          <span />
        )}
        <div className="flex flex-wrap items-center gap-2">{footer}</div>
      </div>
    </form>
  );
}

function SkipToggle({
  id,
  checked,
  onChange,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  children: ReactNode;
}) {
  return (
    <label htmlFor={id} className="inline-flex w-fit cursor-pointer items-center gap-2.5 text-xs text-ink-soft">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 accent-tangerine"
      />
      <span>{children}</span>
    </label>
  );
}

type StepProps = {
  draft: Draft;
  errors: FieldErrors;
  setDraft: (p: Partial<Draft>) => void;
  next: () => void;
  back: () => void;
  cancel: () => void;
};

export function NeedStep({ draft, errors, setDraft, next, cancel }: StepProps) {
  return (
    <StepCard
      step="Question 1 of 3 // Domain & Goal"
      title="Which service domain fits your need, and what should it accomplish?"
      onCancel={cancel}
      onSubmit={next}
      footer={<Button type="submit" variant="primary">Proceed to Specs →</Button>}
    >
      <fieldset>
        <legend className="t-label text-ink mb-2 block">Catalogue Service Area</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" role="radiogroup">
          {SERVICE_CATEGORIES.map((c) => {
            const on = draft.service_category === c.value;
            return (
              <label
                key={c.value}
                className={cx(
                  "flex cursor-pointer flex-col rounded-xl border p-3 transition-colors",
                  on
                    ? "border-tangerine bg-tangerine/10 text-ink"
                    : "border-line bg-canvas-subtle hover:border-ink/30"
                )}
              >
                <input
                  type="radio"
                  name="service_category"
                  value={c.value}
                  checked={on}
                  className="sr-only"
                  onChange={() => setDraft({ service_category: c.value })}
                />
                <span className="font-display text-sm font-semibold text-ink">{c.label}</span>
                <span className="mt-1 text-[11px] text-ash">{c.hint}</span>
              </label>
            );
          })}
        </div>
        {errors.service_category && (
          <p className="mt-2 text-xs font-medium text-danger">{errors.service_category}</p>
        )}
      </fieldset>

      <Field id="service_interest" label="Specific Offering" error={errors.service_interest} hint="e.g. Dedicated Business Fibre 100M, Corporate Fleet Lines">
        <TextInput
          id="service_interest"
          value={draft.service_interest}
          maxLength={LIMITS.serviceInterest + 20}
          hasHint
          error={errors.service_interest}
          onChange={(e) => setDraft({ service_interest: e.target.value })}
          autoComplete="off"
        />
      </Field>

      <Field id="need" label="Business Objective" error={errors.need} count={[draft.need.length, LIMITS.need]}>
        <TextArea
          id="need"
          value={draft.need}
          error={errors.need}
          rows={3}
          placeholder="e.g. Reliable high-speed connectivity for a 20-person logistics office in Casablanca"
          onChange={(e) => setDraft({ need: e.target.value })}
        />
      </Field>
    </StepCard>
  );
}

export function RequirementsStep({ draft, errors, setDraft, next, back, cancel }: StepProps) {
  return (
    <StepCard
      step="Question 2 of 3 // Budget & Technical Constraints"
      title="What is your estimated budget and technical requirements?"
      intro="Uncertain fields are safely logged as 'Unknown' in Odoo CRM rather than guessed."
      onBack={back}
      onCancel={cancel}
      onSubmit={next}
      footer={<Button type="submit" variant="primary">Proceed to Timeline →</Button>}
    >
      <Field id="budget" label="Approximate Monthly Budget (MAD)" error={errors.budget}>
        <TextInput
          id="budget"
          value={draft.budgetUnknown ? "" : draft.budget}
          disabled={draft.budgetUnknown}
          error={errors.budget}
          placeholder="e.g. About 3,500 MAD / month"
          onChange={(e) => setDraft({ budget: e.target.value })}
          autoComplete="off"
        />
      </Field>
      <SkipToggle
        id="budget-unknown"
        checked={draft.budgetUnknown}
        onChange={(v) => setDraft({ budgetUnknown: v })}
      >
        Budget not determined yet (Flag as Unknown)
      </SkipToggle>

      <Field
        id="requirements"
        label="Essential Technical Constraints"
        error={errors.requirements}
        count={[draft.requirements.length, LIMITS.optional]}
      >
        <TextArea
          id="requirements"
          value={draft.requirementsUnknown ? "" : draft.requirements}
          disabled={draft.requirementsUnknown}
          rows={2}
          error={errors.requirements}
          placeholder="e.g. Fixed public IP, 4G automatic failover, SLA 4h"
          onChange={(e) => setDraft({ requirements: e.target.value })}
        />
      </Field>
      <SkipToggle
        id="requirements-unknown"
        checked={draft.requirementsUnknown}
        onChange={(v) => setDraft({ requirementsUnknown: v })}
      >
        No specific technical constraints
      </SkipToggle>
    </StepCard>
  );
}

export function TimelineStep({ draft, errors, setDraft, next, back, cancel }: StepProps) {
  const custom = !!draft.timeline && !(TIMELINE_CHOICES as readonly string[]).includes(draft.timeline);
  return (
    <StepCard
      step="Question 3 of 3 // Implementation Schedule"
      title="When does your organisation need this service live?"
      onBack={back}
      onCancel={cancel}
      onSubmit={next}
      footer={<Button type="submit" variant="primary">Review &amp; Contact Details →</Button>}
    >
      <fieldset disabled={draft.timelineUnknown}>
        <legend className="sr-only">Timeline</legend>
        <div className="flex flex-wrap gap-2">
          {TIMELINE_CHOICES.map((t) => {
            const on = !draft.timelineUnknown && draft.timeline === t;
            return (
              <label
                key={t}
                className={cx(
                  "cursor-pointer rounded-full border px-4 py-2 font-mono text-xs transition-colors",
                  on
                    ? "border-tangerine bg-tangerine text-white font-semibold"
                    : "border-line bg-canvas-subtle text-ink hover:border-ink/40",
                  draft.timelineUnknown && "cursor-not-allowed opacity-40"
                )}
              >
                <input
                  type="radio"
                  name="timeline"
                  className="sr-only"
                  checked={on}
                  onChange={() => setDraft({ timeline: t })}
                />
                {t}
              </label>
            );
          })}
        </div>
      </fieldset>

      <Field id="timeline-other" label="Custom Date or Milestone" optional error={errors.timeline}>
        <TextInput
          id="timeline-other"
          value={custom && !draft.timelineUnknown ? draft.timeline : ""}
          disabled={draft.timelineUnknown}
          error={errors.timeline}
          placeholder="e.g. Ahead of our new branch opening in April"
          onChange={(e) => setDraft({ timeline: e.target.value })}
          autoComplete="off"
        />
      </Field>
      <SkipToggle
        id="timeline-unknown"
        checked={draft.timelineUnknown}
        onChange={(v) => setDraft({ timelineUnknown: v })}
      >
        Schedule not fixed yet
      </SkipToggle>
    </StepCard>
  );
}
