import "server-only";

// Demo backend, used when BACKEND_URL is not set. It stands in for Amine's FastAPI service so the
// interface can be built and shown on its own:
// - chat answers come from a few illustrative snippets, never from real catalogue data;
// - enquiries get a placeholder score and are sent to the real n8n webhook (Yassir's workflow),
//   so a demo submission still creates and verifies a real Odoo opportunity.
import {
  TIMELINE_CHOICES, type ChatResponse, type EnquiryRequest, type EnquiryResponse, type ServiceCategory, type Source,
} from "../contract";

const DEMO_SOURCE = (section: string): Source => ({
  title: "Demo catalogue (illustrative demo data)",
  section,
  url: null,
  retrieved_at: null,
});

const TOPICS: { category: ServiceCategory; label: string; service: string; words: RegExp; answer: string }[] = [
  {
    category: "connectivity", label: "Connectivity", service: "Business internet",
    words: /\b(internet|fib(re|er)|wifi|wi-fi|connexion|r[ée]seau|network|bandwidth|d[ée]bit|link|ligne fixe)\b/i,
    answer:
      "Here is what the demo catalogue says for business connectivity:\n" +
      "- Option A: a dedicated business fibre line\n- Option B: a mobile backup link\n" +
      "This is illustrative demo data. In the full system the answer comes from the published catalogue.",
  },
  {
    category: "mobile", label: "Mobile", service: "Business mobile plans",
    words: /\b(mobile|sim|forfait|lines?|smartphones?|4g|5g|data plan|t[ée]l[ée]phone portable)\b/i,
    answer:
      "The demo catalogue lists business mobile plans for teams, with lines managed by the company.\n" +
      "This is illustrative demo data. In the full system the answer comes from the published catalogue.",
  },
  {
    category: "cloud", label: "Cloud", service: "Cloud hosting",
    words: /\b(cloud|host(ing)?|h[ée]bergement|servers?|serveurs?|storage|stockage|backup|sauvegarde|erp)\b/i,
    answer:
      "The demo catalogue groups hosting, storage and backup services under Cloud.\n" +
      "This is illustrative demo data. In the full system the answer comes from the published catalogue.",
  },
  {
    category: "cybersecurity", label: "Cybersecurity", service: "Managed security",
    words: /\b(secur(ity|it[ée])|s[ée]curit[ée]|firewall|pare-feu|cyber|antivirus|attack|attaque|protect)\w*/i,
    answer:
      "The demo catalogue lists security services such as a managed firewall for the company network.\n" +
      "This is illustrative demo data. In the full system the answer comes from the published catalogue.",
  },
  {
    category: "collaboration", label: "Collaboration", service: "Collaboration tools",
    words: /\b(meeting|r[ée]union|visio|video|conferenc\w*|teams|messag\w*|standard t[ée]l[ée]phonique|telephony|voip)\b/i,
    answer:
      "The demo catalogue groups meetings, messaging and business telephony under Collaboration.\n" +
      "This is illustrative demo data. In the full system the answer comes from the published catalogue.",
  },
];

const PRICE = /\b(price|prices|pricing|cost|costs|how much|prix|tarifs?|co[uû]te?|combien|bch[h]?al|ch[h]?al|mad|dh|dirhams?)\b/i;
const GREETING = /^\s*(hi|hello|hey|salam|salut|bonjour|bonsoir|ahlan|marhaba)\b[\s!.,?]*$/i;
const INTEREST = /\b(we need|i need|looking for|bghit|bghina|nous cherchons|je cherche|besoin|offre|offer|company|charika|entreprise|office|bureau|employees|salari[ée]s|team|[ée]quipe)\b/i;

export function demoChat(message: string): ChatResponse {
  if (GREETING.test(message)) {
    return {
      answer: "Salam! Ask me about business internet, mobile, cloud, cybersecurity or collaboration services.",
      status: "answered", sources: [], offer_qualification: false, suggested_service: null,
    };
  }
  const topic = TOPICS.find((t) => t.words.test(message));
  if (PRICE.test(message)) {
    // Prices and contract terms are never guessed.
    return {
      answer: "I can't verify that in the published documents. A sales advisor can confirm prices and conditions with you.",
      status: "abstained", sources: [], offer_qualification: true,
      suggested_service: topic ? { service_interest: topic.service, service_category: topic.category } : null,
    };
  }
  if (topic) {
    return {
      answer: topic.answer, status: "answered", sources: [DEMO_SOURCE(topic.label)], offer_qualification: true,
      suggested_service: { service_interest: topic.service, service_category: topic.category },
    };
  }
  if (INTEREST.test(message)) {
    // Business interest without a clear service: ask which area, without claiming anything.
    return {
      answer: "Happy to help. Which area is it about: internet, mobile lines, cloud, security or collaboration tools? You can also talk to an advisor directly.",
      status: "answered", sources: [], offer_qualification: true, suggested_service: null,
    };
  }
  return {
    answer: "I couldn't find this in the documents I have, so I won't guess. You can rephrase, or ask an advisor.",
    status: "abstained", sources: [], offer_qualification: false, suggested_service: null,
  };
}

// Placeholder score using the example rules in project_Plan.txt (service 0-30, budget 0-40, timeline 0-30).
// The real rules belong to the backend. Budget fit cannot be judged without published prices, so an
// answered budget gets half the points. This is a priority heuristic, not a conversion probability.
const TIMELINE_POINTS: Record<(typeof TIMELINE_CHOICES)[number], number> = {
  "As soon as possible": 30, "Within 30 days": 25, "Within 3 months": 15, "Within 6 months": 10, "Later, no rush": 5,
};
export function demoScore(q: EnquiryRequest["qualification"]): number {
  const service = q.service_category === "other" ? 10 : 30;
  const budget = q.budget ? 20 : 0;
  const timeline = q.timeline ? (TIMELINE_POINTS[q.timeline as keyof typeof TIMELINE_POINTS] ?? 10) : 0;
  return service + budget + timeline;
}

/** Send the enquiry to the n8n webhook, as the FastAPI backend does with backend/crm/client.py. */
export async function demoEnquiry(e: EnquiryRequest): Promise<{ status: number; body: EnquiryResponse }> {
  const url = process.env.N8N_WEBHOOK_URL;
  const token = process.env.WEBHOOK_TOKEN;
  const answer = (status: number, body: Partial<EnquiryResponse> & Pick<EnquiryResponse, "status">) => ({
    status,
    body: { submission_id: e.submission_id, crm_id: null, verified: false, retryable: false, errors: [], ...body },
  });
  if (!url || !token) {
    return answer(500, { status: "crm_not_configured", errors: ["Demo mode needs N8N_WEBHOOK_URL and WEBHOOK_TOKEN."] });
  }
  const payload = {
    submission_id: e.submission_id,
    conversation_id: e.conversation_id,
    contact: e.contact,
    qualification: e.qualification,
    lead_score: demoScore(e.qualification),
    consent: e.consent,
    conversation_summary: `Asked about ${e.qualification.service_interest} in the 7didan chat (demo mode).`,
  };
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-7didan-Token": token },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(60_000),
      cache: "no-store",
    });
    const data = (await res.json().catch(() => null)) as EnquiryResponse | null;
    if (!data || typeof data.status !== "string") return answer(502, { status: "bad_response", retryable: true });
    return { status: res.status, body: data };
  } catch {
    return answer(503, { status: "crm_unavailable", retryable: true, errors: ["The automation service did not answer."] });
  }
}
