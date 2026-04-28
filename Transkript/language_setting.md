# App language settings
_Exported on 28.4.2026 at 14:34:32 MESZ from Cursor (3.2.11)_

---

**User**

kannst du die App auf Deutsch/Englisch/Italienisch einstellen also dass man die Sprache äändern kann

---

**Cursor**

Ich baue dir jetzt direkt eine Sprachumschaltung für Deutsch/Englisch/Italienisch ein. Als ersten Schritt prüfe ich kurz die Frontend-Struktur (`App.tsx` und relevante UI-Komponenten), damit ich die Texte sauber zentralisieren und den Switch gut integrieren kann.

Ich habe die Struktur gesehen: alles sitzt in `frontend/src/App.tsx`. Ich ergänze jetzt eine schlanke i18n-Schicht direkt dort (Sprachzustand + Übersetzungsobjekt + Selector in der UI) und verdrahte dann die sichtbaren Texte in Login, Navigation, Dashboard und Formularen auf Deutsch/Englisch/Italienisch.

Ich ersetze jetzt die wichtigsten sichtbaren UI-Texte und füge den Sprach-Selector im Header ein, damit man sofort zwischen DE/EN/IT wechseln kann. Danach mache ich einen schnellen Lint-Check.

Ja — ist eingebaut.  
Du kannst jetzt in der App zwischen **Deutsch / Englisch / Italienisch** umschalten.

Geändert habe ich in `frontend/src/App.tsx`:

- Sprachsystem ergänzt (`de`, `en`, `it`) mit zentralem `TEXT`-Objekt
- Sprachzustand mit Persistenz über `localStorage` (`kip_language`)
- Sprach-Auswahl im Header hinzugefügt
- Große Teile der sichtbaren UI-Texte auf Übersetzungen umgestellt:
  - Auth (Login/Registrierung)
  - Navigation/Tabs
  - Modellstatus
  - Dashboard-Karten
  - Wellness-/Zyklus-/Privacy-Formulare
  - Coach-Ansichten
- Datums-/Zeitformat auf sprachabhängige Locale umgestellt
- Lint geprüft: **keine Fehler**

Hinweis: Fehlertexte, die direkt vom Backend kommen (`e.message`), bleiben so wie vom Server geliefert. Die lokalen Fallback-Fehlermeldungen sind jetzt sprachabhängig.  

Wenn du willst, kann ich im nächsten Schritt noch die **restlichen Detailtexte/Phasenlabels komplett konsistent** über alle Bereiche hinweg in ein separates i18n-Modul auslagern (z. B. `frontend/src/i18n.ts`), damit `App.tsx` deutlich schlanker wird.

---

**User**

ja gerne

---

**Cursor**

Perfekt, ich mache als Nächstes die saubere Auslagerung in ein eigenes `i18n`-Modul und ziehe dabei die noch verbliebenen festen UI-Texte nach. Danach läuft `App.tsx` deutlich schlanker und die Übersetzungen sind zentral gepflegt.

Ich lagere jetzt die komplette Sprachkonfiguration in eine neue Datei `frontend/src/i18n.ts` aus und passe anschließend `App.tsx` auf Imports um; danach ziehe ich noch die letzten harten Textreste (z. B. Privacy-Fehler/Feldtexte) auf `t.*`.

Super, ist erledigt — jetzt ist es sauber ausgelagert und vollständiger übersetzt.

Ich habe Folgendes umgesetzt:

- Neue zentrale Sprachdatei angelegt: `frontend/src/i18n.ts`
  - enthält `Language`, `LANGUAGE_KEY`, `LOCALES`, `TEXT`
  - alle DE/EN/IT-Strings sind dort gebündelt
- `frontend/src/App.tsx` auf Import umgestellt:
  - `import { LANGUAGE_KEY, LOCALES, TEXT, Language } from "./i18n";`
  - großer Inline-Übersetzungsblock wurde entfernt
- Weitere bisher harte Texte ebenfalls i18n-fähig gemacht:
  - Privacy-Fehler beim Speichern
  - Tagline im Header
  - Seed-Coaches-Zeile (`und/and/e`)
  - Passwort-Hinweis (`mind. 8 Zeichen` etc.)
  - Rollenlabel `Coach`
  - Phasen-Optionen im Zyklus-Select
  - `PMS-Score`
  - Trainingszeile (`min bei Intensität` etc.)
- Checks:
  - `eslint` läuft sauber
  - keine Linter-Fehler in `App.tsx` und `i18n.ts`

Wenn du willst, mache ich als nächsten Schritt noch eine kleine Typisierung wie `type TranslationKey = keyof typeof TEXT.de`, damit fehlende Keys in anderen Sprachen sofort beim Entwickeln auffallen.

---

**User**

ja sicher

---

**Cursor**

Top, ich ergänze jetzt die Typ-Absicherung in `i18n.ts`, damit alle Sprachobjekte exakt dieselben Keys haben und fehlende Übersetzungen direkt als TypeScript-Fehler auffallen. Danach prüfe ich kurz wieder mit Lint.

Perfekt, ist jetzt drin.

Ich habe in `frontend/src/i18n.ts` eine typsichere Struktur ergänzt:

- `defineTranslations(...)` eingeführt, das `Record<Language, T>` erzwingt
- `TEXT` darüber definiert (`defineTranslations({ ... } as const)`)
- `TranslationKey` exportiert:
  - `export type TranslationKey = keyof (typeof TEXT)["de"];`

Damit gilt:
- Alle Sprachobjekte müssen denselben Shape haben
- Fehlende oder falsche Keys fallen jetzt direkt im TypeScript-Check auf
- Keys sind zusätzlich zentral als Typ verfügbar (`TranslationKey`)

Checks:
- `eslint` läuft ohne Fehler
- keine Lint-Diagnosen in `App.tsx` / `i18n.ts`

Wenn du magst, kann ich als nächsten Schritt noch einen kleinen Helfer `t(key: TranslationKey)` ergänzen, damit in `App.tsx` nur noch `t("login")` statt `TEXT[language].login` verwendet wird.

---

**User**

alles klar

---

**Cursor**

Super, dann ist die Sprachumschaltung jetzt sauber abgeschlossen.  
Wenn du später willst, kann ich dir noch:

- ein kleines Sprach-Icon im Header ergänzen,
- die Auswahl zusätzlich im Backend-Userprofil speichern,
- oder eine automatische Browser-Spracherkennung beim ersten Start einbauen.

