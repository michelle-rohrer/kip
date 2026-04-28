import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import volleySyncIcon from "./assets/app_icon.png";
import { LANGUAGE_KEY, LOCALES, TEXT, Language } from "./i18n";

type User = {
  id: number;
  username: string;
  email: string | null;
  role: "player" | "coach";
  team_id: number | null;
  training_uid: string | null;
  player_position: string | null;
  name: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type TeamOption = {
  id: number;
  name: string;
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

type InjuryEntry = {
  id: number;
  player_id: number;
  date: string;
  body_location: string;
  pain_intensity: number;
  is_chronic: boolean;
  medical_attention: boolean;
  time_loss_days: number;
  description: string | null;
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
  coach_name?: string | null;
  share_cycle_data: boolean;
  share_wellness_data: boolean;
};

type Prediction = {
  id?: number;
  player_id?: number;
  player_name?: string | null;
  date?: string;
  risk_score: number;
  risk_level: "green" | "yellow" | "red";
  model_version: string;
  features_used?: Record<string, unknown>;
  player_position?: string | null;
  latest_training_date?: string | null;
  latest_session_rpe?: number | null;
  latest_session_type?: string | null;
  latest_participation_status?: string | null;
  latest_injury_date?: string | null;
  latest_pain_intensity?: number | null;
  latest_medical_attention?: boolean | null;
  latest_time_loss_days?: number | null;
};

type ModelTrainingStatus = {
  status: "ok" | "failed";
  updated_at: string;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  error?: string | null;
  metrics?: Record<string, unknown> | null;
  context?: Record<string, unknown> | null;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ACCESS_TOKEN_KEY = "kip_access_token";
const REFRESH_TOKEN_KEY = "kip_refresh_token";

type PlayerTab = "dashboard" | "wellness" | "cycle" | "training" | "injury" | "privacy";
type CoachTab = "team" | "detail";
type AppTab = PlayerTab | CoachTab;

type TrainingEntry = {
  id: number;
  date: string;
  duration_min: number;
  intensity: number;
  jump_count: number | null;
  session_rpe: number | null;
  session_type: string | null;
  participation_status: string | null;
};

async function apiRequest<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || `HTTP ${response.status}`);
    } catch {
      throw new Error(text || `HTTP ${response.status}`);
    }
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

function formatSleepHours(hours: number) {
  return hours.toFixed(1);
}

function formatShortDate(isoDate: string, locale: string) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString(locale, { day: "2-digit", month: "2-digit" });
}

function formatDateTime(value: string | null | undefined, locale: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale);
}

function mapPositionLabel(position: string | null | undefined, t: Record<string, string>) {
  if (!position) return "-";
  if (position === "setter") return t.posSetter;
  if (position === "outside_hitter") return t.posOutsideHitter;
  if (position === "opposite") return t.posOpposite;
  if (position === "middle_blocker") return t.posMiddleBlocker;
  if (position === "libero") return t.posLibero;
  return position;
}

function mapSessionTypeLabel(value: string | null | undefined, t: Record<string, string>) {
  if (!value) return "-";
  if (value === "team") return t.sessionTypeTeam;
  if (value === "strength") return t.sessionTypeStrength;
  if (value === "technical") return t.sessionTypeTechnical;
  if (value === "recovery") return t.sessionTypeRecovery;
  return value;
}

function mapParticipationLabel(value: string | null | undefined, t: Record<string, string>) {
  if (!value) return "-";
  if (value === "full") return t.participationFull;
  if (value === "modified") return t.participationModified;
  if (value === "individual") return t.participationIndividual;
  if (value === "rest") return t.participationRest;
  return value;
}

