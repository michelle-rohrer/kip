# Phase 5 synthetic data generation
_Exported on 28.3.2026 at 12:59:54 MEZ from Cursor (2.6.22)_

---

**User**

Implement the following to-dos from the plan (the plan is attached for your reference). Do NOT edit the plan file itself.

You have been assigned the following 1 to-do(s) with IDs: phase4

1. [phase4] Phase 5: Synthetische Datengenerierung (realistische korrelierte Daten, Seed-Script)

These to-dos have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the assigned to-dos.

---

**Cursor**


Phase 4 (synthetische Datengenerierung) implementieren. Zuerst den Codebase-Stand prüfen und das Todo als „in Bearbeitung“ markieren.




Implementierung der Datengenerierung: Paket `data_generation` mit `generate.py` und `seed.py` anlegen.




Wir korrigieren die Generierung: leere `consents` entfernen, `build_privacy_consents` hinzufügen und die Mental-Energy-Logik vereinfachen. Anschließend `seed.py` implementieren.




Hier die **kurze Zusammenfassung** (Plan-Phase **4** – synthetische Datengenerierung; im Ticket stand fälschlich „Phase 5“).

## Umgesetzt

1. **`backend/app/data_generation/generate.py`**  
   - **15–20 Spielerinnen** (konfigurierbar, Standard 18), **90–180 Tage** Historie pro Person.  
   - **Zyklus**: Länge ~N(29, 2), auf **26–32** begrenzt; Phasen wie im Plan (Menstruation 1–5, Follikel 6–12, Ovulation 13–15, Luteal bis Zyklusende); `pms_score` und Symptome stärker in **Luteal**/Menstruation.  
   - **Wellness**: Schlafqualität/Schlafdauer gekoppelt; **mentale Energie** an Schlaf; **Muskelkater** an Vortags-Last und Phase; **Stress** bei hohem PMS; **`rpe_previous_day`** an Vortags-Training.  
   - **Training**: **Mo–Sa**, **So frei**; **3-wöchige Blöcke** wechseln Belastungs- und Erholungswochen; `jump_count`, `sprint_times`, `strength_values`, gelegentlich `match_stats`.  
   - **Verletzungen**: seltene Einträge mit erhöhter Rate bei **hohem ACWR** (7-Tage-Summe / (28-Tage-Summe/4)), in **Menstruation/Luteal** und bei **hohem Muskelkater**.  
   - **Team + Trainerin + Spielerinnen** mit `bcrypt`-Hashes wie im restlichen Backend; **`build_privacy_consents`** (~72 % Zyklus, ~78 % Wellness teilen).

2. **`backend/app/data_generation/seed.py`**  
   - Löscht bei Standardlauf bestehende **`synthetic.*@kip.local`**-User und das Team **`Synthetic Team KIP`**, legt dann alles neu an.  
   - Aufruf aus dem **`backend/`**-Verzeichnis:  
     `python3 -m app.data_generation.seed`  
   - Optionen: `--no-replace`, `--seed`, `--players`, `--end-date`.

3. **`backend/app/data_generation/__init__.py`** – Exporte für `SyntheticDatasetConfig`, `build_synthetic_dataset`, `build_privacy_consents`.

4. **`backend/tests/test_data_generation.py`** – Tests für Generator und DB-Seed (inkl. erneutem Seed mit `--replace`-Logik).

**Login für Seed-Accounts:** Passwort wie in `SyntheticDatasetConfig`: `synthetic-seed-password` (Trainerin: `synthetic.coach@kip.local`, Spielerinnen: `synthetic.player.01@kip.local` usw.).

Die Plan-Datei wurde **nicht** geändert. Todo **phase4** ist erledigt.

---

**User**

kannst du eine Dokumentation wie für die anderen Phasen schreiben 

---

**Cursor**


Suche nach vorhandener Phasen-Dokumentation im Projekt.




Erstelle `docs/Phase_5_Dokumentation.md` im Stil von Phase 4 (Umsetzung + Tabellen) und Phase 3 (nummerierte Aufgaben 4.1–4.6). README-Link prüfen und konsistent verlinken.




Hier die Kurzfassung:

## Neue Datei: [`docs/Phase_5_Dokumentation.md`](docs/Phase_5_Dokumentation.md)

Aufbau wie bei den anderen Umsetzungs-Dokus:

- **Kopfzeile mit Einordnung:** Plan-**Phase 4** (Synthetische Datengenerierung) vs. Cursor-Todo **phase4**, plus klarer Hinweis, dass das **nicht** die Core-API-Doku in `Phase_4_Dokumentation.md` ist.
- **Tabelle „Gelieferte Dateien“** (analog zu Phase 4).
- **Abschnitte 4.1–4.6** jeweils mit **„Was wurde gemacht?“** und **„Wofür?“** (an Phase 3 angelehnt), inhaltlich an den Plan gekoppelt.
- **CLI-Tabelle** für `python3 -m app.data_generation.seed` und Optionen.
- **Demo-Logins** (E-Mails + Passwort).
- **Test-Tabelle** wie bei Phase 4.
- **Plan-Mapping** und kurze **Abgrenzung zur ML-Phase** (ACWR nur als Proxy in der Generierung).

## README

Im Abschnitt **Projektdokumentation** sind die Links bereinigt (der alte Pfad `UMSETZUNG-CORE-API-CRUD.md` existierte nicht) und **`Phase_5_Dokumentation.md`** ergänzt; Phasen 1–4 sind dort zum schnellen Finden mit verlinkt.

Wenn du willst, können wir die Überschriften in `Phase_1_Dokumentation.md` (intern noch „Phase 0“) später einmal einheitlich mit dem README benennen.

