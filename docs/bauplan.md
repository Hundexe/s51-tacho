# Bauplan S51-Digitaltacho (Version 1.5, Stand 01.10.2026)

Dieses Dokument beschreibt, was gebaut wird und warum. Teile stehen in [stueckliste.md](stueckliste.md), die Pins im Code in `firmware/include/pins.h`.

**Referenzfahrzeug:** Simson S51B mit VAPE-Zündung (12 V) und Batterie. Andere S51/S50 mit 12-V-Bordnetz sollten ohne Änderungen passen. Bei 6 V muss die Stromversorgung angepasst werden (Abschnitt 4).

**Änderungen**
- 1.1: Dauerplus mit Wächterschaltung, im Stand bleibt nur die Bewegungserkennung wach.
- 1.2: Alarm gibt einen Ton aus. Entschärfen mit Zündschlüssel, PIN oder NFC-Tag.
- 1.3: Für den Nachbau umgeschrieben, Stückliste in eigene Datei ausgelagert.
- 1.4: Günstiger: Kopftemperatur mit PT1000 am ADS1115 statt Thermoelement und MCP9600. Uhr-Modul entfällt, Uhrzeit kommt von GPS und iPhone. GPS-Modul mit u-blox M8 oder M10. Lagesensor MPU6050 statt LSM6DS3 (günstiger, die Adresse ist ohne Uhr-Modul frei).
- 1.5: Anzeige frei gestaltbar mit dem PC-Programm S51 Designer. Layout-Datei (.s51) und Konfiguration (tacho.cfg) kommen per SD-Karte oder WLAN auf den Tacho.

---

## 1. Entscheidungen auf einen Blick

| Thema | Entscheidung |
|---|---|
| Einbauort | Neue Lampenschale aus ASA (3D-Druck), Original-Einsatz Ø 140 mm vorn, Display hinten schräg zum Fahrer, Querformat |
| Original-Tacho | bleibt am Tachohalter als Zweitanzeige |
| Design | „Klar“ + automatischer Nachtmodus, Warnfarben, Startbild mit eigenem Schriftzug |
| Geschwindigkeit | GPS, Hall-Sensor mit 2 Magneten nachrüstbar |
| Drehzahl | Abgriff am Zündkabel, ohne Eingriff in die VAPE |
| Bedienung | Lenker-Tasterpod mit 3 Tastern, vorbereitet für Spotify |
| Strom | Dauerplus. Im Stand alles stromlos, nur ein passiver Erschütterungsschalter bleibt wach |
| Alarm | Bewegung weckt den Tacho, Lagesensor bestätigt, dann Alarmton über Lautsprecher in der Lampe |
| Entschärfen | Zündschlüssel, PIN (Touch oder Lenkertaster) oder NFC-Tag, Sicherheitsstufe einstellbar |
| Handy | Musiksteuerung über Bluetooth (iPhone und Android). Songtitel ohne Zusatz-App nur mit iPhone |
| Gehäuse | ASA, wasserdichte Stecker, Belüftungsmembran |

---

## 2. Pin-Plan (alle 6 freien GPIOs belegt)

| GPIO | Funktion | Hinweis |
|---|---|---|
| 10 | Power-Hold (Ausgang) | hält die Versorgung an, solange der Tacho läuft oder der Alarm prüft |
| 11 | Hall-Sensor Geschwindigkeit | Interrupt, Zeitmessung zwischen Impulsen (optional) |
| 12 | Drehzahl vom Zündkabel | über Signalaufbereitung, Interrupt |
| 13 | I²C SDA | gemeinsamer Bus für alle Module |
| 14 | I²C SCL | 100 kHz wegen Kabellängen |
| 21 | GPS RX | UART, 10 Hz |

Bereits auf dem Board belegt und genutzt: SD-Karte (Fahrtenbuch), Audio-Verstärker (Alarmton, Warntöne), RS485 (Reserve).

Die komplette Belegung steht im Code in `firmware/include/pins.h`.

### I²C-Bus

| Modul | Adresse | Aufgabe |
|---|---|---|
| MCP23017 | 0x20 | Blinker L/R, Fernlicht, Leerlauf, Zündung an, Licht an, 3 Taster, Reserve |
| BH1750 | 0x23 | Umgebungslicht für automatische Helligkeit |
| PN532 | 0x24 | NFC-Leser zum Entschärfen (optional) |
| ADS1115 | 0x48 | A0 Bordspannung, A1 Zylinderkopftemperatur (PT1000), A2–A3 Reserve |
| MPU6050 | 0x68 | Schräglage, bestätigt beim Alarm echte Bewegung, misst nebenbei die Temperatur in der Lampe |
| BME280 | 0x76 | Außentemperatur, Glättewarnung |

---

## 3. Sensoren im Detail

