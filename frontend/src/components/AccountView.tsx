import { useState } from "react";

import { IconKey } from "./icons";
import { Button, Card, CardHeader, Field, TextInput } from "./ui";

type T = Record<string, string>;

export type PasswordChange = { current_password: string; new_password: string };

/** Change your own password.
 *
 * Open to both roles on purpose: coach accounts are created from environment
 * variables on the server, so without this a coach is stuck forever with the
 * password somebody once typed into the Render dashboard.
 */
function ChangePasswordCard({
  t,
  isSaving,
  onSubmit,
}: {
  t: T;
  isSaving: boolean;
  onSubmit: (change: PasswordChange) => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Checked here as well as on the server: a typo in the repeated password is
  // not worth a round trip, and the server never sees the second field anyway.
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (next.length < 8) {
      setError(t.passwordTooShort);
      return;
    }
    if (next !== repeat) {
      setError(t.passwordMismatch);
      return;
    }
    setError(null);
    onSubmit({ current_password: current, new_password: next });
    setCurrent("");
    setNext("");
    setRepeat("");
  }

  return (
    <Card className="animate-fadeUp">
      <CardHeader
        title={t.changePasswordTitle}
        subtitle={t.changePasswordIntro}
        icon={<IconKey size={20} />}
        tone="brand"
      />
      <form className="space-y-4" onSubmit={submit}>
        <Field label={t.currentPassword}>
          <TextInput
            type="password"
            value={current}
            autoComplete="current-password"
            onChange={(event) => setCurrent(event.target.value)}
          />
        </Field>
        <Field label={t.newPassword}>
          <TextInput
            type="password"
            value={next}
            autoComplete="new-password"
            minLength={8}
            onChange={(event) => setNext(event.target.value)}
          />
        </Field>
        <Field label={t.newPasswordRepeat}>
          <TextInput
            type="password"
            value={repeat}
            autoComplete="new-password"
            minLength={8}
            onChange={(event) => setRepeat(event.target.value)}
          />
        </Field>
        {error && (
          <p className="rounded-xl bg-danger-soft px-4 py-3 text-sm font-semibold leading-snug text-danger">
            {error}
          </p>
        )}
        <Button type="submit" loading={isSaving} disabled={!current || !next || !repeat}>
          {t.changePasswordSubmit}
        </Button>
      </form>
    </Card>
  );
}

export function AccountView({
  t,
  isSaving,
  onChangePassword,
}: {
  t: T;
  isSaving: boolean;
  onChangePassword: (change: PasswordChange) => void;
}) {
  return <ChangePasswordCard t={t} isSaving={isSaving} onSubmit={onChangePassword} />;
}
