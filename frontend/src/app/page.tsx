import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { SERVICE_CATEGORIES } from "@/lib/contract";
import { Logo3D } from "@/components/Logo3D";
import { SmoothScroll, Reveal, SplitTitle } from "@/components/Motion";

const QUESTIONS: Record<string, string> = {
  connectivity: "Which internet option fits a 20-person office?",
  mobile: "What mobile plans are there for a sales team?",
  cloud: "Can we host our ERP in the cloud?",
  cybersecurity: "How can we protect our company network?",
  collaboration: "What do you offer for video meetings between two sites?",
  other: "I'm not sure which service I need. Can you help?",
};

const SYSTEM_PILLARS = [
  {
    num: "01",
    label: "CITATIONS",
    title: "Grounding in Official Documentation",
    desc: "Every answer quotes verbatim business catalogue chapters. If a pricing tier or custom SLA isn't published, 7didan explicitly abstains with zero hallucinations.",
    code: "VERIFIED_SOURCE // RAG_GROUNDING",
  },
  {
    num: "02",
    label: "QUALIFICATION",
    title: "Deterministic 3-Question Stepper",
    desc: "Guides enterprise customers through Need, Budget, and Deployment Timeline. Unknown constraints are gracefully preserved rather than hallucinated.",
    code: "STATE_MACHINE // STRUCTURED_JSON",
  },
  {
    num: "03",
    label: "CRM AUTOMATION",
    title: "Instant n8n → Odoo 18 Pipeline",
    desc: "Verified leads auto-sync with Odoo CRM opportunities under a dedicated 7didan tab with automated duplicate suppression and consent verification.",
    code: "WEBHOOK // IDEMPOTENT_WRITE",
  },
];