### 3.1 Geschwindigkeit
- **GPS:** Modul mit u-blox M8 oder M10 (GPS + GLONASS/Galileo, bis 10 Hz), sitzt in der Lampenschale. Liefert auch Uhrzeit und Strecke fürs Fahrtenbuch.
  - Ein NEO-6M funktioniert notfalls auch, empfängt aber nur GPS-Satelliten und schafft höchstens 5 Hz. Die Geschwindigkeit ist damit träger und in Tälern oder zwischen Häusern ungenauer.
- **Hall (nachrüstbar):** Näherungssensor NJK-5002C (M12, NPN, 6–36 V, wasserdicht) an der Gabel, 2 Neodym-Magnete an Nabe oder Bremstrommel. Das Signal läuft über einen Kanal der Optokoppler-Platine an GPIO 11, weil der Sensor mit 12 V arbeitet.
- **Automatische Kalibrierung:** Mit GPS lernt der Tacho den Radumfang selbst.
- Start nur mit GPS, der Original-Tacho bleibt als Rückfallebene.

### 3.2 Drehzahl (VAPE)
- 3–5 Windungen isolierter Draht um das Zündkabel (nicht abisolieren).
- Aufbereitung: Widerstand, Klemmdioden, RC-Filter, Schmitt-Trigger (74HC14, mit 3,3 V versorgt), dann an GPIO 12.
- Software: 1 Impuls = 1 Umdrehung, Totzeit gegen Doppelimpulse, bis ca. 12.000 U/min.
- **Nicht** am weißen Geberkabel zur Zündspule abgreifen.

### 3.3 Kontrollleuchten und Zündung
- 12-V-Signale (Blinker L/R, Fernlicht, Leerlauf, Zündungsplus Kl. 15, Licht an) über eine 8-Kanal-Optokoppler-Platine (PC817, 12 V) auf den MCP23017. Die Ausgangsseite der Platine wird mit 3,3 V versorgt.
- Leerlauf: Die Kontrolllampe schaltet über den Leerlaufschalter nach Masse, der Optokoppler wird passend dazu angeschlossen.

### 3.4 Temperaturen
- **Zylinderkopf:** PT1000-Temperaturfühler (Ersatzteil für 3D-Drucker-Hotends, hält über 400 °C aus).
  - Steckt in einem kleinen Alu-Halter, der unter eine Zylinderkopfmutter geklemmt wird.
  - Ausgewertet über einen Spannungsteiler (Festwiderstand 2,2 kΩ an 3,3 V) am Kanal A1 des ADS1115. Kein eigenes Modul nötig.
  - Gemessen wird am Zylinderkopf statt unter der Zündkerze, die Werte liegen deshalb etwas niedriger. Die Warnschwelle wird bei der ersten Ausfahrt angepasst.
- **Außen:** BME280 in einer belüfteten Kammer an der Unterseite der Lampenschale, weg von der Birne.
- **Gehäuse:** kommt gratis vom eingebauten Temperatursensor des MPU6050.

### 3.5 Bedienung, Musik und iPhone
- **Tasterpod:** 3× IP67-Taster in einer Schelle für den 22-mm-Lenker.
  - Taster 1: kurz Seite wechseln, lang Trip zurücksetzen.
  - Taster 2 und 3: Play/Pause und nächster Titel.
  - Alle drei zusammen: PIN-Eingabe (siehe 4.4).
- **Musiksteuerung:** Der ESP32-S3 meldet sich per Bluetooth LE beim iPhone als Medien-Fernbedienung an.
- **Songtitel:** Das iPhone stellt Titel und Interpret über seine Medien-Schnittstelle (Apple Media Service) bereit. Der Tacho kann sie anzeigen, ohne Zusatz-App. Android bietet diese Schnittstelle nicht, dort bräuchte es eine Begleit-App.

---

## 4. Stromversorgung und Alarm

### 4.1 Prinzip
Der Tacho hängt dauerhaft an der Batterie. Im Stand ist alles stromlos, nur ein passiver Erschütterungsschalter (Federkontakt, braucht selbst keinen Strom) bleibt wach. Ein Board, das nur schläft, würde geschätzt 5–15 mA ziehen und eine kleine Batterie über Wochen leeren, deshalb diese Lösung.

### 4.2 Aufbau

```
Batterie +12 V (Dauerplus)
  └─ Sicherung 2 A
      └─ Verpolschutz (Schottky-Diode) + TVS-Diode (P6KE20A)
          └─ Elektronischer Schalter (P-MOSFET)
               ├─ EIN durch:  Zündungsplus (Kl. 15)
               │          ODER Erschütterungsschalter (kurzer Impuls, über Kondensator verlängert)
               │          ODER Power-Hold (GPIO 10)
               └─ Step-down 12 → 5 V (LM2596HV, auf 5,0 V eingestellt)
                    ├─ WT32-SC01 Plus (über Pin 1 des Erweiterungssteckers)
                    └─ Regler 3,3 V (LD1117V33)
                         └─ alle I²C-Module, GPS, Ausgangsseite der Optokoppler
```

