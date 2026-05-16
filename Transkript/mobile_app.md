# Mobile app development kostenlos
_Exported on 12.5.2026 at 12:26:52 MESZ from Cursor (3.2.21)_

---

**User**

ich möchte statt einer Web-App eine Mobile App machen aber kostenlos, wie genau funktioniert das?

---

**Cursor**

Hier eine knappe Orientierung: **„Mobile App“ + „komplett kostenlos“** hängen davon ab, ob du **nur für dich/Test** bastelst oder **offiziell im App Store / Play Store** veröffentlichst.

## Was praktisch „kostenlos“ geht

### 1. **PWA (Progressive Web App)**
Die App bleibt im Kern **Website + Service Worker**, wird aber vom Browser **„Zum Homescreen hinzufügen“** wie eine App gestartet.  
- **Kostenlos** für Entwicklung und Hosting (je nach Provider; viele haben Free Tiers).  
- **Kein Apple-/Google-Veröffentlichungszwang**, aber **Begrenzungen** gegenüber nativen Apps (Push, manche Hardware-APIs, iOS-Verhalten ist strenger als Android).

### 2. **Web-Technik in einen nativen Mantel**
Mit **Capacitor** oder **Cordova** packst du deine bestehende Web-App in einen kleinen nativen Wrapper (WebView).  
- Entwicklung am Rechner: **oft kostenlos** (Simulator/Emulator, Gerät mit USB).  
- Store-Deployment: siehe unten (Apple/Google Gebühren).

### 3. **Cross-Platform mit React Native (z. B. Expo) oder Flutter**
Eine Codebasis, Builds für Android und iOS. **Expo** erleichtert Aufbau und Test stark.  
- **Lokaler Test** mit Expo Go oft **ohne eigene Gebühren**.  
- **Stores** wieder: Apple/Google.

## Wo „kostenlos“ meist aufhört: Veröffentlichung

- **Apple App Store**: Entwicklerkonto (**jährliche Gebühr**, typisch ca. **99 USD**/Jahr je Region) – ohne geht keine reguläre Veröffentlichung im Store. Du kannst trotzdem **kostenlos entwickeln** und z. B. **intern per TestFlight** verteilen – aber auch dafür brauchst du in der Regel das Konto.  
- **Google Play**: **einmalige** Registrierungsgebühr (üblich um **25 USD**).  
Alternativen ohne Store („Sideloading“, eigene APK-Links, Enterprise-Verteilung) sind für **Breitenpublikum** oft unpraktikabel oder eingeschränkt.

## Was du konkret entscheiden solltest

| Ziel | Sinnvolle Richtung |
|------|--------------------|
| Schnell, kein Store, gratis | **PWA** oder Web + „Installieren“ |
| Bestehende Web-App, native Shell | **Capacitor** |
| Neue App „richtig mobil“, viele Geräte | **React Native (Expo)** oder **Flutter** |
| Max. Store-Reichweite | Store-Accounts budgeting (Apple/Google) |

Wenn du magst: Schreib kurz, ob du eine **bereits bestehende Web-App** (wie in eurem KIP-/VolleySync-Kontext) hast und ob **Apple + Google Stores** Pflicht sind – dann kann ich dir eine **konkrete Strecke** (Technik + kostenfreie Phase vs. erste Store-Kosten) dafür vorschlagen.

---

**User**

und im Appstore gibt es keine Möglichkeiten es kostenlos zu machen?'

---

**Cursor**

Es gibt zwei verschiedene „kostenlos“-Begriffe:

## 1. **App für Nutzer kostenlos** – ja, jederzeit

Im App Store kannst du die App **ohne Kaufpreis** anbieten („Free“). Nutzer zahlen nichts fürs Herunterladen. Optional kannst du später **In-App-Käufe** oder **Abos** anbieten – musst du aber nicht.

## 2. **Dich als Entwickler/in – fast nie komplett kostenlos**

Um eine App **öffentlich im App Store** zu veröffentlichen, brauchst du in der Regel die **Apple Developer Program**-Mitgliedschaft. Die ist **jährlich kostenpflichtig** (in vielen Ländern rund **99 USD/Jahr**; der Betrag kann je nach Land/Währung abweichen).

**Es gibt keine allgemeine „kostenlose App Store-Veröffentlichung“** wie ein Gratis-Hosting-Angebot für jedermann.

### Ausnahmen (eingeschränkt, nicht für alle)

