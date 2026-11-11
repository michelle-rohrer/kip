import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  apiRequest,
  getAccessToken,
  login as loginRequest,
  logoutRequest,
  setSessionExpiredHandler,
  setTokens,
} from "./api";
import { LANGUAGE_KEY, LOCALES, Language, TEXT } from "./i18n";
import {
  AppTab,
  AppleHealthToken,
  CycleEntry,
  CycleEstimate,
  InjuryEntry,
  IntegrationStatus,
  ModelTrainingStatus,
  Prediction,
  PrivacyConsent,
  SyncResult,
  TeamOption,
  TokenResponse,
  TrainingEntry,
  User,
  WearableDaily,
  WearableProvider,
  DeviceSuggestions,
  WellnessEntry,
} from "./types";
import { num, todayIso } from "./utils";
import { AppShell, Logo, NavItem } from "./components/Shell";
import { LoginView, RegisterForm } from "./components/LoginView";
import { CoachDetailView, CoachTeamView, SystemStatusCard } from "./components/CoachViews";
import {
  CycleForm,
  CycleView,
  InjuryForm,
  InjuryView,
  PlayerDashboard,
  PrivacyView,
  TrainingForm,
  TrainingView,
  TrendPoint,
  WellnessForm,
  WellnessView,
} from "./components/PlayerViews";
import { IntegrationsView } from "./components/IntegrationsView";
import { AccountView, type PasswordChange } from "./components/AccountView";
import {
  IconDrop,
  IconDumbbell,
  IconHome,
  IconPulseAlert,
  IconShield,
  IconSparkle,
  IconUser,
  IconUsers,
} from "./components/icons";
import { Skeleton, Toast, ToastKind } from "./components/ui";

const THEME_KEY = "kip_theme";

/** A connected device is pulled again once its last sync is this old. */
const STALE_SYNC_MS = 6 * 60 * 60 * 1000;

type ToastMessage = { id: number; message: string; kind: ToastKind };

function readLanguage(): Language {
  try {
    const saved = localStorage.getItem(LANGUAGE_KEY);
    if (saved === "de" || saved === "en" || saved === "it") return saved;
  } catch {
    /* storage blocked */
  }
  return "de";
}

