# Dashboard plot understanding and details
_Exported on 28.4.2026 at 13:21:44 MESZ from Cursor (3.2.11)_

---

**User**

der Plot auf dem Dashboard ist nicht verständlich, was genau bedeutet er. Kann man dort dann auch drauf gehen und detailreichere plots haben

---

**Cursor**

Ich schaue mir jetzt kurz die Dashboard-Implementierung an, damit ich dir konkret sagen kann, was der aktuelle Plot bedeutet und ob/wie wir daraus eine klickbare Detailansicht machen können.

Ich habe die Ursache gefunden: der aktuelle Plot ist nur eine unlabeled Mini-Sparkline ohne Achsen/Legende. Ich baue ihn jetzt verständlicher um (Beschreibung + Skala) und ergänze eine klickbare Detailansicht mit mehreren Linien und Tagesdetails.

Der Plot war bisher tatsächlich schwer verständlich: Er hat nur eine Linie gezeigt, ohne zu erklären, **was** dargestellt wird und ohne Detailinteraktion.

Ich habe das direkt verbessert in `frontend/src/App.tsx`:

- Der Plot ist jetzt beschriftet: Er zeigt den **7-Tage-Wellness-Durchschnitt** aus `Schlafqualität`, `mentaler Energie` und `Motivation` (Skala 1–10).
- Es gibt eine klarere Einordnung (`niedriger` ↔ `höher`) und sichtbare Punkte.
- Neu: Button **„Detailansicht öffnen“** im Dashboard.
- In der Detailansicht siehst du jetzt mehrere Linien:
  - Durchschnitt (blau)
  - Schlafqualität (grün)
  - Mentale Energie (lila)
  - Motivation (orange)
- Zusätzlich sind die Tage klickbar; beim Klick bekommst du darunter die **Tagesdetails** mit allen Einzelwerten.

Kurz: Ja, man kann jetzt „draufgehen“ und deutlich detailreichere Plots sehen.

