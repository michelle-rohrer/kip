import { FormEvent, ReactNode, useState } from "react";
import {
  CycleEntry,
  CyclePhase,
  InjuryEntry,
  Prediction,
  PrivacyConsent,
  TrainingEntry,
  DeviceSuggestions,
  User,
  WearableDaily,
  WellnessEntry,
} from "../types";
import {
  computeStreak,
  firstName,
  formatLongDate,
  formatShortDate,
  formatSleepHours,
  formatWeekday,
  greetingKey,
  mapParticipationLabel,
  mapPhaseLabel,
  mapSessionTypeLabel,
  metric,
  num,
  todayIso,
} from "../utils";
import { ChartLegend, RiskGauge, Series, TrendChart } from "./charts";
import {
  IconAlert,
  IconCalendar,
  IconCheck,
  IconClock,
  IconDrop,
  IconDumbbell,
  IconFlame,
  IconHeart,
  IconMoonSleep,
  IconPlus,
  IconPulseAlert,
  IconShield,
  IconSparkle,
  IconTrend,
  IconWatch,
} from "./icons";
import {
  Button,
  Card,
  CardHeader,
  Chip,
  EmptyState,
  Field,
  Segmented,
  SliderField,
  StatTile,
  Stepper,
  Switch,
  TextInput,
  Textarea,
  ToggleChip,
} from "./ui";
import { TONE_CHIP, Tone, cx } from "./theme";

export type WellnessForm = {
  date: string;
  sleep_hours: number;
  sleep_quality: number;
  muscle_soreness: number;
  mental_energy: number;
  stress_level: number;
  motivation: number;
  rpe_previous_day: number;
  free_text: string;
};

export type CycleForm = {
  date: string;
  cycle_day: number;
  phase: CyclePhase;
  cycle_length: number;
  pms_score: number;
  cramps: boolean;
  migraine: boolean;
  fatigue: boolean;
  contraception_type: string;
  notes: string;
};

export type TrainingForm = {
  date: string;
  duration_min: number;
  intensity: number;
  session_rpe: number;
  session_type: "team" | "strength" | "technical" | "recovery";
  participation_status: "full" | "modified" | "individual" | "rest";
};

export type InjuryForm = {
  date: string;
  body_location: string;
  pain_intensity: number;
  is_chronic: boolean;
  medical_attention: boolean;
  time_loss_days: number;
  description: string;
};

export type TrendPoint = {
  date: string;
  score: number;
  sleep_quality: number;
  mental_energy: number;
  motivation: number;
};

type T = Record<string, string>;

function riskCopy(level: Prediction["risk_level"], t: T) {
  if (level === "red") return { label: t.riskHigh, hint: t.riskHighHint };
  if (level === "yellow") return { label: t.riskMedium, hint: t.riskMediumHint };
  return { label: t.riskLow, hint: t.riskLowHint };
}

function HistoryRow({
  icon,
  tone = "neutral",
  title,
  subtitle,
  meta,
}: {
  icon: ReactNode;
  tone?: Tone;
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-line bg-raised px-3.5 py-3">
      <span className={cx("grid h-9 w-9 shrink-0 place-items-center rounded-xl", TONE_CHIP[tone])}>
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-semibold leading-snug text-ink">{title}</p>
        {subtitle && <p className="text-xs leading-snug text-muted">{subtitle}</p>}
      </div>
      {meta && <span className="shrink-0 text-xs font-semibold text-subtle">{meta}</span>}
    </li>
  );
}

/**
 * Values a device measured, offered for the form the player is looking at.
 * Nothing is stored until she presses the button - the device measures, she
 * decides.
 */
function SuggestionBanner({ t, parts, onApply }: { t: T; parts: string[]; onApply: () => void }) {
  if (parts.length === 0) return null;
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ok/40 bg-ok-soft/60 p-4">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-sm font-bold text-ink">
          <IconWatch size={16} className="text-ok" />
          {t.suggestionTitle}
        </p>
        <p className="mt-0.5 text-xs leading-snug text-muted">{parts.join(" · ")}</p>
      </div>
      <Button type="button" variant="secondary" icon={<IconCheck size={16} />} onClick={onApply}>
        {t.applySuggestion}
      </Button>
    </div>
  );
}

/* ============================================================ dashboard */

