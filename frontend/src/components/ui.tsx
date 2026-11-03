import {
  ButtonHTMLAttributes,
  CSSProperties,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  useEffect,
  useState,
} from "react";
import { IconCheck, IconX } from "./icons";
import { TONE_CHIP, TONE_TEXT, Tone, cx, toneVar } from "./theme";

/* ---------------------------------------------------------------- layout */

export function Card({
  children,
  className,
  padded = true,
  style,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
  style?: CSSProperties;
}) {
  return (
    <section className={cx("card", padded && "p-5 sm:p-6", className)} style={style}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  subtitle,
  icon,
  tone = "brand",
  action,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  tone?: Tone;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {icon && (
          <span
            className={cx("grid h-10 w-10 shrink-0 place-items-center rounded-xl", TONE_CHIP[tone])}
          >
            {icon}
          </span>
        )}
        <div>
          <h3 className="text-[17px] font-bold leading-tight text-ink">{title}</h3>
          {subtitle && <p className="mt-1 text-sm leading-snug text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function Chip({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <span className={cx("chip", TONE_CHIP[tone], className)}>{children}</span>;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <h2 className="text-sm font-bold uppercase tracking-[0.08em] text-subtle">{children}</h2>
      {action}
    </div>
  );
}

/* --------------------------------------------------------------- buttons */

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  icon?: ReactNode;
  block?: boolean;
  loading?: boolean;
};

export function Button({
  variant = "primary",
  icon,
  block,
  loading,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const base =
    variant === "primary"
      ? "btn-primary"
      : variant === "secondary"
        ? "btn-secondary"
        : variant === "danger"
          ? "btn bg-danger-soft text-danger hover:brightness-105"
          : "btn-ghost";
  return (
    <button
      className={cx(base, block && "w-full", className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cx(
        "h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
      aria-hidden="true"
    />
  );
}

export function IconButton({
  label,
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cx(
        "grid h-10 w-10 place-items-center rounded-xl border border-line bg-card text-muted transition hover:text-ink active:scale-95",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/* ---------------------------------------------------------------- inputs */

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cx("block", className)}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-subtle">{hint}</span>}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx("field-input", props.className)} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cx(
        "field-input appearance-none bg-[right_0.9rem_center] bg-no-repeat pr-10",
        props.className,
      )}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none' stroke='%23818ca6' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='M3 6l5 5 5-5'/%3E%3C/svg%3E\")",
        backgroundSize: "1rem",
        ...props.style,
      }}
    />
  );
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx("field-input resize-y", props.className)} />;
}