### 4.3 Ablauf

**Fahren**
1. Zündung an: Der Schalter geht an, der Tacho startet und setzt Power-Hold.
2. Je nach Sicherheitsstufe gleich Fahransicht oder erst Entsperren (4.4).
3. Zündung aus: Kilometerstand und Fahrt speichern, Alarm schärfen, Power-Hold freigeben. Alles stromlos.

**Alarm**
1. Jemand bewegt das Moped. Der Erschütterungsschalter schaltet die Versorgung ein.
2. Der Tacho startet ohne Display und erkennt an der fehlenden Zündung, dass der Alarm ihn geweckt hat.
3. Der Lagesensor prüft etwa 2 s, ob sich das Moped wirklich bewegt oder neigt.
4. Echte Bewegung: Alarmton, z. B. 30 s lang, danach erneut scharf.
5. Fehlauslösung: sofort wieder aus. Empfindlichkeit einstellbar, nach mehreren Fehlauslösungen pro Stunde kurze Pause.
6. Jede Auslösung landet im Alarm-Protokoll, mit Uhrzeit, sobald GPS oder iPhone die Zeit geliefert hat.

**Alarmton**
- Über den Audio-Verstärker des Boards (NS4168, 2,5 W an 4 Ω) und einen wasserfesten 4-Ω-Lautsprecher (ca. 40–50 mm) in der Lampenschale.
- Deutlich hörbar in der Nähe, aber keine Sirene. Wenn es lauter sein soll: 12-V-Piezosirene über einen freien MCP23017-Ausgang und einen MOSFET nachrüsten.

### 4.4 Entschärfen und Sicherheitsstufen

| Stufe | Zündung an mit Schlüssel | Entsperren |
|---|---|---|
| 1 Komfort | entschärft sofort | nicht nötig |
| 2 Sicher (Vorschlag) | startet den Tacho, Sperrbildschirm erscheint | innerhalb von 30 s PIN oder NFC-Tag, sonst Alarm |

Warum Stufe 2: Das Zündschloss lässt sich kurzschließen. Wer das tut, kennt die PIN nicht und hat den Tag nicht.

**Entsperr-Wege**
- **PIN am Display:** Ziffernblock auf dem Touchscreen, 4–6 Stellen.
- **PIN per Lenkertaster:** eine Tastenfolge aus den 3 Tastern, z. B. 1-3-3-2. Funktioniert mit Handschuhen und bei Regen.
- **NFC-Tag (optional):** PN532-Leser unsichtbar hinter der Lampenschale, Tag am Schlüsselbund kurz hinhalten.
- Nach 3 falschen PINs: 1 Minute Sperre und Alarmton.

### 4.5 Strombilanz (geschätzt)

| Zustand | Verbrauch |
|---|---|
| Fahrt, volle Helligkeit | ca. 1,2 W, an 12 V gut 100 mA |
| Abgestellt, Alarm scharf | praktisch 0 (Leckstrom des MOSFET) |
| Alarmprüfung | einige Sekunden wie beim Fahren, ohne Display |

---

## 5. Lampenschale

- **Vorn:** Aufnahme für Original-Scheinwerfereinsatz Ø 140 mm und Lampenring.
- **Hinten:** Display-Aufnahme, Querformat, ca. 15–25° nach oben geneigt, Glasfront mit TPU- oder Silikondichtung.
- **Oben:** kleine Sonnenblende, mitgedruckt.
- **Innen:**
  - Hitzeschild (Alu-Blech) zwischen Birne und Elektronik
  - Platz für Platine, GPS, Module und gegebenenfalls vorhandene Kabelverbindungen
  - Lautsprecher mit Öffnung nach unten (Wasser läuft ab)
  - Erschütterungsschalter fest verschraubt
  - NFC-Leser direkt hinter einer dünnen Wandstelle (optional)
  - Belüftungsmembran gegen Beschlagen
- **Unten:** zwei wasserdichte Stecker (z. B. Deutsch DT oder Superseal) plus eine Kabelverschraubung für die Leitung des Temperaturfühlers.
- **Befestigung:** an den originalen Lampenhaltern der Gabel.
- **Fenster:** für den Lichtsensor neben dem Display.
- **Material:** ASA, Wandstärke ≥ 3 mm, 4–5 Perimeter.

**Noch zu erfassen, bevor die Schale konstruiert wird:** Fotos der Lampe von hinten und von der Seite, Fotos der Halterung an der Gabel, Abstand der Befestigungspunkte, Tiefe des Einsatzes, und ob in der Lampe Kabelverbindungen sitzen.

