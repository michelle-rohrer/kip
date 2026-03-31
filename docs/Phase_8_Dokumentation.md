# Umsetzung: Trainerinnen-App (Team-Uebersicht, Ampelsystem, Detailansicht)

Diese Seite beschreibt **was im Code umgesetzt wurde** fuer das Arbeitspaket **Trainerinnen-App** mit Team-Uebersicht, Risiko-Ampel und Spielerinnen-Detailansicht.

**Einordnung:** Im Projektplan ist dies die mobile Phase fuer die Trainerinnen-App. Das zugewiesene Todo war `phase7`, inhaltlich geht es um die Trainerinnen-Funktionen.

---

## Gelieferte Dateien (Frontend)

| Bereich | Pfad |
|---------|------|
| Rollenbasierte App mit Coach-Ansichten | `frontend/src/App.tsx` |

---

## 1) Rollenbasierte App-Navigation

### Was wurde gemacht?

- Bestehende App von reiner Spielerinnen-Ansicht auf **rollenbasiertes UI** erweitert.
- Nach Login (`GET /api/auth/me`) wird die Navigation dynamisch gesetzt:
  - `player`: `Dashboard`, `Wellness-Check`, `Zyklus`, `Privacy-Settings`
  - `coach`: `Team-Uebersicht`, `Spielerinnen-Detail`
- Header-Texte wurden fuer die Coach-Rolle angepasst (`Trainerinnen-App`).

### Wofuer?

- Gleiche Frontend-Basis kann beide Rollen bedienen.
- Coach-Funktionen sind getrennt und klar von Spielerinnen-Funktionen abgegrenzt.

---

## 2) Team-Uebersicht mit Ampelsystem

### Was wurde gemacht?

- Teamdaten werden fuer Coaches ueber `GET /api/predictions/team` geladen.
- Liste wird nach `risk_score` absteigend sortiert.
- Pro Spielerin wird angezeigt:
  - Spielerinnen-ID
  - Risiko-Score in Prozent
  - Risiko-Level (`green`, `yellow`, `red`) mit farbigem Punkt (Ampellogik)
- Pro Zeile gibt es einen `Detail`-Button zum direkten Wechsel in die Detailansicht.

### Wofuer?

- Trainerinnen sehen auf einen Blick, welche Spielerinnen den hoechsten Belastungs-/Risikostatus haben.
- Priorisierung im Teamalltag wird durch Sortierung und Ampelfarben erleichtert.

---

## 3) Spielerinnen-Detailansicht

### Was wurde gemacht?

- Auswahl der Spielerin ueber Dropdown basierend auf dem Team-Prediction-Set.
- Detaildaten werden parallel geladen:
  - `GET /api/wellness/{player_id}`
  - `GET /api/cycle/{player_id}`
  - `GET /api/training/{player_id}`
- Angezeigt werden:
  - **Wellness-Verlauf** (letzte Eintraege)
  - **Trainingsbelastung** (Dauer und Intensitaet)
  - **Zyklusdaten** (Tag und Phase)
  - **Verletzungshistorie** als Platzhalter-Hinweis (Coach-Read-Endpoint fehlt aktuell im Backend)
- Ein manueller `Aktualisieren`-Button ist fuer den Re-Load vorhanden.

### Wofuer?

- Trainerinnen erhalten einen kompakten, operativen Einzelblick je Spielerin.
- Alle fuer die Belastungssteuerung relevanten Daten sind in einer Ansicht gebuendelt.

---

## 4) Datenschutz- und Fehlerverhalten in der Coach-Ansicht

### Was wurde gemacht?

- Responses fuer Wellness-/Zyklusabrufe werden mit `Promise.allSettled` verarbeitet.
- Wenn ein Privacy-geschuetzter Endpoint nicht abrufbar ist (z. B. `403`), wird:
  - die jeweilige Liste geleert
  - ein expliziter Hinweis angezeigt (`... sind nicht freigegeben`)
- Trainingsdaten werden unabhaengig davon geladen, sofern Teamzugriff erlaubt ist.

### Wofuer?

- Die Detailansicht bleibt robust, auch wenn einzelne Datenarten datenschutzbedingt gesperrt sind.
- Kein Komplettabbruch der Seite bei partiellen Zugriffsverboten.

---

## 5) Genutzte Backend-Endpunkte (Coach-Flow)

| Methode | Pfad | Zweck |
|---------|------|-------|
| `GET` | `/api/auth/me` | Rolle und Session aufloesen |
| `GET` | `/api/predictions/team` | Team-Risikoliste fuer Uebersicht |
| `GET` | `/api/wellness/{player_id}` | Wellness-Detail einer Spielerin (mit Privacy-Check) |
| `GET` | `/api/cycle/{player_id}` | Zyklus-Detail einer Spielerin (mit Privacy-Check) |
| `GET` | `/api/training/{player_id}` | Trainingshistorie einer Spielerin (Team-Check) |

---

## 6) Hinweise zum aktuellen Umfang

- Umsetzung erfolgte im bestehenden Web-Frontend unter `frontend/` (kein separates `mobile-coach/`-Projekt im aktuellen Repo-Stand).
- Die Team-Uebersicht zeigt aktuell Spielerinnen-ID und Risiko; Name/Profilattribute koennen spaeter ergaenzt werden, sobald ein passender Team-User-Endpoint vorhanden ist.
- Die Verletzungshistorie ist als Abschnitt vorbereitet; ein eigener Coach-Read-Endpoint fuer Injury fehlt derzeit backendseitig.
