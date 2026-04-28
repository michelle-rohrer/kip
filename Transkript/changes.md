# Coaching and player management requests
_Exported on 28.4.2026 at 21:49:49 MESZ from Cursor (3.2.11)_

---

**User**

- kein Register für Coaches möglich 
folgende Logins anlegen
Timo
Killerlippi610

Denise
cazzo!

- Die Namen der Coaches bei Privacy Settings anzeigen lassen

- bei Login einfach mit Benutzernamen

- alle Spielerinnnen/Coaches löschen

- Team_ID random zuteilen 

- bei Coaches Dashboard namen anzeigen lassen der Spielerinnen nicht ID

- Spielerinnen-App löschen, der Name und slogan reichen 

- es müssen verschiedene Teams implementiert werden (sie dürfen die Daten nicht übergreifbar einsehen) BTV Aarau F1 und Eaglets NNV

- Icon von der App wechseln (ich gebe dir später das Bild, sag mir einfach wo ich es speichern soll)

- bei der Coaches Übersicht mit Plots arbeiten und so wenig mit rohen Zahlen wie möglich, gerne auch mit Vergleichslinien usw.

---

**Cursor**

Ich habe deine Anforderungen verstanden und erstelle dir dafür einen umsetzbaren, priorisierten Umsetzungsplan. Bevor ich den finalen Plan schreibe, brauche ich zwei zentrale Entscheidungen von dir, weil sie die Architektur stark beeinflussen.

**Klärung für Umsetzungsplan**

> **Sollen bestehende Accounts komplett ersetzt werden (nur die neuen Coach-Logins + neue Teamstruktur), oder sollen alte Daten/Accounts teilweise migriert werden?**
> - Komplett neu aufsetzen (alles löschen/ersetzen) ✔
> - Teilweise migrieren (bestehende Daten soweit behalten)

> **Bei "Login einfach mit Benutzernamen": Soll das nur für Coaches gelten oder für alle Benutzerrollen?**
> - Nur Coaches
> - Für alle Rollen ✔

Perfekt, danke. Ich prüfe jetzt kurz die relevanten Stellen im Code (Auth, Teams, Coach-Dashboard, App-Branding), damit der Plan konkret auf eure bestehende Struktur passt.

Ich habe die betroffenen Stellen gefunden; für einen sauberen Plan fehlen noch zwei produktrelevante Entscheidungen, damit ich nichts falsch plane.

**Letzte Produktentscheidungen**

> **Was bedeutet "Spielerinnen-App löschen, der Name und Slogan reichen" genau?**
> - Nur Spielerinnen-Funktionen entfernen, Coach-Bereich bleibt voll erhalten
> - Gesamte App auf reine Branding-Seite reduzieren (nur Name + Slogan für alle)
> - Spielerinnen-UI ausblenden, Backend/Endpoints vorerst behalten
>
> Answer: also beim Header der Name

> **"Team_ID random zuteilen": Soll die Zuweisung zufällig nur zwischen den zwei Teams (BTV Aarau F1, Eaglets NNV) passieren oder frei über alle Teams?**
> - Zufällig nur zwischen BTV Aarau F1 und Eaglets NNV
> - Zufällig über alle vorhandenen Teams
> - Coaches manuell Team, Spielerinnen zufällig
>
> Answer: sodass jeder Account einen unique ID hat fürs trainieren. Die Coaches brauchen nichts

Danke, ich sehe zwei Punkte, die ich noch präzise festzurren muss (deine Antwort weicht von den Optionen ab). Ich stelle dir dazu jetzt eine kurze, eindeutige Auswahl.

**Präzisierung vor Plan**

> **Für die Spielerinnen-Ansicht: Was soll im Frontend sichtbar bleiben?**
> - Nur Header mit App-Name (optional Slogan), sonst keine Spielerinnen-UI
> - Login bleibt, danach nur minimaler Screen mit Name/Slogan
> - Spielerinnen-UI bleibt (keine Löschung)
>
> Answer: sorry ich rede nur vom Header vo steht "VOLLEYSYNC
Spielerinnen-App
Track smart. Play strong." dort einfach das Wort Spielerinnen-App löschen

> **Meinst du mit "Team_ID random" tatsächlich Teamzuordnung oder eine separate eindeutige Spielerinnen-ID für Training?**
> - Teamzuordnung zufällig (BTV Aarau F1 / Eaglets NNV)
> - Separate eindeutige Trainings-ID pro Spielerin (nicht Team) ✔
> - Beides: zufällige Teamzuordnung + separate Trainings-ID

Perfekt, jetzt ist es klar. Ich erstelle dir direkt einen priorisierten Implementierungsplan mit konkreten Dateien für Auth, Datenbereinigung, Team-Trennung, UI-Anpassungen und Dashboard-Visualisierung.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Ich setze jetzt direkt mit dem ersten To-do (`model-migration`) an, arbeite die Liste der Reihe nach ab und implementiere alles end-to-end ohne den Plan selbst zu ändern. Zuerst prüfe ich die betroffenen Backend-Dateien und Migrationen im Detail.

