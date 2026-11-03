# Whoop, Oura und Apple Health verbinden

VolleySync kann Schlaf, HRV, Ruhepuls und Erholung direkt vom Gerät übernehmen.
Die Spielerin muss dann nur noch das eintragen, was kein Sensor messen kann:
Muskelkater, Stimmung, Stress, Zyklus, Schmerz.

| Anbieter | Was du einmalig tun musst | Aufwand |
| --- | --- | --- |
| **Apple Health** (Apple Watch / iPhone) | Nichts auf dem Server. Jede Spielerin richtet einen Kurzbefehl ein. | 5 Min pro Spielerin |
| **Oura** | Nichts auf dem Server. Jede Spielerin erzeugt einen persönlichen Token. | 2 Min pro Spielerin |
| **Whoop** | Einmalig eine (kostenlose) Developer-App registrieren. | 10 Min einmalig |

> **Datenschutz:** Gerätedaten liegen auf demselben Freigabe-Schalter wie die
> Wellness-Daten. Die Trainerin sieht sie nur, wenn die Spielerin unter
> *Datenfreigaben* „Wellness teilen" eingeschaltet hat. Die Zugangstokens von
> Whoop und Oura liegen verschlüsselt in der Datenbank.

---

## In der App

Avatar oben rechts antippen → **Geräte & Sync**. Dort steht für jeden der drei
Anbieter, ob er verbunden ist, wann zuletzt synchronisiert wurde und was zuletzt
angekommen ist.

Die App holt neue Daten automatisch, wenn die letzte Synchronisation mehr als
sechs Stunden her ist. Der Knopf *Jetzt synchronisieren* erzwingt es sofort.

---

## 1) Apple Health (Apple Watch, iPhone)

Apple hat bewusst **keine** Cloud-Schnittstelle: Health-Daten verlassen das
iPhone nur, wenn die Besitzerin sie selbst verschickt. Deshalb holt VolleySync
nichts ab – das iPhone schickt.

**In der App:** *Geräte & Sync* → Apple Health → **Einrichten**. Es erscheinen
eine URL und ein Token. Der Token wird **nur einmal** angezeigt.

**Variante A – Kurzbefehle (gratis, auf jedem iPhone vorhanden)**

1. App *Kurzbefehle* → **+** → neuer Kurzbefehl.
2. Aktion **„Health-Sample suchen"** hinzufügen, Typ *Schlafanalyse*,
   Zeitraum *Heute*. Das Ganze nochmals für *Herzfrequenzvariabilität* und
   *Ruhepuls*.
3. Aktion **„Inhalte einer URL abrufen"** hinzufügen:
   - URL: die URL aus der App
   - Methode: **POST**
   - Header: `X-Ingest-Token` = der Token aus der App
   - Anfragetext: **JSON**, mit den Feldern `date`, `sleep_hours`, `hrv_ms`,
     `resting_hr`
4. *Automation* → **Tageszeit** → täglich 08:00 → diesen Kurzbefehl ausführen,
   „Vor dem Ausführen fragen" ausschalten.

**Variante B – Health Auto Export (App aus dem App Store, ca. 3 EUR)**

In der App eine *REST API* Automation anlegen, als URL die URL aus VolleySync
eintragen, Header `X-Ingest-Token` setzen, Format *JSON*, und die Metriken
`sleep_analysis`, `heart_rate_variability`, `resting_heart_rate`,
`respiratory_rate`, `step_count`, `active_energy` auswählen. VolleySync
versteht dieses Format direkt.

**Zum Testen** (Token einsetzen):

```bash
curl -X POST "https://volleysync-api.onrender.com/api/integrations/apple-health/ingest" \
  -H "X-Ingest-Token: DEIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-11-03","sleep_hours":7.5,"hrv_ms":54,"resting_hr":48,"steps":8200}'
```

Antwort `{"days_written":1,...}` heisst: angekommen.

---

## 2) Oura Ring

**Variante A – persönlicher Token (empfohlen, nichts zu registrieren)**

