"use client";

import type { ContactDetails, QualificationAnswers } from "@/lib/contract";
import { SERVICE_CATEGORIES } from "@/lib/contract";
import type { Outcome } from "@/lib/outcome";
import { LIMITS, type FieldErrors } from "@/lib/validation";
import { Alert, Button, Field, TextInput } from "../ui";
import { StepCard } from "./Qualification";

type Props = {
  answers: QualificationAnswers;
  contact: ContactDetails;
  consent: boolean;
  errors: FieldErrors;
  sending: boolean;
  outcome: Outcome | null;
  setContact: (p: Partial<ContactDetails>) => void;
  setConsent: (v: boolean) => void;
  submit: () => void;
  decline: () => void;
  back: () => void;
  editAnswers: () => void;
  cancel: () => void;
};

const QUESTION_FIELDS = ["service_interest", "service_category", "need", "budget", "requirements", "timeline"];

function Summary({ answers, onEdit }: { answers: QualificationAnswers; onEdit: () => void }) {
  const category = SERVICE_CATEGORIES.find((c) => c.value === answers.service_category)?.label ?? "";
  const rows: [string, string | null][] = [
    ["Service Offering", `${answers.service_interest} (${category})`],
    ["Need Objective", answers.need],
    ["Budget", answers.budget],
    ["Specifications", answers.requirements],
    ["Timeline", answers.timeline],
  ];

  return (
    <div className="rounded-xl border border-line bg-canvas-subtle p-4">
      <div className="flex items-center justify-between border-b border-line pb-2">
        <p className="t-label text-tangerine">CONFIRMED QUALIFICATION PAYLOAD</p>
        <button
          type="button"
          onClick={onEdit}
          className="font-mono text-xs uppercase tracking-wider text-ink-soft hover:text-ink hover:underline"
        >
          Edit
        </button>
      </div>
      <dl className="mt-3 grid gap-x-4 gap-y-2 text-xs sm:grid-cols-[10rem_1fr]">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-mono text-ash">{k}</dt>
            <dd className="break-words font-medium text-ink">
              {v ?? <span className="font-mono text-ash italic">Unknown</span>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function ContactStep(p: Props) {
  const { contact, errors, outcome, sending } = p;
  const answerErrors = QUESTION_FIELDS.filter((f) => errors[f]).map((f) => errors[f] as string);

  return (
    <StepCard
      step="Final Step // Advisor Verification"
      title="Who should receive the qualified dossier in Odoo CRM?"
      intro="Academic prototype: please input synthetic details (e.g. Salma Bennani, Atlas Logistiq)."
      onBack={sending ? undefined : p.back}
      onCancel={p.cancel}
      onSubmit={p.submit}
      footer={
        <>
          <Button variant="secondary" onClick={p.decline} disabled={sending}>
            Decline &amp; Discard
          </Button>
          <Button type="submit" variant="primary" loading={sending}>
            {sending ? "Verifying with Odoo…" : outcome?.kind === "retry" ? "Retry Sync" : "Sync Enquiry to CRM"}
          </Button>
        </>
      }
    >
      {outcome && outcome.kind !== "success" && outcome.kind !== "declined" && (
        <Alert tone={outcome.kind === "retry" ? "warning" : "error"} title={outcome.title}>
          <p>{outcome.message}</p>
          {outcome.kind === "fix" && (outcome.other.length > 0 || answerErrors.length > 0) && (
            <ul className="mt-2 list-disc pl-5 font-mono text-xs text-danger">
              {[...answerErrors, ...outcome.other].map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          )}
          {answerErrors.length > 0 && (
            <button
              type="button"
              onClick={p.editAnswers}
              className="mt-2 font-mono text-xs text-tangerine hover:underline"
            >
              ← Edit answers
            </button>
          )}
        </Alert>
      )}

      <Summary answers={p.answers} onEdit={p.editAnswers} />

      <fieldset disabled={sending} className="grid gap-5 sm:grid-cols-2 pt-2">
        <legend className="sr-only">Contact Details</legend>
        <Field id="name" label="Representative Name" error={errors.name}>
          <TextInput
            id="name"
            value={contact.name}
            maxLength={LIMITS.name + 10}
            error={errors.name}
            autoComplete="name"
            placeholder="e.g. Salma Bennani"
            onChange={(e) => p.setContact({ name: e.target.value })}
          />
        </Field>
        <Field id="company" label="Enterprise Name" error={errors.company}>
          <TextInput
            id="company"
            value={contact.company}
            maxLength={LIMITS.company + 10}
            error={errors.company}
            autoComplete="organization"
            placeholder="e.g. Atlas Logistiq SARL"
            onChange={(e) => p.setContact({ company: e.target.value })}
          />
        </Field>
        <Field id="email" label="Corporate Email" error={errors.email}>
          <TextInput
            id="email"
            type="email"
            inputMode="email"
            value={contact.email}
            error={errors.email}
            autoComplete="email"
            placeholder="e.g. s.bennani@atlaslogistiq.ma"
            onChange={(e) => p.setContact({ email: e.target.value })}
          />
        </Field>
        <Field id="phone" label="Phone (Optional)" optional error={errors.phone}>
          <TextInput
            id="phone"
            type="tel"
            inputMode="tel"
            value={contact.phone ?? ""}
            error={errors.phone}
            autoComplete="tel"
            placeholder="+212 6 00 00 00 00"
            onChange={(e) => p.setContact({ phone: e.target.value })}
          />
        </Field>
      </fieldset>

      <div className="pt-2">
        <label
          htmlFor="consent"
          className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-canvas-subtle p-4 text-xs text-ink-soft transition-colors has-[:checked]:border-tangerine has-[:checked]:bg-tangerine/5"
        >
          <input
            id="consent"
            type="checkbox"
            checked={p.consent}
            disabled={sending}
            onChange={(e) => p.setConsent(e.target.checked)}
            aria-invalid={!!errors.consent || undefined}
            className="mt-0.5 size-4 accent-tangerine shrink-0"
          />
          <span className="leading-relaxed">
            I consent to transmitting this qualified record to the Orange Maroc Business sales CRM via n8n.
            Without this verification, no record is created or transmitted.
          </span>
        </label>
        {errors.consent && (
          <p className="mt-1.5 text-xs font-medium text-danger">{errors.consent}</p>
        )}
      </div>
    </StepCard>
  );
}
