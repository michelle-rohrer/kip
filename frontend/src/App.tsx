import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = {
  id: number;
  email: string;
  role: "player" | "coach";
  team_id: number | null;
  name: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type WellnessEntry = {
  id: number;
  date: string;
  sleep_hours: number;
  sleep_quality: number;
  muscle_soreness: number;
  mental_energy: number;
  stress_level: number;
  motivation: number;
  rpe_previous_day: number | null;
  free_text: string | null;
};

type CycleEntry = {
  id: number;
  date: string;
  cycle_day: number;
  phase: "menstruation" | "follicular" | "ovulation" | "luteal";
  cycle_length: number;
  pms_score: number | null;
  cramps: boolean;
  migraine: boolean;
  fatigue: boolean;
  contraception_type: string | null;
  notes: string | null;
};

type PrivacyConsent = {
  id: number;
  coach_id: number;
  share_cycle_data: boolean;
  share_wellness_data: boolean;
};

type Prediction = {
  id?: number;
  player_id?: number;
  date?: string;
  risk_score: number;
  risk_level: "green" | "yellow" | "red";
  model_version: string;
  features_used?: Record<string, unknown>;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ACCESS_TOKEN_KEY = "kip_access_token";
const REFRESH_TOKEN_KEY = "kip_refresh_token";

type PlayerTab = "dashboard" | "wellness" | "cycle" | "privacy";
type CoachTab = "team" | "detail";
type AppTab = PlayerTab | CoachTab;

type TrainingEntry = {
  id: number;
  date: string;
  duration_min: number;
  intensity: number;
  jump_count: number | null;
};

async function apiRequest<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

function riskColor(level: Prediction["risk_level"]) {
  if (level === "red") return "bg-red-500";
  if (level === "yellow") return "bg-amber-400";
  return "bg-emerald-500";
}

function formatTrendPoints(values: number[]) {
  if (values.length === 0) {
    return "";
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const spread = Math.max(max - min, 1);
  return values
    .map((value, idx) => {
      const x = (idx / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - ((value - min) / spread) * 100;
      return `${x},${y}`;
    })
    .join(" ");
}

function App() {
  const [email, setEmail] = useState("synthetic.coach.01@kip.local");
  const [password, setPassword] = useState("synthetic-seed-password");
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<AppTab>("dashboard");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [wellness, setWellness] = useState<WellnessEntry[]>([]);
  const [cycle, setCycle] = useState<CycleEntry[]>([]);
  const [consents, setConsents] = useState<PrivacyConsent[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [teamPredictions, setTeamPredictions] = useState<Prediction[]>([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedPlayerWellness, setSelectedPlayerWellness] = useState<WellnessEntry[]>([]);
  const [selectedPlayerCycle, setSelectedPlayerCycle] = useState<CycleEntry[]>([]);
  const [selectedPlayerTraining, setSelectedPlayerTraining] = useState<TrainingEntry[]>([]);
  const [selectedPlayerCycleBlocked, setSelectedPlayerCycleBlocked] = useState(false);
  const [selectedPlayerWellnessBlocked, setSelectedPlayerWellnessBlocked] = useState(false);

  const [wellnessForm, setWellnessForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    sleep_hours: 8,
    sleep_quality: 7,
    muscle_soreness: 4,
    mental_energy: 7,
    stress_level: 4,
    motivation: 8,
    rpe_previous_day: 6,
    free_text: "",
  });
  const [cycleForm, setCycleForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    cycle_day: 1,
    phase: "menstruation" as CycleEntry["phase"],
    cycle_length: 28,
    pms_score: 0,
    cramps: false,
    migraine: false,
    fatigue: false,
    contraception_type: "",
    notes: "",
  });

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setWellness([]);
    setCycle([]);
    setConsents([]);
    setPrediction(null);
    setTeamPredictions([]);
    setSelectedPlayerId(null);
    setSelectedPlayerWellness([]);
    setSelectedPlayerCycle([]);
    setSelectedPlayerTraining([]);
    setSelectedPlayerCycleBlocked(false);
    setSelectedPlayerWellnessBlocked(false);
    setMessage("Abgemeldet.");
  }, []);

  const loadPlayerData = useCallback(async () => {
    if (!accessToken || !user || user.role !== "player") return;
    setIsLoading(true);
    setError(null);
    try {
      const [wellnessEntries, cycleEntries, privacyConsents, risk] = await Promise.all([
        apiRequest<WellnessEntry[]>("/api/wellness/", undefined, accessToken),
        apiRequest<CycleEntry[]>("/api/cycle/", undefined, accessToken),
        apiRequest<PrivacyConsent[]>("/api/privacy/consent", undefined, accessToken),
        apiRequest<Prediction>(`/api/predictions/${user.id}`, undefined, accessToken),
      ]);
      setWellness(wellnessEntries);
      setCycle(cycleEntries);
      setConsents(privacyConsents);
      setPrediction(risk);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler beim Laden.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, user]);

  const loadCoachData = useCallback(async () => {
    if (!accessToken || !user || user.role !== "coach") return;
    setIsLoading(true);
    setError(null);
    try {
      const team = await apiRequest<Prediction[]>("/api/predictions/team", undefined, accessToken);
      setTeamPredictions(team);
      if (team.length > 0 && selectedPlayerId === null) {
        setSelectedPlayerId(team[0].player_id ?? null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Teamdaten konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, user, selectedPlayerId]);

  const loadCoachPlayerDetail = useCallback(async () => {
    if (!accessToken || !user || user.role !== "coach" || !selectedPlayerId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [wellnessRes, cycleRes, trainingRes] = await Promise.allSettled([
        apiRequest<WellnessEntry[]>(`/api/wellness/${selectedPlayerId}`, undefined, accessToken),
        apiRequest<CycleEntry[]>(`/api/cycle/${selectedPlayerId}`, undefined, accessToken),
        apiRequest<TrainingEntry[]>(`/api/training/${selectedPlayerId}`, undefined, accessToken),
      ]);

      if (wellnessRes.status === "fulfilled") {
        setSelectedPlayerWellness(wellnessRes.value);
        setSelectedPlayerWellnessBlocked(false);
      } else {
        setSelectedPlayerWellness([]);
        setSelectedPlayerWellnessBlocked(true);
      }

      if (cycleRes.status === "fulfilled") {
        setSelectedPlayerCycle(cycleRes.value);
        setSelectedPlayerCycleBlocked(false);
      } else {
        setSelectedPlayerCycle([]);
        setSelectedPlayerCycleBlocked(true);
      }

      if (trainingRes.status === "fulfilled") {
        setSelectedPlayerTraining(trainingRes.value);
      } else {
        setSelectedPlayerTraining([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Detaildaten konnten nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, user, selectedPlayerId]);

  useEffect(() => {
    if (!accessToken) return;
    apiRequest<User>("/api/auth/me", undefined, accessToken)
      .then((me) => {
        setUser(me);
        setTab(me.role === "coach" ? "team" : "dashboard");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Session konnte nicht geladen werden.");
        logout();
      });
  }, [accessToken, logout]);

  useEffect(() => {
    if (user?.role === "player") {
      void loadPlayerData();
      return;
    }
    if (user?.role === "coach") {
      void loadCoachData();
    }
  }, [loadCoachData, loadPlayerData, user?.role]);

  useEffect(() => {
    if (user?.role === "coach") {
      void loadCoachPlayerDetail();
    }
  }, [loadCoachPlayerDetail, user?.role]);

  const wellnessTrend = useMemo(() => {
    return wellness
      .slice(0, 7)
      .reverse()
      .map((entry) => Math.round((entry.sleep_quality + entry.mental_energy + entry.motivation) / 3));
  }, [wellness]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const tokens = await apiRequest<TokenResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      setMessage("Login erfolgreich.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login fehlgeschlagen.");
    }
  }

  async function handleWellnessSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setError(null);
    try {
      await apiRequest<WellnessEntry>("/api/wellness/", {
        method: "POST",
        body: JSON.stringify({
          ...wellnessForm,
          rpe_previous_day: wellnessForm.rpe_previous_day || null,
          free_text: wellnessForm.free_text || null,
        }),
      }, accessToken);
      setMessage("Wellness-Check gespeichert.");
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Wellness konnte nicht gespeichert werden.");
    }
  }

  async function handleCycleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setError(null);
    try {
      await apiRequest<CycleEntry>("/api/cycle/", {
        method: "POST",
        body: JSON.stringify({
          ...cycleForm,
          pms_score: cycleForm.pms_score || null,
          contraception_type: cycleForm.contraception_type || null,
          notes: cycleForm.notes || null,
        }),
      }, accessToken);
      setMessage("Zyklus-Eintrag gespeichert.");
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Zyklus-Eintrag konnte nicht gespeichert werden.");
    }
  }

  async function handlePrivacySave(consent: PrivacyConsent) {
    if (!accessToken) return;
    setError(null);
    try {
      await apiRequest<PrivacyConsent>("/api/privacy/consent", {
        method: "PUT",
        body: JSON.stringify({
          coach_id: consent.coach_id,
          share_cycle_data: consent.share_cycle_data,
          share_wellness_data: consent.share_wellness_data,
        }),
      }, accessToken);
      setMessage(`Freigaben fuer Coach ${consent.coach_id} gespeichert.`);
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Privacy-Einstellungen konnten nicht gespeichert werden.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <section className="mx-auto max-w-5xl px-6 py-10">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">{user?.role === "coach" ? "Trainerinnen-App" : "Spielerinnen-App"}</h1>
            <p className="mt-1 text-slate-700">
              {user?.role === "coach"
                ? "Team-Uebersicht mit Ampelsystem und Detailansichten."
                : "Wellness, Zyklus, Risiko-Dashboard und Privacy-Freigaben."}
            </p>
          </div>
          {user && (
            <button className="rounded bg-slate-800 px-4 py-2 text-white" onClick={logout} type="button">
              Logout
            </button>
          )}
        </header>

        {error && <p className="mb-4 rounded bg-red-100 px-4 py-2 text-sm text-red-800">{error}</p>}
        {message && <p className="mb-4 rounded bg-emerald-100 px-4 py-2 text-sm text-emerald-800">{message}</p>}

        {!user && (
          <form className="max-w-md space-y-3 rounded bg-white p-6 shadow" onSubmit={handleLogin}>
            <h2 className="text-xl font-semibold">Login</h2>
            <label className="block text-sm">
              E-Mail
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                required
              />
            </label>
            <label className="block text-sm">
              Passwort
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                required
              />
            </label>
            <button className="w-full rounded bg-blue-600 px-4 py-2 font-medium text-white" type="submit">
              Einloggen
            </button>
          </form>
        )}

        {user && (
          <>
            <nav className="mb-6 flex flex-wrap gap-2">
              {(user.role === "coach"
                ? [
                    { key: "team", label: "Team-Uebersicht" },
                    { key: "detail", label: "Spielerinnen-Detail" },
                  ]
                : [
                    { key: "dashboard", label: "Dashboard" },
                    { key: "wellness", label: "Wellness-Check" },
                    { key: "cycle", label: "Zyklus" },
                    { key: "privacy", label: "Privacy-Settings" },
                  ]
              ).map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setTab(item.key as AppTab)}
                  className={`rounded px-4 py-2 text-sm font-medium ${
                    tab === item.key ? "bg-blue-600 text-white" : "bg-white text-slate-700 shadow"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>

            {isLoading && <p className="mb-4 text-sm text-slate-600">Daten werden geladen...</p>}

            {user.role === "player" && tab === "dashboard" && (
              <section className="grid gap-4 md:grid-cols-2">
                <article className="rounded bg-white p-4 shadow">
                  <h3 className="text-lg font-semibold">Aktueller Risiko-Score</h3>
                  {prediction ? (
                    <div className="mt-3 flex items-center gap-3">
                      <span className={`h-4 w-4 rounded-full ${riskColor(prediction.risk_level)}`} />
                      <p>
                        {prediction.risk_level.toUpperCase()} - {(prediction.risk_score * 100).toFixed(1)}%
                      </p>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">Keine Vorhersage vorhanden.</p>
                  )}
                </article>
                <article className="rounded bg-white p-4 shadow">
                  <h3 className="text-lg font-semibold">Wellness-Trend (7 Tage)</h3>
                  {wellnessTrend.length > 1 ? (
                    <svg viewBox="0 0 100 100" className="mt-3 h-28 w-full rounded bg-slate-100 p-2">
                      <polyline
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="3"
                        points={formatTrendPoints(wellnessTrend)}
                      />
                    </svg>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">Noch nicht genug Eintraege fuer eine Trendanzeige.</p>
                  )}
                </article>
                <article className="rounded bg-white p-4 shadow md:col-span-2">
                  <h3 className="text-lg font-semibold">Letzte Eintraege</h3>
                  <div className="mt-3 grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="font-medium">Wellness</p>
                      <ul className="mt-2 text-sm text-slate-700">
                        {wellness.slice(0, 3).map((entry) => (
                          <li key={entry.id}>{entry.date}: Schlaf {entry.sleep_hours}h, Energie {entry.mental_energy}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium">Zyklus</p>
                      <ul className="mt-2 text-sm text-slate-700">
                        {cycle.slice(0, 3).map((entry) => (
                          <li key={entry.id}>{entry.date}: Tag {entry.cycle_day}, Phase {entry.phase}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </article>
              </section>
            )}

            {user.role === "player" && tab === "wellness" && (
              <form className="space-y-3 rounded bg-white p-6 shadow" onSubmit={handleWellnessSubmit}>
                <h3 className="text-lg font-semibold">Wellness-Check</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm">
                    Datum
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="date"
                      value={wellnessForm.date}
                      onChange={(event) => setWellnessForm((prev) => ({ ...prev, date: event.target.value }))}
                    />
                  </label>
                  <label className="text-sm">
                    Schlafstunden
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={1}
                      max={24}
                      step={0.5}
                      value={wellnessForm.sleep_hours}
                      onChange={(event) =>
                        setWellnessForm((prev) => ({ ...prev, sleep_hours: Number(event.target.value) }))
                      }
                    />
                  </label>
                  {[
                    { key: "sleep_quality", label: "Schlafqualitaet" },
                    { key: "muscle_soreness", label: "Muskelkater" },
                    { key: "mental_energy", label: "Mentale Energie" },
                    { key: "stress_level", label: "Stress" },
                    { key: "motivation", label: "Motivation" },
                    { key: "rpe_previous_day", label: "RPE Vortag" },
                  ].map((item) => (
                    <label key={item.key} className="text-sm">
                      {item.label} (1-10)
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="number"
                        min={1}
                        max={10}
                        value={wellnessForm[item.key as keyof typeof wellnessForm]}
                        onChange={(event) =>
                          setWellnessForm((prev) => ({
                            ...prev,
                            [item.key]: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
                <label className="block text-sm">
                  Notiz
                  <textarea
                    className="mt-1 w-full rounded border px-3 py-2"
                    rows={3}
                    value={wellnessForm.free_text}
                    onChange={(event) => setWellnessForm((prev) => ({ ...prev, free_text: event.target.value }))}
                  />
                </label>
                <button className="rounded bg-blue-600 px-4 py-2 text-white" type="submit">
                  Wellness speichern
                </button>
              </form>
            )}

            {user.role === "player" && tab === "cycle" && (
              <form className="space-y-3 rounded bg-white p-6 shadow" onSubmit={handleCycleSubmit}>
                <h3 className="text-lg font-semibold">Zyklus-Tracking</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm">
                    Datum
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="date"
                      value={cycleForm.date}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, date: event.target.value }))}
                    />
                  </label>
                  <label className="text-sm">
                    Zyklustag
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={1}
                      max={60}
                      value={cycleForm.cycle_day}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, cycle_day: Number(event.target.value) }))}
                    />
                  </label>
                  <label className="text-sm">
                    Zykluslaenge
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={20}
                      max={45}
                      value={cycleForm.cycle_length}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, cycle_length: Number(event.target.value) }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    Phase
                    <select
                      className="mt-1 w-full rounded border px-3 py-2"
                      value={cycleForm.phase}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, phase: event.target.value as CycleEntry["phase"] }))
                      }
                    >
                      <option value="menstruation">Menstruation</option>
                      <option value="follicular">Follikular</option>
                      <option value="ovulation">Ovulation</option>
                      <option value="luteal">Luteal</option>
                    </select>
                  </label>
                  <label className="text-sm">
                    PMS-Score (0-10)
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={0}
                      max={10}
                      value={cycleForm.pms_score}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, pms_score: Number(event.target.value) }))}
                    />
                  </label>
                  <label className="text-sm">
                    Verhuetung
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      value={cycleForm.contraception_type}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, contraception_type: event.target.value }))
                      }
                    />
                  </label>
                </div>
                <div className="flex flex-wrap gap-4 text-sm">
                  <label>
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={cycleForm.cramps}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, cramps: event.target.checked }))}
                    />
                    Kraempfe
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={cycleForm.migraine}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, migraine: event.target.checked }))}
                    />
                    Migraene
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={cycleForm.fatigue}
                      onChange={(event) => setCycleForm((prev) => ({ ...prev, fatigue: event.target.checked }))}
                    />
                    Muedigkeit
                  </label>
                </div>
                <label className="block text-sm">
                  Notiz
                  <textarea
                    className="mt-1 w-full rounded border px-3 py-2"
                    rows={3}
                    value={cycleForm.notes}
                    onChange={(event) => setCycleForm((prev) => ({ ...prev, notes: event.target.value }))}
                  />
                </label>
                <button className="rounded bg-blue-600 px-4 py-2 text-white" type="submit">
                  Zyklus speichern
                </button>
              </form>
            )}

            {user.role === "player" && tab === "privacy" && (
              <section className="rounded bg-white p-6 shadow">
                <h3 className="text-lg font-semibold">Privacy-Settings</h3>
                {consents.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">Keine Coach-Freigaben vorhanden.</p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {consents.map((consent) => (
                      <article key={consent.id} className="rounded border p-3">
                        <p className="mb-2 font-medium">Coach ID: {consent.coach_id}</p>
                        <div className="flex flex-wrap gap-4 text-sm">
                          <label>
                            <input
                              type="checkbox"
                              className="mr-2"
                              checked={consent.share_wellness_data}
                              onChange={(event) =>
                                setConsents((prev) =>
                                  prev.map((item) =>
                                    item.id === consent.id ? { ...item, share_wellness_data: event.target.checked } : item,
                                  ),
                                )
                              }
                            />
                            Wellness teilen
                          </label>
                          <label>
                            <input
                              type="checkbox"
                              className="mr-2"
                              checked={consent.share_cycle_data}
                              onChange={(event) =>
                                setConsents((prev) =>
                                  prev.map((item) =>
                                    item.id === consent.id ? { ...item, share_cycle_data: event.target.checked } : item,
                                  ),
                                )
                              }
                            />
                            Zyklus teilen
                          </label>
                          <button
                            className="rounded bg-slate-800 px-3 py-1 text-white"
                            type="button"
                            onClick={() => void handlePrivacySave(consent)}
                          >
                            Speichern
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            )}

            {user.role === "coach" && tab === "team" && (
              <section className="rounded bg-white p-6 shadow">
                <h3 className="text-lg font-semibold">Team-Uebersicht</h3>
                {teamPredictions.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">Keine Spielerinnen mit Vorhersage gefunden.</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {[...teamPredictions]
                      .sort((a, b) => b.risk_score - a.risk_score)
                      .map((item) => (
                        <li
                          key={`${item.player_id}-${item.date ?? "today"}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded border p-3"
                        >
                          <div className="flex items-center gap-3">
                            <span className={`h-4 w-4 rounded-full ${riskColor(item.risk_level)}`} />
                            <p className="font-medium">Spielerin #{item.player_id}</p>
                          </div>
                          <div className="flex items-center gap-3 text-sm">
                            <span>
                              {(item.risk_score * 100).toFixed(1)}% - {item.risk_level.toUpperCase()}
                            </span>
                            <button
                              type="button"
                              className="rounded bg-slate-800 px-3 py-1 text-white"
                              onClick={() => {
                                setSelectedPlayerId(item.player_id ?? null);
                                setTab("detail");
                              }}
                            >
                              Detail
                            </button>
                          </div>
                        </li>
                      ))}
                  </ul>
                )}
              </section>
            )}

            {user.role === "coach" && tab === "detail" && (
              <section className="space-y-4 rounded bg-white p-6 shadow">
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <p className="text-sm text-slate-600">Spielerin waehlen</p>
                    <select
                      className="mt-1 rounded border px-3 py-2"
                      value={selectedPlayerId ?? ""}
                      onChange={(event) => setSelectedPlayerId(Number(event.target.value))}
                    >
                      {teamPredictions.map((item) => (
                        <option key={`sel-${item.player_id}`} value={item.player_id}>
                          Spielerin #{item.player_id}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    className="rounded bg-blue-600 px-4 py-2 text-white"
                    onClick={() => void loadCoachPlayerDetail()}
                  >
                    Aktualisieren
                  </button>
                </div>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">Wellness-Verlauf</h4>
                  {selectedPlayerWellnessBlocked ? (
                    <p className="mt-2 text-sm text-amber-700">Wellnessdaten sind nicht freigegeben.</p>
                  ) : selectedPlayerWellness.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">Keine Wellness-Daten vorhanden.</p>
                  ) : (
                    <ul className="mt-2 space-y-1 text-sm">
                      {selectedPlayerWellness.slice(0, 7).map((entry) => (
                        <li key={entry.id}>
                          {entry.date}: Energie {entry.mental_energy}, Motivation {entry.motivation}, Schlaf{" "}
                          {entry.sleep_hours}h
                        </li>
                      ))}
                    </ul>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">Trainingsbelastung</h4>
                  {selectedPlayerTraining.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">Keine Trainingsdaten vorhanden.</p>
                  ) : (
                    <ul className="mt-2 space-y-1 text-sm">
                      {selectedPlayerTraining.slice(0, 7).map((entry) => (
                        <li key={entry.id}>
                          {entry.date}: {entry.duration_min} min bei Intensitaet {entry.intensity}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">Zyklusdaten</h4>
                  {selectedPlayerCycleBlocked ? (
                    <p className="mt-2 text-sm text-amber-700">Zyklusdaten sind nicht freigegeben.</p>
                  ) : selectedPlayerCycle.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">Keine Zyklusdaten vorhanden.</p>
                  ) : (
                    <ul className="mt-2 space-y-1 text-sm">
                      {selectedPlayerCycle.slice(0, 7).map((entry) => (
                        <li key={entry.id}>
                          {entry.date}: Tag {entry.cycle_day}, Phase {entry.phase}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">Verletzungshistorie</h4>
                  <p className="mt-2 text-sm text-slate-600">
                    Fuer Verletzungen existiert aktuell noch kein Coach-Read-Endpoint im Backend.
                  </p>
                </article>
              </section>
            )}
          </>
        )}
      </section>
    </main>
  );
}

export default App;
