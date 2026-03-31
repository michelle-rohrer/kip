# Phase 9 – Integration, Docker und Deployment

Diese Seite beschreibt **was im Code umgesetzt wurde** fuer das Arbeitspaket **Integration, Docker-Setup und End-to-End-Test**.

**Einordnung:** Im Projektplan ist dies die Integrations-/Deployment-Phase (Docker, Compose, E2E). Das zugewiesene Todo lautete `phase8`. Die Trainerinnen-App ist separat in der Dokumentation beschrieben (siehe Phase 7/8).

---

## Gelieferte Dateien

| Bereich | Pfad |
|---------|------|
| Backend-Dockerfile | `backend/Dockerfile` |
| Frontend-Dockerfile | `frontend/Dockerfile` |
| Docker-Compose-Setup | `docker-compose.yml` |
| Umgebungsvariablen-Vorlage | `.env.example` |
| Backend E2E-Test | `backend/tests/test_e2e_flow.py` |
| Projekt-README (Ergaenzung) | `README.md` |

---

## 1) Docker-Images fuer Backend und Frontend

### Was wurde gemacht?

- **Backend (`backend/Dockerfile`)**
  - Basis: `python:3.12-slim`.
  - `pip` wird vor der Installation der Requirements aktualisiert.
  - Alle Abhaengigkeiten aus `requirements.txt` werden installiert.
  - Start des FastAPI-Backends mit `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - Kein `--reload` im Container-Command (produktionsnaeheres Verhalten).
- **Frontend (`frontend/Dockerfile`)**
  - Basis: `node:20-alpine`.
  - Installation ueber `npm ci` (reproduzierbare Builds anhand `package-lock.json`).
  - Start des Vite-Devservers auf Port `5173`.

### Wofuer?

- Klare Container-Basis fuer das Backend (FastAPI) und das Web-Frontend.
- Reproduzierbare Installationen, die sich sowohl lokal als auch spaeter im Deployment nutzen lassen.

---

## 2) Docker Compose: Orchestrierung von DB, Backend und Frontend

### Was wurde gemacht?

- `docker-compose.yml` definiert drei Services:
  - `db` (PostgreSQL 16, `postgres:16-alpine`)
  - `backend` (FastAPI-API)
  - `frontend` (Vite-Frontend)
- Gemeinsames Netzwerk `calm_net` auf Basis eines Bridge-Networks eingefuehrt.
- **Datenbank-Service (`db`)**
  - Konfiguration ueber Umgebungsvariablen (User, Passwort, DB-Name, Port).
  - Volume `postgres_data` fuer persistente Daten.
  - Healthcheck mit `pg_isready`, damit abhaengige Services erst nach erfolgreicher Initialisierung starten.
- **Backend-Service**
  - Baut das Image aus `backend/Dockerfile`.
  - Verwendet `.env` fuer DB- und JWT-Parameter.
  - Healthcheck, der `http://127.0.0.1:8000/health/db` im Container aufruft.
  - `depends_on` mit `condition: service_healthy` auf `db`.
- **Frontend-Service**
  - Baut das Image aus `frontend/Dockerfile`.
  - Lauscht auf Port `5173`.
  - Abhaengigkeit zu `backend` mit `condition: service_healthy`.
- Entwicklungs-Bind-Mounts fuer Backend/Frontend wurden im Compose-File entfernt, damit der Compose-Stand eher einem Deployment-Setup entspricht.

### Wofuer?

- Ein konsistenter Stack aus Datenbank, Backend und Frontend, der mit einem Befehl (`docker compose up --build`) lauffaehig ist.
- Healthchecks stellen sicher, dass z. B. das Frontend erst dann startet, wenn API und DB bereit sind.

---

## 3) Umgebungsvariablen-Vorlage (`.env.example`)

### Was wurde gemacht?

- Neue Datei `.env.example` im Projekt-Root angelegt mit folgenden Schluesseln:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`
  - `BACKEND_PORT`, `FRONTEND_PORT`
  - `DATABASE_URL` (Default-URL zur DB im Docker-Setup)
  - `JWT_SECRET_KEY`, `JWT_ALGORITHM`
  - `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- README ergaenzt mit dem Hinweis, `.env.example` nach `.env` zu kopieren.

### Wofuer?

- Einheitliche Konfiguration fuer alle Teammitglieder und Umgebungen.
- Senkung der Einstiegshuerrde: ein Kopieren/Anpassen reicht, um das Projekt via Docker Compose zu starten.

---

## 4) End-to-End-Test des Kernflows (`backend/tests/test_e2e_flow.py`)

### Was wurde gemacht?

- Neuer Pytest `test_e2e_register_login_submit_wellness_and_get_prediction` implementiert.
- Der Test baut eine FastAPI-App mit allen relevanten Routern (`auth`, `wellness`, `training`, `predictions`, `cycle`, `injury`, `privacy`) auf In-Memory-SQLite auf.
- Abgedeckter Flow:
  1. `POST /api/auth/register` – Spielerin registrieren.
  2. `POST /api/auth/login` – Login und Erhalt eines Access-Tokens.
  3. `POST /api/wellness/` – Wellness-Eintrag fuer einen Tag anlegen.
  4. `POST /api/training/` – Trainings-Eintrag fuer denselben Tag anlegen.
  5. `GET /api/predictions/{player_id}` – Risiko-Score und -Level abrufen.
- Im Assertion-Teil wird geprueft:
  - Statuscodes der einzelnen Schritte (201/200).
  - Gueltiger `risk_score` im Intervall `[0.0, 1.0]`.
  - `risk_level` in `{green, yellow, red}`.

### Wofuer?

- Sicherstellung, dass der Kernfluss von Registrierung bis Vorhersage in der Backend-Domäne technisch funktioniert.
- Fruehes Auffangen von Integrationsfehlern, die bei rein isolierten Unit-/API-Tests unentdeckt bleiben wuerden.

---

## 5) Nutzungshinweise und Validierung

### Start des Stacks

1. `.env.example` nach `.env` kopieren und Werte bei Bedarf anpassen.
2. Im Projekt-Root:

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend-API: `http://localhost:8000`
- Healthchecks:
  - `GET http://localhost:8000/health`
  - `GET http://localhost:8000/health/db`

### Ausfuehrung des E2E-Tests (ohne Docker)

```bash
cd backend
pytest tests/test_e2e_flow.py
```

Ergebnis zum Zeitpunkt der Implementierung: **1 passed**.

