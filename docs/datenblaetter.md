# Datenblätter

Datenblätter von Herstellern liegen nicht im Repo, weil sie nicht unter der Lizenz dieses Projekts stehen. Hier sind die Quellen.

## WT32-SC01 Plus (ZX3D50CE08S-USRC-4832)

Das Board wird unter zwei Namen verkauft: als **SC01 Plus** von Smart Panlee und als **WT32-SC01 Plus** von Wireless-Tag. Es ist dieselbe Hardware.

- Produktseite Smart Panlee: http://en.smartpanle.com/product-item-15.html
- Produktseite Wireless-Tag: https://en.wireless-tag.com/product-item-26.html
- Datenblatt (PDF, Smart Panlee): https://img03.71360.com/w3/4e1e0o/20241022/49b7bc08380acfd89eda802ed27ace56.pdf?dl=1&dlf=ZX3D50CE08S-USRC-4832.pdf
- Datenblatt V1.9 (PDF, Wireless-Tag): https://img01.71360.com/w3/77q677/20241031/bf724a7a164740edb1896e09c5ea50d5.pdf?dl=1&dlf=WT32-SC01+PLUS%28ZX3D50CE08S-USRC-4832%29Datasheet-V1.9+EN.pdf

Falls die Links nicht mehr gehen: nach „ZX3D50CE08S-USRC-4832 Datasheet“ suchen.

### Die wichtigsten Daten daraus

Damit der Nachbau auch ohne Datenblatt funktioniert, hier das Wesentliche. Die vollständige Pinbelegung steht in `firmware/include/pins.h`.

| Eigenschaft | Wert |
|---|---|
| Modul | ESP32-S3 (WT32-S3-WROVER-N16R2: 16 MB Flash, 2 MB PSRAM) |
| Display | 3,5", 480 × 320, Treiber ST7796, 8-Bit-Parallel (i80), RGB565 |
| Touch | kapazitiv, FT6336U, I²C Adresse 0x38, Single-Touch |
| Audio | I²S-Verstärker, 2,5 W an 4 Ω |
| SD-Karte | über SPI |
| RS485 | mit Flusssteuerung |
| Versorgung | 4,7–5,5 V, typisch 175 mA bei voller Helligkeit (max. 190 mA) |
| Erweiterungsstecker | 8-polig MX1.25: +5 V, GND, GPIO 10, 11, 12, 13, 14, 21 (3,3-V-Pegel) |
| Debug-Stecker | 7-polig MX1.25: +5 V, +3,3 V, TX, RX, EN, BOOT (GPIO 0), GND |
| Lautsprecher-Stecker | 2-polig MX1.25 |
| RS485-Stecker | 4-polig MX1.25: A, B, GND, +5 V |
| Rahmenmaße | ca. 92 × 60 mm, Tiefe ca. 11 mm ohne Stecker |

## Weitere Teile

Links zu den Datenblättern der Sensoren und Module kommen hier dazu, sobald die Schaltpläne in `hardware/` entstehen.
