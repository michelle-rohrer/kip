# Umsetzung: Synthetische Datengenerierung (Seed)

Diese Seite beschreibt **was im Code umgesetzt wurde** für die Arbeitspakete **realistische, korrelierte Demo-Daten** und **Seed-Skript** – im übergeordneten Projektplan als **Phase 4: Synthetische Datengenerierung** geführt (Aufgaben **4.1**–**4.6**).

**Einordnung:** Das Cursor-Todo **phase4** bezeichnet diese Phase. **Nicht verwechseln** mit der Umsetzungsdoku *Core API (CRUD)* unter [Phase_4_Dokumentation.md](Phase_4_Dokumentation.md) – dort handelt es sich um Plan-**Phase 3** (Wellness, Zyklus, Training, Privacy).

---

## Gelieferte Dateien (Backend)

| Bereich | Pfad |
|---------|------|
| Generierung (Logik, Konfiguration) | `backend/app/data_generation/generate.py` |
| Datenbank-Seed (CLI + Persistenz) | `backend/app/data_generation/seed.py` |
| Paket-Exporte | `backend/app/data_generation/__init__.py` |
| Tests | `backend/tests/test_data_generation.py` |

Abhängigkeiten: bestehende SQLAlchemy-Modelle (`app.models`), `hash_password` aus `app/services/auth.py`, `SessionLocal` aus `app/db.py`, **NumPy** (bereits in `requirements.txt`).

---

## 4.1 Umfang der synthetischen Spielerinnen und Zeiträume

### Was wurde gemacht?

- Pro Lauf werden **15–20 Spielerinnen** erzeugt (Standard **18**; CLI `--players` clippt auf 15–20).
- Pro Spielerin wird ein **zufälliger** Zeitraum zwischen **90 und 180 Tagen** gewählt; das **Enddatum** ist standardmäßig **heute** (`end_date`), per CLI mit `--end-date YYYY-MM-DD` überschreibbar.
- Es werden ein **Team**, eine **Trainerin** (`UserRole.coach`) und die **Spielerinnen** (`UserRole.player`) als echte `User`-Zeilen mit **bcrypt-Hash** (gleicher Mechanismus wie Produktiv-Registrierung) angelegt.

### Wofür?

- Ausreichend Volumen für spätere **ML-/Feature-Pipelines** und UI-Demos ohne echte Gesundheitsdaten.
- Reproduzierbare Demos durch festen Default-**Random-Seed** (`42`), überschreibbar per `--seed` oder `SyntheticDatasetConfig.random_seed`.

---

## 4.2 Zyklusdaten (Länge, Phasen, PMS/Symptome)

### Was wurde gemacht?

- **Zykluslänge** pro Spielerin: Stichprobe aus einer **Normalverteilung** um 29 Tage (σ ≈ 2), anschließend auf **26–32 Tage** begrenzt.
- **Phasen** aus dem **Zyklustag** (`cycle_day`) und fester Aufteilung innerhalb eines Zyklus:
  - Menstruation: Tage **1–5**
  - Follikelphase: **6–12**
  - Ovulation: **13–15**
  - Lutealphase: **16** bis Zyklusende
- **Zyklustag pro Kalenderdatum:** über einen pro Spielerin gewählten **Anker** (`cycle_anchor`) und Modulo der Zykluslänge.
- **`pms_score`:** vor allem in **Luteal** (stärker gegen Zyklusende), optional auch Menstruation; Werte im erlaubten Bereich **0–10**.
- **Symptome:** `cramps`, `migraine`, `fatigue` mit erhöhter Wahrscheinlichkeit in **Menstruation** bzw. **Luteal** (teilweise leicht in Ovulation).
- Optional **`contraception_type`** (z. B. Pille, IUP, Implantat) für einen Teil der Spielerinnen.

### Wofür?

- Plausible **phasenabhängige** Muster für Wellness und spätere Modelle, ohne medizinischen Claim auf Individualprognose.

---

## 4.3 Wellness-Daten und Korrelationen

### Was wurde gemacht?

- Täglich ein `WellnessEntry` pro Spielerin und Datum (passend zu API-Constraints **1–10** für Skalen, Schlafstunden **> 0** und ≤ 24).
- **Schlafqualität** und **Schlafdauer** sind gekoppelt; in Luteal/Müdigkeit leicht verschlechtert.
- **Mentale Energie** positiv mit **Schlafqualität** verknüpft (plus Rauschen).
- **Muskelkater** steigt mit **Vortags-Trainingslast** (Proxy aus Intensität × Dauer) und ist in Menstruation/Luteal leicht erhöht.
- **Stress** kann bei höherem **PMS-Score** ansteigen.
- **`rpe_previous_day`** bezieht sich auf das **Vortagstraining** (Intensität und Last), nur wenn am Vortag trainiert wurde.

### Wofür?

- Daten, in denen **Schlaf, Belastung und Zyklus** sichtbar korrelieren – nützlich für Feature-Engineering und visuelle Trends in Apps.

---

## 4.4 Trainingsdaten (Wochenrhythmus, Periodisierung)

### Was wurde gemacht?

