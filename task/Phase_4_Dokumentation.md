# Umsetzung: Core API-Endpoints (CRUD)

Diese Seite beschreibt **was im Code umgesetzt wurde** für die Arbeitspakete **Wellness, Zyklus, Training, Verletzung, Datenschutz inkl. Tests** – im Cursor-Plan als *„Phase 4: Core API-Endpoints CRUD …“* geführt, im Markdown-Plan entspricht das **Phase 3: Core API-Endpoints (CRUD)**.

**Auth:** Alle folgenden Endpoints (außer dem Hinweis) setzen einen gültigen **Bearer Access-Token** voraus (`Authorization: Bearer …`), wie er nach `POST /api/auth/login` ausgegeben wird.

---

## Gelieferte Dateien (Backend)

| Bereich | Pfad |
|---------|------|
| Router Wellness | `backend/app/routers/wellness.py` |
| Router Zyklus | `backend/app/routers/cycle.py` |
| Router Training | `backend/app/routers/training.py` |
| Router Verletzung | `backend/app/routers/injury.py` |
| Router Privacy | `backend/app/routers/privacy.py` |
| Datenschutz-Logik | `backend/app/services/privacy.py` |
| Pydantic-Schemas | `backend/app/schemas/wellness.py`, `cycle.py`, `training.py`, `injury.py`, `privacy.py` |
| Router-Export | `backend/app/routers/__init__.py` |
| App-Einbindung | `backend/app/main.py` (alle fünf Router nach `auth_router`) |
| Tests | `backend/tests/test_core_endpoints.py`, gemeinsames DB-Fixture `backend/tests/conftest.py` |

---

## Endpoints und Rollen

| Modul | Methode | Pfad | Rolle | Kurzbeschreibung |
|-------|---------|------|-------|------------------|
| Wellness | `POST` | `/api/wellness/` | `player` | Neuen Tageseintrag anlegen |
| Wellness | `GET` | `/api/wellness/` | `player` | Eigene Liste, optional `date_from`, `date_to` |
| Wellness | `GET` | `/api/wellness/{player_id}` | `coach` | Liste der Spielerin, wenn Team + Wellness-Freigabe |
| Zyklus | `POST` | `/api/cycle/` | `player` | Zykluseintrag anlegen |
| Zyklus | `GET` | `/api/cycle/` | `player` | Eigene Liste, optional Datumsfilter |
| Zyklus | `GET` | `/api/cycle/{player_id}` | `coach` | Liste der Spielerin, wenn Team + Zyklus-Freigabe |
| Training | `POST` | `/api/training/` | `player` | Trainingseinheit anlegen |
| Training | `GET` | `/api/training/` | `player` | Eigene Liste, optional Datumsfilter |
| Training | `GET` | `/api/training/{player_id}` | `coach` | Liste der Spielerin bei **gleichem Team** (kein separates Privacy-Flag im Modell) |
| Verletzung | `POST` | `/api/injury/` | `player` | Schmerz-/Verletzungseintrag |
| Verletzung | `GET` | `/api/injury/` | `player` | Eigene Liste, optional Datumsfilter |
| Privacy | `GET` | `/api/privacy/consent` | `player` | Alle Consent-Zeilen dieser Spielerin (sortiert nach `coach_id`) |
| Privacy | `PUT` | `/api/privacy/consent` | `player` | Consent für ein `coach_id`-Paar anlegen oder aktualisieren (Upsert) |

**Hinweise zum Umfang „CRUD“:** Es gibt durchgängig **Create** (`POST`) und **Read** (`GET`-Listen). Es fehlen bewusst (Stand Implementierung) **Update/Delete** für Wellness-, Zyklus-, Trainings- und Verletzungseinträge; **Privacy** ist über `PUT` als Upsert aktualisierbar.

---

## Datenschutz-Service (`app/services/privacy.py`)

