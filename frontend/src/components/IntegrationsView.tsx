import { FormEvent, ReactNode, useState } from "react";
import { AppleHealthToken, IntegrationStatus, WearableDaily, WearableProvider } from "../types";
import { formatDateTime, formatShortDate } from "../utils";
import {
  IconAlert,
  IconCheck,
  IconCopy,
  IconHeart,
  IconLink,
  IconMoonSleep,
  IconPhone,
  IconRefresh,
  IconRing,
  IconUnlink,
  IconWatch,
} from "./icons";
import { Button, Card, CardHeader, Chip, EmptyState, Field, Switch, TextInput } from "./ui";
import { Tone } from "./theme";

type T = Record<string, string>;

const PROVIDER_META: Record<
  WearableProvider,
  { labelKey: string; descriptionKey: string; tone: Tone; icon: ReactNode }
> = {
  whoop: {
    labelKey: "providerWhoop",
    descriptionKey: "providerWhoopDescription",
    tone: "danger",
    icon: <IconWatch size={22} />,
  },
  oura: {
    labelKey: "providerOura",
    descriptionKey: "providerOuraDescription",
    tone: "iris",
    icon: <IconRing size={22} />,
  },
  apple_health: {
    labelKey: "providerAppleHealth",
    descriptionKey: "providerAppleHealthDescription",
    tone: "ok",
    icon: <IconPhone size={22} />,
  },
};

const PROVIDER_ORDER: WearableProvider[] = ["whoop", "oura", "apple_health"];

async function copyToClipboard(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    // Clipboard access needs a secure context; the value stays selectable.
    return false;
  }
}

function CopyRow({ label, value, t }: { label: string; value: string; t: T }) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <span className="field-label">{label}</span>
      <div className="mt-1.5 flex items-stretch gap-2">
        <code className="min-w-0 flex-1 select-all overflow-x-auto whitespace-nowrap rounded-xl border border-line bg-raised px-3 py-2.5 text-xs text-ink">
          {value}
        </code>
        <Button
          variant="secondary"
          type="button"
          icon={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
          className="shrink-0"
          onClick={() => {
            void copyToClipboard(value).then((ok) => {
              if (ok) {
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              }
            });
          }}
        >
          {copied ? t.copied : t.copy}
        </Button>
      </div>
    </div>
  );
}

function StatusChip({ status, t }: { status: IntegrationStatus; t: T }) {
  if (status.connected && status.last_sync_status === "failed") {
    return <Chip tone="warn">{t.deviceNeedsAttention}</Chip>;
  }
  if (status.connected) return <Chip tone="ok">{t.deviceConnected}</Chip>;
  if (!status.configured) return <Chip tone="neutral">{t.deviceNotAvailable}</Chip>;
  return <Chip tone="neutral">{t.deviceNotConnected}</Chip>;
}

function OuraTokenForm({
  t,
  isBusy,
  onSubmit,
}: {
  t: T;
  isBusy: boolean;
  onSubmit: (token: string) => void;
}) {
  const [token, setToken] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token.trim()) return;
    onSubmit(token.trim());
    setToken("");
  }

  return (
    <form
      className="mt-3 space-y-3 rounded-xl border border-line bg-raised p-4"
      onSubmit={handleSubmit}
    >
      <p className="text-sm leading-snug text-muted">{t.ouraTokenHelp}</p>
      <a
        href="https://cloud.ouraring.com/personal-access-tokens"
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand underline"
      >
        <IconLink size={15} /> cloud.ouraring.com
      </a>
      <Field label={t.ouraTokenLabel}>
        <TextInput
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
          autoComplete="off"
          spellCheck={false}
        />
      </Field>
      <Button type="submit" loading={isBusy} disabled={!token.trim()}>
        {t.connectDevice}
      </Button>
    </form>
  );
}