export function WearableSummary({
  t,
  locale,
  entry,
  onOpenDevices,
}: {
  t: T;
  locale: string;
  entry: WearableDaily;
  onOpenDevices: () => void;
}) {
  const tiles = [
    {
      key: "sleep",
      label: t.sleep,
      value: entry.sleep_hours === null ? "–" : `${entry.sleep_hours.toFixed(1)} h`,
      tone: "brand" as Tone,
      icon: <IconMoonSleep size={14} />,
    },
    {
      key: "readiness",
      label: t.readiness,
      value: entry.readiness_score === null ? "–" : `${entry.readiness_score}`,
      tone: "ok" as Tone,
      icon: <IconHeart size={14} />,
    },
    {
      key: "hrv",
      label: "HRV",
      value: entry.hrv_ms === null ? "–" : `${Math.round(entry.hrv_ms)} ms`,
      tone: "iris" as Tone,
      icon: <IconTrend size={14} />,
    },
    {
      key: "rhr",
      label: t.restingHr,
      value: entry.resting_hr === null ? "–" : `${Math.round(entry.resting_hr)}`,
      tone: "warn" as Tone,
      icon: <IconPulseAlert size={14} />,
    },
  ];

  return (
    <Card className="animate-fadeUp">
      <CardHeader
        title={t.deviceToday}
        subtitle={`${t.measuredOn} ${formatShortDate(entry.date, locale)}`}
        icon={<IconWatch size={20} />}
        tone="ok"
        action={
          <button
            type="button"
            onClick={onOpenDevices}
            className="shrink-0 text-xs font-semibold text-brand underline"
          >
            {t.devicesTitle}
          </button>
        }
      />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map((tile) => (
          <StatTile
            key={tile.key}
            label={tile.label}
            value={tile.value}
            tone={tile.tone}
            icon={tile.icon}
          />
        ))}
      </div>
    </Card>
  );
}

