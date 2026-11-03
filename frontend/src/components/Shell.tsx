import { ReactNode, useEffect, useRef, useState } from "react";
import { LANGUAGE_LABELS, Language } from "../i18n";
import { AppTab, User } from "../types";
import {
  IconChevronDown,
  IconGlobe,
  IconLogout,
  IconMoon,
  IconShield,
  IconSun,
  IconWatch,
} from "./icons";
import { Chip } from "./ui";
import { cx } from "./theme";

export type NavItem = {
  key: AppTab;
  label: string;
  icon: ReactNode;
};

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <span
      className="grid shrink-0 place-items-center rounded-full font-display font-bold text-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        backgroundImage: "linear-gradient(135deg, rgb(var(--c-brand)), rgb(var(--c-iris)))",
      }}
      aria-hidden="true"
    >
      {initials || "?"}
    </span>
  );
}

export function Logo({ size = 36, withText = true }: { size?: number; withText?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <img
        src="/logo.png"
        alt=""
        width={size}
        height={size}
        className="rounded-xl shadow-card"
        style={{ width: size, height: size }}
      />
      {withText && (
        <span className="font-display text-lg font-extrabold tracking-tight text-ink">
          Volley<span className="text-gradient">Sync</span>
        </span>
      )}
    </span>
  );
}

export function AppShell({
  user,
  navItems,
  tab,
  onTabChange,
  language,
  onLanguageChange,
  theme,
  onThemeToggle,
  onLogout,
  onOpenPrivacy,
  onOpenDevices,
  offline,
  children,
  t,
}: {
  user: User;
  navItems: NavItem[];
  tab: AppTab;
  onTabChange: (tab: AppTab) => void;
  language: Language;
  onLanguageChange: (language: Language) => void;
  theme: "light" | "dark";
  onThemeToggle: () => void;
  onLogout: () => void;
  onOpenPrivacy?: () => void;
  onOpenDevices?: () => void;
  offline: boolean;
  children: ReactNode;
  t: Record<string, string>;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [menuOpen]);

  return (
    <div className="app-shell-bg min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/80 bg-bg/85 backdrop-blur-xl pt-safe">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 lg:px-8">
          <Logo />
          <div className="flex items-center gap-2">
            {offline && (
              <Chip tone="warn" className="hidden sm:inline-flex">
                {t.offlineBadge}
              </Chip>
            )}
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                className="flex items-center gap-2 rounded-pill border border-line bg-card py-1 pl-1 pr-2.5 transition active:scale-95"
              >
                <Avatar name={user.name} size={32} />
                <span className="hidden max-w-[9rem] truncate text-sm font-semibold text-ink sm:block">
                  {user.name}
                </span>
                <IconChevronDown size={16} className="text-subtle" />
              </button>

              {menuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10 animate-fadeIn bg-ink/10"
                    onClick={() => setMenuOpen(false)}
                    aria-hidden="true"
                  />
                  <div
                    role="menu"
                    className="absolute right-0 z-20 mt-2 w-72 animate-fadeUp rounded-card border border-line bg-card p-3 shadow-lift"
                  >
                    <div className="flex items-center gap-3 rounded-xl bg-raised p-3">
                      <Avatar name={user.name} size={40} />
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">{user.name}</p>
                        <p className="truncate text-xs text-muted">
                          {user.role === "coach" ? t.coachApp : t.playerApp}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 space-y-2">
                      <label className="block">
                        <span className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-subtle">
                          <IconGlobe size={14} /> {t.language}
                        </span>
                        <select
                          className="w-full rounded-xl border border-line bg-raised px-3 py-2.5 text-sm font-medium text-ink"
                          value={language}
                          onChange={(event) => onLanguageChange(event.target.value as Language)}
                        >
                          {(Object.keys(LANGUAGE_LABELS) as Language[]).map((code) => (
                            <option key={code} value={code}>
                              {LANGUAGE_LABELS[code]}
                            </option>
                          ))}
                        </select>
                      </label>

                      <button
                        type="button"
                        onClick={onThemeToggle}
                        className="flex w-full items-center justify-between rounded-xl border border-line bg-raised px-3 py-2.5 text-sm font-semibold text-ink"
                      >
                        <span className="flex items-center gap-2">
                          {theme === "dark" ? <IconMoon size={16} /> : <IconSun size={16} />}
                          {t.appearance}
                        </span>
                        <span className="text-xs font-medium text-muted">
                          {theme === "dark" ? t.themeDark : t.themeLight}
                        </span>
                      </button>

                      {onOpenDevices && (
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpen(false);
                            onOpenDevices();
                          }}
                          className="flex w-full items-center gap-2 rounded-xl border border-line bg-raised px-3 py-2.5 text-sm font-semibold text-ink"
                        >
                          <IconWatch size={16} className="text-ok" />
                          {t.devicesTitle}
                        </button>
                      )}

                      {onOpenPrivacy && (
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpen(false);
                            onOpenPrivacy();
                          }}
                          className="flex w-full items-center gap-2 rounded-xl border border-line bg-raised px-3 py-2.5 text-sm font-semibold text-ink"
                        >
                          <IconShield size={16} className="text-brand" />
                          {t.privacySettings}
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => {
                          setMenuOpen(false);
                          onLogout();
                        }}
                        className="flex w-full items-center gap-2 rounded-xl bg-danger-soft px-3 py-2.5 text-sm font-semibold text-danger"
                      >
                        <IconLogout size={16} />
                        {t.logout}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-6xl gap-8 px-4 pb-32 pt-5 lg:px-8 lg:pb-12">
        <aside className="sticky top-24 hidden h-fit w-56 shrink-0 lg:block">
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const active = item.key === tab;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onTabChange(item.key)}
                  className={cx(
                    "flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold transition",
                    active
                      ? "bg-card text-ink shadow-card"
                      : "text-muted hover:bg-card/60 hover:text-ink",
                  )}
                >
                  <span className={active ? "text-brand" : "text-subtle"}>{item.icon}</span>
                  {item.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1 space-y-5">{children}</main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-card/95 backdrop-blur-xl pb-safe lg:hidden">
        <div className="mx-auto flex max-w-lg items-stretch justify-around px-1">
          {navItems.map((item) => {
            const active = item.key === tab;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => onTabChange(item.key)}
                aria-current={active ? "page" : undefined}
                className="group flex min-w-0 flex-1 flex-col items-center gap-1 px-1 pb-2 pt-2.5 transition active:scale-95"
              >
                <span
                  className={cx(
                    "grid h-8 w-12 place-items-center rounded-pill transition",
                    active ? "bg-brand-soft text-brand" : "text-subtle",
                  )}
                >
                  {item.icon}
                </span>
                <span
                  className={cx(
                    "w-full truncate text-center text-[10px] font-semibold leading-none",
                    active ? "text-ink" : "text-subtle",
                  )}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
