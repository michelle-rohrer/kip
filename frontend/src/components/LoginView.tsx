import { FormEvent } from "react";
import { LANGUAGE_LABELS, Language } from "../i18n";
import { TeamOption } from "../types";
import { IconMoon, IconShield, IconSparkle, IconSun, IconTrend } from "./icons";
import { Button, Field, Select, TextInput } from "./ui";
import { cx } from "./theme";
import { Logo } from "./Shell";

export type RegisterForm = {
  username: string;
  email: string;
  password: string;
  name: string;
  team_id: string;
  player_position: string;
};

export function LoginView({
  t,
  language,
  onLanguageChange,
  theme,
  onThemeToggle,
  isRegisterMode,
  onModeChange,
  username,
  password,
  onUsernameChange,
  onPasswordChange,
  registerForm,
  onRegisterFormChange,
  availableTeams,
  isLoading,
  onLogin,
  onRegister,
}: {
  t: Record<string, string>;
  language: Language;
  onLanguageChange: (language: Language) => void;
  theme: "light" | "dark";
  onThemeToggle: () => void;
  isRegisterMode: boolean;
  onModeChange: (register: boolean) => void;
  username: string;
  password: string;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  registerForm: RegisterForm;
  onRegisterFormChange: (update: Partial<RegisterForm>) => void;
  availableTeams: TeamOption[];
  isLoading: boolean;
  onLogin: (event: FormEvent<HTMLFormElement>) => void;
  onRegister: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const highlights = [
    { icon: <IconSparkle size={18} />, text: t.heroPoint1 },
    { icon: <IconTrend size={18} />, text: t.heroPoint2 },
    { icon: <IconShield size={18} />, text: t.heroPoint3 },
  ];

  return (
    <div className="app-shell-bg min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 lg:px-8">
        <div className="flex items-center justify-between gap-3">
          <Logo />
          <div className="flex items-center gap-2">
            <select
              className="h-10 rounded-xl border border-line bg-card px-3 text-sm font-semibold text-ink"
              value={language}
              onChange={(event) => onLanguageChange(event.target.value as Language)}
              aria-label={t.language}
            >
              {(Object.keys(LANGUAGE_LABELS) as Language[]).map((code) => (
                <option key={code} value={code}>
                  {LANGUAGE_LABELS[code]}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onThemeToggle}
              aria-label={t.appearance}
              className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-card text-muted transition active:scale-95"
            >
              {theme === "dark" ? <IconMoon size={18} /> : <IconSun size={18} />}
            </button>
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center py-8">
          <div className="grid w-full items-center gap-10 lg:grid-cols-2 lg:gap-16">
            <div className="hidden lg:block">
              <p className="chip bg-brand-soft text-brand-ink">{t.appTagline}</p>
              <h1 className="mt-4 font-display text-5xl font-extrabold leading-[1.05] tracking-tight text-ink">
                Volley<span className="text-gradient">Sync</span>
              </h1>
              <p className="mt-4 max-w-md text-lg leading-relaxed text-muted">{t.loginSubtitle}</p>
              <ul className="mt-8 space-y-3">
                {highlights.map((item) => (
                  <li key={item.text} className="flex items-start gap-3">
                    <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-card text-brand shadow-card">
                      {item.icon}
                    </span>
                    <span className="max-w-sm text-sm leading-relaxed text-muted">{item.text}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="card animate-fadeUp p-6 sm:p-7">
              <div className="mb-5 grid grid-cols-2 gap-1 rounded-xl bg-raised p-1">
                {[
                  { value: false, label: t.login },
                  { value: true, label: t.register },
                ].map((option) => (
                  <button
                    key={String(option.value)}
                    type="button"
                    onClick={() => onModeChange(option.value)}
                    className={cx(
                      "min-h-[42px] rounded-lg text-sm font-bold transition",
                      isRegisterMode === option.value
                        ? "bg-card text-ink shadow-card"
                        : "text-muted",
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              {!isRegisterMode ? (
                <form className="space-y-4" onSubmit={onLogin}>
                  <div>
                    <h2 className="font-display text-2xl font-extrabold text-ink">
                      {t.loginWelcome}
                    </h2>
                    <p className="mt-1 text-sm text-muted">{t.loginSubtitle}</p>
                  </div>
                  <Field label={t.username}>
                    <TextInput
                      value={username}
                      onChange={(event) => onUsernameChange(event.target.value)}
                      type="text"
                      autoComplete="username"
                      autoCapitalize="none"
                      required
                    />
                  </Field>
                  <Field label={t.password}>
                    <TextInput
                      value={password}
                      onChange={(event) => onPasswordChange(event.target.value)}
                      type="password"
                      autoComplete="current-password"
                      required
                    />
                  </Field>
                  <Button type="submit" block loading={isLoading}>
                    {isLoading ? t.loggingIn : t.signIn}
                  </Button>
                  {/* No demo credentials here any more. The names used to be
                      Timo and Denise, which are real coach accounts now - the
                      hint pointed at people, not at test data. The seed prints
                      its own logins when it runs. */}
                </form>
              ) : (
                <form className="space-y-4" onSubmit={onRegister}>
                  <div>
                    <h2 className="font-display text-2xl font-extrabold text-ink">
                      {t.createAccount}
                    </h2>
                    <p className="mt-1 text-sm text-muted">{t.registerSubtitle}</p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label={t.name} className="sm:col-span-2">
                      <TextInput
                        value={registerForm.name}
                        onChange={(event) => onRegisterFormChange({ name: event.target.value })}
                        type="text"
                        autoComplete="name"
                        required
                      />
                    </Field>
                    <Field label={t.username}>
                      <TextInput
                        value={registerForm.username}
                        onChange={(event) => onRegisterFormChange({ username: event.target.value })}
                        type="text"
                        autoComplete="username"
                        autoCapitalize="none"
                        required
                      />
                    </Field>
                    <Field label={t.email}>
                      <TextInput
                        value={registerForm.email}
                        onChange={(event) => onRegisterFormChange({ email: event.target.value })}
                        type="email"
                        autoComplete="email"
                        autoCapitalize="none"
                        required
                      />
                    </Field>
                    <Field label={t.password} hint={t.passwordMin} className="sm:col-span-2">
                      <TextInput
                        value={registerForm.password}
                        onChange={(event) => onRegisterFormChange({ password: event.target.value })}
                        type="password"
                        autoComplete="new-password"
                        minLength={8}
                        required
                      />
                    </Field>
                    <Field label={t.team}>
                      <Select
                        value={registerForm.team_id}
                        onChange={(event) => onRegisterFormChange({ team_id: event.target.value })}
                        required
                      >
                        <option value="">{t.selectTeam}</option>
                        {availableTeams.map((team) => (
                          <option key={team.id} value={String(team.id)}>
                            {team.name}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field label={t.playerPosition}>
                      <Select
                        value={registerForm.player_position}
                        onChange={(event) =>
                          onRegisterFormChange({ player_position: event.target.value })
                        }
                        required
                      >
                        <option value="">{t.selectPlayerPosition}</option>
                        <option value="setter">{t.posSetter}</option>
                        <option value="outside_hitter">{t.posOutsideHitter}</option>
                        <option value="opposite">{t.posOpposite}</option>
                        <option value="middle_blocker">{t.posMiddleBlocker}</option>
                        <option value="libero">{t.posLibero}</option>
                      </Select>
                    </Field>
                  </div>
                  <Button
                    type="submit"
                    block
                    loading={isLoading}
                    disabled={isLoading || availableTeams.length === 0}
                  >
                    {isLoading ? t.registering : t.createAccount}
                  </Button>
                </form>
              )}
            </div>
          </div>
        </div>

        <p className="pb-2 text-center text-xs text-subtle">VolleySync · {t.appTagline}</p>
      </div>
    </div>
  );
}