export function SliderField({
  label,
  value,
  onChange,
  min = 0,
  max = 10,
  step = 1,
  tone = "brand",
  suffix,
  lowLabel,
  highLabel,
  valueLabel,
}: {
  label: ReactNode;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  tone?: Tone;
  suffix?: string;
  lowLabel?: string;
  highLabel?: string;
  valueLabel?: string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  const color = toneVar(tone);
  return (
    <div className="select-none">
      <div className="flex items-baseline justify-between gap-3">
        <span className="field-label">{label}</span>
        <span className="font-display text-lg font-bold tabular-nums" style={{ color }}>
          {value}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        className="vs-range mt-1"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        style={
          {
            "--range-track": `linear-gradient(90deg, ${color} ${pct}%, rgb(var(--c-line)) ${pct}%)`,
            "--range-thumb": color,
          } as CSSProperties
        }
      />
      <div className="flex justify-between text-[11px] font-medium text-subtle">
        <span>{lowLabel}</span>
        <span className="text-muted">{valueLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  );
}

export function Stepper({
  label,
  value,
  onChange,
  min,
  max,
  suffix,
}: {
  label: ReactNode;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  suffix?: string;
}) {
  const clamp = (next: number) => Math.min(max, Math.max(min, next));
  return (
    <div>
      <span className="field-label">{label}</span>
      <div className="mt-1.5 flex items-center gap-2">
        <button
          type="button"
          aria-label="-"
          onClick={() => onChange(clamp(value - 1))}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-line bg-raised text-xl font-bold text-muted active:scale-95"
        >
          −
        </button>
        <div className="flex h-11 flex-1 items-center justify-center rounded-xl border border-line bg-raised font-display text-lg font-bold tabular-nums text-ink">
          {value}
          {suffix ? <span className="ml-1 text-sm font-medium text-subtle">{suffix}</span> : null}
        </div>
        <button
          type="button"
          aria-label="+"
          onClick={() => onChange(clamp(value + 1))}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-line bg-raised text-xl font-bold text-muted active:scale-95"
        >
          +
        </button>
      </div>
    </div>
  );
}

export type SegmentedOption<T extends string> = {
  value: T;
  label: string;
  icon?: ReactNode;
};

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  tone = "brand",
  className,
}: {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  tone?: Tone;
  className?: string;
}) {
  return (
    <div className={cx("flex flex-wrap gap-2 py-1", className)}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cx(
              "flex min-h-[42px] shrink-0 items-center gap-2 rounded-xl border px-3.5 text-sm font-semibold transition active:scale-[0.98]",
              active
                ? "border-transparent text-white shadow-glow"
                : "border-line bg-card text-muted hover:text-ink",
            )}
            style={
              active
                ? {
                    backgroundImage: `linear-gradient(120deg, ${toneVar(tone)}, rgb(var(--c-iris)))`,
                  }
                : undefined
            }
          >
            {option.icon}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function ToggleChip({
  label,
  active,
  onClick,
  tone = "brand",
  icon,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  tone?: Tone;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "flex min-h-[42px] items-center gap-2 rounded-xl border px-3.5 text-sm font-semibold transition active:scale-[0.98]",
        active ? cx(TONE_CHIP[tone], "border-transparent") : "border-line bg-card text-muted",
      )}
    >
      {icon}
      {label}
      {active && <IconCheck size={16} />}
    </button>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  tone = "brand",
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: ReactNode;
  description?: ReactNode;
  tone?: Tone;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-4 rounded-xl border border-line bg-raised px-4 py-3 text-left transition active:scale-[0.99]"
    >
      <span>
        <span className="block text-[15px] font-semibold text-ink">{label}</span>
        {description && <span className="mt-0.5 block text-xs text-muted">{description}</span>}
      </span>
      <span
        className={cx(
          "relative h-7 w-12 shrink-0 rounded-pill transition",
          checked ? "" : "bg-line",
        )}
        style={checked ? { backgroundColor: toneVar(tone) } : undefined}
      >
        <span
          className={cx(
            "absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all",
            checked ? "left-6" : "left-1",
          )}
        />
      </span>
    </button>
  );
}

/* ------------------------------------------------------------- feedback */

export function StatTile({
  label,
  value,
  hint,
  tone = "brand",
  icon,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-line bg-raised p-3.5">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-subtle">
        {icon && <span className={TONE_TEXT[tone]}>{icon}</span>}
        {label}
      </div>
      <p className="mt-1.5 font-display text-2xl font-extrabold leading-none text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-line bg-raised px-6 py-8 text-center">
      {icon && (
        <span className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-soft text-brand">
          {icon}
        </span>
      )}
      <p className="font-display text-base font-bold text-ink">{title}</p>
      {description && <p className="mt-1 max-w-xs text-sm text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} />;
}

export type ToastKind = "success" | "error" | "info";

export function Toast({
  message,
  kind,
  onClose,
}: {
  message: string;
  kind: ToastKind;
  onClose: () => void;
}) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const hide = window.setTimeout(() => setLeaving(true), 3200);
    const remove = window.setTimeout(onClose, 3600);
    return () => {
      window.clearTimeout(hide);
      window.clearTimeout(remove);
    };
  }, [onClose]);

  const tone: Tone = kind === "success" ? "ok" : kind === "error" ? "danger" : "brand";
  return (
    <div
      role="status"
      className={cx(
        "pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl border border-line bg-card p-3.5 shadow-lift transition",
        leaving ? "translate-y-2 opacity-0" : "animate-fadeUp",
      )}
    >
      <span
        className={cx(
          "mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full",
          TONE_CHIP[tone],
        )}
      >
        {kind === "success" ? <IconCheck size={14} /> : <IconX size={14} />}
      </span>
      <p className="flex-1 text-sm font-medium leading-snug text-ink">{message}</p>
      <button
        type="button"
        onClick={onClose}
        className="shrink-0 rounded-lg p-1 text-subtle hover:text-ink"
        aria-label="OK"
      >
        <IconX size={16} />
      </button>
    </div>
  );
}
