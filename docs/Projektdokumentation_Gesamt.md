# Projektdokumentation Gesamt - VolleySync

## Ziel des Projekts

VolleySync unterstuetzt zyklusbewusste Belastungssteuerung im Volleyball.  
Das System kombiniert subjektive Inputs (Wellness, Schmerz, Zyklus) und Trainingsdaten, um Risiko-Signale fuer Trainerinnen sichtbar zu machen.

## Was das System heute kann

- Spielerinnen:
  - Registrierung mit Team und Position
  - Wellness-Check
  - Zyklus-Tracking
  - Trainingseintrag (inkl. sRPE, Session-Typ, Teilnahme)
  - Schmerz/Verletzungseintrag (inkl. medizinische Betreuung, Ausfalltage)
  - Privacy-Einwilligungen gegenueber Coaches
- Trainerinnen:
  - Team-Risikoansicht mit priorisierter Liste
  - Detailansicht je Spielerin
  - Sichtbarkeit zyklus-/wellnessbezogener Daten consent-basiert
- ML:
  - Risiko-Scoring
  - Training mit Bootstrap zu Echtdaten
  - Ground-Truth-naeheres Labeling ueber Verletzungssignale
  - Trainingsstatus-Tracking

## Architektur

### Backend

- Framework: FastAPI
- Schichten:
  - `routers`: API-Endpunkte
  - `schemas`: Pydantic Request/Response
  - `models`: SQLAlchemy-Entitaeten
  - `services`: Businesslogik (Auth, Privacy, etc.)
  - `ml`: Feature Engineering, Labeling, Training, Prediction
- DB-Migrationen mit Alembic

### Frontend

- React + TypeScript + Tailwind
- Single-Page-App mit Rollenlogik:
  - Player-Ansichten
  - Coach-Ansichten
- i18n in Deutsch, Englisch, Italienisch

### Datenhaltung

- PostgreSQL
- Haupttabellen:
  - `users`, `teams`
  - `wellness_entries`, `cycle_entries`, `training_entries`, `injury_entries`
  - `privacy_consents`, `risk_predictions`

## Wie wir vorgegangen sind (Umsetzungsansatz)

1. **Fundament**
   - Projekt-Setup, Docker, DB, Migrationen
   - Authentifizierung und Rollen
2. **Datenerfassung**
   - Core-Domaenen: Wellness, Zyklus, Training, Verletzung
   - Privacy-by-design mit expliziten Freigaben
3. **Coach-Nutzen**
   - Team-Uebersicht und Detailansicht
   - Priorisierung nach Risiko/Schmerz/Ausfall
4. **ML-Basis**
   - Feature Engineering (Belastung, Trends, Interaktionen)
   - Labeling zuerst heuristisch, dann um Ground-Truth-Signale erweitert
5. **Operationalisierung**
   - Retrain-CLI
   - periodischer Retrainer
   - Trainingsstatus/Fehlerkontext
6. **Qualitaet**
   - API-Tests
   - Linting und CI

## ML-Details fuer den produktiven Betrieb

### Labeling

- Zielvariable: `overload_risk_3d`
- Grundlage:
  - ACWR-/Wellness-Heuristiken
  - plus Injury-Signale (`time_loss_days`, `medical_attention`, hohe Schmerzintensitaet)

### Trainings-Gates

Training wird nur ausgefuehrt, wenn Mindestqualitaet erreicht wird:

- Mindestanzahl realer Zeilen (`ML_MIN_REAL_ROWS`)
- Mindestanzahl positiver Labels (`ML_MIN_POSITIVE_ROWS`)
- ausreichende Klassenbalance

### Betriebsmodi

- `bootstrap_mixed`: solange echte Daten knapp sind
- `real_only`: sobald Gates fuer Echtdaten erfuellt sind

## Offene Erweiterungen (Roadmap)

- Match-Exposure (geplant spaeter)
- Readiness-Endpoint fuer Retrain-Freigabe
- erweiterte Modellueberwachung (Data Drift, Kalibrierung)
- besserer Explainability-Layer fuer Coach-Entscheidungen

## Definition of Done fuer neue Features

- API + Schema + Modell konsistent
- Migration vorhanden (falls DB-Aenderung)
- Frontend-Integration inkl. i18n
- Tests gruen
- README/Docs aktualisiert
