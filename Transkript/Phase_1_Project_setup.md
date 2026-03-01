# Phase 0 project setup tasks
_Exported on 28.2.2026 at 16:48:43 MEZ from Cursor (2.5.26)_

---

**User**

Implement the following to-dos from the plan (the plan is attached for your reference). Do NOT edit the plan file itself.

You have been assigned the following 1 to-do(s) with IDs: phase0

1. [phase0] Phase 0: Projekt-Setup (Struktur, Docker, Grundgerüste Backend + Frontend, README)

These to-dos have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the assigned to-dos.

---

**Cursor**

Ich setze jetzt **Phase 0** um: zuerst prüfe ich die aktuelle Projektstruktur, dann lege ich das Monorepo-Grundgerüst inkl. `docker-compose`, Backend-/Frontend-Scaffold, `.gitignore`, `.env.example` und `README` an. Danach prüfe ich kurz auf offensichtliche Lint-/Strukturprobleme.

Ich starte jetzt mit den eigentlichen Dateien für **Phase 0** (aktuell in Bearbeitung): zuerst Root-Konfiguration (`.gitignore`, `.env.example`, `docker-compose`, `README`), danach Backend- und Frontend-Grundgerüste mit lauffähigen Minimal-Setups.

Als Nächstes ergänze ich das Backend-Grundgerüst inkl. FastAPI-Health-Check und Platzhalter-Paketen (`models`, `schemas`, `routers`, `services`, `ml`, `tests`), damit die Struktur sofort lauffähig ist.

Ich bin gerade beim Frontend-Scaffold (Vite + React + TS + Tailwind) und ergänze jetzt die Konfigurations- und `src`-Dateien, damit `npm run dev` direkt funktioniert.

Ich habe die komplette Phase-0-Struktur jetzt angelegt und prüfe als letzten Schritt kurz auf IDE-Lintfehler in den neuen Backend-/Frontend-Dateien.

`phase0` ist umgesetzt (Struktur, Docker, Backend-/Frontend-Grundgerüst, README), **ohne** die Plan-Datei zu ändern.

Umgesetzt wurde:

- Root-Setup mit `.gitignore`, `.env.example` und `docker-compose.yml`
- Backend-Grundgerüst unter `backend/`:
  - `app/main.py` mit FastAPI + `GET /health`
  - Paketstruktur `models/`, `schemas/`, `routers/`, `services/`, `ml/`
  - `requirements.txt` mit den geforderten Basis-Abhängigkeiten
  - `Dockerfile`
- Frontend-Grundgerüst unter `frontend/`:
  - Vite + React + TypeScript + Tailwind Konfiguration (`package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.cjs`, `postcss.config.cjs`)
  - Start-Dateien `index.html`, `src/main.tsx`, `src/App.tsx`, `src/index.css`
  - `Dockerfile`
- Datenordner vorbereitet: `data/synthetic/.gitkeep`
- `README.md` mit Projektbeschreibung und Setup-Anleitung (`docker compose up --build`)

Zusätzlich geprüft:
- IDE-Lints auf `backend/` und `frontend/`: keine Fehler.

Wichtig: Ich habe im Git-Status eine **unerwartete Änderung** gesehen, die ich nicht selbst ausgelöst habe:
- `D Transkript/Phase0_Konzept.md`
- `?? Transkript/Phase_0_Konzept.md`

Wie soll ich damit umgehen (ignorieren, prüfen, oder gezielt bereinigen)?

---

**User**

kannst du mir im /task ein Dokument anlegen, wo du beschreibst wofür was gemacht wurde

---

**Cursor**

Ja — ich lege dir jetzt im Ordner `task` eine übersichtliche Dokumentation an, die für **Phase 0** je Punkt erklärt, **was** erstellt wurde und **wofür** es dient.

Ich habe dir das Dokument hier angelegt:

- `task/Phase0_Dokumentation.md`

Inhalt:
- Für jeden Phase-0-Punkt (`0.1` bis `0.6`) jeweils:
  - **Was wurde gemacht**
  - **Wofür wurde es gemacht**
- Zusätzlich ein Abschnitt zu `.env.example`.

Wenn du möchtest, kann ich dir auch noch eine zweite Version als **kurze Abgabe-Zusammenfassung (max. 1 Seite)** erstellen.

---

**User**

2 Fragen: 
- muss ich Doker auf meinemPC installieren und einrichten?
- die env sachen sind das nur Beispiele oder stimmen die schon?

---

**Cursor**

Ja, genau:

- **Docker:** Wenn du das Projekt wie vorgesehen mit `docker compose up` starten willst, musst du Docker auf deinem PC installiert haben (am einfachsten **Docker Desktop**). Großes Extra-Setup brauchst du dann meist nicht.
- **`.env`-Werte:** Die in `.env.example` sind **Beispiel-/Defaultwerte** für lokale Entwicklung. Sie funktionieren oft direkt lokal, sind aber **nicht** für Produktion gedacht (z. B. `JWT_SECRET=change_me_in_production`).

Praktisch für dich:
1. Docker installieren (falls noch nicht vorhanden).
2. `.env.example` nach `.env` kopieren.
3. Bei Bedarf Ports/Passwörter anpassen.
4. Dann `docker compose up --build` starten.

Wenn du möchtest, kann ich dir als Nächstes eine konkrete, sichere `.env` für deinen lokalen Rechner vorschlagen.

