# VolleySync oeffentlich stellen – Schritt fuer Schritt

Ziel: Deine Spielerinnen oeffnen einen Link auf dem Handy, loggen sich ein und tragen ihre Daten ein.

**Aufbau (gewaehlt: schnell + immer erreichbar)**

| Teil | Dienst | Kosten |
| --- | --- | --- |
| Datenbank (PostgreSQL) | [Neon](https://neon.tech) | gratis |
| Backend (FastAPI) | [Render](https://render.com) Web Service, Plan *Starter* | ca. 7 USD/Monat |
| Frontend (React) | Render Static Site | gratis |

Der Starter-Plan ist bewusst gewaehlt: Der Gratis-Plan von Render schlaeft nach 15 Minuten ein, der erste
Aufruf dauert dann bis zu einer Minute. Mit *Starter* ist die App sofort da.

Zeitaufwand beim ersten Mal: ca. 30–45 Minuten.

---

## Stand heute (Stand 3. November 2026)

| Teil | Status |
| --- | --- |
| Frontend | **laeuft** auf [volleysync.vercel.app](https://volleysync.vercel.app), deployt selbst aus `main` |
| Backend | **fehlt** – `volleysync-api.onrender.com` antwortet mit 404 |
| Datenbank | **fehlt** |

Das Frontend ist also schon oeffentlich, zeigt aber auf ein Backend
(`https://volleysync.onrender.com`), das nicht antwortet. Zu tun bleiben die
Datenbank und der Backend-Service – danach laeuft die App.

> `volleysync.onrender.com` laeuft beim Aufruf in einen Timeout statt in ein 404.
> Das deutet auf einen **bestehenden, pausierten Render-Service** unter genau
> diesem Namen hin. Schau zuerst im Render-Dashboard nach: gibt es den Service
> schon, reaktivierst du ihn (Schritt 2 entfaellt dann) und setzt nur die
> Umgebungsvariablen. Gibt es ihn nicht, legst du ihn neu an.

**Wenn Vercel das Frontend bleibt**, musst du in Schritt 2 nur `volleysync-api`
anlegen – die Static Site aus `render.yaml` ist dann ueberfluessig. Zwei Dinge
muessen dann zusammenpassen:

- in Vercel: `VITE_API_BASE_URL` = die URL des Render-Backends (danach **Redeploy**,
  der Wert wird in den Build eingebacken)
- auf Render: `CORS_ALLOW_ORIGINS` = `https://volleysync.vercel.app`

---

## 0) Vorbereitung

- [ ] Code ist auf `main` gepusht (`git status` sauber)
- [ ] Konto bei [neon.tech](https://neon.tech) (GitHub-Login moeglich)
- [ ] Konto bei [render.com](https://render.com) + Kreditkarte hinterlegt
- [ ] Zwei Werte lokal erzeugen und irgendwo sicher zwischenspeichern:

```bash
# JWT-Secret (Login-Schluessel, mind. 32 Zeichen)
openssl rand -hex 32

# Coach-Passwort fuer dich, falls dir keins einfaellt
openssl rand -base64 18
```

---

## 1) Datenbank bei Neon anlegen

1. Auf neon.tech einloggen -> **New Project**
2. Name: `volleysync`, Region: **Europe (Frankfurt)**
3. Nach dem Anlegen: **Connection string** kopieren (Format
   `postgresql://user:passwort@ep-xyz.eu-central-1.aws.neon.tech/neondb?sslmode=require`)
4. Diesen String brauchst du gleich als `DATABASE_URL`

> Das Backend wandelt `postgresql://` automatisch in das richtige Treiberformat um – du musst am
> String nichts aendern.

---

## 2) Services bei Render anlegen (Blueprint)

Im Repo liegt `render.yaml`. Render liest die Datei und erstellt beide Services automatisch.

1. Render Dashboard -> **New** -> **Blueprint**
2. Repository `michelle-rohrer/kip` auswaehlen, Branch `main`
3. Render zeigt zwei Services: `volleysync-api` und `volleysync-app`
4. Render fragt jetzt die Werte ab, die in `render.yaml` mit `sync: false` markiert sind:

**Fuer `volleysync-api`:**

| Variable | Wert |
| --- | --- |
| `DATABASE_URL` | Connection String aus Neon (Schritt 1) |
| `JWT_SECRET_KEY` | Der `openssl rand -hex 32`-Wert |
| `CORS_ALLOW_ORIGINS` | `https://volleysync.vercel.app` (bzw. die Render-Frontend-URL) |
| `TRUSTED_HOSTS` | vorlaeufig `volleysync-api.onrender.com` |
| `BOOTSTRAP_COACH_USERNAME` | dein Login, z. B. `michelle` |
| `BOOTSTRAP_COACH_PASSWORD` | dein Coach-Passwort (mind. 8 Zeichen) |
| `BOOTSTRAP_COACH_NAME` | z. B. `Michelle Rohrer` |
| `API_BASE_URL` | vorlaeufig `https://volleysync-api.onrender.com` |
| `FRONTEND_BASE_URL` | `https://volleysync.vercel.app` (bzw. die Render-Frontend-URL) |

> **Wichtig bei den Teams:** Eine Trainerin sieht nur Spielerinnen **ihres eigenen Teams**.
> `BOOTSTRAP_TEAMS` steht standardmaessig auf zwei Teams und dein Coach-Konto landet im
> ersten davon. Wenn du alle Spielerinnen in einer Uebersicht willst, setze
> `BOOTSTRAP_TEAMS` auf genau **ein** Team – sonst registriert sich die Haelfte in ein
> Team, das du nicht siehst. Mit `BOOTSTRAP_COACH_TEAM` bestimmst du, in welches Team
> dein Coach-Konto kommt.

`WEARABLE_ENCRYPTION_KEY` und `CRON_SECRET` erzeugt Render selbst – dort nichts eintragen.
Die Whoop-/Oura-Variablen bleiben vorerst leer; sie sind nur fuer die Geraete-Anbindung
noetig (siehe `docs/Wearables_Anleitung.md`) und die App laeuft auch ohne sie.

**Fuer `volleysync-app`:**

| Variable | Wert |
| --- | --- |
| `VITE_API_BASE_URL` | vorlaeufig `https://volleysync-api.onrender.com` |

5. **Apply** klicken. Der erste Build dauert 5–10 Minuten.

Beim Start des Backends passiert automatisch:

- `alembic upgrade head` – Datenbank-Tabellen anlegen/aktualisieren
- `python -m app.bootstrap` – Teams anlegen und dein Coach-Konto erstellen
- danach startet die API

---

## 3) Echte URLs eintragen

Render vergibt die endgueltigen URLs erst nach dem ersten Deploy. Sie stehen oben auf der jeweiligen
Service-Seite und sehen meist so aus wie oben angenommen. Falls sie abweichen (z. B. mit Zusatz-Suffix):

1. `volleysync-api` -> **Environment**:
   - `CORS_ALLOW_ORIGINS` = exakte Frontend-URL **ohne Slash am Ende**
   - `TRUSTED_HOSTS` = Hostname der API **ohne** `https://`
   - `API_BASE_URL` = exakte API-URL **ohne Slash am Ende**
   - `FRONTEND_BASE_URL` = exakte Frontend-URL **ohne Slash am Ende**
2. Frontend -> **Environment**:
   - auf Vercel: Project `volleysync` -> Settings -> Environment Variables ->
     `VITE_API_BASE_URL` = exakte API-URL **ohne Slash am Ende** -> danach
     **Redeploy**
   - auf Render (falls Static Site): `volleysync-app` -> `VITE_API_BASE_URL`
3. Beide Services **Manual Deploy -> Deploy latest commit**

> `VITE_API_BASE_URL` wird beim Build in die Dateien eingebacken. Nach einer Aenderung muss das
> Frontend **neu gebaut** werden – ein Neustart reicht nicht.

---

## 4) Smoke-Test (5 Minuten)

```bash
# API lebt?
curl https://volleysync-api.onrender.com/health          # {"status":"ok"}

# Datenbank verbunden?
curl https://volleysync-api.onrender.com/health/db       # {"status":"ok"}

# Teams vorhanden (brauchen die Spielerinnen zur Registrierung)?
curl https://volleysync-api.onrender.com/api/teams/
```

Danach im Browser:

- [ ] Frontend-URL oeffnet die Login-Seite
- [ ] Login als Coach funktioniert (dein `BOOTSTRAP_COACH_USERNAME`)
- [ ] Registrierung als Testspielerin funktioniert, Team ist waehlbar
- [ ] Wellness-Eintrag speichern -> erscheint im Dashboard
- [ ] Denselben Tag nochmals speichern -> der Eintrag wird ueberschrieben, keine Fehlermeldung
- [ ] Coach sieht die Spielerin in der Team-Uebersicht
- [ ] Menue (Avatar) -> **Geraete & Sync** oeffnet sich und zeigt drei Karten

---

## 5) Spielerinnen einladen

Schick ihnen die Frontend-URL plus diese kurze Anleitung:

> **VolleySync installieren**
> 1. Link im Handy-Browser oeffnen
> 2. **iPhone (Safari):** Teilen-Symbol unten -> *Zum Home-Bildschirm*
>    **Android (Chrome):** Menue (drei Punkte) -> *App installieren*
> 3. Konto erstellen (Name, Benutzername, E-Mail, Passwort, Team, Position)
> 4. Unter *Datenfreigaben* selbst entscheiden, was die Trainerin sehen darf
> 5. Optional: unter *Geraete & Sync* Whoop, Oura oder Apple Health verbinden –
>    dann kommen Schlaf, HRV und Erholung automatisch

Die App laeuft danach wie eine normale App im Vollbild, ohne Browserleiste. Login bleibt bestehen
(60 Tage), es muss sich also niemand staendig neu anmelden.

---

## 6) Updates ausrollen

```bash
git checkout -b feature/meine-aenderung
# ... arbeiten ...
cd backend && ../.venv-ci/bin/python -m pytest        # Tests
cd ../frontend && npm run lint && npm run build       # Frontend
git commit -am "..." && git push -u origin feature/meine-aenderung
```

PR nach `main` mergen -> Render deployt beide Services automatisch (`autoDeploy: true`).
Migrationen laufen beim Start mit, du musst nichts von Hand ausfuehren.

Rollback: In Render auf der Service-Seite unter **Events** -> **Rollback** auf den letzten guten Deploy.

---

## 7) ML-Modell trainieren

Ohne trainiertes Modell rechnet die App mit einer Heuristik (`heuristic-v1`) – die App funktioniert
also sofort, die Anzeige stimmt nur noch nicht ML-basiert.

Sobald genug echte Daten da sind, in Render: `volleysync-api` -> **Shell**:

```bash
python -m app.ml.retrain
```

Status pruefen: als Coach einloggen -> Karte **Modell-Training** unten aufklappen.

> Achtung: Die Modelldatei liegt im Container und ist nach jedem Deploy weg. Fuer dauerhaftes
> Speichern spaeter entweder eine **Persistent Disk** (Render, ab ca. 1 USD/Monat) an
> `/app/app/ml/models` haengen oder das Training als Cron Job einrichten.

**Niemals `python -m app.data_generation.seed` in Produktion ausfuehren.** Der Befehl loescht alle
echten Daten und legt Testkonten mit Passwoertern an, die im Repository stehen.

---

## 8) Datenschutz – bevor echte Daten reinkommen

Zyklus- und Gesundheitsdaten sind besonders schuetzenswerte Personendaten (revDSG/DSGVO). Das ist
keine Rechtsberatung, aber diese Punkte solltest du vorher erledigen:

- [ ] **Einwilligung** schriftlich einholen (kurzes Formular reicht): welche Daten, wofuer, wie lange,
      wer sieht sie, Widerruf jederzeit moeglich
- [ ] Bei Minderjaehrigen: Einwilligung der Eltern
- [ ] Spielerinnen erklaeren, dass **Zyklus- und Wellnessdaten nur nach eigener Freigabe** beim Coach
      landen (Menue -> Datenfreigaben)
- [ ] Fuer die Thesis: nur **anonymisierte/aggregierte** Auswertungen verwenden
- [ ] Loeschung auf Wunsch: aktuell nur direkt in der Datenbank moeglich – als naechstes Feature
      einplanen (steht schon in `backlog.txt`)

---

## 9) Kosten und Limits

| Posten | Kosten |
| --- | --- |
| Render Web Service (Starter) | ca. 7 USD/Monat |
| Render Static Site | 0 |
| Neon Free (0.5 GB) | 0 |
| **Total** | **ca. 7 USD/Monat** |

0.5 GB reichen fuer ein Team ueber Jahre – ein taeglicher Eintrag pro Spielerin sind wenige KB.

---

## 10) Wenn etwas nicht geht

| Symptom | Ursache | Loesung |
| --- | --- | --- |
| Login-Seite laedt, aber Login meldet "Keine Verbindung zum Server" | `VITE_API_BASE_URL` falsch oder Frontend nicht neu gebaut | Wert pruefen, Frontend neu deployen |
| Browser-Konsole zeigt CORS-Fehler | `CORS_ALLOW_ORIGINS` passt nicht exakt zur Frontend-URL | exakte URL ohne Slash am Ende eintragen, API neu deployen |
| API antwortet mit **400 Invalid host header** | `TRUSTED_HOSTS` falsch | nur Hostname (ohne `https://`) eintragen |
| Backend startet nicht, Log sagt `JWT_SECRET_KEY must be set` | Secret fehlt oder ist zu kurz | `openssl rand -hex 32` neu setzen |
| Registrierung zeigt keine Teams | Bootstrap lief nicht | Render Shell: `python -m app.bootstrap` |
| Coach sieht eine Spielerin nicht | Spielerin hat ein anderes Team gewaehlt | Team der Spielerin in der DB angleichen oder `BOOTSTRAP_TEAMS` auf ein Team reduzieren |
| Coach-Login geht nicht | Konto fehlt oder Passwort vergessen | `BOOTSTRAP_COACH_RESET_PASSWORD=true` + neues `BOOTSTRAP_COACH_PASSWORD` setzen, deployen, danach die Variable wieder auf `false` |
| Spielerinnen sehen nach Update die alte Version | Service Worker Cache | Seite einmal neu laden; `index.html`/`sw.js` sind bereits vom Caching ausgenommen |
| Alles langsam beim ersten Aufruf | Service schlaeft (Gratis-Plan) | Plan `starter` pruefen |
| Whoop/Oura lassen sich nicht verbinden | `API_BASE_URL` oder die Redirect-URI beim Anbieter stimmt nicht | siehe `docs/Wearables_Anleitung.md` |
