// Small shared building blocks: buttons, form fields, alerts, the 7didan mark.
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
export { cx };

export function Spinner({ className = "size-4" }: { className?: string }) {
  return (
    <svg className={cx("animate-spin", className)} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
};
export function Button({ variant = "primary", loading = false, className, children, disabled, type = "button", ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        "inline-flex min-h-11 items-center justify-center gap-2 px-5 font-mono text-[11px] font-medium uppercase tracking-[0.18em]",
        "transition-[background-color,color,border-color,transform] duration-200 active:scale-[0.97]",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        variant === "primary" && "border border-tangerine bg-tangerine text-white hover:border-ink hover:bg-ink",
        variant === "secondary" && "border border-ink/30 bg-transparent text-ink hover:border-ink hover:bg-ink hover:text-white",
        variant === "ghost" && "text-ash hover:text-ink",
        className,
      )}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

type FieldProps = { id: string; label: string; hint?: ReactNode; error?: string; optional?: boolean; count?: [number, number]; children: ReactNode };
export function Field({ id, label, hint, error, optional, count, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="t-label text-ink">
          {label} {optional && <span className="text-ash normal-case tracking-normal">(optional)</span>}
        </label>
        {count && (
          <span className={cx("font-mono text-[11px] tabular-nums", count[0] > count[1] ? "text-danger" : "text-ash")} aria-hidden="true">
            {count[0]} / {count[1]}
          </span>
        )}
      </div>
      {children}
      {hint && !error && <p id={`${id}-hint`} className="text-xs text-ash">{hint}</p>}
      {error && <p id={`${id}-error`} className="text-xs font-medium text-danger" role="alert">{error}</p>}
    </div>
  );
}

// Underline inputs for light mode
const inputClass = (error?: string) =>
  cx(
    "w-full border-0 border-b bg-transparent px-0 py-2.5 text-[16px] text-ink placeholder:text-ash/60 transition-colors",
    "focus:border-tangerine focus:outline-none disabled:text-ash disabled:opacity-60",
    error ? "border-danger" : "border-ink/20 hover:border-ink/50",
  );
const describedBy = (id: string, error?: string, hint?: boolean) =>
  [error ? `${id}-error` : null, hint && !error ? `${id}-hint` : null].filter(Boolean).join(" ") || undefined;

export function TextInput({ id, error, hasHint, ...rest }: InputHTMLAttributes<HTMLInputElement> & { id: string; error?: string; hasHint?: boolean }) {
  return <input id={id} aria-invalid={!!error || undefined} aria-describedby={describedBy(id, error, hasHint)} className={inputClass(error)} {...rest} />;
}
export function TextArea({ id, error, hasHint, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement> & { id: string; error?: string; hasHint?: boolean }) {
  return <textarea id={id} aria-invalid={!!error || undefined} aria-describedby={describedBy(id, error, hasHint)} className={cx(inputClass(error), "min-h-20 resize-y")} {...rest} />;
}

export function Alert({ tone, title, children, action }: { tone: "error" | "warning" | "info" | "success"; title: string; children?: ReactNode; action?: ReactNode }) {
  const bar = { error: "bg-danger", warning: "bg-sun", info: "bg-ash", success: "bg-success" }[tone];
  return (
    <div role={tone === "error" || tone === "warning" ? "alert" : "status"} className="relative overflow-hidden border border-line bg-canvas-card px-5 py-4 text-sm shadow-sm">
      <span className={cx("absolute inset-y-0 left-0 w-[3px]", bar)} aria-hidden="true" />
      <p className="font-display text-[15px] font-semibold text-ink">{title}</p>
      {children && <div className="mt-1 text-ink-soft">{children}</div>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/** The 7didan mark */
export function Mark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="-0.56 -0.7 1.3 1.5" className={className} aria-hidden="true">
      <path
        d="M-0.16 -0.5 L0.16 -0.5 Q0.5 -0.5 0.5 -0.16 L0.5 0.16 Q0.5 0.5 0.16 0.5 L-0.1 0.5 L-0.44 0.76 Q-0.5 0.6 -0.5 0.347 L-0.5 -0.16 Q-0.5 -0.5 -0.16 -0.5 Z"
        fill="#ff6b1a"
      />
      <path d="M-0.25 -0.3 L0.27 -0.3 L0.27 -0.17 L0.03 0.31 L-0.13 0.31 L0.1 -0.17 L-0.25 -0.17 Z" fill="#ffffff" />
      <path
        d="M0.47 -0.67 L0.509 -0.509 L0.67 -0.47 L0.509 -0.431 L0.47 -0.27 L0.431 -0.431 L0.27 -0.47 L0.431 -0.509 Z"
        fill="#ffc83d"
      />
    </svg>
  );
}

export function Logo({ className }: { className?: string; light?: boolean }) {
  return (
    <span className={cx("inline-flex items-center gap-2.5 font-display text-xl font-bold tracking-[-0.03em] text-ink", className)}>
      <Mark className="size-7" />
      <span>7didan</span>
    </span>
  );
}