| Funktion | Zweck |
|----------|--------|
| `get_player_or_404` | Lädt User per ID; **404**, wenn nicht existent oder Rolle nicht `player`. |
| `assert_same_team` | **403**, wenn Coach- oder Spielerin-`team_id` fehlt oder abweicht. |
| `assert_coach_can_view_wellness` | Team-Check + Zeile `PrivacyConsent` für (Spielerin, Coach) mit `share_wellness_data == true`, sonst **403**. |
| `assert_coach_can_view_cycle` | wie oben mit `share_cycle_data`. |
| `assert_coach_can_view_training` | nur Team + existierende Spielerin (kein Consent-Feld für Training). |
| `assert_player_can_set_consent_for_coach` | `coach_id` muss existierende **Coach**-Rolle haben und gleiches Team wie Spielerin; sonst **400**/**403**. |

Freigaben sind **pro Paar** (`player_id`, `coach_id`) in der Tabelle `privacy_consents` gespeichert.

---

## Validierung (Pydantic, Auszug)

| Schema | Wesentliche Grenzen |
|--------|---------------------|
| `WellnessEntryCreate` | `sleep_hours` > 0 und ≤ 24; Skalen 1–10; `rpe_previous_day` optional 1–10 |
| `CycleEntryCreate` | `cycle_day` 1–60; `cycle_length` 20–45; `pms_score` optional 0–10; `phase` Enum der DB |
| `TrainingEntryCreate` | `duration_min` 1–600; `intensity` 1–10; `jump_count` optional ≥ 0; JSON-Felder optional |
| `InjuryEntryCreate` | `body_location` 1–255 Zeichen; `pain_intensity` 1–10 |
| `PrivacyConsentUpsert` | `coach_id`; `share_cycle_data`, `share_wellness_data` (bool) |

---

## HTTP-Status (typisch)

| Code | Wann |
|------|------|
| `201` | Erfolgreiches `POST` |
| `200` | Erfolgreiches `GET` / `PUT` |
| `400` | z. B. ungültige `coach_id` bei Privacy |
| `403` | Falsche Rolle; kein Teamzugriff; fehlende oder abgeschaltete Freigabe (Wellness/Zyklus) |
| `404` | `player_id` bei Coach-Routen: keine Spielerin mit dieser ID |
| `409` | Doppelter Wellness- oder Zyklus-Eintrag **für dasselbe Datum** (Unique Constraint) |
| `422` | Validierungsfehler (Pydantic) |

---

## Tests (`backend/tests/test_core_endpoints.py`)

| Test | Geprüftes Verhalten |
|------|----------------------|
| `test_wellness_happy_path_and_coach_access_with_consent` | Spielerin legt an und listet; Coach ohne Consent **403**; nach `PUT …/privacy/consent` mit `share_wellness_data` Zugriff **200** |
| `test_wellness_duplicate_date_conflict` | Zweites `POST` gleiches Datum → **409** |
| `test_wellness_validation_out_of_range` | z. B. `sleep_hours` ungültig → **422** |
| `test_wellness_coach_list_forbidden_without_player_role` | Coach darf `GET /api/wellness/` nicht → **403** |
| `test_cycle_coach_requires_share_cycle` | Coach ohne `share_cycle_data` **403**; mit Freigabe **200** |
| `test_training_coach_same_team` | Coach im gleichen Team sieht Trainingsliste |
| `test_training_coach_different_team_forbidden` | Coach anderem Team → **403** |
| `test_injury_player_only` | Coach `GET /api/injury/` → **403**; Spielerin listet eigene Einträge |
| `test_privacy_get_and_invalid_coach` | Leere Liste; fiktive `coach_id` → **400** |
| `test_privacy_upsert_updates` | Zweites `PUT` gleicher Coach: gleiche `id`, aktualisierte Flags |

Die Tests bauen eine **in-memory-SQLite**-Session über `conftest.py` und registrieren alle genannten Router plus Auth.

---

## Einordnung im Plan

| Plan-Aufgabe (Phase 3) | Umsetzung |
|------------------------|-----------|
| 3.1–3.5 Router | wie Tabelle oben |
| 3.6 Datenschutz-Service | `services/privacy.py` + Nutzung in Wellness-, Zyklus-, Trainings-Routern |
| 3.7 Tests | `test_core_endpoints.py` (Happy Path, Validierung, Rechte, Privacy, Team) |

Detaillierte **OpenAPI**-Schemas am laufenden Server: `http://localhost:8000/docs`.
