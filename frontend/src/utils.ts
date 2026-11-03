/** Local calendar date as YYYY-MM-DD (toISOString would shift across midnight). */
export function isoOf(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayIso() {
  return isoOf(new Date());
}

export function formatShortDate(isoDate: string, locale: string) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString(locale, { day: "2-digit", month: "2-digit" });
}

export function formatWeekday(isoDate: string, locale: string) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString(locale, { weekday: "short" });
}

export function formatLongDate(isoDate: string, locale: string) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" });
}

export function formatDateTime(value: string | null | undefined, locale: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}

/** Numeric value with a fallback - API metrics are all optional. */
export function num(value: number | null | undefined, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

/** Optional metric rendered for display; missing values show as an en dash. */
export function metric(value: number | null | undefined, suffix = ""): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value}${suffix}` : "–";
}

export function formatSleepHours(hours: number | null | undefined) {
  return typeof hours === "number" && Number.isFinite(hours) ? hours.toFixed(1) : "–";
}

export function mapPositionLabel(position: string | null | undefined, t: Record<string, string>) {
  if (!position) return "-";
  const map: Record<string, string> = {
    setter: t.posSetter,
    outside_hitter: t.posOutsideHitter,
    opposite: t.posOpposite,
    middle_blocker: t.posMiddleBlocker,
    libero: t.posLibero,
  };
  return map[position] ?? position;
}

export function mapSessionTypeLabel(value: string | null | undefined, t: Record<string, string>) {
  if (!value) return "-";
  const map: Record<string, string> = {
    team: t.sessionTypeTeam,
    strength: t.sessionTypeStrength,
    technical: t.sessionTypeTechnical,
    recovery: t.sessionTypeRecovery,
  };
  return map[value] ?? value;
}

export function mapParticipationLabel(value: string | null | undefined, t: Record<string, string>) {
  if (!value) return "-";
  const map: Record<string, string> = {
    full: t.participationFull,
    modified: t.participationModified,
    individual: t.participationIndividual,
    rest: t.participationRest,
  };
  return map[value] ?? value;
}

export function mapPhaseLabel(value: string | null | undefined, t: Record<string, string>) {
  if (!value) return "-";
  const map: Record<string, string> = {
    menstruation: t.phaseMenstruation,
    follicular: t.phaseFollicular,
    ovulation: t.phaseOvulation,
    luteal: t.phaseLuteal,
  };
  return map[value] ?? value;
}

export function greetingKey(date = new Date()) {
  const hour = date.getHours();
  if (hour < 11) return "greetingMorning";
  if (hour >= 18) return "greetingEvening";
  return "greetingDay";
}

export function firstName(name: string) {
  return name.split(/\s+/)[0] ?? name;
}

/**
 * Consecutive days with an entry, counted back from today (a missing entry for
 * today is fine as long as yesterday is covered - the streak is still alive).
 */
export function computeStreak(dates: string[]): number {
  const unique = new Set(dates);
  if (unique.size === 0) return 0;

  const cursor = new Date(`${todayIso()}T00:00:00`);
  if (!unique.has(todayIso())) {
    cursor.setDate(cursor.getDate() - 1);
    if (!unique.has(isoOf(cursor))) return 0;
  }

  let streak = 0;
  for (;;) {
    if (!unique.has(isoOf(cursor))) break;
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}
