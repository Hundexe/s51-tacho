# S51-Tacho

Digitaltacho für eine Simson S51B (12 V, VAPE-Zündung) auf Basis des **WT32-SC01 Plus** (ESP32-S3, 3,5" Touch-Display 480 × 320). Das Display sitzt in einer selbst gedruckten Lampenschale, der Original-Tacho bleibt als Zweitanzeige.

## Funktionen (geplant)

- Geschwindigkeit per GPS, Hall-Sensor am Vorderrad nachrüstbar
- Drehzahl vom Zündkabel, Gangberechnung, Schaltblitz
- Kontrollleuchten: Blinker, Fernlicht, Leerlauf
- Zylinderkopf- und Außentemperatur, Bordspannung, Schräglage
- Trip, Max, Durchschnitt, Fahrzeit, Tank-Kilometer, Wartungserinnerung
- Fahrtenbuch auf SD-Karte, Updates per WLAN
- Musiksteuerung und Songtitel vom iPhone
- Bewegungsalarm mit Alarmton, entsperren per Schlüssel, PIN oder NFC-Tag
- Im Stand praktisch kein Ruhestrom

Der vollständige Plan steht in [docs/bauplan.md](docs/bauplan.md).

## Ordner

| Ordner | Inhalt |
|---|---|
| `firmware/` | PlatformIO-Projekt für das SC01 Plus |
| `hardware/` | Schaltpläne für Stromversorgung, Eingänge, Drehzahl, Alarm |
| `cad/` | Lampenschale, Tasterpod, Halter |
| `docs/` | Bauplan, Datenblätter |

## Stand

| Phase | Status |
|---|---|
| 1 Display-Test mit Demo-Daten | Code vorhanden, noch nicht auf echter Hardware getestet |
| 2 Oberfläche mit LVGL | offen |
| 3 I²C-Module | offen |
| 4 GPS und Drehzahl | offen |
| 5 Stromversorgung und Alarm | offen |
| 6 Provisorischer Einbau | offen |
| 7 Lampenschale | offen |
| 8 Extras | offen |

## Firmware bauen und flashen

Voraussetzung: [VS Code](https://code.visualstudio.com/) mit der Erweiterung **PlatformIO IDE**.

1. Ordner `firmware/` in VS Code öffnen.
2. Board per USB-C anschließen.
3. In der PlatformIO-Leiste **Upload** klicken, oder im Terminal:
   ```
   pio run -t upload
   pio device monitor
   ```

Falls das Board sich nicht flashen lässt: Am Debug-Stecker Pin 6 (BOOT/GPIO 0) mit Pin 7 (GND) verbinden, Reset drücken, Verbindung lösen und erneut hochladen.

Falls die Farben falsch aussehen: in `firmware/include/lgfx_sc01plus.h` den Wert `invert` oder `rgb_order` umstellen.