function AppleHealthSetup({ t, token }: { t: T; token: AppleHealthToken | null }) {
  const steps = [t.appleStep1, t.appleStep2, t.appleStep3, t.appleStep4];
  return (
    <div className="mt-3 space-y-4 rounded-xl border border-line bg-raised p-4">
      <p className="text-sm leading-snug text-muted">{t.appleHealthHelp}</p>
      {token ? (
        <div className="space-y-3">
          <CopyRow label={t.appleIngestUrl} value={token.ingest_url} t={t} />
          <CopyRow label={t.appleIngestToken} value={token.ingest_token} t={t} />
          <p className="flex items-start gap-2 rounded-xl bg-warn-soft px-3 py-2.5 text-xs font-semibold leading-snug text-warn">
            <IconAlert size={15} className="mt-px shrink-0" />
            {t.appleTokenOnce}
          </p>
          <ol className="space-y-2">
            {steps.map((step, index) => (
              <li key={step} className="flex gap-3 text-sm leading-snug text-ink">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand-ink">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <p className="text-sm text-subtle">{t.appleTokenHint}</p>
      )}
    </div>
  );
}

function ProviderCard({
  t,
  locale,
  status,
  appleToken,
  busyProvider,
  onConnectOAuth,
  onConnectOuraToken,
  onCreateAppleToken,
  onSync,
  onDisconnect,
  onToggleCycleSync,
}: {
  t: T;
  locale: string;
  status: IntegrationStatus;
  appleToken: AppleHealthToken | null;
  busyProvider: WearableProvider | null;
  onConnectOAuth: (provider: WearableProvider) => void;
  onConnectOuraToken: (token: string) => void;
  onCreateAppleToken: () => void;
  onSync: (provider: WearableProvider) => void;
  onDisconnect: (provider: WearableProvider) => void;
  onToggleCycleSync: (provider: WearableProvider, enabled: boolean) => void;
}) {
  const meta = PROVIDER_META[status.provider];
  const isBusy = busyProvider === status.provider;
  const [showSetup, setShowSetup] = useState(false);

  const isApple = status.provider === "apple_health";
  const isOura = status.provider === "oura";

  return (
    <Card className="animate-fadeUp">
      <CardHeader
        title={t[meta.labelKey]}
        subtitle={t[meta.descriptionKey]}
        icon={meta.icon}
        tone={meta.tone}
        action={<StatusChip status={status} t={t} />}
      />

      {status.connected && (
        <dl className="mb-4 grid gap-2 text-sm sm:grid-cols-2">
          <div className="rounded-xl border border-line bg-raised px-3.5 py-2.5">
            <dt className="text-xs font-semibold uppercase tracking-wide text-subtle">
              {t.lastSync}
            </dt>
            <dd className="mt-0.5 font-semibold text-ink">
              {formatDateTime(status.last_sync_at, locale)}
            </dd>
          </div>
          <div className="rounded-xl border border-line bg-raised px-3.5 py-2.5">
            <dt className="text-xs font-semibold uppercase tracking-wide text-subtle">
              {t.lastDeviceData}
            </dt>
            <dd className="mt-0.5 font-semibold text-ink">
              {status.last_data_date ? formatShortDate(status.last_data_date, locale) : t.never}
            </dd>
          </div>
        </dl>
      )}

      {status.last_error && (
        <p className="mb-4 flex items-start gap-2 rounded-xl bg-danger-soft px-3.5 py-2.5 text-xs font-semibold leading-snug text-danger">
          <IconAlert size={15} className="mt-px shrink-0" />
          {status.last_error}
        </p>
      )}

      {!status.configured && !status.connected && (
        <p className="mb-4 rounded-xl border border-dashed border-line px-3.5 py-2.5 text-sm leading-snug text-muted">
          {t.deviceNotConfiguredHint}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {status.connected ? (
          <>
            {!isApple && (
              <Button
                variant="secondary"
                icon={<IconRefresh size={18} />}
                loading={isBusy}
                onClick={() => onSync(status.provider)}
              >
                {t.syncNow}
              </Button>
            )}
            {isApple && (
              <Button
                variant="secondary"
                icon={<IconPhone size={18} />}
                onClick={() => {
                  setShowSetup(true);
                  onCreateAppleToken();
                }}
              >
                {t.newIngestToken}
              </Button>
            )}
            <Button
              variant="danger"
              icon={<IconUnlink size={18} />}
              onClick={() => onDisconnect(status.provider)}
            >
              {t.disconnectDevice}
            </Button>
          </>
        ) : (
          <>
            {status.supports_oauth && (
              <Button
                icon={<IconLink size={18} />}
                loading={isBusy}
                onClick={() => onConnectOAuth(status.provider)}
              >
                {t.connectDevice}
              </Button>
            )}
            {isApple && (
              <Button
                icon={<IconPhone size={18} />}
                onClick={() => {
                  setShowSetup(true);
                  onCreateAppleToken();
                }}
              >
                {t.setUpDevice}
              </Button>
            )}
            {isOura && !status.supports_oauth && (
              <Button variant="secondary" onClick={() => setShowSetup((open) => !open)}>
                {showSetup ? t.hideSetup : t.usePersonalToken}
              </Button>
            )}
          </>
        )}
      </div>

      {status.connected && (
        <div className="mt-4 border-t border-line pt-4">
          <Switch
            label={t.cycleSyncLabel}
            description={t.cycleSyncHint}
            tone="bloom"
            checked={status.sync_cycle}
            onChange={(value) => onToggleCycleSync(status.provider, value)}
          />
        </div>
      )}

      {isOura && showSetup && !status.connected && (
        <OuraTokenForm t={t} isBusy={isBusy} onSubmit={onConnectOuraToken} />
      )}
      {isApple && (showSetup || appleToken) && <AppleHealthSetup t={t} token={appleToken} />}
    </Card>
  );
}

export function IntegrationsView({
  t,
  locale,
  statuses,
  daily,
  appleToken,
  busyProvider,
  onConnectOAuth,
  onConnectOuraToken,
  onCreateAppleToken,
  onSync,
  onDisconnect,
  onToggleCycleSync,
}: {
  t: T;
  locale: string;
  statuses: IntegrationStatus[];
  daily: WearableDaily[];
  appleToken: AppleHealthToken | null;
  busyProvider: WearableProvider | null;
  onConnectOAuth: (provider: WearableProvider) => void;
  onConnectOuraToken: (token: string) => void;
  onCreateAppleToken: () => void;
  onSync: (provider: WearableProvider) => void;
  onDisconnect: (provider: WearableProvider) => void;
  onToggleCycleSync: (provider: WearableProvider, enabled: boolean) => void;
}) {
  const ordered = PROVIDER_ORDER.map((provider) =>
    statuses.find((status) => status.provider === provider),
  ).filter((status): status is IntegrationStatus => status !== undefined);

  return (
    <>
      <Card className="animate-fadeUp">
        <CardHeader
          title={t.devicesTitle}
          subtitle={t.devicesIntro}
          icon={<IconWatch size={20} />}
          tone="brand"
        />
        <p className="rounded-xl border border-line bg-raised px-4 py-3 text-sm leading-snug text-muted">
          {t.devicesPrivacyNote}
        </p>
      </Card>

      {ordered.map((status) => (
        <ProviderCard
          key={status.provider}
          t={t}
          locale={locale}
          status={status}
          appleToken={status.provider === "apple_health" ? appleToken : null}
          busyProvider={busyProvider}
          onConnectOAuth={onConnectOAuth}
          onConnectOuraToken={onConnectOuraToken}
          onCreateAppleToken={onCreateAppleToken}
          onSync={onSync}
          onDisconnect={onDisconnect}
          onToggleCycleSync={onToggleCycleSync}
        />
      ))}

      <Card className="animate-fadeUp">
        <CardHeader title={t.deviceData} icon={<IconHeart size={20} />} tone="neutral" />
        {daily.length === 0 ? (
          <EmptyState
            icon={<IconMoonSleep size={22} />}
            title={t.noDeviceData}
            description={t.noDeviceDataHint}
          />
        ) : (
          /* A row per day rather than a table: on a phone a six-column table
             would need sideways scrolling to read a single night. */
          <ul className="space-y-2.5">
            {daily.slice(0, 14).map((row) => (
              <li key={row.id} className="rounded-xl border border-line bg-raised px-3.5 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[15px] font-bold text-ink">
                    {formatShortDate(row.date, locale)}
                  </p>
                  <p className="text-xs font-semibold text-subtle">
                    {t[PROVIDER_META[row.provider].labelKey]}
                  </p>
                </div>
                <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
                  {[
                    {
                      key: "sleep",
                      label: t.sleep,
                      value: row.sleep_hours === null ? null : `${row.sleep_hours.toFixed(1)} h`,
                    },
                    {
                      key: "readiness",
                      label: t.readiness,
                      value: row.readiness_score === null ? null : String(row.readiness_score),
                    },
                    {
                      key: "hrv",
                      label: "HRV",
                      value: row.hrv_ms === null ? null : `${Math.round(row.hrv_ms)} ms`,
                    },
                    {
                      key: "rhr",
                      label: t.restingHr,
                      value: row.resting_hr === null ? null : `${Math.round(row.resting_hr)} bpm`,
                    },
                    {
                      key: "steps",
                      label: t.steps,
                      value: row.steps === null ? null : row.steps.toLocaleString(locale),
                    },
                  ]
                    .filter((item) => item.value !== null)
                    .map((item) => (
                      <div key={item.key} className="flex items-baseline gap-1.5">
                        <dt className="font-semibold uppercase tracking-wide text-subtle">
                          {item.label}
                        </dt>
                        <dd className="font-bold tabular-nums text-ink">{item.value}</dd>
                      </div>
                    ))}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