export function PlayerDashboard({
  t,
  locale,
  user,
  prediction,
  wellness,
  cycle,
  training,
  injuries,
  trend,
  wearable,
  onNavigate,
}: {
  t: T;
  locale: string;
  user: User;
  prediction: Prediction | null;
  wellness: WellnessEntry[];
  cycle: CycleEntry[];
  training: TrainingEntry[];
  injuries: InjuryEntry[];
  trend: TrendPoint[];
  wearable: WearableDaily | null;
  onNavigate: (tab: "wellness" | "cycle" | "training" | "injury" | "devices") => void;
}) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const today = todayIso();
  const streak = computeStreak(wellness.map((entry) => entry.date));
  const activePoint = activeIndex === null ? null : (trend[activeIndex] ?? null);

  const quickActions = [
    {
      key: "wellness" as const,
      label: t.wellness,
      icon: <IconSparkle size={22} />,
      tone: "brand" as Tone,
      done: wellness.some((entry) => entry.date === today),
    },
    {
      key: "training" as const,
      label: t.trainingLoad,
      icon: <IconDumbbell size={22} />,
      tone: "iris" as Tone,
      done: training.some((entry) => entry.date === today),
    },
    {
      key: "cycle" as const,
      label: t.cycle,
      icon: <IconDrop size={22} />,
      tone: "bloom" as Tone,
      done: cycle.some((entry) => entry.date === today),
    },
    {
      key: "injury" as const,
      label: t.injuryTracking,
      icon: <IconPulseAlert size={22} />,
      tone: "warn" as Tone,
      done: injuries.some((entry) => entry.date === today),
    },
  ];

  const series: Series[] = [
    { key: "score", label: t.avgBlue, values: trend.map((p) => p.score), tone: "brand" },
    {
      key: "sleep",
      label: t.greenSleep,
      values: trend.map((p) => p.sleep_quality),
      tone: "ok",
      area: false,
    },
    {
      key: "mental",
      label: t.purpleMental,
      values: trend.map((p) => p.mental_energy),
      tone: "iris",
      area: false,
    },
    {
      key: "motivation",
      label: t.orangeMotivation,
      values: trend.map((p) => p.motivation),
      tone: "warn",
      area: false,
    },
  ];

  const latestWellness = wellness[0];
  const latestTraining = training[0];
  const latestCycle = cycle[0];

  return (
    <>
      <header className="animate-fadeUp">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-muted">{formatLongDate(today, locale)}</p>
            <h1 className="mt-0.5 font-display text-[26px] font-extrabold leading-tight text-ink sm:text-3xl">
              {t[greetingKey()]}, {firstName(user.name)}
            </h1>
          </div>
          <div
            className={cx(
              "flex items-center gap-2.5 rounded-card border border-line bg-card px-4 py-2.5 shadow-card",
            )}
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-warn-soft text-warn">
              <IconFlame size={20} />
            </span>
            <div>
              <p className="font-display text-lg font-extrabold leading-none text-ink">
                {streak}{" "}
                <span className="text-xs font-semibold text-muted">
                  {streak === 1 ? t.streakDay : t.streakDays}
                </span>
              </p>
              <p className="text-[11px] text-subtle">{streak > 0 ? t.streakKeep : t.streakStart}</p>
            </div>
          </div>
        </div>
      </header>

      <section className="grid gap-5 lg:grid-cols-5">
        <Card className="animate-fadeUp lg:col-span-2">
          <CardHeader title={t.currentRiskScore} icon={<IconTrend size={20} />} tone="brand" />
          {prediction ? (
            <RiskGauge
              score={prediction.risk_score}
              level={prediction.risk_level}
              label={riskCopy(prediction.risk_level, t).label}
              caption={riskCopy(prediction.risk_level, t).hint}
            />
          ) : (
            <EmptyState
              icon={<IconTrend size={22} />}
              title={t.noPrediction}
              description={t.noDataYetHint}
              action={
                <Button icon={<IconPlus size={18} />} onClick={() => onNavigate("wellness")}>
                  {t.startNow}
                </Button>
              }
            />
          )}
        </Card>

        <Card className="animate-fadeUp lg:col-span-3">
          <CardHeader
            title={t.quickActions}
            subtitle={t.tapToEdit}
            icon={<IconPlus size={20} />}
            tone="iris"
          />
          <div className="grid grid-cols-2 gap-3">
            {quickActions.map((action) => (
              <button
                key={action.key}
                type="button"
                onClick={() => onNavigate(action.key)}
                className="group flex flex-col items-start gap-2 rounded-xl border border-line bg-raised p-4 text-left transition hover:border-brand/40 hover:shadow-card active:scale-[0.98]"
              >
                <span
                  className={cx(
                    "grid h-11 w-11 place-items-center rounded-xl",
                    action.tone === "brand" && "bg-brand-soft text-brand-ink",
                    action.tone === "iris" && "bg-iris-soft text-iris",
                    action.tone === "bloom" && "bg-bloom-soft text-bloom",
                    action.tone === "warn" && "bg-warn-soft text-warn",
                  )}
                >
                  {action.icon}
                </span>
                <span className="text-[15px] font-bold leading-tight text-ink">{action.label}</span>
                <span
                  className={cx("chip", action.done ? "bg-ok-soft text-ok" : "bg-card text-subtle")}
                >
                  {action.done ? <IconCheck size={13} /> : <IconPlus size={13} />}
                  {action.done ? t.todayDone : t.todayOpen}
                </span>
              </button>
            ))}
          </div>
        </Card>
      </section>

      {wearable && (
        <WearableSummary
          t={t}
          locale={locale}
          entry={wearable}
          onOpenDevices={() => onNavigate("devices")}
        />
      )}

      <Card className="animate-fadeUp">
        <CardHeader
          title={t.wellnessTrend}
          subtitle={t.trendDescription}
          icon={<IconSparkle size={20} />}
          tone="brand"
          action={
            <Chip tone="neutral" className="hidden whitespace-nowrap sm:inline-flex">
              {t.lastSevenDays}
            </Chip>
          }
        />
        {trend.length > 1 ? (
          <>
            <TrendChart
              series={series}
              labels={trend.map((point) => formatWeekday(point.date, locale))}
              activeIndex={activeIndex}
              onSelect={(index) => setActiveIndex(index === activeIndex ? null : index)}
            />
            <ChartLegend series={series} />
            {activePoint ? (
              <div className="mt-4 rounded-xl border border-brand/30 bg-brand-soft/60 p-4">
                <p className="text-sm font-bold text-ink">
                  {t.detailsFor} {formatShortDate(activePoint.date, locale)}
                </p>
                <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label={t.avg} value={activePoint.score} tone="brand" />
                  <StatTile label={t.greenSleep} value={activePoint.sleep_quality} tone="ok" />
                  <StatTile label={t.purpleMental} value={activePoint.mental_energy} tone="iris" />
                  <StatTile label={t.orangeMotivation} value={activePoint.motivation} tone="warn" />
                </div>
              </div>
            ) : (
              <p className="mt-3 text-xs text-subtle">{t.clickPointsForDayDetails}</p>
            )}
          </>
        ) : (
          <EmptyState
            icon={<IconSparkle size={22} />}
            title={t.notEnoughTrendData}
            description={t.noDataYetHint}
            action={
              <Button icon={<IconPlus size={18} />} onClick={() => onNavigate("wellness")}>
                {t.wellnessCheck}
              </Button>
            }
          />
        )}
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.latestEntries} icon={<IconClock size={20} />} tone="neutral" />
        {!latestWellness && !latestTraining && !latestCycle ? (
          <EmptyState
            icon={<IconCalendar size={22} />}
            title={t.noDataYet}
            description={t.noDataYetHint}
          />
        ) : (
          <ul className="space-y-2.5">
            {latestWellness && (
              <HistoryRow
                icon={<IconMoonSleep size={18} />}
                tone="brand"
                title={`${t.sleep} ${formatSleepHours(latestWellness.sleep_hours)} h · ${t.energy} ${metric(latestWellness.mental_energy)}/10`}
                subtitle={`${t.wellness} · ${t.sleepQuality} ${metric(latestWellness.sleep_quality)}/10`}
                meta={formatShortDate(latestWellness.date, locale)}
              />
            )}
            {latestTraining && (
              <HistoryRow
                icon={<IconDumbbell size={18} />}
                tone="iris"
                title={`${metric(latestTraining.duration_min)} ${t.minutesShort} · ${t.intensityLabel} ${metric(latestTraining.intensity)}/10`}
                subtitle={[
                  mapSessionTypeLabel(latestTraining.session_type, t),
                  mapParticipationLabel(latestTraining.participation_status, t),
                ]
                  .filter((part) => part !== "-")
                  .join(" · ")}
                meta={formatShortDate(latestTraining.date, locale)}
              />
            )}
            {latestCycle && (
              <HistoryRow
                icon={<IconDrop size={18} />}
                tone="bloom"
                title={`${mapPhaseLabel(latestCycle.phase, t)} · ${t.day} ${metric(latestCycle.cycle_day)}`}
                subtitle={`${t.cycleLength} ${metric(latestCycle.cycle_length)} ${t.daysShort}`}
                meta={formatShortDate(latestCycle.date, locale)}
              />
            )}
          </ul>
        )}
      </Card>
    </>
  );
}

