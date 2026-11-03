import { ReactNode, useId } from "react";
import { RiskLevel } from "../types";
import { Tone, cx, riskTone, toneVar, toneVarAlpha } from "./theme";

/* ------------------------------------------------------------ risk gauge */

export function RiskGauge({
  score,
  level,
  label,
  caption,
  size = "lg",
}: {
  score: number;
  level: RiskLevel;
  label: string;
  caption?: ReactNode;
  size?: "sm" | "lg";
}) {
  const id = useId();
  const pct = Math.min(100, Math.max(0, score * 100));
  const color = toneVar(riskTone(level));

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 200 116"
        className={cx("w-full", size === "lg" ? "max-w-[280px]" : "max-w-[180px]")}
        role="img"
        aria-label={`${label} ${pct.toFixed(0)}%`}
      >
        <defs>
          <linearGradient id={`${id}-arc`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgb(var(--c-ok))" />
            <stop offset="55%" stopColor="rgb(var(--c-warn))" />
            <stop offset="100%" stopColor="rgb(var(--c-danger))" />
          </linearGradient>
        </defs>
        <path
          d="M26 96A74 74 0 0 1 174 96"
          fill="none"
          stroke="rgb(var(--c-line))"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <path
          d="M26 96A74 74 0 0 1 174 96"
          fill="none"
          stroke={`url(#${id}-arc)`}
          strokeWidth="16"
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={`${pct} 100`}
          style={{ transition: "stroke-dasharray 600ms cubic-bezier(0.22,1,0.36,1)" }}
        />
        <text
          x="100"
          y="82"
          textAnchor="middle"
          className="font-display"
          style={{ fontSize: 34, fontWeight: 800, fill: "rgb(var(--c-ink))" }}
        >
          {pct.toFixed(0)}
          <tspan style={{ fontSize: 16, fill: "rgb(var(--c-subtle))" }}>%</tspan>
        </text>
        <text
          x="100"
          y="103"
          textAnchor="middle"
          style={{ fontSize: 13, fontWeight: 700, fill: color, letterSpacing: "0.04em" }}
        >
          {label.toUpperCase()}
        </text>
      </svg>
      {caption && <p className="mt-1 text-center text-sm leading-snug text-muted">{caption}</p>}
    </div>
  );
}

/* ------------------------------------------------------------ line chart */

export type Series = {
  key: string;
  label: string;
  values: number[];
  tone: Tone;
  area?: boolean;
};

const CHART_W = 320;
const CHART_H = 150;
const PAD_X = 14;
const PAD_TOP = 14;
const PAD_BOTTOM = 26;

function buildPoints(values: number[], min: number, max: number) {
  const span = Math.max(max - min, 1);
  const usableW = CHART_W - PAD_X * 2;
  const usableH = CHART_H - PAD_TOP - PAD_BOTTOM;
  return values.map((value, index) => {
    const x = PAD_X + (index / Math.max(values.length - 1, 1)) * usableW;
    const y = PAD_TOP + (1 - (value - min) / span) * usableH;
    return { x, y, value };
  });
}

function smoothPath(points: { x: number; y: number }[]) {
  if (points.length === 0) return "";
  if (points.length === 1) return `M${points[0].x},${points[0].y}`;
  let path = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const current = points[i];
    const next = points[i + 1];
    const midX = (current.x + next.x) / 2;
    path += ` C${midX},${current.y} ${midX},${next.y} ${next.x},${next.y}`;
  }
  return path;
}

