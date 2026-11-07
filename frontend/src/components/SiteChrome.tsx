import Link from "next/link";
import { Logo } from "./ui";

export function Disclaimer({ className = "" }: { className?: string }) {
  return (
    <p className={className}>
      Independent academic prototype (Group 10, Webmarketing &amp; CRM) built on publicly available Orange Maroc
      Business information. Not affiliated with or endorsed by Orange Maroc. Demonstration data is synthetic.
    </p>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur-md">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 sm:px-10">
        <Link href="/" aria-label="7didan home" className="group flex items-center gap-3">
          <Logo />
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.22em] text-ash transition-colors group-hover:text-ink sm:inline-block">
            / Group 10
          </span>
        </Link>
        <nav className="flex items-center gap-3 sm:gap-6">
          <a
            href="#film"
            className="t-label hidden text-ink-soft transition-colors hover:text-ink md:inline-block"
          >
            Launch Film
          </a>
          <a
            href="#architecture"
            className="t-label hidden text-ink-soft transition-colors hover:text-ink md:inline-block"
          >
            System
          </a>
          <a
            href="#services"
            className="t-label hidden text-ink-soft transition-colors hover:text-ink sm:inline-block"
          >
            Catalogue
          </a>
          <Link
            href="/chat"
            className="inline-flex min-h-11 items-center gap-2 border border-ink bg-ink px-5 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-white transition-all duration-200 hover:border-tangerine hover:bg-tangerine active:scale-[0.97]"
          >
            <span>Query 7didan</span>
            <span aria-hidden="true">→</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line bg-canvas-subtle py-16 text-ink-soft">
      <div className="mx-auto flex max-w-7xl flex-col gap-10 px-6 sm:px-10 md:flex-row md:items-start md:justify-between">
        <div className="max-w-md space-y-4">
          <Logo />
          <p className="font-display text-lg text-ink font-semibold">
            Smart answers. Three questions. Zero retyping.
          </p>
          <p className="font-mono text-xs uppercase tracking-wider text-ash">
            Group 10 · Yassir Hamri · Amal · Amine
          </p>
        </div>
        <div className="max-w-lg space-y-3">
          <p className="t-label text-ink">Governance &amp; Context</p>
          <Disclaimer className="text-xs leading-relaxed text-ash" />
        </div>
      </div>
    </footer>
  );
}
