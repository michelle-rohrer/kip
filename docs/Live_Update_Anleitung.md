# Live Update Anleitung - VolleySync

Diese Anleitung beschreibt, wie du Updates sicher auf Staging und danach auf Production bringst.

## 1) Einmalige Voraussetzungen

### GitHub Secrets setzen

Fuer die Deploy-Workflows muessen im Repository folgende Secrets gesetzt sein:

- `STAGING_BACKEND_DEPLOY_HOOK_URL`
- `STAGING_FRONTEND_DEPLOY_HOOK_URL`
- `PRODUCTION_BACKEND_DEPLOY_HOOK_URL`
- `PRODUCTION_FRONTEND_DEPLOY_HOOK_URL`

Die Werte kommen aus deinem Hosting (z. B. Render/Railway/Vercel Deploy Hooks).

### Branch-Strategie

- `develop` = Staging
- `main` = Production

## 2) Update vorbereiten (lokal)

1. Branch erstellen:
   - `git checkout -b feature/<name>`
2. Aenderungen umsetzen
3. Lokal pruefen:
   - Backend: `cd backend && pytest`
   - Frontend: `cd frontend && npm run lint && npm run build`
4. Wenn Datenbank-Schema geaendert wurde:
   - Alembic-Migration muss im PR enthalten sein

## 3) Staging deployen

1. PR nach `develop` erstellen
2. CI muss gruen sein
3. PR mergen
4. GitHub Action `Deploy Staging` startet automatisch
5. Staging manuell testen:
   - Login/Registrierung
   - Player-Flows (Wellness, Zyklus, Training, Verletzung)
   - Coach-Uebersicht
   - API Health (`/health`)

## 4) Production deployen

1. Wenn Staging stabil ist: `develop` nach `main` mergen
2. GitHub Action `Deploy Production` startet automatisch
3. Smoke-Test in Production:
   - Health Endpoint
   - Login
   - Kernansichten laden

## 5) Wichtige Sonderfaelle

### A) Migrationen nach Deploy anwenden

Wenn DB-Felder neu sind, musst du auf dem Zielsystem Migrationen ausfuehren:

- `cd backend && alembic upgrade head`

Ohne diesen Schritt kann das Backend trotz erfolgreichem Deploy Laufzeitfehler werfen.

### B) Modelltraining nach Daten-/Label-Aenderungen

Nach ML-relevanten Updates:

1. Optional Daten seeden (nur Test/Staging):
   - `cd backend && python -m app.data_generation.seed`
2. Training starten:
   - `cd backend && python -m app.ml.retrain`
3. Status kontrollieren:
   - `GET /api/predictions/model-status`

### C) Rollback-Strategie

Bei Problemen in Production:

1. Letzten funktionierenden Commit identifizieren
2. Revert-PR auf `main` erstellen
3. Nach Merge deployt Production automatisch auf stabilen Stand

## 6) Checkliste vor jedem Live-Update

- CI komplett gruen
- Migration enthalten (falls DB-Aenderung)
- `.env.example` aktualisiert (falls neue ENV)
- README/Doku aktualisiert
- Staging manuell getestet
- Production Smoke-Test geplant
