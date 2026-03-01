# cycle-aware-load-monitoring – Cycle-Aware Load Monitoring

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

## Voraussetzungen

- Docker + Docker Compose

## Setup

1. Umgebungsvariablen vorbereiten:
   - `.env.example` nach `.env` kopieren und Werte bei Bedarf anpassen.
2. Services starten:
   - `docker compose up --build`

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