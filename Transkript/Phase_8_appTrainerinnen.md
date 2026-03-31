# Phase 8 mobile trainerinnen-app to-dos
_Exported on 31.3.2026 at 10:22:23 MESZ from Cursor (2.6.22)_

---

**User**

Implement the following to-dos from the plan (the plan is attached for your reference). Do NOT edit the plan file itself.

You have been assigned the following 1 to-do(s) with IDs: phase7

1. [phase7] Phase 8: Mobile Trainerinnen-App (Team-Übersicht, Ampelsystem, Detailansicht)

These to-dos have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the assigned to-dos.

---

**Cursor**

Ich setze jetzt direkt `phase7` auf **in_progress**, prüfe anschließend den aktuellen Stand der Trainerinnen-App und implementiere Team-Übersicht mit Ampelsystem plus Detailansicht inkl. API-Anbindung. Danach teste ich die Änderungen kurz und fixe ggf. Lint-Probleme.

Ich habe gesehen, dass es aktuell keine separate `mobile-coach`-App im Repo gibt; ich implementiere die geforderten Trainerinnen-Ansichten daher in der vorhandenen `frontend`-App und binde sie an die neuen Prediction-Endpunkte im Backend an. Jetzt lese ich die relevanten Dateien.

Ich baue jetzt `frontend/src/App.tsx` auf eine rollenbasierte UI um: Spielerinnen-Ansicht bleibt erhalten, dazu kommen fuer Trainerinnen Team-Liste mit Ampelstatus und eine Detailansicht pro Spielerin inklusive Wellness-/Training-/Zyklusdaten (mit Privacy-Hinweisen bei fehlender Freigabe).

Die UI-Umstellung ist drin. Ich pruefe jetzt mit einem Frontend-Build/Typecheck, ob alles sauber kompiliert, und behebe danach direkt eventuelle Fehler.

Ich habe `phase7` umgesetzt, ohne die Plan-Datei zu veraendern.

Geaendert wurde `frontend/src/App.tsx`:

- Rollenbasierte App-Logik eingefuehrt (`player` und `coach`) statt nur Spielerinnen-Flow.
- **Trainerinnen-App** integriert mit zwei Bereichen:
  - `Team-Uebersicht`: Liste aller Spielerinnen aus `/api/predictions/team`, nach Risiko sortiert, mit **Ampelsystem** (gruen/gelb/rot) und Score.
  - `Spielerinnen-Detail`: Auswahl einer Spielerin und Laden von:
    - Wellness-Verlauf (`/api/wellness/{player_id}`)
    - Trainingsbelastung (`/api/training/{player_id}`)
    - Zyklusdaten (`/api/cycle/{player_id}`)
- Privacy-Verhalten sauber abgefangen:
  - Wenn Wellness/Zyklus nicht freigegeben sind (z. B. 403), wird ein klarer Hinweis angezeigt statt ein Hard-Fail.
- Verletzungshistorie als Abschnitt in der Detailansicht aufgenommen; Hinweis ergänzt, dass aktuell kein Coach-Read-Endpoint dafuer existiert.
- Bestehender Spielerinnen-Bereich bleibt erhalten (Dashboard, Wellness, Zyklus, Privacy).

Validierung:

- `ReadLints` auf `frontend/src/App.tsx`: keine Lint-Fehler.
- Build konnte ich hier nicht lokal ausfuehren, weil in der Umgebung kein `node`/`npm` installiert ist.

To-do-Status:

- `phase7` ist auf **completed** gesetzt.

---

**User**

kannst du Dokumentation machen? (/docs/)

---

**Cursor**

Ja, ich erstelle jetzt die passende Doku in `docs/` fuer die umgesetzte Trainerinnen-App (Team-Uebersicht, Ampelsystem, Detailansicht) im bestehenden Stil der anderen Phasen-Dokumente.

Ich dokumentiere jetzt die eben umgesetzte Trainerinnen-App als eigene Datei unter `docs/`, im gleichen Aufbau wie die vorhandenen Phasen-Dokus.

Ja, erledigt — ich habe die Doku fuer die Trainerinnen-App angelegt:

- Neu: `docs/Phase_8_Dokumentation.md`
- Inhalt:
  - Rollenbasierte Navigation (Player/Coach)
  - Team-Uebersicht mit Ampelsystem und Sortierung nach Risiko
  - Spielerinnen-Detailansicht (Wellness, Training, Zyklus)
  - Datenschutz-/Fehlerverhalten bei nicht freigegebenen Daten
  - Verwendete Backend-Endpunkte
  - Aktuelle Grenzen (z. B. kein Coach-Injury-Read-Endpoint)

Wenn du willst, erstelle ich als naechsten Schritt noch eine kurze `docs/README.md` als Uebersicht mit Links auf alle `Phase_*_Dokumentation.md` Dateien.

