# VolleySync – Cycle-Aware Load Monitoring

Track smart. Play strong.

Monorepo für ein Full-Stack-Projekt zur zyklusbewussten Belastungssteuerung im Volleyball:
- **Backend:** FastAPI (Python)
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Datenbank:** PostgreSQL
- **Orchestrierung:** Docker Compose

## Projektstruktur

```text
cycle-aware-load-monitoring/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── ml/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── synthetic/
├── docker-compose.yml
├── .gitignore
├── .env.example
└── README.md
```

## Projektdokumentation

- **Phase 1 – Projekt-Setup:** [docs/Phase_1_Dokumentation.md](docs/Phase_1_Dokumentation.md)
- **Phase 2 – Datenbankmodell und Migrationen:** [docs/Phase_2_Dokumentation.md](docs/Phase_2_Dokumentation.md)
- **Phase 3 – Authentifizierung:** [docs/Phase_3_Dokumentation.md](docs/Phase_3_Dokumentation.md)
- **Umsetzung Core API (Wellness, Zyklus, Training, Verletzung, Privacy, Tests):** [docs/Phase_4_Dokumentation.md](docs/Phase_4_Dokumentation.md)
- **Synthetische Datengenerierung und Seed:** [docs/Phase_5_Dokumentation.md](docs/Phase_5_Dokumentation.md)
- **Qualitaetssicherung und Feinschliff:** [docs/Phase_9_Dokumentation.md](docs/Phase_9_Dokumentation.md)

## Voraussetzungen

- Docker + Docker Compose

## Setup

1. Umgebungsvariablen vorbereiten:
   - `.env.example` nach `.env` kopieren und Werte bei Bedarf anpassen.
2. Services starten:
   - `docker compose up --build`

## End-to-End-Test (Backend)

Der E2E-Test deckt den Kern-Flow ab: Registrieren -> Login -> Wellness eintragen -> Risiko-Vorhersage abrufen.

```bash
cd backend
pytest tests/test_e2e_flow.py
```

## ML-Training-Workflow (Bootstrap -> Echtdaten)

Das Projekt startet robust ohne echte Historie und wechselt spaeter automatisch auf echte Daten:

1. **Optionaler Bootstrap mit synthetischen Daten**
   ```bash
   cd backend
   python -m app.data_generation.seed
   ```
2. **Modell trainieren (mit Echtdaten-Gate)**
   ```bash
   cd backend
   python -m app.ml.retrain
   ```
   - Standard: Wenn noch nicht genug echte Daten vorhanden sind, wird gemischt (real + synthetic) trainiert.
   - Sobald genug echte Label-Zeilen vorhanden sind, trainiert die Pipeline nur mit realen Daten.
3. **Strikter Modus (kein synthetischer Fallback)**
   ```bash
   cd backend
   python -m app.ml.retrain --no-synthetic-bootstrap --min-real-rows 500
   ```
   Wenn das echte Datenvolumen noch nicht reicht, bricht der Lauf bewusst mit Fehler ab.

### Automatischer woechentlicher Retrain-Job (Docker)

Beim `docker compose up` startet zusaetzlich der Service `retrainer`, der periodisch trainiert.

- Default-Intervall: 7 Tage (`ML_RETRAIN_INTERVAL_SECONDS=604800`)
- Schaltet automatisch auf `real_only`, sobald genug echte Daten vorhanden sind
- Nutzt bis dahin optional Bootstrap-Mix (steuerbar per ENV)

Relevante ENV-Variablen:

- `ML_RETRAIN_INTERVAL_SECONDS` (z. B. `604800`)
- `ML_MIN_REAL_ROWS` (z. B. `500`)
- `ML_ALLOW_SYNTHETIC_BOOTSTRAP` (`true`/`false`)
- `ML_RETRAIN_ON_STARTUP` (`true`/`false`)

Trainingsstatus per API abrufen (authentifiziert):

```bash
GET /api/predictions/model-status
```

Response enthaelt u. a.:
- `status` (`ok` oder `failed`)
- `updated_at`, `last_success_at`, `last_failure_at`
- `metrics` (letzter erfolgreicher Trainingslauf)
- `error` + `context` (bei Fehlern)

Nur den Retrainer starten/neu starten:

```bash
docker compose up -d retrainer
docker compose restart retrainer
```

## Qualitaetssicherung

## Security-Hinweise

- Passwoerter werden mit `bcrypt` gehasht gespeichert (kein Klartext).
- In Produktion (`APP_ENV=production`) startet das Backend nur mit sicherem `JWT_SECRET_KEY` (kein Default, mind. 32 Zeichen).
- Auth-Endpunkte `POST /api/auth/login` und `POST /api/auth/register` haben serverseitiges Rate-Limit.
  - Steuerbar ueber `AUTH_RATE_LIMIT_WINDOW_SECONDS` und `AUTH_RATE_LIMIT_MAX_ATTEMPTS`.

### Backend

```bash
cd backend
ruff check .
black --check .
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run lint
npm run format
npm run build
```

## CI/CD (GitHub Actions)

Dieses Repo hat drei Workflows:

- `CI` (`.github/workflows/ci.yml`)
  - Trigger: Pull Requests sowie Push auf `develop` und `main`
  - Backend: `ruff check .`, `black --check .`, `pytest`
  - Frontend: `npm ci`, `npm run lint`, `npm run format`, `npm run build`
- `Deploy Staging` (`.github/workflows/deploy-staging.yml`)
  - Trigger: Push auf `develop`
  - Sendet Deploy-Hooks fuer Frontend und Backend (Staging)
- `Deploy Production` (`.github/workflows/deploy-production.yml`)
  - Trigger: Push auf `main`
  - Sendet Deploy-Hooks fuer Frontend und Backend (Production)

### Benoetigte GitHub Secrets

Fuer die Deploy-Workflows muessen diese Repository-Secrets gesetzt sein:

- `STAGING_BACKEND_DEPLOY_HOOK_URL`
- `STAGING_FRONTEND_DEPLOY_HOOK_URL`
- `PRODUCTION_BACKEND_DEPLOY_HOOK_URL`
- `PRODUCTION_FRONTEND_DEPLOY_HOOK_URL`

Die Hook-URLs bekommst du z. B. in Render, Railway oder Vercel als "Deploy Hook"/"Build Hook".

### Empfohlener Release-Prozess

1. Feature-Branch erstellen und Aenderungen per PR nach `develop` mergen.
2. Nach Merge auf `develop` laeuft automatisch Staging-Deploy.
3. Staging testen (inkl. Login, API-Health, Kern-Flow).
4. `develop` nach `main` mergen.
5. Nach Merge auf `main` laeuft automatisch Production-Deploy.

## Verfügbare Services

- **Frontend:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Health-Check:** `http://localhost:8000/health`
- **PostgreSQL:** Port `5432`

## Lokale Entwicklung ohne Docker (optional)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```