Apple bietet in bestimmten Fällen **Gebührenbefreiungen oder Sonderprogramme**, z. B. für **qualifizierte gemeinnützige Organisationen**, manche **Bildungs-/Behördenkontexte** oder über **gebündelte Ausbildungsprogramme** – das gilt **nicht** pauschal für private Hobbyprojekte. Ob du da reinfällst, steht nur in den **aktuellen** Apple-Richtlinien auf [developer.apple.com](https://developer.apple.com).

### Kurz gesagt

| Was | Kostenlos möglich? |
|-----|-------------------|
| App **kostenlos herunterladbar** für Nutzer | Ja |
| **Ohne** bezahltes Developer-Programm **im öffentlichen** App Store | Praktisch nein (für die meisten) |
| Nur **lokal am Mac** entwickeln / Simulator | Ja (Xcode), aber kein regulärer Store-Release |

Wenn du nur **null Euro für Endnutzer** meinst: das geht. Wenn du **null Euro für dich** beim Store meinst: für die breite Masse gibt es dafür **keine Standardlösung** – nur Sonderfälle bei Apple prüfen oder Wege **ohne** Store (PWA, interne Verteilung, Android mit einmaliger Play-Gebühr, etc.).

---

**User**

Apple bietet in bestimmten Fällen Gebührenbefreiungen oder Sonderprogramme, z. B. für qualifizierte gemeinnützige Organisationen, 

muss man das beantragen oder wie geht das?

---

**Cursor**

Aktuelle Informationen zur Apple-Vorgehensweise bei Gebührenbefreiungen für gemeinnützige Organisationen nachschlagen.



Ja – **bei Apple läuft das nicht automatisch**. Du musst die Befreiung **aktiv beantragen** bzw. beim ersten Mal die passende Option wählen.

## Neuanmeldung (noch kein Developer-Programm-Konto für die Organisation)

Wenn ihr euch als **gemeinnützige Organisation**, **akkreditierte Bildungseinrichtung** oder **Behörde** registriert, gibt es beim **Enrollment** die Möglichkeit, **„Fee waiver“ zu beantragen** – dort wählt ihr das aus und füllt den Prozess weiter aus. Apple prüft und meldet sich ggf., wenn **Nachweise** fehlen.

## Bereits Mitglied (Programm bereits gebucht und bezahlt)

Dann kann der **Account Holder** einen Antrag über das Apple-Formular stellen – **jederzeit vor Ablauf** der aktuellen Mitgliedschaft:  
[Apple – Membership fee waiver request](https://developers.apple.com/contact/membership-fee-waiver/)

Hintergrundinfos und Voraussetzungen:  
[Apple Developer Program fee waiver](https://developers.apple.com/support/fee-waiver)

## Wichtige Voraussetzungen (laut Apple)

- **Rechtsträger** mit Status Nonprofit / Bildung / Staat – **keine** Privatperson, **kein** Einzelunternehmer im Sinne der Ausschlusskriterien.  
- **Kein** „Paid Applications Agreement“ für **kostenpflichtige** Apps oder **In-App-Käufe** (bzw. beendet, falls früher unterschrieben).  
- Ihr verkauft **keine digitalen Güter oder Dienste** über eure Apps in dem Sinne der Regel dort.

(EU-Sonderfall: wenn ihr einen **alternativen App-Marktplatz auf iOS in der EU** betreibt, gibt es dort noch eine Zusatzregel zu Entwickler:innen mit derselben Befreiung – für normale Vereine/App-Projekte meist irrelevant.)

## Ablauf in Kurzform

1. Prüfen, ob ihr die **„eligible organization“**-Kriterien **wirklich** erfüllt (nicht „wir sind gemeinnützig im Sinne Satzung“, sondern was Apple konkret unter der jeweiligen Kategorie versteht).  
2. **Neu:** Enrollment mit Option **fee waiver**. **Schon Mitglied:** Link oben zum **Antrag**.  
3. **Warten auf Prüfung**, ggf. **Dokumente** nachreichen.  
4. Bei **jährlicher Erneuerung** muss der Account Holder die **Fortgeltung der Berechtigung** bestätigen.

**Rückerstattung** für bereits gezahlte Jahresgebühren gibt Apple dafür in der Regel **nicht** aus; die Hoffnung liegt eher bei **vor** der nächsten Zahlung bzw. **vor** erstmaliger kostenpflichtiger Buchung beim passenden Enrollment.

Wenn du willst: Schreib kurz, ob ihr ein **eingetragener Verein / gemeinnützige GmbH / Schule / Behörde** seid und ob die App **kostenlos** bleiben soll ohne kostenpflichtige Inhalte – dann kann man grob einschätzen, ob der Antrag vom **Typ her** zur Apple-Landingpage passt (keine Rechtsberatung, nur strukturell).