export default function Home() {
  return (
    <SmoothScroll>
      <SiteHeader />
      <main className="relative flex flex-col bg-canvas text-ink">
        {/* ── HERO SECTION: Giant Space Grotesk + Outline Type + Real-time 3D Logo ── */}
        <section className="relative flex min-h-[90dvh] flex-col justify-between overflow-hidden border-b border-line px-6 pt-12 pb-14 sm:px-10 md:pt-16 md:pb-20">
          <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col justify-between">
            {/* Top metadata strip */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-6">
              <div className="flex items-center gap-3">
                <span className="inline-block size-2 rounded-full bg-tangerine animate-pulse" />
                <p className="t-label text-ink">B2B CATALOGUE INTELLIGENCE · ORANGE MAROC</p>
              </div>
              <p className="t-label text-ash">ACADEMIC PROTOTYPE // GROUP 10</p>
            </div>

            {/* Giant Title Layout & 3D Logo */}
            <div className="my-auto grid items-center gap-10 py-10 lg:grid-cols-[1.25fr_0.75fr]">
              <div className="space-y-6">
                <h1 className="t-giant font-display text-ink">
                  <span className="block">EVERY</span>
                  <span className="block outline-text">BUSINESS</span>
                  <span className="block text-tangerine">ASKS.</span>
                </h1>

                <p className="max-w-xl text-lg leading-relaxed text-ink-soft md:text-xl">
                  Moroccan Darija, French &amp; English conversational assistant for enterprise catalogues.
                  Grounded answers, 3-question qualification, and verified Odoo CRM handoff.
                </p>

                <div className="flex flex-wrap items-center gap-4 pt-4">
                  <Link
                    href="/chat"
                    className="pill-cta bg-tangerine text-white hover:bg-ink shadow-sm"
                  >
                    <span>Launch Assistant</span>
                    <span className="grid size-10 place-items-center rounded-full bg-white text-ink transition-transform group-hover:translate-x-1">
                      →
                    </span>
                  </Link>

                  <a
                    href="#architecture"
                    className="btn"
                  >
                    Explore Architecture
                  </a>
                </div>
              </div>

              {/* 3D Interactive WebGL Logo viewport */}
              <div className="relative flex items-center justify-center">
                <div className="absolute inset-0 -z-10 rounded-full bg-tangerine/10 blur-[80px]" />
                <Logo3D className="h-80 w-80 sm:h-96 sm:w-96" />
                <div className="absolute -bottom-2 right-4 rounded-full border border-line bg-canvas-card/90 px-4 py-1.5 shadow-sm backdrop-blur-md">
                  <p className="t-label text-ink">INTERACTIVE 3D · MOUSE ORBIT</p>
                </div>
              </div>
            </div>

            {/* Bottom ticker bar */}
            <div className="grid grid-cols-2 gap-4 border-t border-line pt-6 text-xs text-ash sm:grid-cols-4">
              <div>
                <span className="t-label block text-ink">01 / CHANNELS</span>
                <span className="mt-1 block text-ink-soft">Darija, French, English</span>
              </div>
              <div>
                <span className="t-label block text-ink">02 / GROUNDING</span>
                <span className="mt-1 block text-ink-soft">Cited official documentation</span>
              </div>
              <div>
                <span className="t-label block text-ink">03 / CRM ENGINE</span>
                <span className="mt-1 block text-ink-soft">Odoo 18 Enterprise stack</span>
              </div>
              <div>
                <span className="t-label block text-ink">04 / WORKFLOW</span>
                <span className="mt-1 block text-ink-soft">n8n 1.88 Orchestration</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── FILM SECTION: Embedded Launch Video with Light Sandstone Frame ── */}
        <section id="film" className="border-b border-line bg-canvas-subtle py-24 px-6 sm:px-10">
          <div className="mx-auto max-w-7xl">
            <Reveal className="mb-12 flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <p className="t-label text-tangerine">01 — LAUNCH FILM</p>
                <h2 className="t-h2 mt-2 text-ink">
                  <SplitTitle text="Engineered for production reality." />
                </h2>
              </div>
              <p className="max-w-md text-sm text-ink-soft">
                Watch the complete 22-second launch composition highlighting Moroccan Darija voice intake,
                real-time document retrieval, and instant Odoo CRM qualification.
              </p>
            </Reveal>

            {/* Cinematic Video Player Frame */}
            <Reveal delay={120} className="relative aspect-video overflow-hidden rounded-2xl border border-line bg-ink shadow-xl">
              <video
                src="/7didan-film.mp4"
                poster="/7didan-film.jpg"
                controls
                playsInline
                preload="metadata"
                className="h-full w-full object-cover"
              />
              <div className="pointer-events-none absolute bottom-4 left-4 rounded-md border border-white/20 bg-ink/80 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-white backdrop-blur-md">
                1080P · 30 FPS · STUDIO MASTER
              </div>
            </Reveal>
          </div>
        </section>

        {/* ── SYSTEM ARCHITECTURE: Sandstone Mono Card Grid ── */}
        <section id="architecture" className="border-b border-line bg-canvas py-28 px-6 sm:px-10">
          <div className="mx-auto max-w-7xl">
            <Reveal className="mb-16">
              <p className="t-label text-tangerine">02 — SYSTEM ARCHITECTURE</p>
              <h2 className="t-h2 mt-2 text-ink">
                <SplitTitle text="Three pillars of evidence-based qualification." />
              </h2>
            </Reveal>

            <div className="grid gap-6 md:grid-cols-3">
              {SYSTEM_PILLARS.map((p, idx) => (
                <Reveal
                  key={p.num}
                  delay={idx * 100}
                  className="flex flex-col justify-between rounded-xl border border-line bg-canvas-card p-8 shadow-sm transition-all hover:-translate-y-1 hover:border-tangerine/60 hover:shadow-md"
                >
                  <div className="space-y-6">
                    <div className="flex items-center justify-between border-b border-line pb-4">
                      <span className="font-mono text-sm font-bold text-tangerine">{p.num}</span>
                      <span className="t-label text-ash">{p.label}</span>
                    </div>
                    <h3 className="font-display text-2xl font-semibold text-ink">{p.title}</h3>
                    <p className="text-sm leading-relaxed text-ink-soft">{p.desc}</p>
                  </div>
                  <div className="mt-8 border-t border-line/60 pt-4">
                    <code className="font-mono text-[11px] text-ash">{p.code}</code>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── SERVICE TOPICS: Interactive Exploration Cards ── */}
        <section id="services" className="border-b border-line bg-canvas-subtle py-28 px-6 sm:px-10">
          <div className="mx-auto max-w-7xl">
            <Reveal className="mb-16 flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <p className="t-label text-tangerine">03 — SERVICE DIRECTORY</p>
                <h2 className="t-h2 mt-2 text-ink">
                  <SplitTitle text="Pick a service to inspect." />
                </h2>
              </div>
              <p className="max-w-md text-sm text-ink-soft">
                Each category pre-initializes the conversation context with verified catalogue references.
              </p>
            </Reveal>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {SERVICE_CATEGORIES.map((c, i) => (
                <Reveal key={c.value} delay={i * 60}>
                  <Link
                    href={{ pathname: "/chat", query: { q: QUESTIONS[c.value] } }}
                    className="group flex h-full flex-col justify-between rounded-xl border border-line bg-canvas-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:border-tangerine hover:shadow-md"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-ash">0{i + 1}</span>
                        <span className="font-mono text-xs text-tangerine opacity-0 transition-opacity group-hover:opacity-100">
                          QUERY →
                        </span>
                      </div>
                      <h3 className="mt-4 font-display text-xl font-bold text-ink group-hover:text-tangerine">
                        {c.label}
                      </h3>
                      <p className="mt-2 text-xs leading-relaxed text-ink-soft">{c.hint}</p>
                    </div>

                    <div className="mt-6 border-t border-line/50 pt-3">
                      <p className="line-clamp-1 font-mono text-[11px] text-ash group-hover:text-ink">
                        &quot;{QUESTIONS[c.value]}&quot;
                      </p>
                    </div>
                  </Link>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── CALL TO ACTION BANNER ── */}
        <section className="bg-canvas py-24 px-6 text-center sm:px-10">
          <Reveal className="mx-auto max-w-3xl space-y-8">
            <p className="t-label text-tangerine">OPEN SYSTEM CHANNEL</p>
            <h2 className="t-h2 text-ink">
              3ndek so2al? <br />
              <span className="outline-text">Swl 7didan.</span>
            </h2>
            <p className="text-base text-ink-soft">
              No personal information is collected up front. Test catalogue questions freely with zero pushy sales friction.
            </p>
            <div className="pt-4">
              <Link
                href="/chat"
                className="pill-cta bg-tangerine text-white hover:bg-ink shadow-sm"
              >
                <span>Launch Conversational Assistant</span>
                <span className="grid size-10 place-items-center rounded-full bg-white text-ink">
                  →
                </span>
              </Link>
            </div>
          </Reveal>
        </section>
      </main>
      <SiteFooter />
    </SmoothScroll>
  );
}
