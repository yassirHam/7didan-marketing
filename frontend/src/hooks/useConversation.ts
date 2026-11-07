"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import type { ChatResponse, ContactDetails, EnquiryRequest, ServiceCategory, Source } from "@/lib/contract";
import { newId, sendMessage, submitEnquiry, trackEvent, type Mode } from "@/lib/client";
import { outcomeOf, type Outcome } from "@/lib/outcome";
import {
  hasErrors, validateContact, validateNeed, validateRequirements, validateTimeline, type FieldErrors,
} from "@/lib/validation";

export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: ChatResponse["status"];
  sources?: Source[];
  offer?: boolean;
  suggested?: ChatResponse["suggested_service"];
};

/** chat → need → requirements → timeline → contact → result. The three middle steps are the three questions. */
export type Phase = "chat" | "need" | "requirements" | "timeline" | "contact" | "result";
export const QUESTION_STEPS = ["need", "requirements", "timeline"] as const;

export type Draft = {
  service_category: ServiceCategory | "";
  service_interest: string;
  need: string;
  budget: string;
  budgetUnknown: boolean;
  requirements: string;
  requirementsUnknown: boolean;
  timeline: string;
  timelineUnknown: boolean;
};
const EMPTY_DRAFT: Draft = {
  service_category: "", service_interest: "", need: "", budget: "", budgetUnknown: false,
  requirements: "", requirementsUnknown: false, timeline: "", timelineUnknown: false,
};
const EMPTY_CONTACT: ContactDetails = { name: "", company: "", email: "", phone: "" };

type State = {
  conversationId: string | null;
  mode: Mode | null;
  messages: Message[];
  thinking: boolean;
  chatError: { text: string; message: string } | null;
  phase: Phase;
  draft: Draft;
  contact: ContactDetails;
  consent: boolean;
  errors: FieldErrors;
  submissionId: string | null; // fixed for the whole enquiry, so retries cannot create duplicates
  sending: boolean;
  outcome: Outcome | null;
  completed: boolean; // qualification_completed was reported
};

const initial: State = {
  conversationId: null, mode: null, messages: [], thinking: false, chatError: null, phase: "chat",
  draft: EMPTY_DRAFT, contact: EMPTY_CONTACT, consent: false, errors: {}, submissionId: null,
  sending: false, outcome: null, completed: false,
};

type Action =
  | { type: "conversation"; id: string }
  | { type: "user"; message: Message }
  | { type: "assistant"; message: Message; mode: Mode }
  | { type: "chatError"; text: string; message: string }
  | { type: "retrying" }
  | { type: "finishEnquiry"; note: Message }
  | { type: "phase"; phase: Phase; errors?: FieldErrors }
  | { type: "draft"; patch: Partial<Draft> }
  | { type: "contact"; patch: Partial<ContactDetails> }
  | { type: "consent"; value: boolean }
  | { type: "errors"; errors: FieldErrors }
  | { type: "startQualification"; prefill: Partial<Draft> }
  | { type: "completed" }
  | { type: "sending"; submissionId: string }
  | { type: "outcome"; outcome: Outcome }
  | { type: "leaveQualification"; note: Message }
  | { type: "reset" };

