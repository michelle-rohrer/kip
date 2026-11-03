export type Role = "player" | "coach";

export type User = {
  id: number;
  username: string;
  email: string | null;
  role: Role;
  team_id: number | null;
  training_uid: string | null;
  player_position: string | null;
  name: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type TeamOption = {
  id: number;
  name: string;
};

/**
 * Every metric is optional: the API stores partial check-ins, so the UI must
 * never assume a number is there.
 */
export type WellnessEntry = {
  id: number;
  date: string;
  sleep_hours: number | null;
  sleep_quality: number | null;
  muscle_soreness: number | null;
  mental_energy: number | null;
  stress_level: number | null;
  motivation: number | null;
  rpe_previous_day: number | null;
  free_text: string | null;
};

export type InjuryEntry = {
  id: number;
  player_id: number;
  date: string;
  body_location: string;
  pain_intensity: number | null;
  is_chronic: boolean;
  medical_attention: boolean;
  time_loss_days: number | null;
  description: string | null;
};

export type CyclePhase = "menstruation" | "follicular" | "ovulation" | "luteal";

export type MenstrualFlow = "none" | "light" | "medium" | "heavy";

/** What the app works out from her recorded period days. */
export type CycleEstimate = {
  date: string;
  available: boolean;
  cycle_day: number | null;
  phase: CyclePhase | null;
  cycle_length: number | null;
  period_start: string | null;
  flow: MenstrualFlow | null;
};

export type CycleEntry = {
  id: number;
  date: string;
  cycle_day: number | null;
  phase: CyclePhase | null;
  cycle_length: number | null;
  menstrual_flow: MenstrualFlow | null;
  pms_score: number | null;
  cramps: boolean;
  migraine: boolean;
  fatigue: boolean;
  contraception_type: string | null;
  notes: string | null;
};

export type TrainingEntry = {
  id: number;
  date: string;
  duration_min: number | null;
  intensity: number | null;
  session_rpe: number | null;
  session_type: string | null;
  participation_status: string | null;
};

export type PrivacyConsent = {
  id: number;
  coach_id: number;
  coach_name?: string | null;
  share_cycle_data: boolean;
  share_wellness_data: boolean;
};

export type RiskLevel = "green" | "yellow" | "red";

export type Prediction = {
  id?: number;
  player_id?: number;
  player_name?: string | null;
  date?: string;
  risk_score: number;
  risk_level: RiskLevel;
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

export type ModelTrainingStatus = {
  status: "ok" | "failed";
  updated_at: string;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  error?: string | null;
  metrics?: Record<string, unknown> | null;
  context?: Record<string, unknown> | null;
};

export type WearableProvider = "whoop" | "oura" | "apple_health";

export type IntegrationStatus = {
  provider: WearableProvider;
  /** A connection exists and can deliver data. */
  connected: boolean;
  /** The server has the credentials this provider needs. */
  configured: boolean;
  /** OAuth is available, so the player never has to paste a token. */
  supports_oauth: boolean;
  /** Cycle data is only taken from this provider once the player allows it. */
  sync_cycle: boolean;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_error: string | null;
  last_data_date: string | null;
};

export type WearableDaily = {
  id: number;
  player_id: number;
  date: string;
  provider: WearableProvider;
  sleep_hours: number | null;
  sleep_score: number | null;
  readiness_score: number | null;
  hrv_ms: number | null;
  resting_hr: number | null;
  respiratory_rate: number | null;
  strain: number | null;
  steps: number | null;
  active_calories: number | null;
  workout_minutes: number | null;
  workout_sport: string | null;
  menstrual_flow: string | null;
};

export type WellnessSuggestion = {
  sleep_hours: number | null;
  sleep_quality: number | null;
  readiness_score: number | null;
  hrv_ms: number | null;
  resting_hr: number | null;
  strain: number | null;
};

export type TrainingSuggestion = {
  duration_min: number | null;
  /** Only present when the device measured strain. */
  intensity: number | null;
  /** Only present when the sport is one the app recognises. */
  session_type: string | null;
  sport: string | null;
};

export type CycleSuggestion = {
  cycle_day: number | null;
  phase: CyclePhase | null;
  cycle_length: number | null;
  flow: string | null;
};

/** What the three forms can prefill for one day, from one call. */
export type DeviceSuggestions = {
  date: string;
  sources: WearableProvider[];
  wellness: WellnessSuggestion | null;
  training: TrainingSuggestion | null;
  cycle: CycleSuggestion | null;
};

export type AppleHealthToken = {
  provider: string;
  ingest_token: string;
  ingest_url: string;
};

export type SyncResult = {
  provider: WearableProvider;
  days_written: number;
  first_day: string | null;
  last_day: string | null;
  synced_at: string;
};

export type PlayerTab =
  | "dashboard"
  | "wellness"
  | "cycle"
  | "training"
  | "injury"
  | "privacy"
  | "devices";
export type CoachTab = "team" | "detail";
export type AppTab = PlayerTab | CoachTab;
