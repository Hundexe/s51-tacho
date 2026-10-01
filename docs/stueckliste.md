# Stückliste

Alles, was für den Nachbau gekauft werden muss. Die Spalte „Phase“ sagt, ab wann das Teil gebraucht wird (siehe Abschnitt 8 in [bauplan.md](bauplan.md)).

Modul-Bezeichnungen sind die üblichen Namen der fertigen Breakout-Platinen, wie sie bei Elektronikhändlern und Marktplätzen angeboten werden. Wo ein Hersteller genannt ist, funktioniert auch ein gleichwertiges Teil.

**Stand:** Die Schaltungen in Phase 3–5 sind noch nicht aufgebaut und getestet. Bis dahin kann sich diese Liste ändern.

## Hauptteile

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| 1 | WT32-SC01 Plus (ZX3D50CE08S-USRC-4832), Variante mit 16 MB Flash | Display und Rechner | 1 | Datenblatt in `datenblaetter/` |
| 1 | USB-C-Kabel (Daten) | Flashen | 1 | reine Ladekabel funktionieren nicht |

## Sensoren und Module (I²C)

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| 1 | MCP23017-Modul | Ein-/Ausgänge für Kontrollleuchten, Zündung, Taster | 3 | Adresse 0x20 (A0–A2 auf GND) |
| 1 | ADS1115-Modul | Bordspannung messen | 3 | Adresse 0x48 (ADDR auf GND) |
| 1 | MCP9600-Modul | Thermoelement-Wandler für Zylinderkopftemperatur | 3 | Adresse 0x60 |
| 1 | Thermoelement-Ring Typ K, 14 mm | Zylinderkopftemperatur unter der Zündkerze | 3 | Ring passt unter eine Zündkerze mit 14-mm-Gewinde |
| 1 | DS3231-Modul + Knopfzelle CR2032 | Uhr | 3 | Viele Module haben eine Ladeschaltung für LIR2032-Akkus. Mit CR2032 die Lade-Diode oder den Widerstand davor auslöten |
| 1 | LSM6DS3-Modul | Schräglage, Bestätigung beim Alarm | 3 | Adresse 0x6A. Kein MPU6050 nehmen, der kollidiert mit der Uhr (0x68) |
| 1 | BME280-Modul | Außentemperatur | 3 | Adresse 0x76. Ein BMP280 geht auch, misst aber keine Luftfeuchte |
| 1 | BH1750-Modul | Umgebungslicht | 3 | Adresse 0x23 |
| 1 | GPS-Modul mit u-blox M10 und Antenne | Geschwindigkeit, Uhrzeit, Strecke | 4 | 3,3-V-tauglicher UART-Ausgang |

## Eingänge und Signalaufbereitung

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| 1 | Optokoppler-Platine 4- oder 8-Kanal, 12 V, mit PC817 | 12-V-Signale (Blinker, Fernlicht, Leerlauf, Zündung) sicher an den MCP23017 | 3 | Eingangsseite für 12 V ausgelegt |
| 1 | 74LVC1G17 (Schmitt-Trigger) | Drehzahlsignal säubern | 4 | gibt es auch als Adapterplatine |
| – | Widerstände, Dioden (z. B. BAT54S), Kondensatoren | Schutz und Filter für das Drehzahlsignal | 4 | Werte folgen mit dem Schaltplan in `hardware/` |
| 1 m | isolierter Draht, dünn | Abgriff am Zündkabel | 4 | 3–5 Windungen um das Zündkabel |

## Stromversorgung und Alarm

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| 1 | Step-down 12 V → 5 V, Eingang bis mind. 36 V, mind. 1 A | Versorgung | 5 | z. B. Pololu D36V28F5 |
| 1 | Flachsicherung 2 A + fliegender Halter | Absicherung am Dauerplus | 5 | |
| 1 | TVS-Diode SMBJ18A | Schutz vor Spannungsspitzen | 5 | |
| 1 | P-Kanal-MOSFET, mind. 30 V, Logic-Level | Elektronischer Hauptschalter | 5 | genaues Bauteil folgt mit dem Schaltplan |
| – | Kleinteile für Selbsthaltung (NPN-Transistor, Dioden, Widerstände, Kondensator) | Schalter-Logik | 5 | Werte folgen mit dem Schaltplan |
| 3 | Passiver Erschütterungsschalter (Federkontakt, z. B. SW-18010P) | weckt den Tacho bei Bewegung | 5 | mehrere Empfindlichkeiten testen |
| 1 | Lautsprecher 4 Ω, 2–3 W, ca. 40–50 mm, wasserfest | Alarm- und Warntöne | 5 | an den Lautsprecher-Stecker des Boards (MX1.25, 2-polig) |

## Bedienung

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| 3 | Drucktaster IP67, Ø 12 mm, Schließer | Tasterpod am Lenker | 3 | |
| 1 | Kabel 4-adrig, ca. 1 m | Tasterpod zur Lampe | 3 | |

## Gehäuse und Verkabelung

| Menge | Teil | Zweck | Phase | Hinweis |
|---|---|---|---|---|
| ca. 300 g | ASA-Filament | Lampenschale, Tasterpod | 7 | Drucker mit geschlossenem Bauraum empfohlen |
| ca. 50 g | TPU-Filament | Dichtungen | 7 | |
| 2 | Wasserdichter Steckverbinder 8–12-polig (z. B. Deutsch DT oder Superseal) | Bordnetz und Sensoren | 6 | |
| 1 | Kabelverschraubung M12 | Thermoelement-Leitung | 6 | |
| 1 | Belüftungsmembran (M12 oder zum Einkleben) | gegen Beschlagen | 7 | |
| 1 | Alu-Blech ca. 0,5–1 mm | Hitzeschild zwischen Birne und Elektronik | 7 | |
| – | Fahrzeugleitung 0,5 mm², Schrumpfschlauch, Lochrasterplatine | Aufbau | 3–6 | |
| 1 | Original-Scheinwerfereinsatz Ø 140 mm + Lampenring | wird in die neue Schale übernommen | 7 | vorhanden am Fahrzeug |

## Optional

| Menge | Teil | Zweck | Hinweis |
|---|---|---|---|
| 1 | PN532-NFC-Modul (I²C-Modus) + NFC-Tag (z. B. NTAG215) | Entschärfen per Tag | Adresse 0x24 |
| 1 | Näherungssensor NJK-5002C (M12, NPN, 6–36 V) + 2 Neodym-Magnete | Geschwindigkeit am Vorderrad | ohne Hall läuft die Geschwindigkeit über GPS |
| 1 | 12-V-Piezosirene | lauterer Alarm | über MOSFET an freien MCP23017-Ausgang |

## Werkzeug

- Lötkolben, Multimeter (auch zum Messen des Ruhestroms in Phase 5)
- 3D-Drucker, der ASA drucken kann
- PC mit VS Code und PlatformIO
