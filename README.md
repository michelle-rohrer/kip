# VolleySync - Cycle-Aware Load Monitoring

Track smart. Play strong.

VolleySync ist ein Full-Stack-Projekt für zyklusbewusste Belastungssteuerung im Volleyball.  
Spielerinnen erfassen Wellness-, Zyklus-, Trainings- und Verletzungsdaten. Trainerinnen erhalten eine priorisierte Team-Übersicht mit Risiko-Signalen.

Schlaf, HRV, Ruhepuls und Erholung muss niemand von Hand eintippen: Whoop, Oura und
Apple Health lassen sich direkt verbinden (`docs/Wearables_Anleitung.md`).

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, scikit-learn
- Frontend: React, Vite, TypeScript, Tailwind (installierbare PWA, Hell-/Dunkelmodus, DE/EN/IT)
- Datenbank: PostgreSQL
- Wearables: Whoop (OAuth), Oura (OAuth oder persönlicher Token), Apple Health (Push vom iPhone)
- Orchestrierung: Docker Compose
- CI/CD: GitHub Actions (CI, Staging Deploy, Production Deploy)
- Hosting: Render (Backend + Static Site) und Neon (Postgres) -> `render.yaml`

## Live gehen

Komplette Anleitung: `docs/Deployment_Anleitung.md`

Kurzfassung: Neon-Datenbank anlegen -> Render Blueprint aus `render.yaml` starten ->
`DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ALLOW_ORIGINS`, `TRUSTED_HOSTS`, `VITE_API_BASE_URL`
und die `BOOTSTRAP_COACH_*`-Variablen setzen. Migrationen und das Anlegen von Teams/Coach
laufen beim Start automatisch (`backend/start.sh`).

## Schnellstart (lokal mit Docker)

1. `.env.example` nach `.env` kopieren und Werte anpassen.
2. Services starten:
   - `docker compose up --build`
3. API prüfen:
   - `http://localhost:8000/health`
4. Frontend öffnen:
   - `http://localhost:5173`

## Wichtige Befehle

- DB-Migrationen anwenden:
  - `cd backend && alembic upgrade head`
- Teams und Coach-Konto anlegen (idempotent, läuft in Produktion automatisch):
  - `cd backend && python -m app.bootstrap`
- Synthetische Daten seeden (nur lokal/Test - löscht alle Daten!):
  - `cd backend && python -m app.data_generation.seed`
  - Gegen eine gehostete Datenbank oder mit `APP_ENV=production` bricht der
    Befehl ab. Die Demo-Logins stehen danach im Terminal.
- Modell manuell trainieren:
  - `cd backend && python -m app.ml.retrain`
- Voller Backend-Testlauf:
  - `cd backend && pytest`

## ML-Workflow (Bootstrap zu Echtdaten)

Die Pipeline ist für den Übergang von wenig Daten zu echten Teamdaten vorbereitet:

- `bootstrap_mixed`: Training mit real + synthetic, falls noch zu wenig reale Daten vorhanden sind.
- `real_only`: automatische Umschaltung, sobald genug reale Daten und positive Labels vorhanden sind.

Relevante ENV-Variablen:

- `ML_RETRAIN_INTERVAL_SECONDS`
- `ML_MIN_REAL_ROWS`
- `ML_MIN_POSITIVE_ROWS`
- `ML_ALLOW_SYNTHETIC_BOOTSTRAP`
- `ML_RETRAIN_ON_STARTUP`

Trainingsstatus:

- Endpoint: `GET /api/predictions/model-status` (authentifiziert)
- Enthalten: Status, Zeitstempel, letzte Metriken, Fehlerkontext

## Projektstruktur

```text
kip/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   │   ├── wearables/    # Whoop, Oura, Apple Health + Sync
│   │   │   └── crypto.py     # Verschlüsselung der Geräte-Tokens
│   │   ├── models/
│   │   ├── ml/
│   │   └── bootstrap.py      # Teams + Coach-Konto beim Start
│   ├── alembic/
│   ├── start.sh              # Migration + Bootstrap + uvicorn
│   └── tests/
├── frontend/
│   ├── public/               # PWA-Manifest, Icons, Service Worker
│   └── src/
│       ├── components/       # UI-Bausteine, Charts, Views
│       ├── api.ts            # API-Client inkl. Token-Refresh
│       └── i18n.ts
├── docs/
├── render.yaml               # Hosting-Blueprint
├── docker-compose.yml
├── .env.example
└── README.md
```

## Doku

- Gesamtübersicht + Vorgehen: `docs/Projektdokumentation_Gesamt.md`
- Deployment (öffentlich stellen): `docs/Deployment_Anleitung.md`
- Whoop / Oura / Apple Health verbinden: `docs/Wearables_Anleitung.md`
- Live-Update Anleitung (Staging/Production): `docs/Live_Update_Anleitung.md`
- Historische Phasen-Dokumentation: `docs/Phase_1_Dokumentation.md` bis `docs/Phase_9_Dokumentation.md`

## Qualitätssicherung

Backend:

- `cd backend && ruff check .`
- `cd backend && black --check .`
- `cd backend && pytest`

Frontend:

- `cd frontend && npm install`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

## Security-Hinweise

- Passwörter werden mit `bcrypt` gehasht.
- In Produktion ist ein sicherer `JWT_SECRET_KEY` Pflicht (mind. 32 Zeichen).
- Auth-Endpoints sind serverseitig rate-limited.
- Refresh-Tokens liegen in der Datenbank (`refresh_sessions`), werden bei jeder
  Nutzung rotiert und überleben einen Deploy - Logout wirkt sofort.
- `app.data_generation.seed` darf nie in Produktion laufen: der Befehl löscht als
  Erstes jeden Nutzer und jedes Team. Er weigert sich inzwischen selbst, wenn
  `APP_ENV=production` ist oder `DATABASE_URL` auf eine gehostete Datenbank zeigt
  (Neon, Render, AWS, Supabase) - vorbei kommt nur, wer `--yes-delete-every-account`
  ausschreibt.
- Die Seed-Konten heissen `seed_coach_a` / `seed_coach_b` und bekommen bei jedem
  Lauf ein neues Zufallspasswort, das der Befehl ausgibt. Früher standen hier die
  Vornamen der echten Trainerinnen samt festem Passwort im Repository.

## Release-Flow (Kurz)

1. Feature-Branch -> PR -> Merge nach `develop`
2. Automatischer Staging-Deploy
3. Staging testen
4. Merge `develop` -> `main`
5. Automatischer Production-Deploy