function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "conversation": return { ...s, conversationId: a.id };
    case "user": return { ...s, messages: [...s.messages, a.message], thinking: true, chatError: null };
    case "assistant": return { ...s, messages: [...s.messages, a.message], thinking: false, mode: a.mode };
    case "chatError": return { ...s, thinking: false, chatError: { text: a.text, message: a.message } };
    case "retrying": return { ...s, thinking: true, chatError: null };
    // A finished enquiry (sent or declined): the next one starts with fresh answers and a new submission ID.
    case "finishEnquiry":
      return { ...s, phase: "chat", errors: {}, draft: EMPTY_DRAFT, completed: false, outcome: null, submissionId: null, consent: false, messages: [...s.messages, a.note] };
    case "phase": return { ...s, phase: a.phase, errors: a.errors ?? {} };
    case "draft": return { ...s, draft: { ...s.draft, ...a.patch }, errors: {} };
    case "contact": {
      const cleared = { ...s.errors };
      Object.keys(a.patch).forEach((k) => delete cleared[k]);
      return { ...s, contact: { ...s.contact, ...a.patch }, errors: cleared };
    }
    case "consent": {
      const rest = { ...s.errors };
      delete rest.consent;
      return { ...s, consent: a.value, errors: rest };
    }
    case "errors": return { ...s, errors: a.errors };
    case "startQualification":
      return { ...s, phase: "need", errors: {}, outcome: null, draft: { ...s.draft, ...a.prefill } };
    case "completed": return { ...s, completed: true, phase: "contact", errors: {} };
    case "sending": return { ...s, sending: true, submissionId: a.submissionId, outcome: null };
    case "outcome": {
      const o = a.outcome;
      const done = o.kind === "success" || o.kind === "declined";
      return { ...s, sending: false, outcome: o, phase: done ? "result" : "contact", errors: o.kind === "fix" ? o.fields : {} };
    }
    case "leaveQualification":
      return {
        ...s, phase: "chat", errors: {}, draft: EMPTY_DRAFT, completed: false, outcome: null, messages: [...s.messages, a.note],
        // After an unconfirmed send the record may exist, so keep its ID: a later send then cannot duplicate it.
        submissionId: s.outcome?.kind === "retry" ? s.submissionId : null,
      };
    case "reset": return initial;
  }
}

export const toAnswers = (d: Draft): EnquiryRequest["qualification"] => ({
  service_category: d.service_category as ServiceCategory,
  service_interest: d.service_interest.trim(),
  need: d.need.trim(),
  budget: d.budgetUnknown || !d.budget.trim() ? null : d.budget.trim(),
  requirements: d.requirementsUnknown || !d.requirements.trim() ? null : d.requirements.trim(),
  timeline: d.timelineUnknown || !d.timeline.trim() ? null : d.timeline.trim(),
});

