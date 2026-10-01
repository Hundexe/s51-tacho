# Firmware

PlatformIO-Projekt für das WT32-SC01 Plus (ESP32-S3, 16 MB Flash, 2 MB PSRAM). Pins: `include/pins.h`, Display-Treiber: `include/lgfx_sc01plus.h`.

Aktueller Stand: **Phase 1**, Display- und Touch-Test mit Demo-Werten (siehe [docs/bauplan.md](../docs/bauplan.md)).

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

## Decoder-Test am PC

`hosttest/` enthält ein kleines Programm, das den C++-Decoder (`lib/s51layout`) am PC übersetzt. Die Tests in `designer/tests/test_cpp_decoder.py` vergleichen seine Ausgabe mit dem Python-Decoder.