function readTheme(): "light" | "dark" {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage blocked */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function App() {
  const [language, setLanguage] = useState<Language>(readLanguage);
  const [theme, setTheme] = useState<"light" | "dark">(readTheme);
  const [offline, setOffline] = useState(!navigator.onLine);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [registerForm, setRegisterForm] = useState<RegisterForm>({
    username: "",
    email: "",
    password: "",
    name: "",
    team_id: "",
    player_position: "",
  });
  const [availableTeams, setAvailableTeams] = useState<TeamOption[]>([]);

  const [user, setUser] = useState<User | null>(null);
  const [bootstrapping, setBootstrapping] = useState(Boolean(getAccessToken()));
  const [tab, setTab] = useState<AppTab>("dashboard");
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const [wellness, setWellness] = useState<WellnessEntry[]>([]);
  const [cycle, setCycle] = useState<CycleEntry[]>([]);
  const [training, setTraining] = useState<TrainingEntry[]>([]);
  const [injuries, setInjuries] = useState<InjuryEntry[]>([]);
  const [consents, setConsents] = useState<PrivacyConsent[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [teamPredictions, setTeamPredictions] = useState<Prediction[]>([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [selectedPlayerWellness, setSelectedPlayerWellness] = useState<WellnessEntry[]>([]);
  const [selectedPlayerCycle, setSelectedPlayerCycle] = useState<CycleEntry[]>([]);
  const [selectedPlayerTraining, setSelectedPlayerTraining] = useState<TrainingEntry[]>([]);
  const [selectedPlayerCycleBlocked, setSelectedPlayerCycleBlocked] = useState(false);
  const [selectedPlayerWellnessBlocked, setSelectedPlayerWellnessBlocked] = useState(false);
  const [modelStatus, setModelStatus] = useState<ModelTrainingStatus | null>(null);

  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [wearableDaily, setWearableDaily] = useState<WearableDaily[]>([]);
  const [suggestion, setSuggestion] = useState<DeviceSuggestions | null>(null);
  const [cycleEstimate, setCycleEstimate] = useState<CycleEstimate | null>(null);
  const [appleToken, setAppleToken] = useState<AppleHealthToken | null>(null);
  const [busyProvider, setBusyProvider] = useState<WearableProvider | null>(null);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const [wellnessForm, setWellnessForm] = useState<WellnessForm>({
    date: todayIso(),
    sleep_hours: 8,
    sleep_quality: 7,
    muscle_soreness: 4,
    mental_energy: 7,
    stress_level: 4,
    motivation: 8,
    rpe_previous_day: 6,
    free_text: "",
  });
  const [cycleForm, setCycleForm] = useState<CycleForm>({
    date: todayIso(),
    menstrual_flow: "none",
    // Left null on purpose: the server derives them from her period days
    // unless she opens the manual override.
    cycle_day: null,
    phase: null,
    cycle_length: null,
    pms_score: 0,
    cramps: false,
    migraine: false,
    fatigue: false,
    contraception_type: "",
    notes: "",
  });
  const [trainingForm, setTrainingForm] = useState<TrainingForm>({
    date: todayIso(),
    duration_min: 75,
    intensity: 6,
    session_rpe: 6,
    session_type: "team",
    participation_status: "full",
  });
  const [injuryForm, setInjuryForm] = useState<InjuryForm>({
    date: todayIso(),
    body_location: "",
    pain_intensity: 4,
    is_chronic: false,
    medical_attention: false,
    time_loss_days: 0,
    description: "",
  });

  const t = TEXT[language] as unknown as Record<string, string>;
  const locale = LOCALES[language];
  const toastId = useRef(0);
  const oauthReturnHandled = useRef(false);
  const autoSyncDone = useRef(false);

  const pushToast = useCallback((message: string, kind: ToastKind = "info") => {
    toastId.current += 1;
    const id = toastId.current;
    setToasts((prev) => [...prev.slice(-2), { id, message, kind }]);
  }, []);

  const describeError = useCallback(
    (error: unknown, fallback: string) => {
      if (error instanceof ApiError) {
        if (error.isNetwork) return t.connectionProblem;
        if (error.status === 401) return t.sessionLoadFailed;
        // A 422 carries the API's own wording, which is a raw regex. A player
        // once saw "String should match pattern '^[A-Za-z0-9._-]{1,64}$'" and
        // had no way to tell that it meant the username box.
        if (error.status === 422) {
          if (error.field === "username") return t.invalidUsername;
          if (error.field === "email") return t.invalidEmail;
          return t.invalidField;
        }
        // These two arrive as English prose in `detail`, with no field to go on.
        // They are the likeliest 400 on the register form, and short usernames
        // collide quickly in a squad of fourteen.
        if (error.status === 400) {
          if (error.message === "Username already registered") return t.usernameTaken;
          if (error.message === "Email already registered") return t.emailTaken;
        }
        return error.message || fallback;
      }
      return error instanceof Error ? error.message : fallback;
    },
    [
      t.connectionProblem,
      t.sessionLoadFailed,
      t.invalidUsername,
      t.invalidEmail,
      t.invalidField,
      t.usernameTaken,
      t.emailTaken,
    ],
  );

  /* ----------------------------------------------------------- app chrome */

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* storage blocked */
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      localStorage.setItem(LANGUAGE_KEY, language);
    } catch {
      /* storage blocked */
    }
  }, [language]);

  useEffect(() => {
    const goOnline = () => setOffline(false);
    const goOffline = () => setOffline(true);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  /* ---------------------------------------------------------------- auth */

  const resetSessionState = useCallback(() => {
    setUser(null);
    setWellness([]);
    setCycle([]);
    setTraining([]);
    setInjuries([]);
    setConsents([]);
    setPrediction(null);
    setTeamPredictions([]);
    setSelectedPlayerId(null);
    setSelectedPlayerWellness([]);
    setSelectedPlayerCycle([]);
    setSelectedPlayerTraining([]);
    setSelectedPlayerCycleBlocked(false);
    setSelectedPlayerWellnessBlocked(false);
    setModelStatus(null);
    setIntegrations([]);
    setWearableDaily([]);
    setSuggestion(null);
    setAppleToken(null);
    setBusyProvider(null);
    autoSyncDone.current = false;
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      resetSessionState();
      pushToast(t.sessionLoadFailed, "error");
    });
    return () => setSessionExpiredHandler(null);
  }, [pushToast, resetSessionState, t.sessionLoadFailed]);

  const loadCurrentUser = useCallback(async () => {
    const me = await apiRequest<User>("/api/auth/me");
    setUser(me);
    setTab(me.role === "coach" ? "team" : "dashboard");
    return me;
  }, []);

  useEffect(() => {
    if (!getAccessToken()) return;
    let cancelled = false;
    loadCurrentUser()
      .catch(() => {
        if (!cancelled) setTokens(null);
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loadCurrentUser]);

  const loadAvailableTeams = useCallback(async () => {
    try {
      const teams = await apiRequest<TeamOption[]>("/api/teams/", { auth: false });
      setAvailableTeams(teams);
    } catch {
      setAvailableTeams([]);
    }
  }, []);

  useEffect(() => {
    if (user || !isRegisterMode) return;
    void loadAvailableTeams();
  }, [isRegisterMode, loadAvailableTeams, user]);

  /* ---------------------------------------------------------- data loads */

  /**
   * Device data is optional everywhere: a player without a wearable must not
   * see an error, so each call is tolerated on its own.
   */
  const loadWearables = useCallback(async (forDate: string) => {
    const [statusRes, dailyRes, suggestionRes] = await Promise.allSettled([
      apiRequest<IntegrationStatus[]>("/api/integrations/"),
      apiRequest<WearableDaily[]>("/api/integrations/daily"),
      apiRequest<DeviceSuggestions>(
        `/api/integrations/suggestion?date=${encodeURIComponent(forDate)}`,
      ),
    ]);
    const statuses = statusRes.status === "fulfilled" ? statusRes.value : [];
    setIntegrations(statuses);
    setWearableDaily(dailyRes.status === "fulfilled" ? dailyRes.value : []);
    setSuggestion(suggestionRes.status === "fulfilled" ? suggestionRes.value : null);
    return statuses;
  }, []);

  /**
   * Keep connected devices fresh without a cron job: once per session, pull
   * anything that has not synced in the last six hours. Failures are silent -
   * the device page shows the real error when the player goes looking.
   */
  const autoSyncStaleDevices = useCallback(
    async (statuses: IntegrationStatus[]) => {
      if (autoSyncDone.current) return;
      autoSyncDone.current = true;

      const cutoff = Date.now() - STALE_SYNC_MS;
      const stale = statuses.filter(
        (status) =>
          status.connected &&
          status.provider !== "apple_health" &&
          (!status.last_sync_at || new Date(status.last_sync_at).getTime() < cutoff),
      );
      if (stale.length === 0) return;

      await Promise.allSettled(
        stale.map((status) =>
          apiRequest<SyncResult>(`/api/integrations/${status.provider.replace("_", "-")}/sync`, {
            method: "POST",
            body: JSON.stringify({ days: 14 }),
          }),
        ),
      );
      await loadWearables(todayIso());
    },
    [loadWearables],
  );

  const loadPlayerData = useCallback(async () => {
    if (!user || user.role !== "player") return;
    setIsLoading(true);
    try {
      const [wellnessEntries, cycleEntries, trainingEntries, injuryEntries, privacyConsents, risk] =
        await Promise.all([
          apiRequest<WellnessEntry[]>("/api/wellness/"),
          apiRequest<CycleEntry[]>("/api/cycle/"),
          apiRequest<TrainingEntry[]>("/api/training/"),
          apiRequest<InjuryEntry[]>("/api/injury/"),
          apiRequest<PrivacyConsent[]>("/api/privacy/consent"),
          apiRequest<Prediction>(`/api/predictions/${user.id}`),
        ]);
      setWellness(wellnessEntries);
      setCycle(cycleEntries);
      setTraining(trainingEntries);
      setInjuries(injuryEntries);
      setConsents(privacyConsents);
      setPrediction(risk);
      const statuses = await loadWearables(todayIso());
      void autoSyncStaleDevices(statuses);
    } catch (error) {
      pushToast(describeError(error, t.unknownLoadError), "error");
    } finally {
      setIsLoading(false);
    }
  }, [autoSyncStaleDevices, describeError, loadWearables, pushToast, t.unknownLoadError, user]);

  const loadCoachData = useCallback(async () => {
    if (!user || user.role !== "coach") return;
    setIsLoading(true);
    try {
      const team = await apiRequest<Prediction[]>("/api/predictions/team");
      setTeamPredictions(team);
      setSelectedPlayerId((current) => current ?? team[0]?.player_id ?? null);
    } catch (error) {
      pushToast(describeError(error, t.teamLoadFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }, [describeError, pushToast, t.teamLoadFailed, user]);

  const loadModelStatus = useCallback(async () => {
    if (!user) return;
    try {
      setModelStatus(await apiRequest<ModelTrainingStatus>("/api/predictions/model-status"));
    } catch {
      setModelStatus(null);
    }
  }, [user]);

  const loadCoachPlayerDetail = useCallback(async () => {
    if (!user || user.role !== "coach" || !selectedPlayerId) return;
    setIsLoading(true);
    try {
      const [wellnessRes, cycleRes, trainingRes] = await Promise.allSettled([
        apiRequest<WellnessEntry[]>(`/api/wellness/${selectedPlayerId}`),
        apiRequest<CycleEntry[]>(`/api/cycle/${selectedPlayerId}`),
        apiRequest<TrainingEntry[]>(`/api/training/${selectedPlayerId}`),
      ]);

      setSelectedPlayerWellness(wellnessRes.status === "fulfilled" ? wellnessRes.value : []);
      setSelectedPlayerWellnessBlocked(wellnessRes.status !== "fulfilled");
      setSelectedPlayerCycle(cycleRes.status === "fulfilled" ? cycleRes.value : []);
      setSelectedPlayerCycleBlocked(cycleRes.status !== "fulfilled");
      setSelectedPlayerTraining(trainingRes.status === "fulfilled" ? trainingRes.value : []);
    } catch (error) {
      pushToast(describeError(error, t.detailLoadFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }, [describeError, pushToast, selectedPlayerId, t.detailLoadFailed, user]);

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

  /**
   * After the Whoop/Oura consent screen the provider sends the player back to
   * `/?integration=whoop&status=connected`. Report the outcome, land on the
   * devices page and strip the parameters so a reload does not repeat it.
   */
  useEffect(() => {
    if (!user || oauthReturnHandled.current) return;
    const params = new URLSearchParams(window.location.search);
    const provider = params.get("integration");
    const result = params.get("status");
    if (!provider || !result) return;

    oauthReturnHandled.current = true;
    const message = params.get("message");
    if (result === "connected") {
      pushToast(t.deviceConnectedToast, "success");
    } else if (result === "connected_with_warning") {
      pushToast(
        message ? `${t.deviceConnectedPartly}: ${message}` : t.deviceConnectedPartly,
        "info",
      );
    } else if (result === "denied") {
      // The provider says *why* it refused - dropping that turned every
      // rejected scope into a shrug for whoever had to debug it.
      pushToast(message ? `${t.deviceConnectDenied}: ${message}` : t.deviceConnectDenied, "info");
    } else {
      pushToast(message ? `${t.deviceConnectFailed}: ${message}` : t.deviceConnectFailed, "error");
    }

    if (user.role === "player") setTab("devices");
    params.delete("integration");
    params.delete("status");
    params.delete("message");
    const query = params.toString();
    window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }, [
    pushToast,
    t.deviceConnectDenied,
    t.deviceConnectFailed,
    t.deviceConnectedPartly,
    t.deviceConnectedToast,
    user,
  ]);

  // What the cycle form would save, recomputed as she changes the date or
  // ticks the period, so she sees it before pressing save.
  useEffect(() => {
    if (user?.role !== "player") return;
    let cancelled = false;
    const query = new URLSearchParams({ date: cycleForm.date });
    if (cycleForm.menstrual_flow) query.set("flow", cycleForm.menstrual_flow);
    apiRequest<CycleEstimate>(`/api/cycle/estimate?${query.toString()}`)
      .then((value) => {
        if (!cancelled) setCycleEstimate(value);
      })
      .catch(() => {
        if (!cancelled) setCycleEstimate(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.role, cycleForm.date, cycleForm.menstrual_flow, cycle]);

  // Picking another date in the wellness form should offer that day's device
  // values, not yesterday's.
  useEffect(() => {
    if (user?.role !== "player") return;
    let cancelled = false;
    apiRequest<DeviceSuggestions>(
      `/api/integrations/suggestion?date=${encodeURIComponent(wellnessForm.date)}`,
    )
      .then((value) => {
        if (!cancelled) setSuggestion(value);
      })
      .catch(() => {
        if (!cancelled) setSuggestion(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.role, wellnessForm.date]);

  useEffect(() => {
    if (user?.role === "coach") {
      void loadCoachPlayerDetail();
    }
  }, [loadCoachPlayerDetail, user?.role]);

  /* ------------------------------------------------------------ derived */

  const wellnessTrend = useMemo<TrendPoint[]>(
    () =>
      wellness
        .slice(0, 7)
        .reverse()
        .map((entry) => {
          const sleepQuality = num(entry.sleep_quality);
          const mentalEnergy = num(entry.mental_energy);
          const motivation = num(entry.motivation);
          return {
            date: entry.date,
            sleep_quality: sleepQuality,
            mental_energy: mentalEnergy,
            motivation,
            score: Math.round((sleepQuality + mentalEnergy + motivation) / 3),
          };
        }),
    [wellness],
  );

  /** The most recent day a device reported something, for the dashboard tile. */
  const latestWearable = useMemo<WearableDaily | null>(() => {
    if (wearableDaily.length === 0) return null;
    return [...wearableDaily].sort((a, b) => b.date.localeCompare(a.date))[0] ?? null;
  }, [wearableDaily]);

  const teamRiskAverage = useMemo(() => {
    if (teamPredictions.length === 0) return 0;
    return teamPredictions.reduce((sum, item) => sum + item.risk_score, 0) / teamPredictions.length;
  }, [teamPredictions]);

  const coachPriorityList = useMemo(
    () =>
      [...teamPredictions].sort((a, b) => {
        const timeLoss = (b.latest_time_loss_days ?? 0) - (a.latest_time_loss_days ?? 0);
        if (timeLoss !== 0) return timeLoss;
        const pain = (b.latest_pain_intensity ?? 0) - (a.latest_pain_intensity ?? 0);
        if (pain !== 0) return pain;
        return b.risk_score - a.risk_score;
      }),
    [teamPredictions],
  );

  /* ----------------------------------------------------------- handlers */

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      await loginRequest(username, password);
      await loadCurrentUser();
      setPassword("");
      pushToast(t.loginSuccess, "success");
    } catch (error) {
      pushToast(describeError(error, t.loginFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      await apiRequest<User>("/api/auth/register", {
        auth: false,
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
      pushToast(t.registerSuccess, "success");
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
    } catch (error) {
      pushToast(describeError(error, t.registerFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogout() {
    await logoutRequest();
    resetSessionState();
    setTab("dashboard");
    pushToast(t.logoutDone, "info");
  }

  async function handleWellnessSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      // PUT upserts: a second save for the same day corrects the first one
      // instead of failing with a conflict.
      await apiRequest<WellnessEntry>("/api/wellness/", {
        method: "PUT",
        body: JSON.stringify({ ...wellnessForm, free_text: wellnessForm.free_text || null }),
      });
      pushToast(t.wellnessSaved, "success");
      await loadPlayerData();
      setTab("dashboard");
    } catch (error) {
      pushToast(describeError(error, t.wellnessSaveFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCycleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      await apiRequest<CycleEntry>("/api/cycle/", {
        method: "PUT",
        body: JSON.stringify({
          ...cycleForm,
          contraception_type: cycleForm.contraception_type || null,
          notes: cycleForm.notes || null,
        }),
      });
      // Derived values come back from the server; keep the form on "derive"
      // so tomorrow's entry is not pinned to today's numbers.
      setCycleForm((prev) => ({ ...prev, cycle_day: null, phase: null, cycle_length: null }));
      pushToast(t.cycleSaved, "success");
      await loadPlayerData();
    } catch (error) {
      pushToast(describeError(error, t.cycleSaveFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTrainingSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      await apiRequest<TrainingEntry>("/api/training/", {
        method: "POST",
        body: JSON.stringify({
          date: trainingForm.date,
          duration_min: trainingForm.duration_min,
          intensity: trainingForm.intensity,
          session_rpe: trainingForm.session_rpe,
          session_type: trainingForm.session_type,
          participation_status: trainingForm.participation_status,
        }),
      });
      pushToast(t.trainingSaved, "success");
      await loadPlayerData();
    } catch (error) {
      pushToast(describeError(error, t.trainingSaveFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleInjurySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    try {
      await apiRequest<InjuryEntry>("/api/injury/", {
        method: "POST",
        body: JSON.stringify({ ...injuryForm, description: injuryForm.description || null }),
      });
      pushToast(t.injurySaved, "success");
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
    } catch (error) {
      pushToast(describeError(error, t.injurySaveFailed), "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handlePrivacySave(consent: PrivacyConsent) {
    try {
      await apiRequest<PrivacyConsent>("/api/privacy/consent", {
        method: "PUT",
        body: JSON.stringify({
          coach_id: consent.coach_id,
          share_cycle_data: consent.share_cycle_data,
          share_wellness_data: consent.share_wellness_data,
        }),
      });
      pushToast(
        `${t.consentSavedPrefix} ${consent.coach_name ?? `${t.coach} ${consent.coach_id}`} ${t.consentSavedSuffix}`,
        "success",
      );
      await loadPlayerData();
    } catch (error) {
      pushToast(describeError(error, t.privacySaveFailed), "error");
    }
  }

  /* ---------------------------------------------------------- integrations */

  const refreshIntegrations = useCallback(async () => {
    await loadWearables(wellnessForm.date);
  }, [loadWearables, wellnessForm.date]);

  async function handleConnectOAuth(provider: WearableProvider) {
    setBusyProvider(provider);
    try {
      const { authorize_url } = await apiRequest<{ authorize_url: string }>(
        `/api/integrations/${provider.replace("_", "-")}/authorize`,
        { method: "POST" },
      );
      // Leaves the app on purpose: the provider's consent screen must run in
      // a real browser tab, and it sends the player back to the app after.
      window.location.href = authorize_url;
    } catch (error) {
      pushToast(describeError(error, t.deviceConnectFailed), "error");
      setBusyProvider(null);
    }
  }

  async function handleConnectOuraToken(token: string) {
    setBusyProvider("oura");
    try {
      await apiRequest<IntegrationStatus>("/api/integrations/oura/personal-token", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
      pushToast(t.deviceConnectedToast, "success");
      await refreshIntegrations();
    } catch (error) {
      pushToast(describeError(error, t.deviceConnectFailed), "error");
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleCreateAppleToken() {
    setBusyProvider("apple_health");
    try {
      const issued = await apiRequest<AppleHealthToken>("/api/integrations/apple-health/token", {
        method: "POST",
      });
      setAppleToken(issued);
      await refreshIntegrations();
    } catch (error) {
      pushToast(describeError(error, t.deviceConnectFailed), "error");
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleSyncProvider(provider: WearableProvider) {
    setBusyProvider(provider);
    try {
      const result = await apiRequest<SyncResult>(
        `/api/integrations/${provider.replace("_", "-")}/sync`,
        { method: "POST", body: JSON.stringify({ days: 14 }) },
      );
      pushToast(`${t.syncDone} (${result.days_written})`, "success");
      await refreshIntegrations();
      await loadPlayerData();
    } catch (error) {
      pushToast(describeError(error, t.syncFailed), "error");
      await refreshIntegrations();
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleDisconnectProvider(provider: WearableProvider) {
    setBusyProvider(provider);
    try {
      await apiRequest<void>(`/api/integrations/${provider.replace("_", "-")}`, {
        method: "DELETE",
      });
      if (provider === "apple_health") setAppleToken(null);
      pushToast(t.deviceDisconnectedToast, "info");
      await refreshIntegrations();
    } catch (error) {
      pushToast(describeError(error, t.deviceDisconnectFailed), "error");
    } finally {
      setBusyProvider(null);
    }
  }

  async function handleDeleteAccount(password: string) {
    setIsDeletingAccount(true);
    try {
      await apiRequest<void>("/api/auth/me", {
        method: "DELETE",
        body: JSON.stringify({ password }),
      });
      // The account is gone, so there is nothing left to log out of - drop the
      // tokens locally and go back to the login screen.
      setTokens(null);
      resetSessionState();
      setTab("dashboard");
      pushToast(t.accountDeleted, "info");
    } catch (error) {
      // The server answers 403 for a wrong confirmation password; its English
      // detail text has no place in a dialog this consequential.
      const message =
        error instanceof ApiError && error.status === 403
          ? t.deleteAccountWrongPassword
          : describeError(error, t.deleteAccountFailed);
      pushToast(message, "error");
    } finally {
      setIsDeletingAccount(false);
    }
  }

  async function handleChangePassword(change: PasswordChange) {
    setIsChangingPassword(true);
    try {
      // The change revokes every refresh session, this one included. The
      // response carries a fresh pair so the device that just changed the
      // password is not the first one thrown out - storing it is not optional.
      const tokens = await apiRequest<TokenResponse>("/api/auth/password", {
        method: "POST",
        body: JSON.stringify(change),
      });
      setTokens(tokens);
      pushToast(t.passwordChanged, "success");
    } catch (error) {
      const message =
        error instanceof ApiError && error.status === 403
          ? t.passwordWrongCurrent
          : error instanceof ApiError && error.status === 400
            ? t.passwordSameAsOld
            : describeError(error, t.passwordChangeFailed);
      pushToast(message, "error");
    } finally {
      setIsChangingPassword(false);
    }
  }

  function handleApplyWellnessSuggestion() {
    const values = suggestion?.wellness;
    if (!values) return;
    setWellnessForm((prev) => ({
      ...prev,
      sleep_hours: values.sleep_hours ?? prev.sleep_hours,
      sleep_quality: values.sleep_quality ?? prev.sleep_quality,
    }));
    pushToast(t.suggestionApplied, "success");
  }

  function handleApplyTrainingSuggestion() {
    const values = suggestion?.training;
    if (!values) return;
    setTrainingForm((prev) => ({
      ...prev,
      duration_min: values.duration_min ?? prev.duration_min,
      intensity: values.intensity ?? prev.intensity,
      // Only overwrite the session type when the device named a sport we know;
      // otherwise the player's own choice stands.
      session_type:
        (values.session_type as TrainingForm["session_type"] | null) ?? prev.session_type,
    }));
    pushToast(t.suggestionApplied, "success");
  }

  function handleApplyCycleSuggestion() {
    const values = suggestion?.cycle;
    if (!values) return;
    setCycleForm((prev) => ({
      ...prev,
      cycle_day: values.cycle_day ?? prev.cycle_day,
      phase: values.phase ?? prev.phase,
      cycle_length: values.cycle_length ?? prev.cycle_length,
    }));
    pushToast(t.suggestionApplied, "success");
  }

  async function handleToggleCycleSync(provider: WearableProvider, enabled: boolean) {
    setBusyProvider(provider);
    try {
      await apiRequest<IntegrationStatus>(
        `/api/integrations/${provider.replace("_", "-")}/cycle-sync`,
        { method: "PUT", body: JSON.stringify({ enabled }) },
      );
      pushToast(enabled ? t.cycleSyncOn : t.cycleSyncOff, "success");
      await refreshIntegrations();
    } catch (error) {
      pushToast(describeError(error, t.deviceConnectFailed), "error");
    } finally {
      setBusyProvider(null);
    }
  }

  /* -------------------------------------------------------------- render */

  if (bootstrapping) {
    return (
      <div className="app-shell-bg grid min-h-screen place-items-center px-6">
        <div className="w-full max-w-sm space-y-4 text-center">
          <div className="flex justify-center">
            <Logo size={56} withText={false} />
          </div>
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <p className="text-sm text-muted">{t.loading}</p>
        </div>
      </div>
    );
  }

  const toastLayer = (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          message={toast.message}
          kind={toast.kind}
          onClose={() => setToasts((prev) => prev.filter((item) => item.id !== toast.id))}
        />
      ))}
    </div>
  );

  if (!user) {
    return (
      <>
        <LoginView
          t={t}
          language={language}
          onLanguageChange={setLanguage}
          theme={theme}
          onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
          isRegisterMode={isRegisterMode}
          onModeChange={setIsRegisterMode}
          username={username}
          password={password}
          onUsernameChange={setUsername}
          onPasswordChange={setPassword}
          registerForm={registerForm}
          onRegisterFormChange={(update) => setRegisterForm((prev) => ({ ...prev, ...update }))}
          availableTeams={availableTeams}
          isLoading={isLoading}
          onLogin={handleLogin}
          onRegister={handleRegister}
        />
        {toastLayer}
      </>
    );
  }

  const navItems: NavItem[] =
    user.role === "coach"
      ? [
          { key: "team", label: t.teamOverview, icon: <IconUsers size={22} /> },
          { key: "detail", label: t.playerDetail, icon: <IconUser size={22} /> },
        ]
      : [
          { key: "dashboard", label: t.dashboard, icon: <IconHome size={22} /> },
          { key: "wellness", label: t.wellness, icon: <IconSparkle size={22} /> },
          { key: "cycle", label: t.cycle, icon: <IconDrop size={22} /> },
          { key: "training", label: t.trainingLoad, icon: <IconDumbbell size={22} /> },
          { key: "injury", label: t.injuryTracking, icon: <IconPulseAlert size={22} /> },
        ];

  return (
    <>
      <AppShell
        user={user}
        navItems={navItems}
        tab={tab}
        onTabChange={setTab}
        language={language}
        onLanguageChange={setLanguage}
        theme={theme}
        onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
        onLogout={() => void handleLogout()}
        onOpenPrivacy={user.role === "player" ? () => setTab("privacy") : undefined}
        onOpenDevices={user.role === "player" ? () => setTab("devices") : undefined}
        onOpenAccount={() => setTab("account")}
        offline={offline}
        t={t}
      >
        {offline && (
          <div className="flex items-center gap-2 rounded-xl border border-warn/40 bg-warn-soft px-4 py-3 text-sm font-semibold text-warn">
            <IconShield size={18} />
            {t.connectionProblem}
          </div>
        )}

        {user.role === "player" && tab === "dashboard" && (
          <PlayerDashboard
            t={t}
            locale={locale}
            user={user}
            prediction={prediction}
            wellness={wellness}
            cycle={cycle}
            training={training}
            injuries={injuries}
            trend={wellnessTrend}
            wearable={latestWearable}
            onNavigate={(next) => setTab(next)}
          />
        )}

        {user.role === "player" && tab === "wellness" && (
          <WellnessView
            t={t}
            locale={locale}
            form={wellnessForm}
            onChange={(update) => setWellnessForm((prev) => ({ ...prev, ...update }))}
            onSubmit={handleWellnessSubmit}
            isLoading={isLoading}
            entries={wellness}
            suggestion={suggestion}
            onApplySuggestion={handleApplyWellnessSuggestion}
          />
        )}

        {user.role === "player" && tab === "cycle" && (
          <CycleView
            t={t}
            locale={locale}
            form={cycleForm}
            onChange={(update) => setCycleForm((prev) => ({ ...prev, ...update }))}
            onSubmit={handleCycleSubmit}
            isLoading={isLoading}
            entries={cycle}
            suggestion={suggestion}
            onApplySuggestion={handleApplyCycleSuggestion}
            estimate={cycleEstimate}
          />
        )}

        {user.role === "player" && tab === "training" && (
          <TrainingView
            t={t}
            locale={locale}
            form={trainingForm}
            onChange={(update) => setTrainingForm((prev) => ({ ...prev, ...update }))}
            onSubmit={handleTrainingSubmit}
            isLoading={isLoading}
            entries={training}
            suggestion={suggestion}
            onApplySuggestion={handleApplyTrainingSuggestion}
          />
        )}

        {user.role === "player" && tab === "injury" && (
          <InjuryView
            t={t}
            locale={locale}
            form={injuryForm}
            onChange={(update) => setInjuryForm((prev) => ({ ...prev, ...update }))}
            onSubmit={handleInjurySubmit}
            isLoading={isLoading}
            entries={injuries}
          />
        )}

        {user.role === "player" && tab === "devices" && (
          <IntegrationsView
            t={t}
            locale={locale}
            statuses={integrations}
            daily={wearableDaily}
            appleToken={appleToken}
            busyProvider={busyProvider}
            onConnectOAuth={(provider) => void handleConnectOAuth(provider)}
            onConnectOuraToken={(token) => void handleConnectOuraToken(token)}
            onCreateAppleToken={() => void handleCreateAppleToken()}
            onSync={(provider) => void handleSyncProvider(provider)}
            onDisconnect={(provider) => void handleDisconnectProvider(provider)}
            onToggleCycleSync={(provider, enabled) => void handleToggleCycleSync(provider, enabled)}
          />
        )}

        {user.role === "player" && tab === "privacy" && (
          <PrivacyView
            t={t}
            consents={consents}
            onToggle={(consentId, update) =>
              setConsents((prev) =>
                prev.map((item) => (item.id === consentId ? { ...item, ...update } : item)),
              )
            }
            onSave={(consent) => void handlePrivacySave(consent)}
            isDeleting={isDeletingAccount}
            onDeleteAccount={(password) => void handleDeleteAccount(password)}
          />
        )}

        {tab === "account" && (
          <AccountView
            t={t}
            isSaving={isChangingPassword}
            onChangePassword={(change) => void handleChangePassword(change)}
          />
        )}

        {user.role === "coach" && tab === "team" && (
          <CoachTeamView
            t={t}
            predictions={coachPriorityList}
            teamAverage={teamRiskAverage}
            onSelectPlayer={(playerId) => {
              setSelectedPlayerId(playerId);
              setTab("detail");
            }}
          />
        )}

        {user.role === "coach" && tab === "detail" && (
          <CoachDetailView
            t={t}
            locale={locale}
            predictions={coachPriorityList}
            selectedPlayerId={selectedPlayerId}
            onSelectPlayer={setSelectedPlayerId}
            onRefresh={() => void loadCoachPlayerDetail()}
            wellness={selectedPlayerWellness}
            cycle={selectedPlayerCycle}
            training={selectedPlayerTraining}
            wellnessBlocked={selectedPlayerWellnessBlocked}
            cycleBlocked={selectedPlayerCycleBlocked}
            isLoading={isLoading}
          />
        )}

        {user.role === "coach" && <SystemStatusCard t={t} locale={locale} status={modelStatus} />}
      </AppShell>
      {toastLayer}
    </>
  );
}

export default App;
