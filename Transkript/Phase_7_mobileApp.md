# Phase 7 mobile app to-dos
_Exported on 31.3.2026 at 10:15:11 MESZ from Cursor (2.6.22)_

---

**User**

Implement the following to-dos from the plan (the plan is attached for your reference). Do NOT edit the plan file itself.

You have been assigned the following 1 to-do(s) with IDs: phase6

1. [phase6] Phase 7: Mobile Spielerinnen-App (Wellness-Check, Zyklus, Dashboard, Privacy-Settings)

These to-dos have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the assigned to-dos.

---

**Cursor**

Ich setze jetzt `phase6` auf **in_progress** und prüfe direkt die bestehende Struktur in `mobile-player`, damit ich Wellness-Check, Zyklus, Dashboard und Privacy-Settings vollständig umsetzen kann.

Ich habe gesehen, dass es statt `mobile-player` einen `frontend`-Ordner gibt. Ich schaue jetzt dort nach der Player-App-Struktur und implementiere die vier Screens inkl. Navigation/API-Anbindung an der bestehenden Architektur.

Ich habe die Backend-Contracts geprüft und baue jetzt die Player-App im `frontend` konkret aus: mit Login, API-Service, Tabs für Wellness/Zyklus/Dashboard/Privacy und echten Requests auf die vorhandenen Endpunkte.

Die UI-Implementierung ist jetzt drin. Ich führe als Nächstes einen Build im `frontend` aus, prüfe TypeScript-Fehler und korrigiere alles, was noch blockiert.

`phase6` ist umgesetzt und als **completed** markiert.

Geändert wurde `frontend/src/App.tsx` mit einer vollständigen Spielerinnen-Oberfläche für:

- **Wellness-Check**: Formular für alle relevanten Felder (`/api/wellness/` POST)
- **Zyklus-Tracking**: Formular inkl. Phase/Symptome/Notizen (`/api/cycle/` POST)
- **Dashboard**:
  - aktueller Risiko-Score mit Ampel (`/api/predictions/{player_id}`)
  - einfache 7-Tage-Trendanzeige als SVG-Linie
  - letzte Wellness- und Zyklus-Einträge
- **Privacy-Settings**:
  - Consent-Liste laden (`/api/privacy/consent` GET)
  - Freigaben pro Coach umschalten und speichern (`/api/privacy/consent` PUT)

Zusätzlich enthalten:

- Login-Flow mit `/api/auth/login` und Session-Laden via `/api/auth/me`
- Token-Speicherung in `localStorage`
- Tab-Navigation zwischen `Dashboard`, `Wellness-Check`, `Zyklus`, `Privacy-Settings`
- Fehler-/Success-Feedback und Ladezustände

Validierung:

- `ReadLints` für `frontend/src/App.tsx`: **keine Linterfehler**
- Build konnte ich hier nicht ausführen, da in der Umgebung weder `node` noch `npm` verfügbar sind (`command not found`)

Wenn du willst, kann ich als nächsten Schritt noch die UI in kleinere Komponenten aufteilen (`src/components/player/*`) und einen kleinen API-Service in `src/lib/api.ts` auslagern.

---

**User**

kannst du die Dokumentation noch dazu schreiben (siehe /docs/)

---

**Cursor**

Ich ergänze jetzt die Doku im `docs/`-Stil passend zu den bisherigen Phasen und schreibe eine neue Datei für die eben umgesetzte Spielerinnen-App. Ich prüfe kurz die vorhandene Struktur, damit Format und Einordnung konsistent sind.

Ich habe die neue Doku-Datei erstellt. Ich prüfe jetzt noch kurz auf Konsistenz im `docs`-Ordner und gebe dir danach direkt die genaue Datei.

Ja, ist ergänzt.

Ich habe die neue Doku unter `docs/Phase_7_Dokumentation.md` geschrieben, passend zum Stil der bestehenden Phasen-Dokumente in `docs/`.

Enthalten sind u. a.:

- Einordnung der Umsetzung (Todo `phase6`, inhaltlich Spielerinnen-App)
- gelieferte Datei (`frontend/src/App.tsx`)
- Abschnitte zu:
  - Login/Session
  - Navigation
  - Wellness-Check
  - Zyklus-Tracking
  - Dashboard
  - Privacy-Settings
- Tabelle mit allen genutzten Backend-Endpunkten
- Hinweise zum aktuellen Umfang (Web-Frontend statt React Native)

Wenn du magst, ergänze ich als Nächstes noch eine kurze Verlinkung in `README.md` auf die neue `Phase_7_Dokumentation.md`.

