import { useState } from "react";
import {
  CycleEntry,
  ModelTrainingStatus,
  Prediction,
  TrainingEntry,
  WellnessEntry,
} from "../types";
import {
  formatDateTime,
  formatShortDate,
  formatWeekday,
  mapParticipationLabel,
  mapPhaseLabel,
  mapPositionLabel,
  mapSessionTypeLabel,
  num,
} from "../utils";
import { BarChart, ChartLegend, RiskRing, Series, TrendChart } from "./charts";
import {
  IconAlert,
  IconChevronDown,
  IconChevronRight,
  IconDrop,
  IconDumbbell,
  IconInfo,
  IconRefresh,
  IconShield,
  IconSparkle,
  IconUsers,
} from "./icons";
import { Button, Card, CardHeader, Chip, EmptyState, Select, StatTile } from "./ui";
import { Tone, cx, riskTone, toneVar } from "./theme";

type T = Record<string, string>;

function levelLabel(level: Prediction["risk_level"], t: T) {
  if (level === "red") return t.riskHigh;
  if (level === "yellow") return t.riskMedium;
  return t.riskLow;
}

export function CoachTeamView({
  t,
  predictions,
  teamAverage,
  onSelectPlayer,
}: {
  t: T;
  predictions: Prediction[];
  teamAverage: number;
  onSelectPlayer: (playerId: number) => void;
}) {
  const red = predictions.filter((item) => item.risk_level === "red").length;
  const yellow = predictions.filter((item) => item.risk_level === "yellow").length;
  const green = predictions.filter((item) => item.risk_level === "green").length;
  const timeLoss = predictions.reduce((sum, item) => sum + (item.latest_time_loss_days ?? 0), 0);

  return (
    <>
      <header className="animate-fadeUp">
        <h1 className="font-display text-[26px] font-extrabold leading-tight text-ink sm:text-3xl">
          {t.teamOverview}
        </h1>
        <p className="mt-1 text-sm text-muted">{t.priorityList}</p>
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label={t.teamRiskAverage}
          value={`${(teamAverage * 100).toFixed(0)}%`}
          tone="brand"
          icon={<IconUsers size={14} />}
        />
        <StatTile
          label={t.playersInTeam}
          value={predictions.length}
          tone="neutral"
          icon={<IconUsers size={14} />}
        />
        <StatTile
          label={t.needsAttention}
          value={red + yellow}
          hint={`${red} ${t.riskHigh} · ${yellow} ${t.riskMedium}`}
          tone={red > 0 ? "danger" : "warn"}
          icon={<IconAlert size={14} />}
        />
        <StatTile
          label={t.inTheGreen}
          value={green}
          tone="ok"
          hint={timeLoss > 0 ? `${timeLoss} ${t.outOfPlay}` : t.allGood}
          icon={<IconSparkle size={14} />}
        />
      </div>

      <Card className="animate-fadeUp">
        <CardHeader title={t.priorityList} icon={<IconUsers size={20} />} tone="brand" />
        {predictions.length === 0 ? (
          <EmptyState icon={<IconUsers size={22} />} title={t.noPlayers} />
        ) : (
          <ul className="space-y-3">
            {predictions.map((item) => {
              const tone: Tone = riskTone(item.risk_level);
              const chips: Array<{ label: string; tone: Tone } | null> = [
                item.latest_session_rpe === null || item.latest_session_rpe === undefined
                  ? null
                  : { label: `sRPE ${item.latest_session_rpe}`, tone: "brand" as Tone },
                item.latest_session_type
                  ? {
                      label: mapSessionTypeLabel(item.latest_session_type, t),
                      tone: "iris" as Tone,
                    }
                  : null,
                item.latest_participation_status
                  ? {
                      label: mapParticipationLabel(item.latest_participation_status, t),
                      tone: "neutral" as Tone,
                    }
                  : null,
                item.latest_pain_intensity
                  ? {
                      label: `${t.painIntensity}: ${item.latest_pain_intensity}`,
                      tone: (item.latest_pain_intensity >= 7 ? "danger" : "warn") as Tone,
                    }
                  : null,
                item.latest_time_loss_days
                  ? {
                      label: `${t.timeLossDays}: ${item.latest_time_loss_days}`,
                      tone: "danger" as Tone,
                    }
                  : null,
              ];
              const visibleChips = chips.filter(Boolean) as Array<{ label: string; tone: Tone }>;
              return (
                <li key={`${item.player_id}-${item.date ?? "today"}`}>
                  <button
                    type="button"
                    onClick={() => item.player_id && onSelectPlayer(item.player_id)}
                    className="w-full rounded-xl border border-line bg-raised p-4 text-left transition hover:border-brand/40 hover:shadow-card active:scale-[0.995]"
                  >
                    <div className="flex items-center gap-3.5">
                      <RiskRing score={item.risk_score} level={item.risk_level} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-display text-[17px] font-bold text-ink">
                          {item.player_name ?? `${t.player} #${item.player_id}`}
                        </p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted">
                          {item.player_position && (
                            <>
                              <span>{mapPositionLabel(item.player_position, t)}</span>
                              <span aria-hidden="true">·</span>
                            </>
                          )}
                          <span
                            className={cx(
                              "font-bold",
                              tone === "danger" && "text-danger",
                              tone === "warn" && "text-warn",
                              tone === "ok" && "text-ok",
                            )}
                          >
                            {levelLabel(item.risk_level, t)}
                          </span>
                        </p>
                      </div>
                      <IconChevronRight size={20} className="shrink-0 text-subtle" />
                    </div>

                    <div className="mt-3 h-2 w-full overflow-hidden rounded-pill bg-line">
                      <div
                        className="h-full rounded-pill transition-all"
                        style={{
                          width: `${Math.min(100, Math.max(2, item.risk_score * 100))}%`,
                          backgroundColor: toneVar(tone),
                        }}
                      />
                    </div>

                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {visibleChips.map((chip, index) => (
                        <Chip key={`${item.player_id}-chip-${index}`} tone={chip.tone}>
                          {chip.label}
                        </Chip>
                      ))}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </>
  );
}

export function CoachDetailView({
  t,
  locale,
  predictions,
  selectedPlayerId,
  onSelectPlayer,
  onRefresh,
  wellness,
  cycle,
  training,
  wellnessBlocked,
  cycleBlocked,
  isLoading,
}: {
  t: T;
  locale: string;
  predictions: Prediction[];
  selectedPlayerId: number | null;
  onSelectPlayer: (playerId: number) => void;
  onRefresh: () => void;
  wellness: WellnessEntry[];
  cycle: CycleEntry[];
  training: TrainingEntry[];
  wellnessBlocked: boolean;
  cycleBlocked: boolean;
  isLoading: boolean;
}) {
  const selected = predictions.find((item) => item.player_id === selectedPlayerId) ?? null;

  const wellnessTrend = wellness
    .slice(0, 7)
    .reverse()
    .map((entry) => {
      const sleepQuality = num(entry.sleep_quality);
      const mentalEnergy = num(entry.mental_energy);
      return {
        date: entry.date,
        score: Math.round((sleepQuality + mentalEnergy + num(entry.motivation)) / 3),
        sleep_quality: sleepQuality,
        mental_energy: mentalEnergy,
      };
    });

  const trainingTrend = training.slice(0, 7).reverse();
  const avgDuration =
    trainingTrend.length === 0
      ? 0
      : trainingTrend.reduce((sum, entry) => sum + num(entry.duration_min), 0) /
        trainingTrend.length;

  const series: Series[] = [
    { key: "score", label: t.avgBlue, values: wellnessTrend.map((p) => p.score), tone: "brand" },
    {
      key: "sleep",
      label: t.greenSleep,
      values: wellnessTrend.map((p) => p.sleep_quality),
      tone: "ok",
      area: false,
    },
    {
      key: "mental",
      label: t.purpleMental,
      values: wellnessTrend.map((p) => p.mental_energy),
      tone: "iris",
      area: false,
    },
  ];

  return (
    <>
      <Card className="animate-fadeUp">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[12rem] flex-1">
            <span className="field-label">{t.selectPlayer}</span>
            <Select
              value={selectedPlayerId ?? ""}
              onChange={(event) => onSelectPlayer(Number(event.target.value))}
            >
              {predictions.map((item) => (
                <option key={`sel-${item.player_id}`} value={item.player_id}>
                  {item.player_name ?? `${t.player} #${item.player_id}`}
                </option>
              ))}
            </Select>
          </div>
          <Button
            variant="secondary"
            icon={<IconRefresh size={18} />}
            onClick={onRefresh}
            loading={isLoading}
          >
            {t.refresh}
          </Button>
        </div>

        {selected && (
          <div className="mt-4 flex items-center gap-4 rounded-xl border border-line bg-raised p-4">
            <RiskRing score={selected.risk_score} level={selected.risk_level} size={60} />
            <div>
              <p className="font-display text-lg font-bold text-ink">
                {selected.player_name ?? `${t.player} #${selected.player_id}`}
              </p>
              <p className="text-sm text-muted">
                {selected.player_position
                  ? `${mapPositionLabel(selected.player_position, t)} · `
                  : ""}
                {t.riskScoreLabel} {(selected.risk_score * 100).toFixed(0)}% (
                {levelLabel(selected.risk_level, t)})
              </p>
            </div>
          </div>
        )}
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.wellnessHistory} icon={<IconSparkle size={20} />} tone="brand" />
        {wellnessBlocked ? (
          <EmptyState icon={<IconShield size={22} />} title={t.wellnessBlocked} />
        ) : wellnessTrend.length < 2 ? (
          <EmptyState icon={<IconSparkle size={22} />} title={t.noWellnessData} />
        ) : (
          <>
            <TrendChart
              series={series}
              labels={wellnessTrend.map((point) => formatWeekday(point.date, locale))}
            />
            <ChartLegend series={series} />
          </>
        )}
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader
          title={t.trainingLoad}
          icon={<IconDumbbell size={20} />}
          tone="iris"
          action={
            trainingTrend.length > 0 ? (
              <Chip tone="iris">
                {t.avg}: {avgDuration.toFixed(0)} {t.minutesShort}
              </Chip>
            ) : undefined
          }
        />
        {trainingTrend.length === 0 ? (
          <EmptyState icon={<IconDumbbell size={22} />} title={t.noTrainingData} />
        ) : (
          <BarChart
            values={trainingTrend.map((entry) => num(entry.duration_min))}
            labels={trainingTrend.map((entry) => formatShortDate(entry.date, locale))}
            tone="iris"
          />
        )}
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.cycleData} icon={<IconDrop size={20} />} tone="bloom" />
        {cycleBlocked ? (
          <EmptyState icon={<IconShield size={22} />} title={t.cycleBlocked} />
        ) : cycle.length === 0 ? (
          <EmptyState icon={<IconDrop size={22} />} title={t.noCycleData} />
        ) : (
          <div className="flex flex-wrap gap-2">
            {cycle.slice(0, 10).map((entry) => (
              <Chip key={entry.id} tone="bloom">
                {formatShortDate(entry.date, locale)} · {mapPhaseLabel(entry.phase, t)} (
                {t.day.slice(0, 1)}
                {entry.cycle_day ?? "–"})
              </Chip>
            ))}
          </div>
        )}
      </Card>

      <Card className="animate-fadeUp">
        <CardHeader title={t.injuryHistory} icon={<IconAlert size={20} />} tone="warn" />
        <p className="text-sm text-muted">{t.noInjuryEndpoint}</p>
      </Card>
    </>
  );
}

export function SystemStatusCard({
  t,
  locale,
  status,
}: {
  t: T;
  locale: string;
  status: ModelTrainingStatus | null;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Card className="animate-fadeUp" padded={false}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 p-4 text-left"
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-raised text-muted">
          <IconInfo size={18} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-bold text-ink">{t.modelTrainingStatus}</span>
          <span className="block truncate text-xs text-muted">
            {status ? `${t.status}: ${status.status}` : t.noTrainingStatus}
          </span>
        </span>
        {status && <Chip tone={status.status === "ok" ? "ok" : "danger"}>{status.status}</Chip>}
        <IconChevronDown
          size={18}
          className={cx("shrink-0 text-subtle transition", open && "rotate-180")}
        />
      </button>

      {open && status && (
        <div className="grid gap-2 border-t border-line p-4 text-sm sm:grid-cols-2">
          <p className="text-muted">
            {t.updated}:{" "}
            <span className="text-ink">{formatDateTime(status.updated_at, locale)}</span>
          </p>
          <p className="text-muted">
            {t.lastSuccess}:{" "}
            <span className="text-ink">{formatDateTime(status.last_success_at, locale)}</span>
          </p>
          <p className="text-muted">
            {t.lastFailure}:{" "}
            <span className="text-ink">{formatDateTime(status.last_failure_at, locale)}</span>
          </p>
          <p className="text-muted">
            {t.mode}:{" "}
            <span className="text-ink">
              {String((status.metrics?.training_data_mode as string | undefined) ?? t.unknown)}
            </span>
          </p>
          <p className="text-muted">
            {t.realRows}:{" "}
            <span className="text-ink">
              {String((status.metrics?.real_rows as number | undefined) ?? "-")}
            </span>
          </p>
          {status.error && (
            <p className="text-danger sm:col-span-2">
              {t.error}: {status.error}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