Ich starte jetzt die eigentliche Umsetzung in Blöcken: zuerst Modell + Migration + Auth-Backend, danach Seed/Reset, dann Frontend/UI/Plots und am Schluss Tests/Lints. Ich lese dafür noch die zentralen Test- und Schema-Dateien, damit nichts bricht.

Ich bin jetzt bei der Seed-/Reset-Logik: ich baue die festen Coach-Accounts, zwei Teams und eindeutige Trainings-IDs ein, sodass die Datenbasis komplett neu erzeugt werden kann.

Ich passe gerade die Tests und Hilfsfunktionen an die neue Regel „kein Coach-Register“ an, damit die Suite weiterhin die Team-Isolation korrekt prüft.

Ich habe die Kernänderungen umgesetzt und gehe jetzt in die Verifikation: zuerst Backend-Tests, danach Frontend-Build/Lints und anschließend fixe ich verbleibende Fehler.

Umsetzung ist vollständig gemäß Plan erfolgt.

Geändert wurde end-to-end in Backend, Frontend, Seed und Tests:

- Auth auf **Username + Passwort** umgestellt in `backend/app/schemas/auth.py`, `backend/app/services/auth.py`, `backend/app/routers/auth.py` und `frontend/src/App.tsx`.
- Coach-Registrierung deaktiviert (`/api/auth/register` mit Rolle `coach` liefert jetzt `403`) in `backend/app/routers/auth.py`.
- User-Modell erweitert um `username` und `training_uid` in `backend/app/models/entities.py` plus Migration `backend/alembic/versions/20260428_000002_username_training_uid.py`.
- Spielerinnen bekommen beim Registern automatisch eine eindeutige Trainings-ID (`training_uid`), Coaches nicht.
- Team-Zuordnung für neue Spielerinnen wird bei fehlender `team_id` zufällig auf `BTV Aarau F1` / `Eaglets NNV` gesetzt in `backend/app/services/auth.py`.
- Seed/Reset neu aufgebaut in `backend/app/data_generation/generate.py` und `backend/app/data_generation/seed.py`:
  - kompletter Datenreset,
  - feste Coach-Accounts `Timo` / `Killerlippi610` und `Denise` / `cazzo!`,
  - zwei Teams,
  - zufällige Teamzuordnung der Spielerinnen,
  - eindeutige Trainings-IDs.
- Privacy/Coach-Namensanzeige umgesetzt:
  - `player_name` im Predictions-Team-Response (`backend/app/schemas/predictions.py`, `backend/app/routers/predictions.py`),
  - in der UI überall Namen statt IDs, inkl. Privacy-Speicherfeedback (`frontend/src/App.tsx`).
- Header angepasst: Text „Spielerinnen-App“ entfernt, jetzt nur noch App-Name + Slogan (`frontend/src/App.tsx`).
- Coach-Übersicht/Detail stärker plot-basiert umgesetzt (Trendcharts statt primär Listen) in `frontend/src/App.tsx`.
- Icon vorbereitet/umgestellt:
  - neue Datei `frontend/src/assets/app-icon.svg`,
  - Import in `frontend/src/App.tsx` auf neues Icon gesetzt.
- Übersetzungen ergänzt für Username in `frontend/src/i18n.ts`.
- Tests auf neue Auth-/Rollenlogik angepasst in:
  - `backend/tests/test_auth.py`
  - `backend/tests/test_core_endpoints.py`
  - `backend/tests/test_e2e_flow.py`
  - `backend/tests/test_data_generation.py`
  - sowie ML-Synthetic-Erkennung angepasst in `backend/app/ml/train.py`.

Validierung:

- Backend-Tests: `23 passed`.
- Frontend-Build: erfolgreich (`tsc -b && vite build`).
- Linter-Diagnosen auf geänderten Dateien: keine Fehler.

Wichtig für dein späteres eigenes Icon-Bild:
- Bitte in `frontend/src/assets/app-icon.svg` (oder `app-icon.png`) speichern; aktuell referenziert die App `app-icon.svg`.

---

**User**

habe die IconApp hinzugefügt

---

**Cursor**

Perfekt — ich binde dein neues Icon jetzt direkt ein und passe die Referenz in der App an. Anschließend prüfe ich kurz per Build, ob alles sauber läuft.

Super, ist eingebunden.

- Die App nutzt jetzt dein neues Icon aus `frontend/src/assets/app_icon.png`.
- Import wurde in `frontend/src/App.tsx` angepasst.
- Frontend-Build läuft erfolgreich.

Wenn du willst, passe ich dir als Nächstes noch das Browser-Tab-Favicon in `frontend/index.html` ebenfalls auf dieses neue Icon an.

---

**User**

ja gerne

---

**Cursor**

Ich passe jetzt direkt auch das Browser-Favicon auf dein neues `app_icon.png` an und verifiziere danach kurz den Build.

Erledigt — das Browser-Tab-Favicon ist jetzt ebenfalls auf dein neues Icon gesetzt.

- Geändert in `frontend/index.html`:
  - `<link rel="icon" type="image/png" href="/src/assets/app_icon.png" />`
- Build-Check erfolgreich, also alles konsistent.

Wenn du willst, kann ich dir noch eine kleinere favicon-Version erzeugen/verwenden, damit der Tab-Icon-Load leichter wird (dein aktuelles PNG ist relativ groß).