function App() {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    if (saved === "de" || saved === "en" || saved === "it") {
      return saved;
    }
    return "de";
  });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    username: "",
    email: "",
    password: "",
    name: "",
    team_id: "",
    player_position: "",
  });
  const [availableTeams, setAvailableTeams] = useState<TeamOption[]>([]);
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    sessionStorage.getItem(ACCESS_TOKEN_KEY),
  );
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<AppTab>("dashboard");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [wellness, setWellness] = useState<WellnessEntry[]>([]);
  const [cycle, setCycle] = useState<CycleEntry[]>([]);
  const [training, setTraining] = useState<TrainingEntry[]>([]);
  const [consents, setConsents] = useState<PrivacyConsent[]>([]);
  const [injuries, setInjuries] = useState<InjuryEntry[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [teamPredictions, setTeamPredictions] = useState<Prediction[]>([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedPlayerWellness, setSelectedPlayerWellness] = useState<WellnessEntry[]>([]);
  const [selectedPlayerCycle, setSelectedPlayerCycle] = useState<CycleEntry[]>([]);
  const [selectedPlayerTraining, setSelectedPlayerTraining] = useState<TrainingEntry[]>([]);
  const [selectedPlayerCycleBlocked, setSelectedPlayerCycleBlocked] = useState(false);
  const [selectedPlayerWellnessBlocked, setSelectedPlayerWellnessBlocked] = useState(false);
  const [isWellnessDetailOpen, setIsWellnessDetailOpen] = useState(false);
  const [selectedTrendIndex, setSelectedTrendIndex] = useState<number | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelTrainingStatus | null>(null);

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
  const [trainingForm, setTrainingForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    duration_min: 75,
    intensity: 6,
    session_rpe: 6,
    session_type: "team" as "team" | "strength" | "technical" | "recovery",
    participation_status: "full" as "full" | "modified" | "individual" | "rest",
    jump_count: "",
  });
  const [injuryForm, setInjuryForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    body_location: "",
    pain_intensity: 4,
    is_chronic: false,
    medical_attention: false,
    time_loss_days: 0,
    description: "",
  });
  const t = TEXT[language];
  const tt = t as Record<string, string>;
  const locale = LOCALES[language];

  useEffect(() => {
    localStorage.setItem(LANGUAGE_KEY, language);
  }, [language]);

  const logout = useCallback(() => {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    setAccessToken(null);
    setUser(null);
    setWellness([]);
    setCycle([]);
    setTraining([]);
    setConsents([]);
    setInjuries([]);
    setPrediction(null);
    setTeamPredictions([]);
    setSelectedPlayerId(null);
    setSelectedPlayerWellness([]);
    setSelectedPlayerCycle([]);
    setSelectedPlayerTraining([]);
    setSelectedPlayerCycleBlocked(false);
    setSelectedPlayerWellnessBlocked(false);
    setMessage(t.logoutDone);
  }, [t.logoutDone]);

  const loadPlayerData = useCallback(async () => {
    if (!accessToken || !user || user.role !== "player") return;
    setIsLoading(true);
    setError(null);
    try {
      const [wellnessEntries, cycleEntries, trainingEntries, injuryEntries, privacyConsents, risk] =
        await Promise.all([
        apiRequest<WellnessEntry[]>("/api/wellness/", undefined, accessToken),
        apiRequest<CycleEntry[]>("/api/cycle/", undefined, accessToken),
        apiRequest<TrainingEntry[]>("/api/training/", undefined, accessToken),
        apiRequest<InjuryEntry[]>("/api/injury/", undefined, accessToken),
        apiRequest<PrivacyConsent[]>("/api/privacy/consent", undefined, accessToken),
        apiRequest<Prediction>(`/api/predictions/${user.id}`, undefined, accessToken),
      ]);
      setWellness(wellnessEntries);
      setCycle(cycleEntries);
      setTraining(trainingEntries);
      setInjuries(injuryEntries);
      setConsents(privacyConsents);
      setPrediction(risk);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.unknownLoadError);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, t.unknownLoadError, user]);

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
      setError(e instanceof Error ? e.message : t.teamLoadFailed);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, selectedPlayerId, t.teamLoadFailed, user]);

  const loadModelStatus = useCallback(async () => {
    if (!accessToken || !user) return;
    try {
      const status = await apiRequest<ModelTrainingStatus>(
        "/api/predictions/model-status",
        undefined,
        accessToken,
      );
      setModelStatus(status);
    } catch {
      setModelStatus(null);
    }
  }, [accessToken, user]);

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
      setError(e instanceof Error ? e.message : t.detailLoadFailed);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, selectedPlayerId, t.detailLoadFailed, user]);

  const loadAvailableTeams = useCallback(async () => {
    try {
      const teams = await apiRequest<TeamOption[]>("/api/teams/");
      setAvailableTeams(teams);
    } catch {
      setAvailableTeams([]);
    }
  }, []);

  useEffect(() => {
    if (!accessToken) return;
    apiRequest<User>("/api/auth/me", undefined, accessToken)
      .then((me) => {
        setUser(me);
        setTab(me.role === "coach" ? "team" : "dashboard");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : t.sessionLoadFailed);
        logout();
      });
  }, [accessToken, logout, t.sessionLoadFailed]);

  useEffect(() => {
    if (user || !isRegisterMode) return;
    void loadAvailableTeams();
  }, [isRegisterMode, loadAvailableTeams, user]);

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
    if (!user) return;
    void loadModelStatus();
  }, [loadModelStatus, user]);

  useEffect(() => {
    if (user?.role === "coach") {
      void loadCoachPlayerDetail();
    }
  }, [loadCoachPlayerDetail, user?.role]);

  const wellnessTrend = useMemo(() => {
    return wellness
      .slice(0, 7)
      .reverse()
      .map((entry) => ({
        date: entry.date,
        sleep_quality: entry.sleep_quality,
        mental_energy: entry.mental_energy,
        motivation: entry.motivation,
        score: Math.round((entry.sleep_quality + entry.mental_energy + entry.motivation) / 3),
      }));
  }, [wellness]);

  const selectedTrendPoint = useMemo(() => {
    if (selectedTrendIndex === null) return null;
    return wellnessTrend[selectedTrendIndex] ?? null;
  }, [selectedTrendIndex, wellnessTrend]);

  const coachWellnessTrend = useMemo(
    () =>
      selectedPlayerWellness
        .slice(0, 7)
        .reverse()
        .map((entry) => ({
          date: entry.date,
          score: Math.round((entry.sleep_quality + entry.mental_energy + entry.motivation) / 3),
          sleep_quality: entry.sleep_quality,
          mental_energy: entry.mental_energy,
          motivation: entry.motivation,
        })),
    [selectedPlayerWellness],
  );

  const coachTrainingTrend = useMemo(
    () =>
      selectedPlayerTraining
        .slice(0, 7)
        .reverse()
        .map((entry) => ({
          date: entry.date,
          duration: entry.duration_min,
          intensity: entry.intensity,
        })),
    [selectedPlayerTraining],
  );

  const coachTrainingAvgDuration = useMemo(() => {
    if (coachTrainingTrend.length === 0) return 0;
    return coachTrainingTrend.reduce((sum, entry) => sum + entry.duration, 0) / coachTrainingTrend.length;
  }, [coachTrainingTrend]);

  const teamRiskAverage = useMemo(() => {
    if (teamPredictions.length === 0) return 0;
    return (
      teamPredictions.reduce((sum, predictionItem) => sum + predictionItem.risk_score, 0) /
      teamPredictions.length
    );
  }, [teamPredictions]);

  const coachPriorityList = useMemo(() => {
    return [...teamPredictions].sort((a, b) => {
      const aTimeLoss = a.latest_time_loss_days ?? 0;
      const bTimeLoss = b.latest_time_loss_days ?? 0;
      if (bTimeLoss !== aTimeLoss) return bTimeLoss - aTimeLoss;
      const aPain = a.latest_pain_intensity ?? 0;
      const bPain = b.latest_pain_intensity ?? 0;
      if (bPain !== aPain) return bPain - aPain;
      return b.risk_score - a.risk_score;
    });
  }, [teamPredictions]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const tokens = await apiRequest<TokenResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setAccessToken(tokens.access_token);
      setMessage(t.loginSuccess);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.loginFailed);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      await apiRequest<User>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: registerForm.username,
          email: registerForm.email,
          password: registerForm.password,
          role: "player",
          name: registerForm.name,
          team_id: Number(registerForm.team_id),
          player_position: registerForm.player_position,
        }),
      });
      setMessage(t.registerSuccess);
      setUsername(registerForm.username);
      setPassword(registerForm.password);
      setIsRegisterMode(false);
      setRegisterForm({
        username: "",
        email: "",
        password: "",
        name: "",
        team_id: "",
        player_position: "",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : t.registerFailed);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleWellnessSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      await apiRequest<WellnessEntry>(
        "/api/wellness/",
        {
          method: "POST",
          body: JSON.stringify({
            ...wellnessForm,
            free_text: wellnessForm.free_text || null,
          }),
        },
        accessToken,
      );
      setMessage(t.wellnessSaved);
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : t.wellnessSaveFailed);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCycleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      await apiRequest<CycleEntry>(
        "/api/cycle/",
        {
          method: "POST",
          body: JSON.stringify({
            ...cycleForm,
            contraception_type: cycleForm.contraception_type || null,
            notes: cycleForm.notes || null,
          }),
        },
        accessToken,
      );
      setMessage(t.cycleSaved);
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : t.cycleSaveFailed);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTrainingSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      await apiRequest<TrainingEntry>(
        "/api/training/",
        {
          method: "POST",
          body: JSON.stringify({
            date: trainingForm.date,
            duration_min: trainingForm.duration_min,
            intensity: trainingForm.intensity,
            session_rpe: trainingForm.session_rpe,
            session_type: trainingForm.session_type,
            participation_status: trainingForm.participation_status,
            jump_count: trainingForm.jump_count ? Number(trainingForm.jump_count) : null,
          }),
        },
        accessToken,
      );
      setMessage(tt.trainingSaved);
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : tt.trainingSaveFailed);
    } finally {
      setIsLoading(false);
    }
  }

  async function handlePrivacySave(consent: PrivacyConsent) {
    if (!accessToken) return;
    setError(null);
    try {
      await apiRequest<PrivacyConsent>(
        "/api/privacy/consent",
        {
          method: "PUT",
          body: JSON.stringify({
            coach_id: consent.coach_id,
            share_cycle_data: consent.share_cycle_data,
            share_wellness_data: consent.share_wellness_data,
          }),
        },
        accessToken,
      );
      setMessage(
        `${t.consentSavedPrefix} ${consent.coach_name ?? `${t.coach} ${consent.coach_id}`} ${t.consentSavedSuffix}`,
      );
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : t.privacySaveFailed);
    }
  }

  async function handleInjurySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) return;
    setIsLoading(true);
    setError(null);
    try {
      await apiRequest<InjuryEntry>(
        "/api/injury/",
        {
          method: "POST",
          body: JSON.stringify({
            ...injuryForm,
            description: injuryForm.description || null,
          }),
        },
        accessToken,
      );
      setMessage(tt.injurySaved);
      setInjuryForm((prev) => ({
        ...prev,
        body_location: "",
        pain_intensity: 4,
        is_chronic: false,
        medical_attention: false,
        time_loss_days: 0,
        description: "",
      }));
      await loadPlayerData();
    } catch (e) {
      setError(e instanceof Error ? e.message : tt.injurySaveFailed);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <section className="mx-auto max-w-5xl px-6 py-10">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <img
              src={volleySyncIcon}
              alt="VolleySync Icon"
              className="h-12 w-12 rounded-lg shadow-sm"
            />
            <div>
              <h1 className="text-3xl font-bold">VolleySync</h1>
              <p className="mt-1 text-slate-700">{t.appTagline}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-700">
              {t.language}
              <select
                className="ml-2 rounded border bg-white px-2 py-1 text-sm"
                value={language}
                onChange={(event) => setLanguage(event.target.value as Language)}
              >
                <option value="de">Deutsch</option>
                <option value="en">English</option>
                <option value="it">Italiano</option>
              </select>
            </label>
            {user && (
              <button
                className="rounded bg-slate-800 px-4 py-2 text-white"
                onClick={logout}
                type="button"
              >
                {t.logout}
              </button>
            )}
          </div>
        </header>

        {error && <p className="mb-4 rounded bg-red-100 px-4 py-2 text-sm text-red-800">{error}</p>}
        {message && (
          <p className="mb-4 rounded bg-emerald-100 px-4 py-2 text-sm text-emerald-800">
            {message}
          </p>
        )}

        {!user && (
          <div className="max-w-md space-y-3 rounded bg-white p-6 shadow">
            <div className="mb-1 flex gap-2">
              <button
                type="button"
                className={`rounded px-3 py-1 text-sm ${
                  !isRegisterMode ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
                }`}
                onClick={() => setIsRegisterMode(false)}
              >
                {t.login}
              </button>
              <button
                type="button"
                className={`rounded px-3 py-1 text-sm ${
                  isRegisterMode ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
                }`}
                onClick={() => setIsRegisterMode(true)}
              >
                {t.register}
              </button>
            </div>

            {!isRegisterMode ? (
              <form className="space-y-3" onSubmit={handleLogin}>
                <h2 className="text-xl font-semibold">{t.login}</h2>
                <p className="text-xs text-slate-600">
                  {t.seedCoaches}: <code>Timo</code> {t.and} <code>Denise</code>
                </p>
                <label className="block text-sm">
                  {t.username}
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    type="text"
                    required
                  />
                </label>
                <label className="block text-sm">
                  {t.password}
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type="password"
                    required
                  />
                </label>
                <button
                  className="w-full rounded bg-blue-600 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-70"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? t.loggingIn : t.signIn}
                </button>
              </form>
            ) : (
              <form className="space-y-3" onSubmit={handleRegister}>
                <h2 className="text-xl font-semibold">{t.register}</h2>
                <label className="block text-sm">
                  {t.name}
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.name}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, name: event.target.value }))
                    }
                    type="text"
                    required
                  />
                </label>
                <label className="block text-sm">
                  {t.username}
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.username}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, username: event.target.value }))
                    }
                    type="text"
                    required
                  />
                </label>
                <label className="block text-sm">
                  {t.email}
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.email}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, email: event.target.value }))
                    }
                    type="email"
                  />
                </label>
                <label className="block text-sm">
                  {t.password} ({t.passwordMin})
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.password}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, password: event.target.value }))
                    }
                    type="password"
                    minLength={8}
                    required
                  />
                </label>
                <label className="block text-sm">
                  {t.teamIdOptional}
                  <select
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.team_id}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, team_id: event.target.value }))
                    }
                    required
                  >
                    <option value="">{t.selectTeam}</option>
                    {availableTeams.map((team) => (
                      <option key={team.id} value={String(team.id)}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  {tt.playerPosition}
                  <select
                    className="mt-1 w-full rounded border px-3 py-2"
                    value={registerForm.player_position}
                    onChange={(event) =>
                      setRegisterForm((prev) => ({ ...prev, player_position: event.target.value }))
                    }
                    required
                  >
                    <option value="">{tt.selectPlayerPosition}</option>
                    <option value="setter">{tt.posSetter}</option>
                    <option value="outside_hitter">{tt.posOutsideHitter}</option>
                    <option value="opposite">{tt.posOpposite}</option>
                    <option value="middle_blocker">{tt.posMiddleBlocker}</option>
                    <option value="libero">{tt.posLibero}</option>
                  </select>
                </label>
                <button
                  className="w-full rounded bg-emerald-600 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-70"
                  type="submit"
                  disabled={isLoading || availableTeams.length === 0}
                >
                  {isLoading ? t.registering : t.createAccount}
                </button>
              </form>
            )}
          </div>
        )}

        {user && (
          <>
            <section className="mb-4 rounded bg-white p-4 shadow">
              <h3 className="text-lg font-semibold">{t.modelTrainingStatus}</h3>
              {!modelStatus ? (
                <p className="mt-2 text-sm text-slate-600">{t.noTrainingStatus}</p>
              ) : (
                <div className="mt-2 grid gap-2 text-sm md:grid-cols-2">
                  <p>
                    {t.status}:{" "}
                    <span
                      className={
                        modelStatus.status === "ok"
                          ? "font-semibold text-emerald-700"
                          : "font-semibold text-red-700"
                      }
                    >
                      {modelStatus.status}
                    </span>
                  </p>
                  <p>
                    {t.updated}: {formatDateTime(modelStatus.updated_at, locale)}
                  </p>
                  <p>
                    {t.lastSuccess}: {formatDateTime(modelStatus.last_success_at, locale)}
                  </p>
                  <p>
                    {t.lastFailure}: {formatDateTime(modelStatus.last_failure_at, locale)}
                  </p>
                  <p>
                    {t.mode}:{" "}
                    {String(
                      (modelStatus.metrics?.training_data_mode as string | undefined) ?? t.unknown,
                    )}
                  </p>
                  <p>
                    {t.realRows}:{" "}
                    {String((modelStatus.metrics?.real_rows as number | undefined) ?? "-")}
                  </p>
                  {modelStatus.error && (
                    <p className="md:col-span-2 text-red-700">
                      {t.error}: {modelStatus.error}
                    </p>
                  )}
                </div>
              )}
            </section>

            <nav className="mb-6 flex flex-wrap gap-2">
              {(user.role === "coach"
                ? [
                    { key: "team", label: t.teamOverview },
                    { key: "detail", label: t.playerDetail },
                  ]
                : [
                    { key: "dashboard", label: t.dashboard },
                    { key: "wellness", label: t.wellnessCheck },
                    { key: "cycle", label: t.cycle },
                    { key: "training", label: t.trainingLoad },
                    { key: "injury", label: tt.injuryTracking },
                    { key: "privacy", label: t.privacySettings },
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

            {isLoading && <p className="mb-4 text-sm text-slate-600">{t.loadingData}</p>}

            {user.role === "player" && tab === "dashboard" && (
              <section className="grid gap-4 md:grid-cols-2">
                <article className="rounded bg-white p-4 shadow">
                  <h3 className="text-lg font-semibold">{t.currentRiskScore}</h3>
                  {prediction ? (
                    <div className="mt-3 flex items-center gap-3">
                      <span
                        className={`h-4 w-4 rounded-full ${riskColor(prediction.risk_level)}`}
                      />
                      <p>
                        {prediction.risk_level.toUpperCase()} -{" "}
                        {(prediction.risk_score * 100).toFixed(1)}%
                      </p>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">{t.noPrediction}</p>
                  )}
                </article>
                <article className="rounded bg-white p-4 shadow">
                  <h3 className="text-lg font-semibold">{t.wellnessTrend}</h3>
                  <p className="mt-2 text-sm text-slate-600">{t.trendDescription}</p>
                  {wellnessTrend.length > 1 ? (
                    <>
                      <svg
                        viewBox="0 0 100 100"
                        className="mt-3 h-28 w-full rounded bg-slate-100 p-2"
                      >
                        <line x1="0" y1="0" x2="100" y2="0" stroke="#cbd5e1" strokeWidth="1" />
                        <line x1="0" y1="100" x2="100" y2="100" stroke="#cbd5e1" strokeWidth="1" />
                        <polyline
                          fill="none"
                          stroke="#2563eb"
                          strokeWidth="3"
                          points={formatTrendPoints(wellnessTrend.map((point) => point.score))}
                        />
                        {wellnessTrend.map((point, idx) => {
                          const max = Math.max(...wellnessTrend.map((item) => item.score));
                          const min = Math.min(...wellnessTrend.map((item) => item.score));
                          const spread = Math.max(max - min, 1);
                          const x = (idx / Math.max(wellnessTrend.length - 1, 1)) * 100;
                          const y = 100 - ((point.score - min) / spread) * 100;
                          return (
                            <circle
                              key={`${point.date}-${idx}`}
                              cx={x}
                              cy={y}
                              r="2.2"
                              fill="#1d4ed8"
                            />
                          );
                        })}
                      </svg>
                      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                        <span>{t.lower}</span>
                        <span>{t.higher}</span>
                      </div>
                      <button
                        type="button"
                        className="mt-3 rounded bg-slate-800 px-3 py-1 text-sm text-white"
                        onClick={() => setIsWellnessDetailOpen((prev) => !prev)}
                      >
                        {isWellnessDetailOpen ? t.hideDetailView : t.openDetailView}
                      </button>
                    </>
                  ) : (
                    <p className="mt-2 text-sm text-slate-600">{t.notEnoughTrendData}</p>
                  )}
                </article>
                {isWellnessDetailOpen && wellnessTrend.length > 1 && (
                  <article className="rounded bg-white p-4 shadow md:col-span-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-lg font-semibold">{t.wellnessDetails}</h3>
                      <p className="text-xs text-slate-600">{t.clickPointsForDayDetails}</p>
                    </div>
                    <svg
                      viewBox="0 0 100 100"
                      className="mt-3 h-52 w-full rounded bg-slate-100 p-2"
                    >
                      <polyline
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2.5"
                        points={formatTrendPoints(wellnessTrend.map((point) => point.score))}
                      />
                      <polyline
                        fill="none"
                        stroke="#0f766e"
                        strokeWidth="2"
                        points={formatTrendPoints(
                          wellnessTrend.map((point) => point.sleep_quality),
                        )}
                      />
                      <polyline
                        fill="none"
                        stroke="#9333ea"
                        strokeWidth="2"
                        points={formatTrendPoints(
                          wellnessTrend.map((point) => point.mental_energy),
                        )}
                      />
                      <polyline
                        fill="none"
                        stroke="#ea580c"
                        strokeWidth="2"
                        points={formatTrendPoints(wellnessTrend.map((point) => point.motivation))}
                      />
                    </svg>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs">
                      <span className="rounded bg-blue-100 px-2 py-1 text-blue-800">
                        {t.avgBlue}
                      </span>
                      <span className="rounded bg-teal-100 px-2 py-1 text-teal-800">
                        {t.greenSleep}
                      </span>
                      <span className="rounded bg-purple-100 px-2 py-1 text-purple-800">
                        {t.purpleMental}
                      </span>
                      <span className="rounded bg-orange-100 px-2 py-1 text-orange-800">
                        {t.orangeMotivation}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-2 md:grid-cols-7">
                      {wellnessTrend.map((point, idx) => (
                        <button
                          key={`detail-${point.date}`}
                          type="button"
                          onClick={() => setSelectedTrendIndex(idx)}
                          className={`rounded border px-2 py-2 text-left text-xs ${
                            selectedTrendIndex === idx
                              ? "border-blue-500 bg-blue-50"
                              : "border-slate-200 bg-white hover:bg-slate-50"
                          }`}
                        >
                          <p className="font-medium">{formatShortDate(point.date, locale)}</p>
                          <p>
                            {t.avg}: {point.score}
                          </p>
                        </button>
                      ))}
                    </div>
                    {selectedTrendPoint && (
                      <div className="mt-4 rounded border border-blue-200 bg-blue-50 p-3 text-sm">
                        <p className="font-semibold">
                          {t.detailsFor} {selectedTrendPoint.date}
                        </p>
                        <p className="mt-1">
                          {t.sleepQuality} {selectedTrendPoint.sleep_quality}, {t.mentalEnergy}{" "}
                          {selectedTrendPoint.mental_energy}, {t.motivationLabel}{" "}
                          {selectedTrendPoint.motivation}, {t.avg} {selectedTrendPoint.score}.
                        </p>
                      </div>
                    )}
                  </article>
                )}
                <article className="rounded bg-white p-4 shadow md:col-span-2">
                  <h3 className="text-lg font-semibold">{t.latestEntries}</h3>
                  <div className="mt-3 grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="font-medium">{t.wellness}</p>
                      <ul className="mt-2 text-sm text-slate-700">
                        {wellness.slice(0, 3).map((entry) => (
                          <li key={entry.id}>
                            {entry.date}: {t.sleep} {formatSleepHours(entry.sleep_hours)}h,{" "}
                            {t.energy} {entry.mental_energy}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium">{t.cycle}</p>
                      <ul className="mt-2 text-sm text-slate-700">
                        {cycle.slice(0, 3).map((entry) => (
                          <li key={entry.id}>
                            {entry.date}: {t.day} {entry.cycle_day}, {t.phase} {entry.phase}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </article>
              </section>
            )}

            {user.role === "player" && tab === "wellness" && (
              <form
                className="space-y-3 rounded bg-white p-6 shadow"
                onSubmit={handleWellnessSubmit}
              >
                <h3 className="text-lg font-semibold">{t.wellnessCheck}</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm">
                    {t.date}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="date"
                      value={wellnessForm.date}
                      onChange={(event) =>
                        setWellnessForm((prev) => ({ ...prev, date: event.target.value }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    {t.sleepHours}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={1}
                      max={24}
                      step={0.5}
                      value={wellnessForm.sleep_hours}
                      onChange={(event) =>
                        setWellnessForm((prev) => ({
                          ...prev,
                          sleep_hours: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  {[
                    { key: "sleep_quality", label: t.sleepQuality },
                    { key: "muscle_soreness", label: t.muscleSoreness },
                    { key: "mental_energy", label: t.mentalEnergy },
                    { key: "stress_level", label: t.stress },
                    { key: "motivation", label: t.motivationLabel },
                    { key: "rpe_previous_day", label: t.rpePreviousDay },
                  ].map((item) => (
                    <label key={item.key} className="text-sm">
                      {item.label} (0-10):{" "}
                      <span className="font-semibold">
                        {wellnessForm[item.key as keyof typeof wellnessForm]}
                      </span>
                      <input
                        className="mt-1 w-full"
                        type="range"
                        min={0}
                        max={10}
                        step={1}
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
                  {t.note}
                  <textarea
                    className="mt-1 w-full rounded border px-3 py-2"
                    rows={3}
                    value={wellnessForm.free_text}
                    onChange={(event) =>
                      setWellnessForm((prev) => ({ ...prev, free_text: event.target.value }))
                    }
                  />
                </label>
                <button
                  className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? t.saving : t.saveWellness}
                </button>
              </form>
            )}

            {user.role === "player" && tab === "cycle" && (
              <form className="space-y-3 rounded bg-white p-6 shadow" onSubmit={handleCycleSubmit}>
                <h3 className="text-lg font-semibold">{t.cycleTracking}</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm">
                    {t.date}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="date"
                      value={cycleForm.date}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, date: event.target.value }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    {t.cycleDay}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={1}
                      max={60}
                      value={cycleForm.cycle_day}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, cycle_day: Number(event.target.value) }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    {t.cycleLength}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      type="number"
                      min={20}
                      max={45}
                      value={cycleForm.cycle_length}
                      onChange={(event) =>
                        setCycleForm((prev) => ({
                          ...prev,
                          cycle_length: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    {t.phase}
                    <select
                      className="mt-1 w-full rounded border px-3 py-2"
                      value={cycleForm.phase}
                      onChange={(event) =>
                        setCycleForm((prev) => ({
                          ...prev,
                          phase: event.target.value as CycleEntry["phase"],
                        }))
                      }
                    >
                      <option value="menstruation">{t.phaseMenstruation}</option>
                      <option value="follicular">{t.phaseFollicular}</option>
                      <option value="ovulation">{t.phaseOvulation}</option>
                      <option value="luteal">{t.phaseLuteal}</option>
                    </select>
                  </label>
                  <label className="text-sm">
                    {t.pmsScore} (0-10):{" "}
                    <span className="font-semibold">{cycleForm.pms_score}</span>
                    <input
                      className="mt-1 w-full"
                      type="range"
                      min={0}
                      max={10}
                      step={1}
                      value={cycleForm.pms_score}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, pms_score: Number(event.target.value) }))
                      }
                    />
                  </label>
                  <label className="text-sm">
                    {t.contraception}
                    <input
                      className="mt-1 w-full rounded border px-3 py-2"
                      value={cycleForm.contraception_type}
                      onChange={(event) =>
                        setCycleForm((prev) => ({
                          ...prev,
                          contraception_type: event.target.value,
                        }))
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
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, cramps: event.target.checked }))
                      }
                    />
                    {t.cramps}
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={cycleForm.migraine}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, migraine: event.target.checked }))
                      }
                    />
                    {t.migraine}
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      className="mr-2"
                      checked={cycleForm.fatigue}
                      onChange={(event) =>
                        setCycleForm((prev) => ({ ...prev, fatigue: event.target.checked }))
                      }
                    />
                    {t.fatigue}
                  </label>
                </div>
                <label className="block text-sm">
                  {t.note}
                  <textarea
                    className="mt-1 w-full rounded border px-3 py-2"
                    rows={3}
                    value={cycleForm.notes}
                    onChange={(event) =>
                      setCycleForm((prev) => ({ ...prev, notes: event.target.value }))
                    }
                  />
                </label>
                <button
                  className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? t.saving : t.saveCycle}
                </button>
              </form>
            )}

            {user.role === "player" && tab === "privacy" && (
              <section className="rounded bg-white p-6 shadow">
                <h3 className="text-lg font-semibold">{t.privacySettings}</h3>
                {consents.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">{t.noConsents}</p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {consents.map((consent) => (
                      <article key={consent.id} className="rounded border p-3">
                        <p className="mb-2 font-medium">
                          {t.coach}: {consent.coach_name ?? `ID ${consent.coach_id}`}
                        </p>
                        <div className="flex flex-wrap gap-4 text-sm">
                          <label>
                            <input
                              type="checkbox"
                              className="mr-2"
                              checked={consent.share_wellness_data}
                              onChange={(event) =>
                                setConsents((prev) =>
                                  prev.map((item) =>
                                    item.id === consent.id
                                      ? { ...item, share_wellness_data: event.target.checked }
                                      : item,
                                  ),
                                )
                              }
                            />
                            {t.shareWellness}
                          </label>
                          <label>
                            <input
                              type="checkbox"
                              className="mr-2"
                              checked={consent.share_cycle_data}
                              onChange={(event) =>
                                setConsents((prev) =>
                                  prev.map((item) =>
                                    item.id === consent.id
                                      ? { ...item, share_cycle_data: event.target.checked }
                                      : item,
                                  ),
                                )
                              }
                            />
                            {t.shareCycle}
                          </label>
                          <button
                            className="rounded bg-slate-800 px-3 py-1 text-white"
                            type="button"
                            onClick={() => void handlePrivacySave(consent)}
                          >
                            {t.save}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            )}

            {user.role === "player" && tab === "injury" && (
              <section className="space-y-4 rounded bg-white p-6 shadow">
                <form className="space-y-3" onSubmit={handleInjurySubmit}>
                  <h3 className="text-lg font-semibold">{tt.injuryTracking}</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-sm">
                      {t.date}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="date"
                        value={injuryForm.date}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({ ...prev, date: event.target.value }))
                        }
                      />
                    </label>
                    <label className="text-sm">
                      {tt.bodyLocation}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        value={injuryForm.body_location}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({ ...prev, body_location: event.target.value }))
                        }
                        required
                      />
                    </label>
                    <label className="text-sm">
                      {tt.painIntensity} (1-10):{" "}
                      <span className="font-semibold">{injuryForm.pain_intensity}</span>
                      <input
                        className="mt-1 w-full"
                        type="range"
                        min={1}
                        max={10}
                        step={1}
                        value={injuryForm.pain_intensity}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({
                            ...prev,
                            pain_intensity: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                    <label className="text-sm flex items-center gap-2 pt-6">
                      <input
                        type="checkbox"
                        checked={injuryForm.is_chronic}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({ ...prev, is_chronic: event.target.checked }))
                        }
                      />
                      {tt.isChronic}
                    </label>
                    <label className="text-sm flex items-center gap-2 pt-6">
                      <input
                        type="checkbox"
                        checked={injuryForm.medical_attention}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({
                            ...prev,
                            medical_attention: event.target.checked,
                          }))
                        }
                      />
                      {tt.medicalAttention}
                    </label>
                    <label className="text-sm">
                      {tt.timeLossDays}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="number"
                        min={0}
                        max={365}
                        value={injuryForm.time_loss_days}
                        onChange={(event) =>
                          setInjuryForm((prev) => ({
                            ...prev,
                            time_loss_days: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                  </div>
                  <label className="block text-sm">
                    {t.note}
                    <textarea
                      className="mt-1 w-full rounded border px-3 py-2"
                      rows={3}
                      value={injuryForm.description}
                      onChange={(event) =>
                        setInjuryForm((prev) => ({ ...prev, description: event.target.value }))
                      }
                    />
                  </label>
                  <button
                    className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70"
                    type="submit"
                    disabled={isLoading}
                  >
                    {isLoading ? t.saving : tt.saveInjury}
                  </button>
                </form>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{t.injuryHistory}</h4>
                  {injuries.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">{tt.noInjuryData}</p>
                  ) : (
                    <ul className="mt-2 space-y-2 text-sm">
                      {injuries.slice(0, 10).map((entry) => (
                        <li key={entry.id} className="rounded bg-slate-50 px-3 py-2">
                          <p className="font-medium">
                            {entry.date} - {entry.body_location}
                          </p>
                          <p>
                            {tt.painIntensity}: {entry.pain_intensity}/10
                            {entry.is_chronic ? ` (${tt.isChronic})` : ""}
                          </p>
                          <p>
                            {tt.medicalAttention}: {entry.medical_attention ? tt.yes : tt.no} -{" "}
                            {tt.timeLossDays}: {entry.time_loss_days}
                          </p>
                          {entry.description && <p className="text-slate-600">{entry.description}</p>}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              </section>
            )}

            {user.role === "player" && tab === "training" && (
              <section className="space-y-4 rounded bg-white p-6 shadow">
                <form className="space-y-3" onSubmit={handleTrainingSubmit}>
                  <h3 className="text-lg font-semibold">{tt.trainingEntry}</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-sm">
                      {t.date}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="date"
                        value={trainingForm.date}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({ ...prev, date: event.target.value }))
                        }
                      />
                    </label>
                    <label className="text-sm">
                      {tt.durationMinutes}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="number"
                        min={1}
                        max={600}
                        value={trainingForm.duration_min}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({
                            ...prev,
                            duration_min: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                    <label className="text-sm">
                      {tt.intensityLabel} (1-10):{" "}
                      <span className="font-semibold">{trainingForm.intensity}</span>
                      <input
                        className="mt-1 w-full"
                        type="range"
                        min={1}
                        max={10}
                        step={1}
                        value={trainingForm.intensity}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({ ...prev, intensity: Number(event.target.value) }))
                        }
                      />
                    </label>
                    <label className="text-sm">
                      {tt.sessionRpeLabel} (0-10):{" "}
                      <span className="font-semibold">{trainingForm.session_rpe}</span>
                      <input
                        className="mt-1 w-full"
                        type="range"
                        min={0}
                        max={10}
                        step={1}
                        value={trainingForm.session_rpe}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({
                            ...prev,
                            session_rpe: Number(event.target.value),
                          }))
                        }
                      />
                    </label>
                    <label className="text-sm">
                      {tt.sessionType}
                      <select
                        className="mt-1 w-full rounded border px-3 py-2"
                        value={trainingForm.session_type}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({
                            ...prev,
                            session_type: event.target.value as
                              | "team"
                              | "strength"
                              | "technical"
                              | "recovery",
                          }))
                        }
                      >
                        <option value="team">{tt.sessionTypeTeam}</option>
                        <option value="strength">{tt.sessionTypeStrength}</option>
                        <option value="technical">{tt.sessionTypeTechnical}</option>
                        <option value="recovery">{tt.sessionTypeRecovery}</option>
                      </select>
                    </label>
                    <label className="text-sm">
                      {tt.participationStatus}
                      <select
                        className="mt-1 w-full rounded border px-3 py-2"
                        value={trainingForm.participation_status}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({
                            ...prev,
                            participation_status: event.target.value as
                              | "full"
                              | "modified"
                              | "individual"
                              | "rest",
                          }))
                        }
                      >
                        <option value="full">{tt.participationFull}</option>
                        <option value="modified">{tt.participationModified}</option>
                        <option value="individual">{tt.participationIndividual}</option>
                        <option value="rest">{tt.participationRest}</option>
                      </select>
                    </label>
                    <label className="text-sm md:col-span-2">
                      {tt.jumpCountOptional}
                      <input
                        className="mt-1 w-full rounded border px-3 py-2"
                        type="number"
                        min={0}
                        value={trainingForm.jump_count}
                        onChange={(event) =>
                          setTrainingForm((prev) => ({ ...prev, jump_count: event.target.value }))
                        }
                      />
                    </label>
                  </div>
                  <button
                    className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70"
                    type="submit"
                    disabled={isLoading}
                  >
                    {isLoading ? t.saving : tt.saveTraining}
                  </button>
                </form>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{tt.trainingHistory}</h4>
                  {training.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">{tt.noTrainingEntries}</p>
                  ) : (
                    <ul className="mt-2 space-y-2 text-sm">
                      {training.slice(0, 10).map((entry) => (
                        <li key={entry.id} className="rounded bg-slate-50 px-3 py-2">
                          <p className="font-medium">
                            {entry.date} - {entry.duration_min} min, {tt.intensityLabel} {entry.intensity},{" "}
                            sRPE {entry.session_rpe ?? "-"}
                          </p>
                          <p className="text-slate-700">
                            {tt.sessionType}: {entry.session_type ?? "-"} - {tt.participationStatus}:{" "}
                            {entry.participation_status ?? "-"}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              </section>
            )}

            {user.role === "coach" && tab === "team" && (
              <section className="rounded bg-white p-6 shadow">
                <h3 className="text-lg font-semibold">{t.teamOverview}</h3>
                {teamPredictions.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">{t.noPlayers}</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {coachPriorityList.map((item) => (
                        <li
                          key={`${item.player_id}-${item.date ?? "today"}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded border p-3"
                        >
                          <div className="flex items-center gap-3">
                            <span
                              className={`h-4 w-4 rounded-full ${riskColor(item.risk_level)}`}
                            />
                            <p className="font-medium">
                              {item.player_name ?? `${t.player} #${item.player_id}`}
                            </p>
                            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                              {mapPositionLabel(item.player_position, tt)}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-sm">
                            <span>
                              {(item.risk_score * 100).toFixed(1)}% -{" "}
                              {item.risk_level.toUpperCase()}
                            </span>
                            <button
                              type="button"
                              className="rounded bg-slate-800 px-3 py-1 text-white"
                              onClick={() => {
                                setSelectedPlayerId(item.player_id ?? null);
                                setTab("detail");
                              }}
                            >
                              {t.detail}
                            </button>
                          </div>
                          <div className="mt-2 w-full">
                            <div className="h-2 w-full rounded bg-slate-200">
                              <div
                                className={`h-2 rounded ${riskColor(item.risk_level)}`}
                                style={{ width: `${Math.min(100, Math.max(0, item.risk_score * 100))}%` }}
                              />
                            </div>
                            <p className="mt-1 text-xs text-slate-600">
                              {t.avg}: {(teamRiskAverage * 100).toFixed(1)}%
                            </p>
                          </div>
                          <div className="mt-2 w-full flex flex-wrap gap-2 text-xs">
                            <span className="rounded bg-blue-50 px-2 py-1 text-blue-800">
                              sRPE: {item.latest_session_rpe ?? "-"}
                            </span>
                            <span className="rounded bg-indigo-50 px-2 py-1 text-indigo-800">
                              {tt.sessionType}: {mapSessionTypeLabel(item.latest_session_type, tt)}
                            </span>
                            <span className="rounded bg-violet-50 px-2 py-1 text-violet-800">
                              {tt.participationStatus}:{" "}
                              {mapParticipationLabel(item.latest_participation_status, tt)}
                            </span>
                            <span
                              className={`rounded px-2 py-1 ${
                                (item.latest_pain_intensity ?? 0) >= 7
                                  ? "bg-red-100 text-red-800"
                                  : "bg-amber-50 text-amber-800"
                              }`}
                            >
                              {tt.painIntensity}: {item.latest_pain_intensity ?? "-"}
                            </span>
                            <span
                              className={`rounded px-2 py-1 ${
                                (item.latest_time_loss_days ?? 0) > 0
                                  ? "bg-red-100 text-red-800"
                                  : "bg-emerald-50 text-emerald-800"
                              }`}
                            >
                              {tt.timeLossDays}: {item.latest_time_loss_days ?? 0}
                            </span>
                            <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
                              {tt.medicalAttention}:{" "}
                              {item.latest_medical_attention ? tt.yes : tt.no}
                            </span>
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
                    <p className="text-sm text-slate-600">{t.selectPlayer}</p>
                    <select
                      className="mt-1 rounded border px-3 py-2"
                      value={selectedPlayerId ?? ""}
                      onChange={(event) => setSelectedPlayerId(Number(event.target.value))}
                    >
                      {teamPredictions.map((item) => (
                        <option key={`sel-${item.player_id}`} value={item.player_id}>
                          {item.player_name ?? `${t.player} #${item.player_id}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    className="rounded bg-blue-600 px-4 py-2 text-white"
                    onClick={() => void loadCoachPlayerDetail()}
                  >
                    {t.refresh}
                  </button>
                </div>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{t.wellnessHistory}</h4>
                  {selectedPlayerWellnessBlocked ? (
                    <p className="mt-2 text-sm text-amber-700">{t.wellnessBlocked}</p>
                  ) : selectedPlayerWellness.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">{t.noWellnessData}</p>
                  ) : (
                    <>
                      <svg viewBox="0 0 100 100" className="mt-3 h-32 w-full rounded bg-slate-100 p-2">
                        <polyline
                          fill="none"
                          stroke="#2563eb"
                          strokeWidth="2.5"
                          points={formatTrendPoints(coachWellnessTrend.map((point) => point.score))}
                        />
                        <polyline
                          fill="none"
                          stroke="#0f766e"
                          strokeWidth="2"
                          points={formatTrendPoints(coachWellnessTrend.map((point) => point.sleep_quality))}
                        />
                        <polyline
                          fill="none"
                          stroke="#9333ea"
                          strokeWidth="2"
                          points={formatTrendPoints(coachWellnessTrend.map((point) => point.mental_energy))}
                        />
                      </svg>
                      <p className="mt-2 text-xs text-slate-600">
                        {t.avgBlue}, {t.greenSleep}, {t.purpleMental}
                      </p>
                    </>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{t.trainingLoad}</h4>
                  {selectedPlayerTraining.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">{t.noTrainingData}</p>
                  ) : (
                    <>
                      <svg viewBox="0 0 100 100" className="mt-3 h-32 w-full rounded bg-slate-100 p-2">
                        <polyline
                          fill="none"
                          stroke="#0f766e"
                          strokeWidth="2.5"
                          points={formatTrendPoints(coachTrainingTrend.map((point) => point.duration))}
                        />
                        <polyline
                          fill="none"
                          stroke="#ea580c"
                          strokeWidth="2"
                          points={formatTrendPoints(coachTrainingTrend.map((point) => point.intensity))}
                        />
                      </svg>
                      <p className="mt-2 text-sm text-slate-700">
                        {t.avg}: {coachTrainingAvgDuration.toFixed(1)} min
                      </p>
                    </>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{t.cycleData}</h4>
                  {selectedPlayerCycleBlocked ? (
                    <p className="mt-2 text-sm text-amber-700">{t.cycleBlocked}</p>
                  ) : selectedPlayerCycle.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-600">{t.noCycleData}</p>
                  ) : (
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {selectedPlayerCycle.slice(0, 7).map((entry) => (
                        <span key={entry.id} className="rounded bg-slate-100 px-2 py-1">
                          {formatShortDate(entry.date, locale)}: {entry.phase} (D{entry.cycle_day})
                        </span>
                      ))}
                    </div>
                  )}
                </article>

                <article className="rounded border p-4">
                  <h4 className="font-semibold">{t.injuryHistory}</h4>
                  <p className="mt-2 text-sm text-slate-600">{t.noInjuryEndpoint}</p>
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
