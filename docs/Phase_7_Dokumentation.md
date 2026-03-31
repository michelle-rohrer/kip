# Umsetzung: Spielerinnen-App (Wellness, Zyklus, Dashboard, Privacy)

Diese Seite beschreibt **was im Code umgesetzt wurde** fuer das Arbeitspaket **Spielerinnen-App** mit den Bereichen Wellness-Check, Zyklus-Tracking, persoenliches Dashboard und Privacy-Settings.

**Einordnung:** Im Projektplan entspricht dies der Mobile-Phase fuer die Spielerinnen-App. Das Cursor-Todo war als **`phase6`** zugewiesen, inhaltlich ist es die Spielerinnen-App-Implementierung.

---

## Gelieferte Dateien (Frontend)

| Bereich | Pfad |
|---------|------|
| Spielerinnen-App (UI + API-Calls + Session) | `frontend/src/App.tsx` |

---

## 1) Login und Session-Handling

### Was wurde gemacht?

- Login-Formular in `App.tsx` implementiert.
- Authentifizierung gegen `POST /api/auth/login`.
- Session-Aufloesung mit `GET /api/auth/me`.
- Access-/Refresh-Token werden im Browser in `localStorage` gespeichert:
  - `kip_access_token`
  - `kip_refresh_token`
- Logout leert Session und lokales Token-Storage.

### Wofuer?

- Spielerinnen koennen sich direkt gegen das bestehende FastAPI-Backend anmelden.
- Geschuetzte Daten werden nur nach gueltigem Login geladen.

---

## 2) Navigation der Spielerinnen-App

### Was wurde gemacht?

- Tab-Navigation innerhalb der App ergaenzt:
  - `Dashboard`
  - `Wellness-Check`
  - `Zyklus`
  - `Privacy-Settings`
- Einheitliche Statusanzeigen fuer:
  - Ladezustand
  - Erfolgsnachrichten
  - Fehlermeldungen

### Wofuer?

- Klarer, schneller Wechsel zwischen den Kernfunktionen der taeglichen Nutzung.
- Bessere UX durch unmittelbares Feedback bei API-Aktionen.

---

## 3) Wellness-Check

### Was wurde gemacht?

- Formular fuer taegliche Wellness-Eingabe umgesetzt mit:
  - Datum
  - Schlafstunden
  - Schlafqualitaet
  - Muskelkater
  - Mentale Energie
  - Stress
  - Motivation
  - RPE Vortag
  - Freitext
- Persistenz via `POST /api/wellness/`.
- Nach erfolgreichem Speichern wird die Uebersicht neu geladen.

### Wofuer?

- Kernfluss fuer den taeglichen Check-in der Spielerin.
- Direkte Datengrundlage fuer Verlaufsanzeige und Risikomodell.

---

## 4) Zyklus-Tracking

### Was wurde gemacht?

- Formular fuer Zykluseintraege umgesetzt mit:
  - Datum
  - Zyklustag
  - Zykluslaenge
  - Phase (`menstruation`, `follicular`, `ovulation`, `luteal`)
  - PMS-Score
  - Symptome (`cramps`, `migraine`, `fatigue`)
  - Verhuetungstyp
  - Notizen
- Persistenz via `POST /api/cycle/`.
- Nach erfolgreichem Speichern werden die Listen aktualisiert.

### Wofuer?

- Strukturierte Erfassung zyklusbezogener Informationen fuer Monitoring und spaetere Auswertung.

---

## 5) Dashboard (Spielerin)

### Was wurde gemacht?

- Abruf der aktuellen Vorhersage ueber `GET /api/predictions/{player_id}`.
- Anzeige von:
  - Risiko-Level (Gruen/Gelb/Rot)
  - Risiko-Score in Prozent
- Letzte Eintraege fuer Wellness und Zyklus werden angezeigt.
- Einfache 7-Tage-Wellness-Trendlinie als SVG-Chart integriert.

### Wofuer?

- Schneller Ueberblick ueber aktuellen Status und kurzfristige Entwicklung.
- Visuelles Feedback fuer alltaegliche Belastungssteuerung.

---

## 6) Privacy-Settings

### Was wurde gemacht?

- Bestehende Freigaben werden geladen mit `GET /api/privacy/consent`.
- Pro Coach koennen folgende Toggles gesetzt werden:
  - `share_wellness_data`
  - `share_cycle_data`
- Speichern je Coach ueber `PUT /api/privacy/consent`.

### Wofuer?

- Spielerinnen behalten die Kontrolle ueber sensible Datenfreigaben.
- Bestehende Privacy-Logik des Backends wird direkt nutzbar gemacht.

---

## 7) Genutzte Backend-Endpunkte (Spielerinnen-App)

| Methode | Pfad | Zweck |
|---------|------|-------|
| `POST` | `/api/auth/login` | Login und Token-Ausgabe |
| `GET` | `/api/auth/me` | Aktuelle Spielerin laden |
| `GET` | `/api/wellness/` | Eigene Wellness-Historie |
| `POST` | `/api/wellness/` | Wellness-Eintrag speichern |
| `GET` | `/api/cycle/` | Eigene Zyklus-Historie |
| `POST` | `/api/cycle/` | Zyklus-Eintrag speichern |
| `GET` | `/api/predictions/{player_id}` | Aktueller Risiko-Score |
| `GET` | `/api/privacy/consent` | Bestehende Freigaben laden |
| `PUT` | `/api/privacy/consent` | Freigaben aktualisieren |

---

## 8) Hinweise zum aktuellen Umfang

- Die Spielerinnen-App ist in diesem Stand als **Single-Page-Frontend** in `frontend/` umgesetzt (nicht als React-Native-Projekt).
- Fokus war die funktionale Abbildung der MVP-Kernseiten und die Backend-Integration.
- Build-Ausfuehrung war in der Agent-Umgebung nicht moeglich, da `node`/`npm` dort nicht verfuegbar waren; die Datei wurde jedoch per Type/Lint-Check validiert.
