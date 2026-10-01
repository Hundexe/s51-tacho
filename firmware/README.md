# Firmware

PlatformIO-Projekt für das WT32-SC01 Plus (ESP32-S3, 16 MB Flash, 2 MB PSRAM). Pins: `include/pins.h`, Display-Treiber: `include/lgfx_sc01plus.h`.

Aktueller Stand: **Phase 2**, der Tacho zeigt Layouts aus dem [S51 Designer](../designer/README.md) an. Alle Werte sind noch Demo-Werte (wie in der Vorschau des Designers), Sensoren kommen ab Phase 3. Version 0.1.0 (Display- und Touch-Test) ist auf einem echten WT32-SC01 Plus getestet.

## Bedienung

**Layout und Einstellungen auf die SD-Karte bringen:** microSD-Karte (FAT32, bis 32 GB) am PC einlegen, im Designer *Datei → Auf SD-Karte exportieren* wählen. Das legt den Ordner `s51` mit `design.s51` und `tacho.cfg` an. Karte in den Slot des Displays stecken und den Tacho neu starten.

**Beim Start**
1. `s51/tacho.cfg` wird gelesen. Fehlt sie, gelten die Standardwerte ([docs/konfiguration.md](../docs/konfiguration.md)).
2. Das Layout `s51/<layout_datei>` wird gelesen und im internen Speicher gesichert. Fehlt es oder ist es beschädigt, nimmt der Tacho die interne Kopie, sonst das eingebaute Layout „Klar“.
3. Hat das Layout eine Startbild-Seite, erscheint sie für `startbild_dauer_s` Sekunden, sonst `startbild_text`.
4. Danach die Tagseite aus `startseite`. Unten erscheinen einige Sekunden lang Hinweise, z. B. „Keine SD-Karte“.

**Seite wechseln:** nach links oder rechts wischen oder auf das rechte bzw. linke Drittel tippen. Unten zeigen Punkte kurz, auf welcher Seite man ist.

**Nachtmodus:** `nachtmodus = an` in der `tacho.cfg` zeigt die Nachtversionen der Seiten und nutzt `helligkeit_nacht`. `auto` verhält sich bis Phase 3 wie `aus`.

**Uhrzeit:** zeigt „--:--“, bis GPS oder iPhone die Zeit liefern (Phase 4).

Die serielle Ausgabe (115200 Baud) zeigt, was beim Start gelesen wurde, auch Hinweise zur `tacho.cfg` mit Zeilennummer.

## Flashen ohne PlatformIO

Jeder Release unter **Releases** (Tag `firmware-v…`) enthält zwei Dateien:

| Datei | Inhalt | Adresse |
|---|---|---|
| `s51-tacho-<Version>-komplett.bin` | Bootloader, Partitionstabelle und Programm in einer Datei | `0x0` |
| `s51-tacho-<Version>-app.bin` | nur das Programm, für Updates | `0x10000` |

Am einfachsten im Browser (Chrome oder Edge am PC, Web Serial):

1. Display mit einem USB-C-**Datenkabel** an den PC anschließen. Reine Ladekabel funktionieren nicht.
2. https://espressif.github.io/esptool-js/ öffnen (offizielles Werkzeug von Espressif).
3. Baudrate 921600, auf **Connect** klicken und den Port wählen (Windows: „USB JTAG/serial debug unit“ oder „USB-Serial-Gerät (COMx)“).
4. Unter „Flash Address“ `0x0` eintragen, die Datei `…-komplett.bin` wählen, **Program** klicken.
5. Nach „Leaving…“ das Kabel kurz abziehen und wieder einstecken. Das Display zeigt „S51“ und die Versionsnummer.

Mit esptool auf der Kommandozeile:

```
python -m pip install esptool
python -m esptool --chip esp32s3 write_flash 0x0 s51-tacho-0.1.0-komplett.bin
```

Klappt die Verbindung nicht: anderes USB-C-Kabel oder anderen USB-Anschluss probieren und die Baudrate auf 115200 senken. Erscheint gar kein Port: Am Debug-Stecker (7-polig, MX1.25) Pin 6 (BOOT/GPIO 0) mit Pin 7 (GND) verbinden, Reset-Taste drücken, Verbindung lösen und erneut verbinden.

## Selbst bauen

```
cd firmware
pio run              # bauen
pio run -t upload    # bauen und über USB-C flashen
pio device monitor   # serielle Ausgabe, 115200 Baud
```

Alle Versionen sind in `platformio.ini` fest gepinnt. GitHub baut die Firmware bei jeder Änderung in `firmware/` (`.github/workflows/firmware-release.yml`).

## Neue Version veröffentlichen

1. `FW_VERSION` in `include/version.h` erhöhen.
2. `release-notes/<Version>.md` anlegen.
3. Commit auf `main` hochladen. GitHub baut die Dateien und legt den Release `firmware-v<Version>` an.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `src/main.cpp` | Ablauf: SD-Karte, Konfiguration, Layout laden, Startbild, Seitenwechsel |
| `include/pins.h` | Alle Pins |
| `include/lgfx_sc01plus.h` | Display- und Touch-Einstellungen für LovyanGFX |
| `lib/s51layout/` | Decoder für Layout (`.s51`) und Konfiguration (`tacho.cfg`) |
| `lib/s51render/` | Zeichnet Seiten: Regeln für Werte und Warnfarben (`s51_values`), Schrift (`s51_text`), Elemente (`s51_render`) |
| `data/s51fonts.bin` | Schriften, erzeugt von `tools/gen_fonts.py` aus `fonts/` |
| `data/klar.s51` | Eingebautes Layout, geschrieben von `designer/tools/make_examples.py` |
| `fonts/` | DejaVu-Schriften mit Lizenz |
| `hosttest/` | Programme, die den Code der Firmware am PC laufen lassen |

## Am PC prüfen

Die Bibliotheken in `lib/` laufen auch am PC:

- `designer/tests/test_cpp_decoder.py` vergleicht den Decoder mit dem Python-Decoder des Designers.
- `designer/tests/test_firmware_render.py` vergleicht Werteformat, Warnfarben, Balken und Kontrollleuchten mit den Regeln des Designers und prüft, dass die Schriften alle Zeichen der Vorlagen enthalten.
- `hosttest/compare.py` zeichnet alle Vorlagen mit dem echten Renderer (LovyanGFX am PC, ohne Display) und stellt sie neben die Vorschau des Designers. Ergebnis: [docs/bilder/firmware/](../docs/bilder/firmware/). Braucht g++, git und Pillow:

```
cd firmware
python hosttest/compare.py /tmp/vergleich
```

![Vergleich Klar](../docs/bilder/firmware/klar.png)

## Schriften neu erzeugen

```
cd firmware
python tools/gen_fonts.py
```

Welche Größen und Zeichen enthalten sind, steht oben in `tools/gen_fonts.py`. Bis 22 px gibt es jede Größe, darüber wird aus der nächstgrößeren Schrift heruntergerechnet. Ab 64 px gibt es nur Ziffern und Zahlzeichen (Geschwindigkeit, Gang, Uhrzeit).