export function useConversation() {
  const [s, dispatch] = useReducer(reducer, initial);
  const state = useRef(s);
  useEffect(() => { state.current = s; }, [s]);

  const ensureConversation = useCallback((): string => {
    if (state.current.conversationId) return state.current.conversationId;
    const id = newId();
    state.current = { ...state.current, conversationId: id };
    dispatch({ type: "conversation", id });
    return id;
  }, []);

  const ask = useCallback(async (conversationId: string, text: string) => {
    const r = await sendMessage(conversationId, text);
    if (!r.ok) { dispatch({ type: "chatError", text: r.error, message: text }); return; }
    const d = r.data;
    dispatch({
      type: "assistant", mode: r.mode,
      message: { id: newId(), role: "assistant", text: d.answer, status: d.status, sources: d.sources, offer: d.offer_qualification, suggested: d.suggested_service },
    });
  }, []);

  const send = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text || state.current.thinking) return;
    const conversationId = ensureConversation();
    dispatch({ type: "user", message: { id: newId(), role: "user", text } });
    await ask(conversationId, text);
  }, [ask, ensureConversation]);

  /** Resend the message that failed; it is already in the transcript. */
  const retryChat = useCallback(async () => {
    const failed = state.current.chatError;
    if (!failed || state.current.thinking) return;
    dispatch({ type: "retrying" });
    await ask(ensureConversation(), failed.message);
  }, [ask, ensureConversation]);

  const startQualification = useCallback((suggested?: Message["suggested"]) => {
    const conversationId = ensureConversation();
    const d = state.current.draft;
    dispatch({
      type: "startQualification",
      prefill: suggested && !d.service_category
        ? { service_category: suggested.service_category, service_interest: suggested.service_interest }
        : {},
    });
    trackEvent(conversationId, "qualification_started");
  }, [ensureConversation]);

  /** Validate the current question and move forward; the last one completes qualification. */
  const next = useCallback(() => {
    const { phase, draft, conversationId } = state.current;
    const answers = toAnswers(draft);
    if (phase === "need") {
      const e = validateNeed(answers);
      dispatch(hasErrors(e) ? { type: "errors", errors: e } : { type: "phase", phase: "requirements" });
    } else if (phase === "requirements") {
      const e = validateRequirements(answers);
      dispatch(hasErrors(e) ? { type: "errors", errors: e } : { type: "phase", phase: "timeline" });
    } else if (phase === "timeline") {
      const e = validateTimeline(answers);
      if (hasErrors(e)) { dispatch({ type: "errors", errors: e }); return; }
      if (!state.current.completed && conversationId) trackEvent(conversationId, "qualification_completed");
      dispatch({ type: "completed" });
    }
  }, []);

  const back = useCallback(() => {
    const order: Phase[] = ["need", "requirements", "timeline", "contact"];
    const i = order.indexOf(state.current.phase);
    if (i > 0) dispatch({ type: "phase", phase: order[i - 1] });
  }, []);

  /** Leave the questions before finishing them: counted as abandoned, nothing is sent. */
  const cancel = useCallback(() => {
    const { conversationId, completed, outcome } = state.current;
    if (conversationId && !completed) trackEvent(conversationId, "abandoned");
    const text = outcome?.kind === "retry"
      ? "No problem. If your enquiry did reach the sales team, an advisor will contact you."
      : "No problem, nothing was sent. You can keep asking questions.";
    dispatch({ type: "leaveQualification", note: { id: newId(), role: "assistant", text } });
  }, []);

  const submit = useCallback(async () => {
    const { contact, consent, draft, conversationId, sending } = state.current;
    if (sending || !conversationId) return;
    const e = validateContact(contact, consent);
    if (hasErrors(e)) { dispatch({ type: "errors", errors: e }); return; }
    const submissionId = state.current.submissionId ?? newId();
    dispatch({ type: "sending", submissionId });
    const result = await submitEnquiry({
      submission_id: submissionId,
      conversation_id: conversationId,
      qualification: toAnswers(draft),
      contact: {
        name: contact.name.trim(), company: contact.company.trim(), email: contact.email.trim(),
        phone: contact.phone?.trim() ? contact.phone.trim() : null,
      },
      consent,
    });
    dispatch({ type: "outcome", outcome: outcomeOf(result) });
  }, []);

  /** The visitor finished the questions but does not want to be contacted. Nothing is sent. */
  const decline = useCallback(() => {
    dispatch({ type: "outcome", outcome: { kind: "declined", title: "Nothing was sent", message: "Your answers stay on this page only. You can keep asking questions or start again." } });
  }, []);

  // Closing the page in the middle of the three questions counts as abandoning them.
  useEffect(() => {
    const onHide = () => {
      const { phase, conversationId, completed } = state.current;
      if (conversationId && !completed && (QUESTION_STEPS as readonly string[]).includes(phase)) {
        trackEvent(conversationId, "abandoned", true);
      }
    };
    window.addEventListener("pagehide", onHide);
    return () => window.removeEventListener("pagehide", onHide);
  }, []);

  return {
    state: s,
    send, retryChat, startQualification, next, back, cancel, submit, decline,
    setDraft: (patch: Partial<Draft>) => dispatch({ type: "draft", patch }),
    setContact: (patch: Partial<ContactDetails>) => dispatch({ type: "contact", patch }),
    setConsent: (value: boolean) => dispatch({ type: "consent", value }),
    editAnswers: () => dispatch({ type: "phase", phase: "need" }),
    finishEnquiry: () => dispatch({
      type: "finishEnquiry",
      note: { id: newId(), role: "assistant", text: "Anything else you'd like to know? Ask away." },
    }),
    reset: () => dispatch({ type: "reset" }),
  };
}
