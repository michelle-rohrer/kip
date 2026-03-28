# Phase 1 – Projekt-Setup Dokumentation

Dieses Dokument beschreibt, welche Arbeiten in Phase 0 umgesetzt wurden und welchem Zweck sie dienen.

## 1.1 Projektstruktur (Monorepo) anlegen

### Was wurde gemacht?
- Basisstruktur für `backend`, `frontend`, `data`, Root-Konfigurationen und Startdateien wurde angelegt.
- Backend-Unterordner erstellt: `app/models`, `app/schemas`, `app/routers`, `app/services`, `app/ml`, `tests`.
- Frontend-Unterordner erstellt: `src`.
- Datenstruktur vorbereitet: `data/synthetic`.

### Wofür?
- Einheitliche, skalierbare Projektorganisation.
- Klare Trennung von Verantwortlichkeiten (API, UI, Daten/ML).
- Grundlage für spätere Erweiterungen in den folgenden Phasen.

## 1.2 `.gitignore` erstellen

### Was wurde gemacht?
- Datei `.gitignore` erstellt mit Einträgen für:
  - Python-Artefakte (`__pycache__`, virtuelle Umgebungen, Caches)
  - Node-Artefakte (`node_modules`, Build-Ordner)
  - Umgebungsdateien (`.env`, `.env.*`)
  - Editor-spezifische Dateien (`.vscode`, `.idea`)
  - macOS-Dateien (`.DS_Store`)

### Wofür?
- Verhindert, dass temporäre/maschinengenerierte Dateien ins Repo gelangen.
- Verhindert das versehentliche Committen sensibler Umgebungsdaten.

## 1.3 `docker-compose.yml` mit Services

### Was wurde gemacht?
- `docker-compose.yml` mit folgenden Services erstellt:
  - `db` (PostgreSQL)
  - `backend` (FastAPI)
  - `frontend` (Vite/React)
- Ports, Volumes, Health-Check und Service-Abhängigkeiten definiert.

### Wofür?
- Start des gesamten Systems mit einem Befehl.
- Reproduzierbare Entwicklungsumgebung für alle Beteiligten.
- Stabile Reihenfolge beim Start (DB -> Backend -> Frontend).

## 1.4 Backend-Grundgerüst (FastAPI)

### Was wurde gemacht?
- `backend/app/main.py` erstellt mit FastAPI-App und Health-Check Endpoint:
  - `GET /health`
- `backend/requirements.txt` mit Basisabhängigkeiten erstellt:
  - `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic`,
    `python-jose`, `passlib`, `bcrypt`, `scikit-learn`, `pandas`, `numpy`
- `backend/Dockerfile` erstellt.
- Paket-Initialisierungen (`__init__.py`) für Backend-Module ergänzt.

### Wofür?
- Sofort lauffähige API-Basis für weitere Endpoints.
- Health-Check als einfacher Betriebsindikator.
- Vorbereitung für Auth, Datenbank, ML und API-Router in späteren Phasen.

## 1.5 Frontend-Grundgerüst (Vite + React + TS + Tailwind)

### Was wurde gemacht?
- Frontend-Basisdateien erstellt:
  - `frontend/package.json`
  - `frontend/index.html`
  - `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`
  - `frontend/tsconfig.json`, `frontend/vite.config.ts`
  - `frontend/tailwind.config.cjs`, `frontend/postcss.config.cjs`
  - `frontend/src/vite-env.d.ts`
  - `frontend/Dockerfile`

### Wofür?
- Modernes Frontend-Setup für schnelle UI-Entwicklung.
- TypeScript für bessere Typsicherheit.
- Tailwind CSS für konsistentes und schnelles UI-Styling.
- Docker-Startfähigkeit analog zum Backend.

## 1.6 README mit Setup-Anleitung

### Was wurde gemacht?
- `README.md` erweitert mit:
  - Projektbeschreibung und Tech-Stack
  - Verzeichnisstruktur
  - Voraussetzungen
  - Docker-Setup (`docker compose up --build`)
  - Lokale Startanleitungen für Backend und Frontend
  - Service-URLs (Frontend, API, Health, DB-Port)

### Wofür?
- Schnelles Onboarding.
- Klare Start-/Nutzungsanleitung für Entwicklung und Demo.

## Zusätzlich angelegte Datei

- `.env.example` mit beispielhaften Umgebungsvariablen für DB, Backend, Frontend.

### Wofür?
- Einheitliche Konfiguration als Vorlage.
- Verhindert, dass echte Secrets in versionierte Dateien gelangen.

