# Phase 3 – Authentifizierung und Benutzerverwaltung Dokumentation

Dieses Dokument beschreibt, welche Arbeiten für Authentifizierung, Benutzerverwaltung und Zugriffskontrolle umgesetzt wurden und welchem Zweck sie dienen.

## 3.1 Pydantic-Schemas für Auth und User

### Was wurde gemacht?
- Neue Auth-/User-Schemas in `backend/app/schemas/auth.py` ergänzt:
  - `UserCreate`
  - `UserLogin`
  - `UserResponse`
  - `TokenResponse`
  - `RefreshTokenRequest`
  - `MessageResponse`
- Schema-Exports in `backend/app/schemas/__init__.py` zentralisiert.
- Eingaben für E-Mail und Passwort validiert (inkl. `EmailStr`, Längenregeln).

### Wofür?
- Klare und typsichere Request-/Response-Verträge für die Auth-API.
- Einheitliche Validierung direkt am API-Rand.
- Saubere Grundlage für Frontend-Integration und API-Dokumentation.

## 3.2 Auth-Service (Passwort-Hashing, JWT, Token-Management)

### Was wurde gemacht?
- Auth-Service in `backend/app/services/auth.py` erstellt mit:
  - Passwort-Hashing und Verifikation (`hash_password`, `verify_password`)
  - Access- und Refresh-Token-Erstellung
  - Token-Decoding/Validierung (`decode_token`)
  - Login-Authentifizierung (`authenticate_user`)
  - Registrierung (`register_user`)
  - Token-Ausgabe (`issue_tokens`)
  - Refresh-Flow mit Rotation (`refresh_tokens`)
  - Logout-Invalidierung (`logout_refresh_token`)
- Refresh-Token-Statusverwaltung über JTI (aktive und widerrufene Tokens) implementiert.
- Service-Exports in `backend/app/services/__init__.py` ergänzt.

### Wofür?
- Sichere Authentifizierung mit kurzlebigem Access-Token und erneuerbarem Refresh-Token.
- Vermeidung von Refresh-Token-Replay durch Rotation/Revocation.
- Kapselung der Auth-Logik in einem zentralen Service.

## 3.3 API-Routen für Registrierung, Login, Refresh, Logout, Current User

### Was wurde gemacht?
- Neuer Router `backend/app/routers/auth.py` mit Endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/refresh`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
- Router in `backend/app/routers/__init__.py` exportiert und in `backend/app/main.py` registriert.

### Wofür?
- Vollständiger Auth-Flow für Client-Apps (Registrieren -> Login -> Token erneuern -> Logout).
- Standardisierter Zugriff auf den aktuell eingeloggten User.
- Trennung der Auth-Routen von anderen Fach-Routern.

## 3.4 JWT-Absicherung über `get_current_user`

### Was wurde gemacht?
- Auth-Dependency `get_current_user` in `backend/app/dependencies/auth.py` implementiert:
  - Bearer-Token aus Authorization-Header lesen
  - Access-Token validieren
  - User aus DB laden
  - 401 bei fehlender/ungültiger Authentifizierung
- Dependency-Exports in `backend/app/dependencies/__init__.py` ergänzt.

### Wofür?
- Einheitliche Zugriffssicherung für geschützte Endpoints.
- Wiederverwendbare Auth-Dependency für das gesamte Backend.
- Saubere Trennung zwischen Router- und Security-Logik.

## 3.5 Rollenbasierte Zugriffskontrolle (`require_role`)

### Was wurde gemacht?
- Rollen-Guard `require_role(role)` in `backend/app/dependencies/auth.py` implementiert.
- Guard baut auf `get_current_user` auf und prüft Rollen `player`/`coach`.
- Bei fehlender Berechtigung wird HTTP 403 zurückgegeben.

### Wofür?
- Erzwingt klare Berechtigungsgrenzen zwischen Spielenden- und Trainerinnen-Funktionen.
- Reduziert Risiko ungewollter Datenzugriffe.
- Wiederverwendbare Grundlage für zukünftige CRUD- und Privacy-Endpunkte.

## 3.6 Abhängigkeiten für Auth-Tests und Laufzeit ergänzt

### Was wurde gemacht?
- `backend/requirements.txt` erweitert um:
  - `email-validator` (für `EmailStr`)
  - `pytest` (Testausführung)
  - `httpx` (FastAPI/Starlette `TestClient`)

### Wofür?
- Sicherstellung, dass Validierung und Tests in lokalen und CI-Umgebungen laufen.
- Vollständige Test-Infrastruktur für API-Tests.

## 3.7 Tests für Auth-Flow und Rollen

### Was wurde gemacht?
- Testdatei `backend/tests/test_auth.py` erstellt.
- Abgedeckte Szenarien:
  - Registrierung + Abruf von `GET /api/auth/me`
  - Login mit ungültigen Credentials
  - Refresh-Token-Rotation und Reuse-Abwehr
  - Logout-Invalidierung von Refresh-Tokens
  - Ungültiges Access-Token
  - Rollenprüfung (`require_role`) mit erwarteter 403-Antwort
- Test-Setup über In-Memory-SQLite und FastAPI-Dependency-Overrides umgesetzt.

### Wofür?
- Frühe Absicherung gegen Regressionsfehler im Auth-Bereich.
- Verlässliche Validierung von Sicherheits- und Berechtigungslogik.
- Schnelles Feedback bei Änderungen am Auth-Service oder an Routern.

## Technische Validierung

### Was wurde gemacht?
- Testausführung des Backends durchgeführt (`python3 -m pytest -q`).
- Lint-Prüfung auf geänderte Dateien ausgeführt.

### Ergebnis
- Alle Auth-Tests erfolgreich: `5 passed`.
- Keine funktionalen Blocker in den neu ergänzten Auth-Komponenten.