/* ============================================================== wellness */

export function WellnessView({
  t,
  locale,
  form,
  onChange,
  onSubmit,
  isLoading,
  entries,
  suggestion,
  onApplySuggestion,
}: {
  t: T;
  locale: string;
  form: WellnessForm;
  onChange: (update: Partial<WellnessForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  entries: WellnessEntry[];
  suggestion: DeviceSuggestions | null;
  onApplySuggestion: () => void;
}) {
  const w = suggestion?.wellness ?? null;
  const wellnessSuggestionParts = !w
    ? []
    : [
        w.sleep_hours === null ? null : `${t.sleep} ${w.sleep_hours.toFixed(1)} h`,
        w.sleep_quality === null ? null : `${t.sleepQuality} ${w.sleep_quality}/10`,
        w.readiness_score === null ? null : `${t.readiness} ${w.readiness_score}`,
      ].filter((part): part is string => part !== null);

  const sliders: Array<{
    key: keyof WellnessForm;
    label: string;
    tone: Tone;
  }> = [
    { key: "sleep_quality", label: t.sleepQuality, tone: "ok" },
    { key: "mental_energy", label: t.mentalEnergy, tone: "brand" },
    { key: "motivation", label: t.motivationLabel, tone: "iris" },
    { key: "muscle_soreness", label: t.muscleSoreness, tone: "warn" },
    { key: "stress_level", label: t.stress, tone: "danger" },
    { key: "rpe_previous_day", label: t.rpePreviousDay, tone: "bloom" },
  ];

  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader
          title={t.wellnessCheck}
          subtitle={t.trendDescription}
          icon={<IconSparkle size={20} />}
          tone="brand"
        />

        <SuggestionBanner t={t} parts={wellnessSuggestionParts} onApply={onApplySuggestion} />

        <form className="space-y-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t.date}>
              <TextInput
                type="date"
                value={form.date}
                max={todayIso()}
                onChange={(event) => onChange({ date: event.target.value })}
              />
            </Field>
            <SliderField
              label={t.sleepHours}
              value={form.sleep_hours}
              onChange={(value) => onChange({ sleep_hours: value })}
              min={3}
              max={12}
              step={0.5}
              suffix=" h"
              tone="brand"
              lowLabel="3 h"
              highLabel="12 h"
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            {sliders.map((slider) => (
              <SliderField
                key={slider.key}
                label={slider.label}
                tone={slider.tone}
                value={form[slider.key] as number}
                onChange={(value) => onChange({ [slider.key]: value } as Partial<WellnessForm>)}
                lowLabel={t.scaleLow}
                highLabel={t.scaleHigh}
              />
            ))}
          </div>

          <Field label={`${t.note} (${t.optional})`}>
            <Textarea
              rows={3}
              value={form.free_text}
              onChange={(event) => onChange({ free_text: event.target.value })}
            />
          </Field>

          <Button type="submit" loading={isLoading} block className="sm:w-auto sm:px-8">
            {isLoading ? t.saving : t.saveWellness}
          </Button>
        </form>
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.wellnessHistory} icon={<IconClock size={20} />} tone="neutral" />
        {entries.length === 0 ? (
          <EmptyState icon={<IconSparkle size={22} />} title={t.noWellnessData} />
        ) : (
          <ul className="space-y-2.5">
            {entries.slice(0, 7).map((entry) => (
              <HistoryRow
                key={entry.id}
                icon={<IconMoonSleep size={18} />}
                tone="brand"
                title={`${t.sleep} ${formatSleepHours(entry.sleep_hours)} h · ${metric(entry.sleep_quality)}/10`}
                subtitle={`${t.mentalEnergy} ${metric(entry.mental_energy)} · ${t.motivationLabel} ${metric(entry.motivation)} · ${t.stress} ${metric(entry.stress_level)}`}
                meta={formatShortDate(entry.date, locale)}
              />
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

/* ================================================================= cycle */

export function CycleView({
  t,
  locale,
  form,
  onChange,
  onSubmit,
  isLoading,
  entries,
  suggestion,
  onApplySuggestion,
}: {
  t: T;
  locale: string;
  form: CycleForm;
  onChange: (update: Partial<CycleForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  entries: CycleEntry[];
  suggestion: DeviceSuggestions | null;
  onApplySuggestion: () => void;
}) {
  const cy = suggestion?.cycle ?? null;
  const suggestionParts = !cy
    ? []
    : [
        cy.cycle_day === null ? null : `${t.cycleDay} ${cy.cycle_day}`,
        cy.phase === null ? null : mapPhaseLabel(cy.phase, t),
        cy.cycle_length === null ? null : `${t.cycleLength} ${cy.cycle_length}`,
      ].filter((part): part is string => Boolean(part));

  const phases: Array<{ value: CyclePhase; label: string }> = [
    { value: "menstruation", label: t.phaseMenstruation },
    { value: "follicular", label: t.phaseFollicular },
    { value: "ovulation", label: t.phaseOvulation },
    { value: "luteal", label: t.phaseLuteal },
  ];

  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader
          title={t.cycleTracking}
          subtitle={t.privacyNoteCycle}
          icon={<IconDrop size={20} />}
          tone="bloom"
        />
        <SuggestionBanner t={t} parts={suggestionParts} onApply={onApplySuggestion} />
        <form className="space-y-6" onSubmit={onSubmit}>
          <Field label={t.date}>
            <TextInput
              type="date"
              value={form.date}
              max={todayIso()}
              onChange={(event) => onChange({ date: event.target.value })}
            />
          </Field>

          <div>
            <span className="field-label">{t.phase}</span>
            <Segmented
              className="mt-1"
              tone="bloom"
              options={phases}
              value={form.phase}
              onChange={(value) => onChange({ phase: value })}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Stepper
              label={t.cycleDay}
              value={form.cycle_day}
              onChange={(value) => onChange({ cycle_day: value })}
              min={1}
              max={60}
            />
            <Stepper
              label={t.cycleLength}
              value={form.cycle_length}
              onChange={(value) => onChange({ cycle_length: value })}
              min={20}
              max={45}
            />
          </div>

          <SliderField
            label={t.pmsScore}
            value={form.pms_score}
            onChange={(value) => onChange({ pms_score: value })}
            tone="bloom"
            lowLabel={t.scaleLow}
            highLabel={t.scaleHigh}
          />

          <div>
            <span className="field-label">{t.symptoms}</span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              <ToggleChip
                label={t.cramps}
                tone="bloom"
                active={form.cramps}
                onClick={() => onChange({ cramps: !form.cramps })}
              />
              <ToggleChip
                label={t.migraine}
                tone="bloom"
                active={form.migraine}
                onClick={() => onChange({ migraine: !form.migraine })}
              />
              <ToggleChip
                label={t.fatigue}
                tone="bloom"
                active={form.fatigue}
                onClick={() => onChange({ fatigue: !form.fatigue })}
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={`${t.contraception} (${t.optional})`}>
              <TextInput
                value={form.contraception_type}
                onChange={(event) => onChange({ contraception_type: event.target.value })}
              />
            </Field>
            <Field label={`${t.note} (${t.optional})`}>
              <TextInput
                value={form.notes}
                onChange={(event) => onChange({ notes: event.target.value })}
              />
            </Field>
          </div>

          <Button type="submit" loading={isLoading} block className="sm:w-auto sm:px-8">
            {isLoading ? t.saving : t.saveCycle}
          </Button>
        </form>
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.cycleData} icon={<IconCalendar size={20} />} tone="neutral" />
        {entries.length === 0 ? (
          <EmptyState icon={<IconDrop size={22} />} title={t.noCycleData} />
        ) : (
          <ul className="space-y-2.5">
            {entries.slice(0, 7).map((entry) => (
              <HistoryRow
                key={entry.id}
                icon={<IconDrop size={18} />}
                tone="bloom"
                title={`${mapPhaseLabel(entry.phase, t)} · ${t.day} ${metric(entry.cycle_day)}`}
                subtitle={[
                  entry.cramps ? t.cramps : null,
                  entry.migraine ? t.migraine : null,
                  entry.fatigue ? t.fatigue : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
                meta={formatShortDate(entry.date, locale)}
              />
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

/* ============================================================== training */

export function TrainingView({
  t,
  locale,
  form,
  onChange,
  onSubmit,
  isLoading,
  entries,
  suggestion,
  onApplySuggestion,
}: {
  t: T;
  locale: string;
  form: TrainingForm;
  onChange: (update: Partial<TrainingForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  entries: TrainingEntry[];
  suggestion: DeviceSuggestions | null;
  onApplySuggestion: () => void;
}) {
  const durations = [45, 60, 75, 90, 120];
  const tr = suggestion?.training ?? null;
  const suggestionParts = !tr
    ? []
    : [
        tr.duration_min === null ? null : `${tr.duration_min} ${t.minutesShort}`,
        tr.sport,
        tr.intensity === null ? null : `${t.intensityLabel} ${tr.intensity}/10`,
      ].filter((part): part is string => Boolean(part));

  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader title={t.trainingEntry} icon={<IconDumbbell size={20} />} tone="iris" />
        <SuggestionBanner t={t} parts={suggestionParts} onApply={onApplySuggestion} />
        <form className="space-y-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t.date}>
              <TextInput
                type="date"
                value={form.date}
                max={todayIso()}
                onChange={(event) => onChange({ date: event.target.value })}
              />
            </Field>
            <Field label={t.durationMinutes}>
              <TextInput
                type="number"
                min={1}
                max={600}
                inputMode="numeric"
                value={form.duration_min}
                onChange={(event) => onChange({ duration_min: Number(event.target.value) })}
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {durations.map((minutes) => (
                  <button
                    key={minutes}
                    type="button"
                    onClick={() => onChange({ duration_min: minutes })}
                    className={cx(
                      "rounded-lg border px-3 py-1.5 text-xs font-bold transition active:scale-95",
                      form.duration_min === minutes
                        ? "border-transparent bg-iris-soft text-iris"
                        : "border-line bg-card text-muted",
                    )}
                  >
                    {minutes} {t.minutesShort}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <SliderField
              label={t.intensityLabel}
              value={form.intensity}
              onChange={(value) => onChange({ intensity: value })}
              min={1}
              tone="iris"
              lowLabel={t.scaleLow}
              highLabel={t.scaleHigh}
            />
            <SliderField
              label={t.sessionRpeLabel}
              value={form.session_rpe}
              onChange={(value) => onChange({ session_rpe: value })}
              tone="warn"
              lowLabel={t.scaleLow}
              highLabel={t.scaleHigh}
            />
          </div>

          <div>
            <span className="field-label">{t.sessionType}</span>
            <Segmented
              className="mt-1"
              tone="iris"
              value={form.session_type}
              onChange={(value) => onChange({ session_type: value })}
              options={[
                { value: "team", label: t.sessionTypeTeam },
                { value: "strength", label: t.sessionTypeStrength },
                { value: "technical", label: t.sessionTypeTechnical },
                { value: "recovery", label: t.sessionTypeRecovery },
              ]}
            />
          </div>

          <div>
            <span className="field-label">{t.participationStatus}</span>
            <Segmented
              className="mt-1"
              tone="brand"
              value={form.participation_status}
              onChange={(value) => onChange({ participation_status: value })}
              options={[
                { value: "full", label: t.participationFull },
                { value: "modified", label: t.participationModified },
                { value: "individual", label: t.participationIndividual },
                { value: "rest", label: t.participationRest },
              ]}
            />
          </div>

          <Button type="submit" loading={isLoading} block className="sm:w-auto sm:px-8">
            {isLoading ? t.saving : t.saveTraining}
          </Button>
        </form>
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.trainingHistory} icon={<IconClock size={20} />} tone="neutral" />
        {entries.length === 0 ? (
          <EmptyState icon={<IconDumbbell size={22} />} title={t.noTrainingEntries} />
        ) : (
          <ul className="space-y-2.5">
            {entries.slice(0, 10).map((entry) => (
              <HistoryRow
                key={entry.id}
                icon={<IconDumbbell size={18} />}
                tone="iris"
                title={`${metric(entry.duration_min)} ${t.minutesShort} · ${t.intensityLabel} ${metric(entry.intensity)}/10`}
                subtitle={[
                  mapSessionTypeLabel(entry.session_type, t),
                  mapParticipationLabel(entry.participation_status, t),
                  entry.session_rpe === null ? null : `sRPE ${entry.session_rpe}`,
                ]
                  .filter((part) => part && part !== "-")
                  .join(" · ")}
                meta={formatShortDate(entry.date, locale)}
              />
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

/* ================================================================ injury */

export function InjuryView({
  t,
  locale,
  form,
  onChange,
  onSubmit,
  isLoading,
  entries,
}: {
  t: T;
  locale: string;
  form: InjuryForm;
  onChange: (update: Partial<InjuryForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  entries: InjuryEntry[];
}) {
  // Values stay canonical (German) so coach views and the ML pipeline keep
  // seeing one consistent set of body locations across UI languages.
  const bodyLocations = [
    { value: "Knie", label: t.bodyKnee },
    { value: "Sprunggelenk", label: t.bodyAnkle },
    { value: "Schulter", label: t.bodyShoulder },
    { value: "Unterer Rücken", label: t.bodyLowBack },
    { value: "Oberschenkel", label: t.bodyThigh },
    { value: "Fuss", label: t.bodyFoot },
    { value: "Hüfte", label: t.bodyHip },
    { value: "Handgelenk", label: t.bodyWrist },
  ];

  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader title={t.injuryTracking} icon={<IconPulseAlert size={20} />} tone="warn" />
        <form className="space-y-6" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t.date}>
              <TextInput
                type="date"
                value={form.date}
                max={todayIso()}
                onChange={(event) => onChange({ date: event.target.value })}
              />
            </Field>
            <Field label={t.bodyLocation}>
              <TextInput
                value={form.body_location}
                onChange={(event) => onChange({ body_location: event.target.value })}
                required
              />
            </Field>
          </div>

          <div className="flex flex-wrap gap-2">
            {bodyLocations.map((location) => (
              <button
                key={location.value}
                type="button"
                onClick={() => onChange({ body_location: location.value })}
                className={cx(
                  "rounded-lg border px-3 py-1.5 text-xs font-bold transition active:scale-95",
                  form.body_location === location.value
                    ? "border-transparent bg-warn-soft text-warn"
                    : "border-line bg-card text-muted",
                )}
              >
                {location.label}
              </button>
            ))}
          </div>

          <SliderField
            label={t.painIntensity}
            value={form.pain_intensity}
            onChange={(value) => onChange({ pain_intensity: value })}
            min={1}
            tone="danger"
            lowLabel={t.scaleLow}
            highLabel={t.scaleHigh}
          />

          <div className="grid gap-3 sm:grid-cols-2">
            <Switch
              label={t.isChronic}
              tone="warn"
              checked={form.is_chronic}
              onChange={(value) => onChange({ is_chronic: value })}
            />
            <Switch
              label={t.medicalAttention}
              tone="warn"
              checked={form.medical_attention}
              onChange={(value) => onChange({ medical_attention: value })}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t.timeLossDays}>
              <TextInput
                type="number"
                min={0}
                max={365}
                inputMode="numeric"
                value={form.time_loss_days}
                onChange={(event) => onChange({ time_loss_days: Number(event.target.value) })}
              />
            </Field>
            <Field label={`${t.note} (${t.optional})`}>
              <TextInput
                value={form.description}
                onChange={(event) => onChange({ description: event.target.value })}
              />
            </Field>
          </div>

          <Button type="submit" loading={isLoading} block className="sm:w-auto sm:px-8">
            {isLoading ? t.saving : t.saveInjury}
          </Button>
        </form>
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.injuryHistory} icon={<IconAlert size={20} />} tone="neutral" />
        {entries.length === 0 ? (
          <EmptyState icon={<IconPulseAlert size={22} />} title={t.noInjuryData} />
        ) : (
          <ul className="space-y-2.5">
            {entries.slice(0, 10).map((entry) => (
              <HistoryRow
                key={entry.id}
                icon={<IconPulseAlert size={18} />}
                tone={num(entry.pain_intensity) >= 7 ? "danger" : "warn"}
                title={`${entry.body_location} · ${metric(entry.pain_intensity)}/10`}
                subtitle={[
                  entry.is_chronic ? t.isChronic : null,
                  entry.medical_attention ? t.medicalAttention : null,
                  num(entry.time_loss_days) > 0
                    ? `${t.timeLossDays}: ${entry.time_loss_days}`
                    : null,
                  entry.description,
                ]
                  .filter(Boolean)
                  .join(" · ")}
                meta={formatShortDate(entry.date, locale)}
              />
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

/* =============================================================== privacy */

function DeleteAccountCard({
  t,
  isDeleting,
  onDelete,
}: {
  t: T;
  isDeleting: boolean;
  onDelete: (password: string) => void;
}) {
  const [armed, setArmed] = useState(false);
  const [password, setPassword] = useState("");

  function reset() {
    setArmed(false);
    setPassword("");
  }

  return (
    <Card className="animate-fadeUp border-danger/30">
      <CardHeader
        title={t.deleteAccountTitle}
        subtitle={t.deleteAccountIntro}
        icon={<IconAlert size={20} />}
        tone="danger"
      />
      {armed ? (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (password) onDelete(password);
          }}
        >
          <p className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold leading-snug text-danger">
            {t.deleteAccountWarning}
          </p>
          <Field label={t.deleteAccountPassword}>
            <TextInput
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="danger" loading={isDeleting} disabled={!password}>
              {t.deleteAccountConfirm}
            </Button>
            <Button type="button" variant="ghost" onClick={reset}>
              {t.cancel}
            </Button>
          </div>
        </form>
      ) : (
        <Button variant="danger" onClick={() => setArmed(true)}>
          {t.deleteAccount}
        </Button>
      )}
    </Card>
  );
}

export function PrivacyView({
  t,
  consents,
  onToggle,
  onSave,
  isDeleting,
  onDeleteAccount,
}: {
  t: T;
  consents: PrivacyConsent[];
  onToggle: (consentId: number, update: Partial<PrivacyConsent>) => void;
  onSave: (consent: PrivacyConsent) => void;
  isDeleting: boolean;
  onDeleteAccount: (password: string) => void;
}) {
  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader
          title={t.privacySettings}
          subtitle={t.privacyIntro}
          icon={<IconShield size={20} />}
          tone="ok"
        />
        {consents.length === 0 ? (
          <EmptyState icon={<IconShield size={22} />} title={t.noConsents} />
        ) : (
          <div className="space-y-4">
            {consents.map((consent) => (
              <div key={consent.id} className="rounded-xl border border-line p-4">
                <div className="mb-3 flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-soft font-display font-bold text-brand-ink">
                    {(consent.coach_name ?? "C").slice(0, 1).toUpperCase()}
                  </span>
                  <div>
                    <p className="font-semibold text-ink">
                      {consent.coach_name ?? `${t.coach} ${consent.coach_id}`}
                    </p>
                    <p className="text-xs text-muted">{t.coach}</p>
                  </div>
                </div>
                <div className="space-y-2.5">
                  <Switch
                    label={t.shareWellness}
                    checked={consent.share_wellness_data}
                    onChange={(value) => onToggle(consent.id, { share_wellness_data: value })}
                  />
                  <Switch
                    label={t.shareCycle}
                    description={t.privacyNoteCycle}
                    tone="bloom"
                    checked={consent.share_cycle_data}
                    onChange={(value) => onToggle(consent.id, { share_cycle_data: value })}
                  />
                </div>
                <Button
                  variant="secondary"
                  className="mt-3 w-full sm:w-auto"
                  icon={<IconCheck size={18} />}
                  onClick={() => onSave(consent)}
                >
                  {t.save}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <DeleteAccountCard t={t} isDeleting={isDeleting} onDelete={onDeleteAccount} />
    </>
  );
}
