# VolleySync - Cycle-Aware Load Monitoring

Track smart. Play strong.

VolleySync ist ein Full-Stack-Projekt fuer zyklusbewusste Belastungssteuerung im Volleyball.  
Spielerinnen erfassen Wellness-, Zyklus-, Trainings- und Verletzungsdaten. Trainerinnen erhalten eine priorisierte Team-Uebersicht mit Risiko-Signalen.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, scikit-learn
- Frontend: React, Vite, TypeScript, Tailwind
- Datenbank: PostgreSQL
- Orchestrierung: Docker Compose
- CI/CD: GitHub Actions (CI, Staging Deploy, Production Deploy)

## Schnellstart (lokal mit Docker)

1. `.env.example` nach `.env` kopieren und Werte anpassen.
2. Services starten:
   - `docker compose up --build`
3. API pruefen:
   - `http://localhost:8000/health`
4. Frontend oeffnen:
   - `http://localhost:5173`

## Wichtige Befehle

- DB-Migrationen anwenden:
  - `cd backend && alembic upgrade head`
- Synthetische Daten seeden:
  - `cd backend && python -m app.data_generation.seed`
- Modell manuell trainieren:
  - `cd backend && python -m app.ml.retrain`
- Voller Backend-Testlauf:
  - `cd backend && pytest`

## ML-Workflow (Bootstrap zu Echtdaten)

Die Pipeline ist fuer den Uebergang von wenig Daten zu echten Teamdaten vorbereitet:

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
│   │   ├── models/
│   │   └── ml/
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Doku

- Gesamtuebersicht + Vorgehen: `docs/Projektdokumentation_Gesamt.md`
- Live-Update Anleitung (Staging/Production): `docs/Live_Update_Anleitung.md`
- Historische Phasen-Dokumentation: `docs/Phase_1_Dokumentation.md` bis `docs/Phase_9_Dokumentation.md`

## Qualitaetssicherung

Backend:

- `cd backend && ruff check .`
- `cd backend && black --check .`
- `cd backend && pytest`

Frontend:

- `cd frontend && npm install`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

## Security-Hinweise

- Passwoerter werden mit `bcrypt` gehasht.
- In Produktion ist ein sicherer `JWT_SECRET_KEY` Pflicht.
- Auth-Endpoints sind serverseitig rate-limited.

## Release-Flow (Kurz)

1. Feature-Branch -> PR -> Merge nach `develop`
2. Automatischer Staging-Deploy
3. Staging testen
4. Merge `develop` -> `main`
5. Automatischer Production-Deploy