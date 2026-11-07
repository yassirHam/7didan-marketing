import type { Source } from "@/lib/contract";
import type { Message } from "@/hooks/useConversation";
import { cx, Mark } from "../ui";

/** Plain text only. Lines starting with "- " or "• " become structured bullet points. */
function AnswerText({ text }: { text: string }) {
  const blocks: { list: boolean; lines: string[] }[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) continue;
    const item = /^\s*(?:[-•*]|\d+[.)])\s+/.exec(line);
    const last = blocks[blocks.length - 1];
    const content = item ? line.slice(item[0].length) : line;
    if (last && last.list === !!item) last.lines.push(content);
    else blocks.push({ list: !!item, lines: [content] });
  }
  return (
    <div className="space-y-2 text-[15px] leading-relaxed">
      {blocks.map((b, i) =>
        b.list ? (
          <ul key={i} className="list-disc space-y-1 pl-5 marker:text-tangerine">
            {b.lines.map((l, j) => (
              <li key={j} className="text-ink-soft">{l}</li>
            ))}
          </ul>
        ) : (
          b.lines.map((l, j) => (
            <p key={`${i}-${j}`} className="text-ink">{l}</p>
          ))
        )
      )}
    </div>
  );
}

function SourceList({ sources }: { sources: Source[] }) {
  return (
    <div className="mt-4 border-t border-line pt-3">
      <p className="t-label text-ash">VERIFIED CITATIONS</p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {sources.map((s, i) => {
          const label = [s.title, s.section].filter(Boolean).join(" · ");
          const date = s.retrieved_at
            ? new Date(s.retrieved_at).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })
            : null;
          const content = (
            <>
              <span className="font-mono text-tangerine">▤</span>
              <span className="text-ink">{label}</span>
              {date && <span className="text-ash">({date})</span>}
            </>
          );
          const pillCls =
            "inline-flex items-center gap-2 rounded border border-line bg-canvas-subtle px-3 py-1 font-mono text-[11px] text-ink transition-colors hover:border-tangerine";

          return (
            <li key={i}>
              {s.url ? (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className={pillCls}
                >
                  {content}
                  <span className="text-ash">↗</span>
                </a>
              ) : (
                <span className={pillCls}>{content}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function MessageBubble({
  message,
  onQualify,
}: {
  message: Message;
  onQualify?: () => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end animate-rise">
        <div className="max-w-[85%] rounded-2xl border border-line bg-canvas-card px-5 py-3 text-[15px] text-ink shadow-sm sm:max-w-[75%]">
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
        </div>
      </div>
    );
  }

  const abstained = message.status === "abstained";

  return (
    <div className="flex items-start gap-3.5 animate-rise">
      <div className="mt-1 shrink-0">
        <Mark className="size-7" />
      </div>

      <div className="max-w-[90%] sm:max-w-[82%] space-y-3">
        <div
          className={cx(
            "relative rounded-2xl border p-5 shadow-sm",
            abstained
              ? "border-sun bg-[#fffbee]"
              : "border-line bg-canvas-card"
          )}
        >
          {abstained && (
            <div className="mb-3 inline-flex items-center gap-1.5 rounded border border-sun bg-sun/15 px-2.5 py-0.5">
              <span className="size-1.5 rounded-full bg-tangerine" />
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-ink">
                Catalogue Abstention · Out of Scope
              </span>
            </div>
          )}

          <AnswerText text={message.text} />

          {message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} />
          )}
        </div>

        {onQualify && (
          <button
            type="button"
            onClick={onQualify}
            className="inline-flex min-h-11 items-center gap-2 rounded-full border border-tangerine bg-tangerine/10 px-5 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-tangerine transition-all hover:bg-tangerine hover:text-white active:scale-[0.97]"
          >
            <span>Proceed to 3-Question Advisor Qualification</span>
            <span aria-hidden="true">→</span>
          </button>
        )}
      </div>
    </div>
  );
}

export function Typing() {
  return (
    <div className="flex items-center gap-3" role="status" aria-label="7didan is reasoning">
      <Mark className="size-7 shrink-0" />
      <div className="flex items-center gap-1.5 rounded-xl border border-line bg-canvas-card px-4 py-3 shadow-sm">
        <span className="font-mono text-xs text-ash">Grounding answer</span>
        <span className="flex gap-1 pl-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="size-1.5 rounded-full bg-tangerine animate-blink"
              style={{ animationDelay: `${i * 0.18}s` }}
            />
          ))}
        </span>
      </div>
    </div>
  );
}
