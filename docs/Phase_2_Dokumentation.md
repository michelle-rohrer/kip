# Phase 2 – Datenbankmodell und Migrationen Dokumentation

Dieses Dokument beschreibt, welche Arbeiten für die Datenbank-Grundlage umgesetzt wurden und welchem Zweck sie dienen.

## 2.1 SQLAlchemy-Modelle definieren

### Was wurde gemacht?
- Zentrale SQLAlchemy-Basis erstellt in `backend/app/models/base.py` (`DeclarativeBase`).
- Entitäten in `backend/app/models/entities.py` ergänzt:
  - `User`
  - `Team`
  - `CycleEntry`
  - `WellnessEntry`
  - `TrainingEntry`
  - `InjuryEntry`
  - `PrivacyConsent`
  - `RiskPrediction`
- Zugehörige Enum-Typen eingeführt:
  - `UserRole` (`player`, `coach`)
  - `CyclePhase` (`menstruation`, `follicular`, `ovulation`, `luteal`)
  - `RiskLevel` (`green`, `yellow`, `red`)
- Beziehungen (Relationships), Foreign Keys, Unique Constraints und Indizes ergänzt (z. B. `player_id + date` bei Tages-Entries, `player_id + coach_id` bei Consents).
- Modell-Exports in `backend/app/models/__init__.py` zentralisiert.

### Wofür?
- Klare, typisierte Datenstruktur als Grundlage für API, Business-Logik und ML.
- Konsistente Abbildung fachlicher Regeln direkt im Datenmodell.
- Gute Erweiterbarkeit für spätere CRUD-, Privacy- und Prediction-Features.

## 2.2 Alembic einrichten und initiale Migration erstellen

### Was wurde gemacht?
- Alembic-Basisstruktur angelegt:
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/script.py.mako`
  - `backend/alembic/versions/`
- `env.py` an `Base.metadata` angebunden, damit das Modell-Schema als Migrationsgrundlage dient.
- Initialmigration erstellt:
  - `backend/alembic/versions/20260301_000001_initial_schema.py`
- Migration enthält:
  - Erstellung aller Tabellen
  - Erstellung aller benötigten Enum-Typen
  - Indizes und Constraints
  - Vollständigen `downgrade()` zum sauberen Zurückrollen

### Wofür?
- Versionierbare, reproduzierbare Datenbankänderungen.
- Gleiches Schema in allen Umgebungen (lokal, Docker, später Deployment).
- Grundlage für sichere, nachvollziehbare Schema-Weiterentwicklung.

## 2.3 Datenbank-Session und Dependency Injection in FastAPI

### Was wurde gemacht?
- Datenbankzugriff in `backend/app/db.py` gekapselt:
  - `engine` mit `DATABASE_URL` (inkl. Default)
  - `SessionLocal`
  - `get_db()` als FastAPI-Dependency
- `backend/app/main.py` erweitert:
  - bestehender Health-Check `GET /health`
  - zusätzlicher DB-Health-Check `GET /health/db` mit Session-Dependency

### Wofür?
- Einheitlicher, sauberer DB-Zugriff über Dependency Injection.
- Korrektes Öffnen/Schließen von Sessions pro Request.
- Frühe Betriebsprüfung, ob API und Datenbank korrekt verbunden sind.

## Technische Validierung

### Was wurde gemacht?
- Syntaxprüfung der neuen Backend- und Alembic-Dateien durchgeführt (`python -m compileall`).
- Lint-Prüfung auf den neu bearbeiteten Pfaden ausgeführt.

### Ergebnis
- Keine Syntaxfehler.
- Keine Lint-Fehler auf den betroffenen Dateien.

