# Live Update Anleitung - VolleySync

Diese Anleitung beschreibt, wie du Updates sicher auf Staging und danach auf Production bringst.

> Erstmaliges Live-Stellen (Hosting, Datenbank, Domains): `docs/Deployment_Anleitung.md`

## 1) Einmalige Voraussetzungen

### GitHub Secrets setzen

Beim Setup ueber `render.yaml` deployt Render nach jedem Push auf `main` automatisch
(`autoDeploy: true`) - dann sind keine Secrets noetig.

Nur falls du autoDeploy im Render-Dashboard abschaltest, hinterlege die Deploy-Hooks als
GitHub Secrets; die Workflows nutzen sie dann automatisch:

- `STAGING_BACKEND_DEPLOY_HOOK_URL`
- `STAGING_FRONTEND_DEPLOY_HOOK_URL`
- `PRODUCTION_BACKEND_DEPLOY_HOOK_URL`
- `PRODUCTION_FRONTEND_DEPLOY_HOOK_URL`

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

### A) Migrationen

Migrationen laufen bei jedem Start automatisch (`backend/start.sh` fuehrt `alembic upgrade head`
und danach `python -m app.bootstrap` aus). Von Hand noetig ist das nur, wenn du ausserhalb des
Containers arbeitest:

- `cd backend && alembic upgrade head`

Wichtig bleibt: Eine Alembic-Migration muss im PR enthalten sein, sobald sich das Schema aendert.

### B) Modelltraining nach Daten-/Label-Aenderungen

Nach ML-relevanten Updates:

1. Optional Daten seeden (**nur** Test/Staging - loescht in Produktion alle echten Daten!):
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
