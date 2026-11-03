import { RiskLevel } from "../types";

/** Semantic colour roles. The actual values live as CSS variables in index.css. */
export type Tone = "brand" | "iris" | "ok" | "warn" | "danger" | "bloom" | "neutral";

const TONE_VAR: Record<Tone, string> = {
  brand: "var(--c-brand)",
  iris: "var(--c-iris)",
  ok: "var(--c-ok)",
  warn: "var(--c-warn)",
  danger: "var(--c-danger)",
  bloom: "var(--c-bloom)",
  neutral: "var(--c-subtle)",
};

export const TONE_TEXT: Record<Tone, string> = {
  brand: "text-brand",
  iris: "text-iris",
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
  bloom: "text-bloom",
  neutral: "text-muted",
};

/** Tinted background + readable foreground, used for chips, icon tiles, badges. */
export const TONE_CHIP: Record<Tone, string> = {
  brand: "bg-brand-soft text-brand-ink",
  iris: "bg-iris-soft text-iris",
  ok: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  danger: "bg-danger-soft text-danger",
  bloom: "bg-bloom-soft text-bloom",
  neutral: "bg-raised text-muted",
};

export function toneVar(tone: Tone) {
  return `rgb(${TONE_VAR[tone]})`;
}

/** Same colour with an alpha channel, e.g. for gradient fills. */
export function toneVarAlpha(tone: Tone, alpha: number) {
  return `rgb(${TONE_VAR[tone]} / ${alpha})`;
}

export function riskTone(level: RiskLevel): Tone {
  if (level === "red") return "danger";
  if (level === "yellow") return "warn";
  return "ok";
}

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}