export function TrendChart({
  series,
  labels,
  domain = [0, 10],
  activeIndex,
  onSelect,
  height = "h-44",
}: {
  series: Series[];
  labels: string[];
  domain?: [number, number];
  activeIndex?: number | null;
  onSelect?: (index: number) => void;
  height?: string;
}) {
  const id = useId();
  const [min, max] = domain;
  const primary = series[0];
  const primaryPoints = primary ? buildPoints(primary.values, min, max) : [];

  return (
    <div className={cx("w-full", height)}>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="h-full w-full overflow-visible">
        <defs>
          {series.map((item) => (
            <linearGradient key={item.key} id={`${id}-${item.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={toneVar(item.tone)} stopOpacity="0.28" />
              <stop offset="100%" stopColor={toneVar(item.tone)} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        {[0, 0.5, 1].map((fraction) => {
          const y = PAD_TOP + fraction * (CHART_H - PAD_TOP - PAD_BOTTOM);
          return (
            <line
              key={fraction}
              x1={PAD_X}
              x2={CHART_W - PAD_X}
              y1={y}
              y2={y}
              stroke="rgb(var(--c-line))"
              strokeWidth="1"
              strokeDasharray={fraction === 1 ? undefined : "3 5"}
            />
          );
        })}

        {series.map((item) => {
          const points = buildPoints(item.values, min, max);
          const line = smoothPath(points);
          const baseY = CHART_H - PAD_BOTTOM;
          return (
            <g key={item.key}>
              {item.area !== false && points.length > 1 && (
                <path
                  d={`${line} L${points[points.length - 1].x},${baseY} L${points[0].x},${baseY} Z`}
                  fill={`url(#${id}-${item.key})`}
                />
              )}
              <path
                d={line}
                fill="none"
                stroke={toneVar(item.tone)}
                strokeWidth={item.area === false ? 2 : 2.75}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={item.area === false ? 0.85 : 1}
              />
            </g>
          );
        })}

        {primaryPoints.map((point, index) => (
          <circle
            key={`dot-${index}`}
            cx={point.x}
            cy={point.y}
            r={activeIndex === index ? 5.5 : 3.5}
            fill="rgb(var(--c-card))"
            stroke={toneVar(primary.tone)}
            strokeWidth={activeIndex === index ? 3.5 : 2.5}
          />
        ))}

        {labels.map((label, index) => {
          const point = primaryPoints[index];
          if (!point) return null;
          return (
            <text
              key={`label-${index}`}
              x={point.x}
              y={CHART_H - 8}
              textAnchor="middle"
              style={{
                fontSize: 10,
                fontWeight: 600,
                fill: activeIndex === index ? "rgb(var(--c-ink))" : "rgb(var(--c-subtle))",
              }}
            >
              {label}
            </text>
          );
        })}

        {onSelect &&
          primaryPoints.map((point, index) => (
            <rect
              key={`hit-${index}`}
              x={point.x - (CHART_W - PAD_X * 2) / Math.max(primaryPoints.length * 2, 2)}
              y={0}
              width={(CHART_W - PAD_X * 2) / Math.max(primaryPoints.length, 1)}
              height={CHART_H}
              fill="transparent"
              style={{ cursor: "pointer" }}
              onClick={() => onSelect(index)}
            />
          ))}
      </svg>
    </div>
  );
}

export function ChartLegend({ series }: { series: Series[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
      {series.map((item) => (
        <span key={item.key} className="flex items-center gap-1.5 text-xs font-medium text-muted">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: toneVar(item.tone) }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------- bar rows */

export function BarChart({
  values,
  labels,
  tone = "brand",
  unit,
}: {
  values: number[];
  labels: string[];
  tone?: Tone;
  unit?: string;
}) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-40 gap-1.5">
      {values.map((value, index) => (
        <div
          key={`${labels[index]}-${index}`}
          className="flex h-full flex-1 flex-col items-center gap-1"
        >
          <span className="text-[10px] font-semibold tabular-nums text-subtle">{value}</span>
          {/* The bar needs a positioned parent with a definite height, otherwise
              its percentage height collapses to zero. */}
          <div className="relative w-full flex-1">
            <div
              className="absolute bottom-0 w-full rounded-t-lg transition-all"
              style={{
                height: `${Math.max(4, (value / max) * 100)}%`,
                backgroundImage: `linear-gradient(180deg, ${toneVar(tone)}, ${toneVarAlpha(tone, 0.4)})`,
              }}
            />
          </div>
          <span className="text-[10px] font-medium text-subtle">{labels[index]}</span>
        </div>
      ))}
      {unit && <span className="sr-only">{unit}</span>}
    </div>
  );
}

/* ------------------------------------------------------------- risk ring */

export function RiskRing({
  score,
  level,
  size = 52,
}: {
  score: number;
  level: RiskLevel;
  size?: number;
}) {
  const pct = Math.min(100, Math.max(0, score * 100));
  const color = toneVar(riskTone(level));
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg width={size} height={size} viewBox="0 0 44 44" className="shrink-0" aria-hidden="true">
      <circle cx="22" cy="22" r={radius} fill="none" stroke="rgb(var(--c-line))" strokeWidth="5" />
      <circle
        cx="22"
        cy="22"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={`${(pct / 100) * circumference} ${circumference}`}
        transform="rotate(-90 22 22)"
        style={{ transition: "stroke-dasharray 500ms ease" }}
      />
      <text
        x="22"
        y="26"
        textAnchor="middle"
        style={{ fontSize: 13, fontWeight: 800, fill: "rgb(var(--c-ink))" }}
      >
        {pct.toFixed(0)}
      </text>
    </svg>
  );
}

export function Sparkline({ values, tone = "brand" }: { values: number[]; tone?: Tone }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 60;
      const y = 18 - ((value - min) / span) * 16;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 60 20" className="h-5 w-16" aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={toneVar(tone)}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
