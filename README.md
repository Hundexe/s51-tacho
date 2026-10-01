# S51-Tacho

Digitaltacho für Simson S51 mit 12-V-Bordnetz auf Basis des **WT32-SC01 Plus** (ESP32-S3, 3,5" Touch-Display 480 × 320). Das Display sitzt in einer selbst gedruckten Lampenschale hinter dem Original-Scheinwerfereinsatz. Der Original-Tacho kann als Zweitanzeige dran bleiben.

Referenzfahrzeug: Simson S51B mit VAPE-Zündung (12 V) und Batterie.

> **Projekt in Entwicklung.** Was schon getestet ist, steht unten in der Statustabelle. Alles andere ist geplant, aber noch nicht nachgebaut.

## Funktionen

- Geschwindigkeit per GPS, Hall-Sensor am Vorderrad nachrüstbar
- Drehzahl vom Zündkabel, Gangberechnung, Schaltblitz
- Kontrollleuchten: Blinker, Fernlicht, Leerlauf
- Zylinderkopf- und Außentemperatur, Bordspannung, Schräglage
- Trip, Max, Durchschnitt, Fahrzeit, Tank-Kilometer, Wartungserinnerung
- Anzeige frei gestaltbar mit dem PC-Programm [S51 Designer](designer/README.md), Übertragung per SD-Karte oder WLAN
- Fahrtenbuch auf SD-Karte, Updates per WLAN
- Musiksteuerung per Bluetooth, Songtitel vom iPhone
- Bewegungsalarm mit Alarmton, entsperren per Zündschlüssel, PIN oder NFC-Tag
- Im Stand praktisch kein Ruhestrom

## Stand

| Phase | Inhalt | Status |
|---|---|---|
| 1 | Display-Test mit Demo-Daten | **Auf echtem WT32-SC01 Plus getestet:** Firmware 0.1.0 läuft, Display und Touch funktionieren. Geflasht mit der Release-Datei über esptool-js im Browser |
| 2 | Oberfläche | Firmware 0.4.0 zeigt Layouts von der SD-Karte mit Startbild, Seitenwechsel, Design-Auswahl (lange drücken) und geglätteten Rundinstrumenten, **auf dem Display getestet**. Werte noch Demo-Werte, Menüs und PIN offen. Designer 0.6.0 mit neuer Oberfläche im Browserfenster, **unter Windows getestet** |
| 3 | I²C-Module | offen |
| 4 | GPS und Drehzahl | offen |
| 5 | Stromversorgung und Alarm | offen |
| 6 | Provisorischer Einbau | offen |
| 7 | Lampenschale | offen |
| 8 | Extras | offen |

## Nachbauen

1. **Lesen:** [docs/bauplan.md](docs/bauplan.md) erklärt, was gebaut wird und warum.
2. **Teile besorgen:** [docs/stueckliste.md](docs/stueckliste.md). Für Phase 1 reicht das Board und ein USB-C-Datenkabel.
3. **Firmware flashen:** siehe unten.
4. **Elektronik aufbauen:** Schaltpläne in [hardware/](hardware/) (folgen ab Phase 3).
5. **Gehäuse drucken:** Dateien und Druckeinstellungen in [cad/](cad/) (folgen in Phase 7).

### Firmware flashen

**Ohne Programmierumgebung:** fertige Datei aus den Releases (`firmware-v…`) im Browser flashen, Anleitung in [firmware/README.md](firmware/README.md).

**Selbst bauen:** Voraussetzung [VS Code](https://code.visualstudio.com/) mit der Erweiterung **PlatformIO IDE**. Alle Bibliotheken lädt PlatformIO beim ersten Bauen selbst, in den Versionen aus `firmware/platformio.ini`.

1. Repo herunterladen und den Ordner `firmware/` in VS Code öffnen.
2. Board per USB-C an den PC anschließen.
3. In der PlatformIO-Leiste unten auf **Upload** (Pfeil nach rechts) klicken, oder im Terminal:
   ```
   pio run -t upload
   pio device monitor
   ```

**Board lässt sich nicht flashen:** Am Debug-Stecker (7-polig, MX1.25) Pin 6 (BOOT/GPIO 0) mit Pin 7 (GND) verbinden, Reset-Taste drücken, Verbindung lösen, erneut hochladen.

**Farben sehen falsch aus:** In `firmware/include/lgfx_sc01plus.h` den Wert `invert` oder `rgb_order` umstellen.

### Anzeige gestalten

Mit dem [S51 Designer](designer/README.md) am PC (Python ohne Zusatzpakete, Oberfläche im Fenster von Edge oder Chrome). Formate und Übertragung:
- [docs/dateiformat-layout.md](docs/dateiformat-layout.md): Layout-Datei `.s51`
- [docs/konfiguration.md](docs/konfiguration.md): Einstellungen `tacho.cfg`
- [docs/uebertragung.md](docs/uebertragung.md): Übertragung per WLAN

### Was Phase 1 zeigt

Die Fahransicht mit Demo-Werten: Geschwindigkeit steigt von 0 auf 60 km/h, Drehzahl und Gang laufen mit, der linke Blinker blinkt. Tippen auf das Display zeigt einen roten Punkt und die Koordinaten. Ausgabe im seriellen Monitor: „S51-Tacho Phase 1 gestartet“.

## Ordner

| Ordner | Inhalt |
|---|---|
| `docs/` | Bauplan, Stückliste, Dateiformate, Übertragung, Links zu Datenblättern |
| `designer/` | PC-Programm S51 Designer (Python) |
| `firmware/` | PlatformIO-Projekt für das SC01 Plus |
| `hardware/` | Schaltpläne und Verdrahtung |
| `cad/` | Lampenschale, Tasterpod, Halter |

## Lizenz

Firmware und Designer unter MIT, Doku, Schaltpläne und CAD unter CC BY-SA 4.0. Details in [LICENSE.md](LICENSE.md).

## Rechtliches

Ein Tacho darf nie weniger anzeigen als die tatsächliche Geschwindigkeit. Ob der Umbau die Betriebserlaubnis des Fahrzeugs berührt, muss jeder Nachbauer selbst klären. Den Original-Tacho dran zu lassen ist der einfachste Weg, auf der sicheren Seite zu bleiben.