- **Sonntag:** kein Training (kein `TrainingEntry`).
- **Montag–Samstag:** eine Einheit pro Tag mit **Dauer** und **Intensität** (1–10).
- **Periodisierung:** in etwa **3-Wochen-Blöcken** wechseln **Belastungswochen** (höhere Intensität/Dauer) und **Erholungswochen** (niedrigere Werte).
- Zusatzfelder: **`jump_count`** (poissonartig aus Last abgeleitet), **`sprint_times`**, **`strength_values`** als JSON; **`match_stats`** gelegentlich.

### Wofür?

- Realistischer **Volleyball-/Krafttraining-Rhythmus** und variable Belastung für Last-Kennzahlen (z. B. später **ACWR** aus denselben Einträgen).

---

## 4.5 Verletzungs-/Schmerzeinträge

### Was wurde gemacht?

- Ereignisse sind **selten** (tägliche Wahrscheinlichkeit mit kleinem Basiswert).
- **Erhöhte Rate**, wenn:
  - ein **ACWR-Proxy** (7-Tage-Summe der Tageslast geteilt durch ein Viertel der 28-Tage-Summe) **hoch** ist,
  - die aktuelle **Zyklusphase** Menstruation oder Luteal ist,
  - der **Muskelkater** des gleichen Tages sehr hoch ist.
- **`body_location`** aus einer festen deutschsprachigen Liste (Knie, Sprunggelenk, …), **`pain_intensity`** 1–10, **`is_chronic`** selten `true`.

### Wofür?

- Demo-Daten mit **überlastungs- und phasenbezogenen** Mustern; die exakte ACWR-Definition für das ML-Modul folgt in der **ML-Phase** des Plans.

---

## 4.6 Seed-Skript und Datenbankbefüllung

### Was wurde gemacht?

- **`seed_database`** in `seed.py`: optional **Vorab-Löschung** aller User mit E-Mail-Muster `synthetic.%@kip.local` (ORM-Cascade entfernt abhängige Einträge), anschließend Löschen des Teams **`Synthetic Team KIP`** (Konfigurierbar über `SyntheticDatasetConfig.team_name`).
- Reihenfolge: Team anlegen → `flush` → **`team_id`** auf Trainerin und alle Spielerinnen → User und **`PrivacyConsent`** (je eine Zeile Spielerin↔Trainerin, zufällige **`share_cycle_data`** / **`share_wellness_data`** mit hoher Wahrscheinlichkeit) → Bulk-Insert aller **Cycle-, Wellness-, Training-, Injury**-Einträge → `commit`.
- **CLI** (aus Verzeichnis **`backend/`**):

```bash
python3 -m app.data_generation.seed
```

| Option | Bedeutung |
|--------|-----------|
| `--no-replace` | Löscht keine bestehenden Synthetic-User (riskiert Duplikate bei gleicher E-Mail). |
| `--seed N` | Zufalls-Seed überschreiben. |
| `--players N` | Anzahl Spielerinnen (15–20). |
| `--end-date YYYY-MM-DD` | Letzter Tag der generierten Historie. |

### Wofür?

- **Ein Befehl** genügt, um eine lokale oder Docker-**PostgreSQL**-Instanz mit konsistenten Demo-Daten zu füllen (nach Migrationen und laufender DB).

**Demo-Zugangsdaten (Standard-Passwort aus Config):**  
Passwort für alle Seed-Accounts: `synthetic-seed-password`  
Trainerin: `synthetic.coach@kip.local`  
Spielerinnen: `synthetic.player.01@kip.local` … (zweistellige Nummer).

---

## Tests (`backend/tests/test_data_generation.py`)

| Test | Geprüftes Verhalten |
|------|----------------------|
| `test_build_synthetic_dataset_produces_expected_entities` | Erwartete Anzahl Spielerinnen und Tage; Zykluslänge und `cycle_day` im gültigen Bereich; Training nicht leer. |
| `test_seed_database_persists_and_replace_clears_previous` | Seed in In-Memory-SQLite; User-/Team-/Consent-Zähler; zweiter Lauf mit `replace=True` ohne Duplikat-Bruch. |

---

## Einordnung im Plan

| Plan-Aufgabe (Phase 4) | Umsetzung |
|------------------------|-----------|
| 4.1 Script, 15–20 Spielerinnen, 90–180 Tage | `build_synthetic_dataset`, `SyntheticDatasetConfig` |
| 4.2 Zyklus realistisch | `_sample_cycle_length`, `_phase_for_day`, `_cycle_day_for_date`, PMS/Symptome |
| 4.3 Wellness-Korrelationen | Schlaf, Last, Phase, RPE-Vortag in `generate.py` |
| 4.4 Training Wochenrhythmus + Periodisierung | Wochentag-Check, 3-Wochen-Blöcke |
| 4.5 Verletzungen, ACWR-Proxy, Phasen | tägliche Zufallsentscheidung mit modifizierter Rate |
| 4.6 Seed | `python -m app.data_generation.seed`, `seed_database` |

---

## Abgrenzung zur ML-Phase (Plan)

Die synthetische Generierung nutzt einen **vereinfachten Last- und ACWR-Proxy** nur für **stochastisch glaubwürdige** Schmerz-/Verletzungshäufigkeit. Die **kanonische** Feature-Berechnung (exakter ACWR, Walk-Forward-Training, Modellversion) ist im Plan der **Feature-Engineering-/ML-Phase** vorbehalten.
