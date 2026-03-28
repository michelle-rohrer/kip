# Phase 4 core API endpoints implementation
_Exported on 28.3.2026 at 12:38:54 MEZ from Cursor (2.6.21)_

---

**User**

Implement the following to-dos from the plan (the plan is attached for your reference). Do NOT edit the plan file itself.

You have been assigned the following 1 to-do(s) with IDs: phase3

1. [phase3] Phase 4: Core API-Endpoints CRUD (Wellness, Zyklus, Training, Injury, Privacy + Tests)

These to-dos have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the assigned to-dos.

---

**Cursor**


Wir implementieren die Core-API-Endpoints (Wellness, Zyklus, Training, Verletzung, Datenschutz) inkl. Tests. Zuerst prüfen wir den aktuellen Stand des Backends.




Implementierung: Schemas, Privacy-Service, Router und Tests erstellen.




Hier die **kurze Zusammenfassung** der umgesetzten Phase „Core API (CRUD)“ (entspricht **Phase 3** im Plan; dein Todo nannte fälschlich „Phase 4“):

## Implementiert

**Datenschutz-Service** (`app/services/privacy.py`): zentrale Prüfungen für Spielerin-Existenz/Rolle, gleiches Team, sowie `share_wellness_data` / `share_cycle_data` aus `PrivacyConsent`. Training ist für Trainerinnen nur bei **gleichem `team_id`** freigegeben (im Modell gibt es kein separates Trainings-Freigabe-Flag).

**Router & Endpoints**

| Bereich | Endpoints |
|--------|-----------|
| **Wellness** | `POST/GET /api/wellness/` (nur `player`), `GET /api/wellness/{player_id}` (`coach` + Wellness-Freigabe) |
| **Zyklus** | `POST/GET /api/cycle/` (nur `player`), `GET /api/cycle/{player_id}` (`coach` + Zyklus-Freigabe) |
| **Training** | `POST/GET /api/training/` (nur `player`), `GET /api/training/{player_id}` (`coach`, gleiches Team) |
| **Verletzung** | `POST/GET /api/injury/` (nur `player`) |
| **Privacy** | `GET /api/privacy/consent`, `PUT /api/privacy/consent` (Upsert pro `coach_id`, nur `player`; Coach muss existieren, Rolle `coach`, gleiches Team) |

**Schemas** unter `app/schemas/` (wellness, cycle, training, injury, privacy) mit sinnvollen Grenzen (z. B. Skalen 1–10).

**App** (`main.py`): alle neuen Router eingebunden.

**Tests** (`tests/conftest.py` mit gemeinsamem `db_session`, `tests/test_core_endpoints.py`): Happy Paths, Duplikat-Datum → 409 (Wellness/Zyklus), Validierung 422, Rollen 403, Datenschutz/Freigaben, Training fremdes Team 403, Privacy-Invalid/Update. `test_auth.py` nutzt jetzt das gemeinsame `db_session`-Fixture.

**Hinweis:** `PUT /api/privacy/consent` setzt Zeitstempel mit `datetime.now(timezone.utc)` (weniger Deprecation-Warnungen als `utcnow()`).

Alle **15** Tests laufen grün (`python3 -m pytest tests/`). Die Plan-Datei wurde **nicht** geändert.

---

**User**

kannst du de dokumentation schreiben

---

**Cursor**


README und vorhandene API-Struktur prüfen, anschließend passende Dokumentation ergänzen.




Wir erstellen `docs/API.md` mit der REST-API-Dokumentation und verlinken sie in der README.




Hier die Änderungen in Kurzform:

## Neu: [docs/API.md](docs/API.md)

Deutschsprachige **REST-API-Dokumentation** mit:

- Basis-URL, Verweise auf **OpenAPI** (`/openapi.json`), **Swagger UI** (`/docs`) und **ReDoc** (`/redoc`)
- **Authentifizierung** (Bearer, Access-/Refresh-Token) und Rollen `player` / `coach`
- Alle Bereiche: **System**, **Auth**, **Wellness**, **Zyklus**, **Training**, **Verletzung**, **Datenschutz**
- Tabellen zu Methoden, Pfaden, Rollen, Query-Parametern und Request-Bodies
- **Datenschutz- und Team-Regeln** (wann Trainerinnen Wellness/Zyklus/Training sehen dürfen)
- Übersicht der **HTTP-Statuscodes** und Hinweis auf **pytest**

## README

Neuer Abschnitt **„Dokumentation“** mit Link auf `docs/API.md` sowie auf `/docs` und `/redoc`.

Wenn du willst, kann ich als Nächstes z. B. nur Mobile-Client-Flows oder ein kurzes **Sequenzdiagramm** (Registrierung → Consent → Abruf) ergänzen.

---

**User**

ich meinte wie die dokumentationen /task zu den phasen

---

**Cursor**


Plan lesen und eine deutschsprachige Phasen-/Task-Dokumentation erstellen (keine API-Doku).




Wir erstellen eine Phasen-/Task-Dokumentation mit Zuordnung der Cursor-Todo-IDs (`phase0`–`phase9`) zu den Plan-Phasen und verlinken sie in der README.




README-Link anpassen: `docs/API.md` fehlt im Repo.




Hier die Anpassung in Kurzform:

## Neu: [docs/PHASEN-UND-TASKS.md](docs/PHASEN-UND-TASKS.md)

Das ist die **Dokumentation zu den Phasen und Tasks** (nicht die HTTP-API). Enthalten sind:

1. **Zuordnung Cursor-Todo ↔ Plan** – Tabelle für `phase0` … `phase9` mit dem Hinweis, dass im Plan-Todo-Text oft „Phase 1“, „Phase 2“ … steht, während die Markdown-Überschriften **Phase 0–9** nutzen (damit nichts durcheinandergerät).

2. **Alle Arbeitspakete** je Phase als kompakte Task-Tabellen (**0.1**–**0.6**, **1.1**–**1.4**, … **9.1**–**9.5**) – inhaltlich wie im Plan, für schnelles Abhaken und für Leser ohne Cursor.

3. **Quelle & Pflege** – Verweis auf `.cursor/plans/volleyball_load_monitoring_140b4d8b.plan.md` und Hinweis, Status der Todos in der **YAML-Frontmatter** des Plans (`todos:`) zu pflegen.

## README

Abschnitt **„Projektdokumentation“** mit Link auf `docs/PHASEN-UND-TASKS.md` und kurzem Hinweis auf Swagger unter `/docs`. (Es gibt aktuell keine `docs/API.md` im Repo; deshalb kein toter Link.)

Wenn du willst, kann ich die Task-Tabellen um eine Spalte **„Erledigt (Datum)“** oder Checkboxen `- [ ]` ergänzen, die ihr im Git manuell abhakt.

---

**User**

kannst du mir die phase 4 Dokumentation erfassen. Bitte im gleichen Stil wie die zu den anderen Phasen /task (Phase 1-3)

---

**Cursor**


Die Datei `docs/PHASEN-UND-TASKS.md` fehlt im Repo. Wir erstellen sie neu und dokumentieren Phase 4 im gleichen Tabellenstil wie die Phasen 1–3.




Wir legen `docs/PHASEN-UND-TASKS.md` neu an: Phasen 0–3 und 5–9 im bekannten Tabellenstil; Phase 4 gleich detailliert ausformuliert.




Hier die Kurzfassung:

## `docs/PHASEN-UND-TASKS.md`

Die Datei ist wieder angelegt. **Phase 4** steht im **gleichen Format** wie die Phasen 1–3: Überschrift **„Phase 4: Synthetische Datengenerierung“** und Tabelle **| Task | Inhalt |** mit **4.1** bis **4.6**.

Inhaltlich ist Phase 4 gegenüber dem Plan ausgebaut, aber im selben Stil wie z. B. **1.1** (viele Anforderungen in einer Zelle) und **3.x** (konkrete Pfade/Konzepte):

| Task | Was drin steht |
|------|----------------|
| **4.1** | `generate.py` / Paket, 15–20 Profile, 90–180 Tage, Anbindung ans DB-Schema und Seed |
| **4.2** | Zykluslänge 26–32, Phasenlängen, PMS/Luteal-Korrelation |
| **4.3** | Wellness-Korrelationen (Schlaf → Energie, Phase → Kater/Müdigkeit, Vortag-Training → RPE), gültige Wertebereiche |
| **4.4** | Wochenrhythmus Mo–Sa/So, Periodisierung, Konsistenz mit anderen Zeitreihen |
| **4.5** | Injuries mit erhöhter Rate bei hoher Last / Phasen, Hinweis auf ACWR-Proxy |
| **4.6** | `python -m app.data_generation.seed`, DB-URL, Idempotenz-Hinweis |

Zusätzlich gibt es unter Phase 4 eine kurze **Abgrenzung** zu Phase 5 (ACWR exakt vs. Proxy für synthetische Daten).

Phasen **0–3** sind wieder als **Tabellen** gefasst (wie zuvor für 1–3). **5–9** nur kompakt, mit Verweis auf den Plan.

## README

Link unter **„Projektdokumentation“** auf `docs/PHASEN-UND-TASKS.md`.

---

**User**

nein ich möchte die Dokumentaation was hier gemacht wurde: Phase 4: Core API-Endpoints CRUD (Wellness, Zyklus, Training, Injury, Privacy + Tests)

---

**Cursor**


Implementierungsdokumentation für die umgesetzten Core-API-Endpoints erstellen. Code prüfen, damit die Doku den Ist-Stand widerspiegelt.




Erstelle die Umsetzungsdokumentation und entferne den ungenutzten Import in `cycle.py`.




Hier die **Umsetzungsdokumentation** für genau diese Arbeitsphase („Core API-Endpoints CRUD …“ im Cursor-Todo, im Plan-Text **Phase 3**):

## Neu: [docs/UMSETZUNG-CORE-API-CRUD.md](docs/UMSETZUNG-CORE-API-CRUD.md)

Inhalt im **Tabellenstil** wie bei euren Phasen-/Task-Docs:

1. **Einordnung** – Cursor-„Phase 4“ vs. Plan-**Phase 3**
2. **Gelieferte Dateien** – Router, `services/privacy.py`, Schemas, `main.py`, Tests
3. **Endpoints & Rollen** – alle Methoden/Pfade mit `player`/`coach`
4. **Datenschutz-Service** – Funktionen und wann 403/404/400
5. **Pydantic-Grenzen** – Kurzüberblick pro Schema
6. **HTTP-Status** – typische Codes (inkl. 409 Wellness/Zyklus pro Datum)
7. **Tests** – Tabelle: welcher Test was prüft
8. **Abgrenzung „CRUD“** – klar benannt: **kein** Update/Delete für Wellness/Zyklus/Training/Injury; Privacy per **PUT** als Upsert

## README

Unter **„Projektdokumentation“** gibt es einen Link auf diese Datei.

## Klein am Code

In `cycle.py` war `get_current_user` unbenutzt – Import entfernt (Tests weiter grün).

