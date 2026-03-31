# Umsetzung: Feature Engineering und ML-Pipeline

Diese Seite beschreibt **was im Code umgesetzt wurde** fuer die Arbeitspakete **Feature Engineering (inkl. ACWR), Labeling, Random-Forest-Training und Prediction-API**.

**Einordnung:** Im Projektplan ist das inhaltlich die ML-Phase (*Feature Engineering und ML-Pipeline*). Im Cursor-Todo war dies als **`phase5`** zugeordnet.

---

## Gelieferte Dateien (Backend)

| Bereich | Pfad |
|---------|------|
| Feature Engineering | `backend/app/ml/features.py` |
| Labeling | `backend/app/ml/labeling.py` |
| Training (Random Forest + Metriken + Persistenz) | `backend/app/ml/train.py` |
| Prediction-Service (Inference + Upsert) | `backend/app/ml/predict.py` |
| Prediction-Router | `backend/app/routers/predictions.py` |
| Prediction-Schema | `backend/app/schemas/predictions.py` |
| Router-Export | `backend/app/routers/__init__.py` |
| App-Einbindung | `backend/app/main.py` |
| Schema-Export | `backend/app/schemas/__init__.py` |
| API-Tests (Erweiterung) | `backend/tests/test_core_endpoints.py` |

---

## 1) Feature Engineering (`app/ml/features.py`)

### Was wurde gemacht?

- Zusammenfuehrung von `TrainingEntry`, `WellnessEntry` und `CycleEntry` auf Tagesebene pro Spielerin.
- Berechnung von **Tageslast**: `daily_load = duration_min * intensity / 90`.
- Berechnung von **ACWR** auf Mittelwert-Basis:
  - **Acute**: gleitender 7-Tage-Mittelwert der Tageslast
  - **Chronic**: gleitender 28-Tage-Mittelwert der Tageslast
  - **ACWR**: `acute / chronic` (mit sicherem Fallback bei sehr kleinen Nennern)
- Rolling Features je Signal (`sleep_quality`, `muscle_soreness`, `mental_energy`, `stress_level`, `motivation`, `daily_load`):
  - `*_ma3`, `*_ma7`
  - `*_delta` (gegenueber Vortag)
- Interaktionsfeatures:
  - `phase_intensity_interaction` (Lutealphase x Intensitaet)
  - `sleep_energy_interaction` (Schlafstunden x mentale Energie)
- Aggregierter Symptomscore:
  - `symptom_score = pms_score + 2*cramps + 2*migraine + fatigue_flag`
- Zyklusphase als kategorische Variable per One-Hot-Encoding (`phase_*`).

### Wofuer?

- Einheitliche, modelltaugliche Tagesmatrix fuer Training und Vorhersage.
- Stabiler Umgang mit lueckenhaften Historien durch definierte Defaultwerte.

---

## 2) Labeling (`app/ml/labeling.py`)

### Was wurde gemacht?

- Zielvariable `overload_risk_3d` als binaeres Label eingefuehrt.
- Ein Tag gilt intern als belastungskritisch bei mindestens einem Signal:
  - `acwr >= 1.35`
  - `muscle_soreness >= 8`
  - `stress_level >= 8` bei gleichzeitig `mental_energy <= 4`
- Das finale Label markiert, ob innerhalb der **naechsten 3 Tage** ein solcher Zustand auftritt.

### Wofuer?

- Konsistente Supervision fuer Klassifikationsmodelle mit kurzem Vorhersagehorizont.

---

## 3) Training-Pipeline (`app/ml/train.py`)

### Was wurde gemacht?

- Aufbau eines Gesamtdatensatzes ueber alle Spielerinnen (`UserRole.PLAYER`).
- Zeitliche Sortierung und zeitbasierte Aufteilung:
  - fruehe 80% Training
  - spaete 20% Test
- Modell: **`RandomForestClassifier`** mit
  - `n_estimators=300`
  - `min_samples_leaf=2`
  - `class_weight="balanced_subsample"`
- Metriken:
  - `PR-AUC`
  - `Recall`
  - `ROC-AUC`
  - `F1`
  - `Brier Score`
- Persistenz des Modells als Bundle (`ModelBundle`) nach:
  - `backend/app/ml/models/risk_model.joblib`
- Versionierung ueber UTC-Zeitstempel (z. B. `rf-20260331123059`).

### Wofuer?

- Reproduzierbarer Trainingslauf mit auswertbaren Kennzahlen und versionierter Modellablage.

---

## 4) Prediction-Service (`app/ml/predict.py`)

### Was wurde gemacht?

- Laden des trainierten Modells aus `risk_model.joblib`, falls vorhanden.
- Inferenz auf Basis des **aktuellsten** Feature-Snapshots einer Spielerin.
- Ampellogik:
  - Gruen: `< 0.35`
  - Gelb: `0.35 - 0.64`
  - Rot: `>= 0.65`
- Fallback, wenn kein Modell vorhanden oder zu wenig Daten:
  - heuristische Scoreschaetzung (`heuristic-v1`) aus zentralen Signalen (`acwr`, `muscle_soreness`, `stress_level`, `mental_energy`)
- Ergebnis wird als `RiskPrediction` pro Tag per Upsert gespeichert/aktualisiert.

### Wofuer?

- API kann immer eine Vorhersage liefern (auch vor erstem Training), bleibt aber modellgetrieben sobald ein Modell vorliegt.

---

## 5) Prediction-API

| Methode | Pfad | Rolle | Verhalten |
|---------|------|-------|-----------|
| `GET` | `/api/predictions/{player_id}` | `player`, `coach` | Spielerin nur fuer sich selbst; Coach fuer Spielerinnen im selben Team (wie Training-Privacy-Logik). |
| `GET` | `/api/predictions/team` | `coach` | Liefert aktuelle Vorhersagen fuer alle Spielerinnen des Coach-Teams. |

### Sicherheits- und Zugriffslogik

- Spielerin: Zugriff nur auf die eigene `player_id`.
- Coach: Team-Zugehoerigkeit wird geprueft (bestehende Service-Logik wird wiederverwendet).

---

## 6) Tests

Ergaenzte API-Tests in `backend/tests/test_core_endpoints.py`:

| Test | Geprueftes Verhalten |
|------|----------------------|
| `test_predictions_player_can_read_own_prediction` | Spielerin kann eigene Vorhersage abrufen; Score in `[0,1]`; gueltiges Risikolevel. |
| `test_predictions_player_cannot_read_other_player` | Spielerin darf keine fremde `player_id` lesen (`403`). |
| `test_predictions_team_for_coach` | Coach kann Team-Vorhersagen abrufen (`/api/predictions/team`). |

Gesamtergebnis Testlauf (Backend): **20 passed**.

---

## 7) Nutzungshinweis

1. Daten vorhanden (z. B. ueber Seed aus Phase 4).
2. Optional Modell trainieren (ueber `train_random_forest(...)` im Python-Kontext).
3. Prediction-Endpunkte aufrufen:
   - `GET /api/predictions/{player_id}`
   - `GET /api/predictions/team`

OpenAPI-Dokumentation am laufenden Service: `http://localhost:8000/docs`.