---

## 6. Software

- **Basis:** PlatformIO mit Arduino-Framework, LovyanGFX als Display-Treiber.
- **Anzeige frei gestaltbar:** Die Fahrseiten entstehen am PC im [S51 Designer](../designer/README.md). Elemente wie Werte, Balken, Rundinstrumente und Kontrollleuchten lassen sich frei platzieren. Der Tacho zeichnet die Seiten aus der Layout-Datei ([dateiformat-layout.md](dateiformat-layout.md)). Menüs (Einstellungen, PIN-Eingabe, Alarm, Übertragung) sind fest eingebaut.
- **Einstellungen** stehen in der Textdatei `tacho.cfg` ([konfiguration.md](konfiguration.md)). PIN und NFC-Tags liegen nur im internen Speicher.
- **Übertragung:** Layout und Einstellungen per SD-Karte (Ordner `s51`) oder per WLAN vom Designer ([uebertragung.md](uebertragung.md)).
- **Startmodus:** Zuerst wird geprüft, warum der Tacho an ist. Zündung → Entsperren oder Fahransicht. Keine Zündung → Alarmprüfung ohne Display.
- **Tasks:** Sensoren (Interrupts, GPS, I²C mit 20 Hz), Oberfläche (30 fps), Speicher und Fahrtenbuch, Bluetooth.
- **Speicher:** 16 MB Flash mit zwei App-Bereichen für Updates per WLAN, dazu Dateisystem für Einstellungen.
- **Uhrzeit:** Es gibt kein eigenes Uhr-Modul. Die Zeit kommt vom GPS, sobald es Satelliten empfängt, oder vom iPhone, sobald es per Bluetooth verbunden ist (iOS stellt die Uhrzeit für verbundene Geräte bereit). Bis dahin zeigt die Uhr „--:--“.
- **Kilometerstand:** im NVS mit Verschleißausgleich, alle 100 m und beim Abschalten.
- **Seiten aus dem Layout:** Das mitgelieferte Layout „Klar“ hat die Seiten Fahrt, Statistik und eine Nachtversion der Fahrseite. Beliebige weitere Seiten lassen sich im Designer anlegen.
- **Fest eingebaute Menüs:**
  - Wartung: Erinnerungen bestätigen
  - Alarm: scharf/aus, PIN ändern, NFC-Tag anlernen, Protokoll
  - Einstellungen: Gänge anlernen, Hinweise zur tacho.cfg anzeigen
  - Übertragung: WLAN für Designer und Firmware-Updates einschalten, Code anzeigen
- **Warnfarben:** Schwellen je Element im Layout, Grenzwerte für Warnungen in der tacho.cfg.
- **WLAN:** nur im Stand und nur, solange das Menü Übertragung offen ist.

---

## 7. Teile

Alle Teile mit Menge, Zweck und Hinweisen stehen in [stueckliste.md](stueckliste.md).

---

## 8. Phasen

1. **Display am Schreibtisch:** Demo-Fahransicht, Touch-Test (Code liegt in `firmware/`).
2. **Oberfläche:** Layout-Datei von SD-Karte laden und zeichnen, Startbild, Nachtmodus, Menüs, Sperrbildschirm mit PIN. Designer am PC, Dateiformate und Decoder sind schon fertig.
3. **I²C-Module am Tisch:** Lage, Außentemperatur, Licht, Spannung, Kopftemperatur, Eingänge.
4. **GPS und Drehzahl:** Drehzahl-Impulse simuliert mit einem zweiten Mikrocontroller.
5. **Stromversorgung und Alarm:** Schutz-, Selbsthaltungs- und Wächterschaltung, Ruhestrom messen, Alarmton.
6. **Provisorischer Einbau:** Probefahrten, Kalibrierung, Gänge anlernen, Alarm-Empfindlichkeit.
7. **Lampenschale:** konstruieren, drucken, abdichten, endgültiger Einbau.
8. **Extras:** Wartung, Fahrtenbuch, WLAN-Updates, iPhone-Musik, NFC, Hall-Sensor.

---

## 9. Offene Punkte

- [ ] Fotos und Maße von Lampe und Gabelhalterung, Kabelverbindungen in der Lampe?
- [ ] Sicherheitsstufe 1 oder 2 als Standard?
- [ ] Hall gleich mit einbauen oder erst nur GPS?

## Herkunft einzelner Entscheidungen
- I²C-Erweiterung bei Pin-Mangel → umgesetzt (MCP23017 + ADS1115)
- Spotify-Bedienelement → Tasterpod mit 3 Tastern, Musiksteuerung über Bluetooth
- Dauerstrom mit Bewegungsalarm → Wächterschaltung (4.1)
- PIN zum Entsperren → Touch-Ziffernblock und Tastenfolge am Lenker (4.4)