1. In der App: *Geräte & Sync* → Oura Ring → **Mit persönlichem Token verbinden**
2. [cloud.ouraring.com/personal-access-tokens](https://cloud.ouraring.com/personal-access-tokens)
   öffnen → *Create a new personal access token* → kopieren
3. Token in VolleySync einfügen → **Verbinden**

Die letzten 14 Tage werden sofort geholt.

**Variante B – OAuth (die Spielerin muss nichts kopieren)**

Dafür braucht es eine Oura-Applikation auf
[cloud.ouraring.com/oauth/applications](https://cloud.ouraring.com/oauth/applications).
Als Redirect-URI eintragen:

```
https://volleysync-api.onrender.com/api/integrations/callback/oura
```

Danach auf Render setzen: `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`. Sobald beide
gesetzt sind, zeigt die App bei Oura einen **Verbinden**-Knopf.

---

## 3) Whoop

Whoop kennt keine persönlichen Tokens – hier führt nur OAuth zum Ziel, und das
braucht eine einmalige Registrierung durch dich.

1. [developer.whoop.com](https://developer.whoop.com) → mit dem Whoop-Konto
   anmelden → **Create new app**
2. Ausfüllen:
   - *Name*: VolleySync
   - *Redirect URI*: `https://volleysync-api.onrender.com/api/integrations/callback/whoop`
   - *Scopes*: `read:recovery`, `read:cycles`, `read:sleep`, `read:workout`,
     `read:profile`, `offline`
3. `Client ID` und `Client Secret` kopieren
4. Auf Render beim Service `volleysync-api` setzen:
   `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` → Service neu deployen

Danach: *Geräte & Sync* → Whoop → **Verbinden** → Whoop-Login → zurück in der App.

> Die Redirect-URI muss **exakt** mit `API_BASE_URL` übereinstimmen, inklusive
> `https://` und ohne Schrägstrich am Ende. Das ist der mit Abstand häufigste
> Fehler.

---

## Welche Werte wo landen

| Feld in VolleySync | Whoop | Oura | Apple Health |
| --- | --- | --- | --- |
| Schlafstunden | Zeit im Bett minus Wachzeit | `total_sleep_duration` | `sleep_analysis` |
| Schlaf-Score | `sleep_performance_percentage` | `daily_sleep.score` | optional |
| Erholung / Readiness | `recovery_score` | `daily_readiness.score` | – |
| HRV | `hrv_rmssd_milli` | `average_hrv` | `heart_rate_variability` |
| Ruhepuls | `resting_heart_rate` | `lowest_heart_rate` | `resting_heart_rate` |
| Strain | `cycle.score.strain` | – | – |
| Schritte | – | `daily_activity.steps` | `step_count` |

Schlafstunden und Schlafqualität schlägt die App im Wellness-Formular als
Vorschlag vor („Übernehmen"). Eingetragen wird nur, was die Spielerin bestätigt –
der Wellness-Eintrag bleibt ihre Aussage, die Gerätedaten bleiben daneben als
Messung stehen.

Das Risiko-Modell nutzt zusätzlich HRV, Ruhepuls und Readiness – und zwar als
Abweichung vom persönlichen Durchschnitt, nicht als Absolutwert. Ein Ruhepuls
von 55 ist für die eine normal und für die andere ein Warnsignal.

---

## Nächtlicher Abgleich (optional)

Die App synchronisiert von selbst, sobald jemand sie öffnet. Wer die Daten schon
vor dem ersten Login des Tages aktuell haben will, ruft nachts einmal auf:

```bash
curl -X POST "https://volleysync-api.onrender.com/api/integrations/sync-all" \
  -H "X-Cron-Secret: $CRON_SECRET"
```

`CRON_SECRET` erzeugt Render beim ersten Deploy automatisch (Service →
Environment). Als Auslöser genügt ein Gratis-Dienst wie cron-job.org.

---

## Wenn etwas nicht klappt

| Symptom | Ursache | Lösung |
| --- | --- | --- |
| Whoop-Karte zeigt „Nicht eingerichtet" | `WHOOP_CLIENT_ID`/`SECRET` fehlen | Auf Render setzen, neu deployen |
| Nach dem Whoop-Login Fehlermeldung | Redirect-URI stimmt nicht mit `API_BASE_URL` überein | Beide exakt angleichen |
| „Der Verbindungslink ist abgelaufen" | Zwischen Klick und Login vergingen >10 Minuten | Nochmals auf *Verbinden* tippen |
| Oura-Token wird abgelehnt | Token unvollständig kopiert | Neu erzeugen und komplett einfügen |
| Apple Health liefert nichts | Falscher Header oder Body | Mit dem `curl` oben prüfen |
| Karte zeigt „Bitte prüfen" | Letzter Abgleich schlug fehl | Fehlertext auf der Karte lesen, ggf. neu verbinden |
| Alle Geräte plötzlich getrennt | `WEARABLE_ENCRYPTION_KEY` oder `JWT_SECRET_KEY` wurde geändert | Spielerinnen verbinden einmalig neu |
