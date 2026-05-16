# Slider input implementation
_Exported on 16.5.2026 at 15:46:48 MESZ from Cursor (3.2.21)_

---

**User**

können wir die Einträge mit Slider machen also keine zahl eingeben sondern eben einen Slider von 0-10

---

**Cursor**

Ja, ich setze das direkt um: ich suche jetzt die betroffenen Eingabefelder im Frontend und ersetze die Zahleneingaben durch Slider mit Bereich `0–10` (inkl. sichtbarem aktuellen Wert).

Ich baue jetzt die Skalenfelder im Player-Formular auf echte Slider um (`0–10`) und zeige den aktuellen Wert direkt daneben an. Dabei korrigiere ich auch die Speicherung von `0`, damit `0` nicht mehr als `null` verloren geht.

Ja, ist umgesetzt: Die relevanten Einträge sind jetzt Slider statt Zahleneingaben.

Geändert in `frontend/src/App.tsx`:

- Wellness-Skalen (`Schlafqualität`, `Muskelkater`, `Mentale Energie`, `Stress`, `Motivation`, `RPE Vortag`) von `number` auf `range` umgestellt
- Bereich überall auf `0–10` gesetzt (`step=1`)
- Aktueller Slider-Wert wird direkt im Label angezeigt
- `PMS-Score` ebenfalls auf Slider `0–10` umgestellt
- Nebenbei ein Datenproblem gefixt: `0` wird beim Speichern nicht mehr als `null` weggeschrieben (bei `rpe_previous_day` und `pms_score`)

Wenn du willst, stelle ich auch `Schlafstunden` noch auf einen Slider um (z. B. `0–12` oder `0–24` mit `0.5`-Schritten).

