# Stückliste und Einkaufsliste

Alles, was für den kompletten Nachbau gekauft werden muss, inklusive Stecker, Kabel, Schrauben und Werkzeug. Zu jedem Teil steht, wofür genau es gebraucht wird, und ein Suchbegriff für AliExpress. Dort ist alles aus dieser Liste erhältlich, die Suche funktioniert auf Englisch am besten.

**So liest man die Liste**
- **Phase** sagt, ab wann ein Teil gebraucht wird (Abschnitt 8 in [bauplan.md](bauplan.md)). Wer schrittweise baut, bestellt zuerst Phase 1–4.
- Angebote auf AliExpress wechseln oft, deshalb stehen hier Suchbegriffe statt Links. Beim Kauf auf die genannten Eckdaten achten (Spannung, Polzahl, Maße).
- Billige Module schwanken in der Qualität. Bei Teilen unter ein paar Euro lohnt es sich, gleich 2 Stück zu nehmen.
- Kabelquerschnitte werden dort meist in AWG angegeben: 0,75 mm² ≈ 18 AWG, 0,5 mm² ≈ 20 AWG, 0,25 mm² ≈ 24 AWG.

**Stand:** Die Schaltungen ab Phase 3 sind geplant, aber noch nicht aufgebaut. Einzelne Teile können sich noch ändern, Änderungen stehen dann in der Git-Historie dieser Datei.

---

## 1. Rechner und Display

- [ ] **1× WT32-SC01 Plus**, Variante mit 16 MB Flash (N16R2) · Phase 1
  Das Herz des Tachos: Display mit Touch, ESP32-S3-Prozessor, Lautsprecher-Verstärker und SD-Kartenslot auf einer Platine. Hier läuft die gesamte Software.
  Suche: `WT32-SC01 Plus ESP32-S3 3.5 inch`
- [ ] **1× USB-C-Datenkabel** · Phase 1
  Zum Aufspielen der Software vom PC. Muss Daten übertragen können, reine Ladekabel gehen nicht.
  Suche: `USB C data cable 1m`
- [ ] **1× microSD-Karte 8–32 GB** · Phase 8
  Speichert das Fahrtenbuch (jede Fahrt als Datei, mit GPS-Strecke). Wird FAT32 formatiert.
  Suche: `micro SD card 16GB`

## 2. Kabel für die Stecker am Board

Das Board hat Stecker im Raster 1,25 mm (Molex PicoBlade, oft „MX1.25“ genannt). **Nicht** mit JST-GH oder JST-SH verwechseln, die passen nicht. Fertig gecrimpte Kabel kaufen, das Crimpen der Kontakte ist sehr fummelig.

- [ ] **1× PicoBlade-Kabel 8-polig**, einseitig mit Buchse, 15–20 cm · Phase 3
  Verbindet den Erweiterungsstecker des Boards mit der eigenen Platine. Darüber laufen 5 V Versorgung, Masse und die 6 freien Pins (Drehzahl, Hall, I²C-Bus, GPS, Power-Hold).
  Suche: `Molex 1.25mm 8 pin cable single head`
- [ ] **1× PicoBlade-Kabel 2-polig**, einseitig mit Buchse · Phase 5
  Schließt den Lautsprecher für den Alarmton an den Lautsprecher-Stecker des Boards an.
  Suche: `Molex 1.25mm 2 pin cable single head`
- [ ] **1× PicoBlade-Kabel 7-polig**, einseitig mit Buchse · optional
  Nur nötig, falls sich das Board per USB-C nicht flashen lässt. Damit wird BOOT (Pin 6) auf Masse gelegt.
  Suche: `Molex 1.25mm 7 pin cable single head`

## 3. Sensoren und Module

Alle Module werden mit **3,3 V** betrieben (Regler in Abschnitt 5.3). So kommt nie ein 5-V-Pegel an die Pins des ESP32, die das nicht vertragen.

- [ ] **1× MCP23017-Modul** · Phase 3
  Port-Erweiterung mit 16 Ein-/Ausgängen über I²C. Liest Blinker, Fernlicht, Leerlauf, Zündung, Licht und die drei Lenkertaster ein, weil das Board selbst nur 6 freie Pins hat.
  Suche: `MCP23017 I2C module`
- [ ] **1× ADS1115-Modul** · Phase 3
  Präziser Analog-Digital-Wandler mit 4 Eingängen. Misst die Bordspannung (A0), um vor Problemen mit Laderegler oder Batterie zu warnen, und die Zylinderkopftemperatur über den PT1000 (A1).
  Suche: `ADS1115 module`
- [ ] **1× PT1000-Temperaturfühler für 3D-Drucker**, Patrone Ø 3 mm, Leitung ca. 1 m · Phase 3
  Misst die Zylinderkopftemperatur und warnt, bevor der Zweitakter zu heiß wird und klemmt. Hält über 400 °C aus. Steckt in einem kleinen Halter aus Alu-Blech (Abschnitt 10), der unter eine Zylinderkopfmutter geklemmt wird. Bis zur Lampe wird die Leitung mit normaler Litze verlängert, das verfälscht den Messwert nicht.
  Suche: `PT1000 3D printer thermistor cartridge`
  Prüfen: PT1000, nicht PT100 und nicht NTC 100K.
- [ ] **1× MPU6050-Modul (GY-521)** · Phase 3
  Lagesensor. Zeigt beim Fahren die Schräglage an, prüft beim Alarm, ob sich das Moped wirklich bewegt, und misst nebenbei die Temperatur in der Lampe.
  Suche: `GY-521 MPU6050`
- [ ] **1× BME280-Modul, 3,3-V-Ausführung** · Phase 3
  Misst die Außentemperatur für die Anzeige und die Glättewarnung unter 3 °C.
  Suche: `BME280 module 3.3V`
- [ ] **1× BH1750-Modul (GY-302)** · Phase 3
  Lichtsensor. Regelt die Displayhelligkeit automatisch und schaltet bei Dunkelheit in den Nachtmodus.
  Suche: `BH1750 GY-302`
- [ ] **1× GPS-Modul mit u-blox M8 oder M10**, UART, 3,3 V, mit Antenne · Phase 4
  Liefert die Geschwindigkeit, die Uhrzeit und die Strecke fürs Fahrtenbuch. Ein eigenes Uhr-Modul gibt es nicht, die Zeit kommt von hier oder vom iPhone. Mit Pufferbatterie oder Supercap findet es nach dem Einschalten schneller Satelliten.
  Suche: `BN-220 GPS` oder `u-blox M10 GPS module`
  Prüfen: u-blox M8 oder M10 (empfängt mehrere Satellitensysteme, bis 10 Hz). Ein NEO-6M geht notfalls, empfängt aber nur GPS und schafft höchstens 5 Hz, die Geschwindigkeit wird damit träger.

## 4. Eingänge vom Moped

- [ ] **1× Optokoppler-Platine, 8 Kanäle, Eingang 12 V, mit PC817** · Phase 3
  Trennt das 12-V-Bordnetz elektrisch vom empfindlichen 3,3-V-Teil. Spitzen und Störungen vom Moped kommen so nicht bis zum Board. Kanäle: Blinker links, Blinker rechts, Fernlicht, Leerlauf, Zündung, Licht an, Hall-Sensor, 1 Reserve. Die Ausgangsseite wird mit 3,3 V versorgt.
  Suche: `8 channel optocoupler isolation board 12V PC817`
- [ ] **1× 74HC14 (DIP-14) und 1× IC-Sockel DIP-14** · Phase 4
  Schmitt-Trigger. Macht aus dem unsauberen Signal vom Zündkabel saubere Rechteck-Impulse, die der ESP32 zählen kann. Der Sockel erlaubt einen einfachen Tausch.
  Suche: `74HC14 DIP` und `DIP 14 IC socket`
- [ ] **2 m isolierter Draht 0,25 mm²** · Phase 4
  Wird 3–5 Mal um das Zündkabel gewickelt. Nimmt dort ohne Eingriff in die Zündung das Drehzahl-Signal ab.
  Suche: `24AWG silicone wire`
- [ ] **1,5 m abgeschirmtes Kabel, 1 Ader + Schirm** · Phase 4
  Führt das Drehzahl-Signal vom Zündkabel zur Lampe. Der Schirm verhindert, dass die Zündung andere Leitungen stört.
  Suche: `shielded cable 1 core microphone`

## 5. Stromversorgung und Alarm

### 5.1 Anschluss an die Batterie
- [ ] **1× Flachsicherungshalter (Mini), wasserdicht, fliegend** · Phase 5
  Sitzt direkt nach der Batterie im Dauerplus. Brennt bei einem Kurzschluss durch, bevor Kabel heiß werden.
  Suche: `mini blade fuse holder waterproof inline`
- [ ] **3× Mini-Flachsicherung 2 A** · Phase 5
  Eine für den Halter, zwei als Ersatz unterwegs.
  Suche: `mini blade fuse 2A`
- [ ] **2× Ringkabelschuh, isoliert**, passend zur Batterieschraube (meist M5 oder M6) · Phase 5
  Schraubt Plus und Masse sauber an die Batteriepole.
  Suche: `insulated ring terminal M6 18AWG`

### 5.2 Schutz, Hauptschalter und Wächter
- [ ] **1× Schottky-Diode SS34 oder 1N5822** · Phase 5
  Verpolschutz. Wird Plus und Minus vertauscht angeschlossen, sperrt sie und nichts geht kaputt.
  Suche: `1N5822 diode`
- [ ] **1× TVS-Diode P6KE20A** · Phase 5
  Fängt kurze Spannungsspitzen aus dem Bordnetz ab, z. B. beim Abschalten von Licht oder Hupe.
  Suche: `P6KE20A TVS diode`
- [ ] **1× P-Kanal-MOSFET IRF4905 (TO-220)** · Phase 5
  Elektronischer Hauptschalter. Trennt im Stand die komplette Elektronik von der Batterie, damit sie nicht leergezogen wird.
  Suche: `IRF4905 TO-220`
- [ ] **2× NPN-Transistor BC547 (oder BC337)** · Phase 5
  Steuern den Hauptschalter an: Er geht an durch Zündung, durch den Erschütterungsschalter oder durch den ESP32 selbst (Power-Hold).
  Suche: `BC547 transistor`
- [ ] **3× Erschütterungsschalter SW-18010P** · Phase 5
  Ein kleiner Federkontakt, der bei Bewegung kurz schließt und dabei selbst keinen Strom braucht. Weckt im Stand den Tacho für die Alarmprüfung. Drei Stück, um die passende Empfindlichkeit auszuprobieren.
  Suche: `SW-18010P vibration switch`

### 5.3 Spannungswandler
- [ ] **1× Step-down-Wandler LM2596HV** (Eingang bis 60 V) · Phase 5
  Macht aus den 12–14,4 V des Bordnetzes die 5 V für das Board. Die HV-Version hält auch Spannungsspitzen aus. **Vor dem ersten Anschließen** am Poti genau auf 5,0 V einstellen und mit dem Multimeter prüfen.
  Suche: `LM2596HV step down module`
- [ ] **1× Spannungsregler LD1117V33 (TO-220)** · Phase 3
  Macht aus 5 V saubere 3,3 V für alle Sensoren und Module.
  Suche: `LD1117V33`
- [ ] **2× Elko 10 µF / 25 V** · Phase 3
  Gehören an Ein- und Ausgang des 3,3-V-Reglers, damit er stabil läuft. Sind auch im Elko-Sortiment (Abschnitt 9) enthalten.

### 5.4 Alarmton
- [ ] **1× Lautsprecher 4 Ω, 2–3 W, Ø 40–50 mm, wasserfest** · Phase 5
  Gibt Alarmton und Warntöne aus. Wird an den Lautsprecher-Stecker des Boards angeschlossen.
  Suche: `waterproof speaker 40mm 4 ohm 3W`

## 6. Bedienung

- [ ] **3× Drucktaster IP67, Ø 12 mm, Schließer** · Phase 3
  Sitzen im Tasterpod am Lenker. Taster 1: Seite wechseln und Trip zurücksetzen. Taster 2 und 3: Musik (Play/Pause, nächster Titel). Alle drei zusammen: PIN eingeben. Funktionieren auch mit Handschuhen.
  Suche: `12mm waterproof metal push button momentary`
- [ ] **1,5 m Steuerleitung 4 × 0,25 mm², ölbeständig** · Phase 3
  Verbindet den Tasterpod mit der Lampe (3 Taster + gemeinsame Masse).
  Suche: `4 core cable 24AWG PVC`

## 7. Wasserdichte Stecker an der Lampenschale

Alles, was vom Moped in die Lampe geht, läuft über Steckverbindungen. Dann lässt sich die Lampe zum Arbeiten abnehmen. Sätze mit fertig angecrimpten Kabeln („Pigtail“) kaufen, dann braucht es keine Spezialzange.

- [ ] **1× Deutsch DT 8-polig, Stecker + Buchse mit Kabeln** · Phase 6
  Bordnetz-Stecker: Dauerplus, Masse, Zündung, Blinker links, Blinker rechts, Fernlicht, Leerlauf, Licht.
  Suche: `Deutsch DT 8 pin connector with wire`
- [ ] **1× Deutsch DT 6-polig, Stecker + Buchse mit Kabeln** · Phase 6
  Sensor-Stecker: Hall-Sensor (3 Adern), Drehzahl (Signal + Schirm), 1 Reserve.
  Suche: `Deutsch DT 6 pin connector with wire`
- [ ] **1× Deutsch DT 4-polig, Stecker + Buchse mit Kabeln** · Phase 6
  Tasterpod-Stecker.
  Suche: `Deutsch DT 4 pin connector with wire`
- [ ] **1× Kabelverschraubung M12 × 1,5, IP68**, für Kabel-Ø 3–6 mm · Phase 7
  Führt die Leitung des Temperaturfühlers dicht ins Gehäuse.
  Suche: `cable gland M12 IP68`
- [ ] **1× Kabelverschraubung M16 × 1,5, IP68** · Phase 7
  Führt das vorhandene Scheinwerfer-Kabel dicht in die neue Lampenschale.
  Suche: `cable gland M16 IP68`

## 8. Kabel und Verbindungen am Moped

- [ ] **Fahrzeugleitung 0,75 mm² (18 AWG): je 5 m rot und schwarz** · Phase 5
  Dauerplus und Masse von der Batterie zur Lampe.
  Suche: `18AWG automotive wire`
- [ ] **Fahrzeugleitung 0,5 mm² (20 AWG): je 3 m in 4 Farben** · Phase 6
  Signalleitungen von Blinker, Fernlicht, Leerlauf, Zündung und Licht zum Bordnetz-Stecker.
  Suche: `20AWG automotive wire`
- [ ] **Silikonlitze 0,25 mm² (24 AWG): 5 Farben** · Phase 3
  Verdrahtung innerhalb der Lampe zwischen Platine und Modulen. Silikon bleibt auch bei Hitze und Vibration flexibel.
  Suche: `24AWG silicone wire kit`
- [ ] **10× Lötverbinder mit Schrumpfschlauch („Solder Seal“)** · Phase 6
  Zapfen die Signale sauber und wasserdicht vom Kabelbaum des Mopeds ab. Besser als Stromdiebe, die mit der Zeit korrodieren.
  Suche: `solder seal wire connectors`
- [ ] **Schrumpfschlauch-Sortiment 3:1 mit Kleber** · Phase 3
  Isoliert und dichtet Lötstellen.
  Suche: `heat shrink tube 3:1 adhesive kit`
- [ ] **3 m Wellrohr NW 7–10, geschlitzt** · Phase 6
  Schützt die neuen Kabel am Rahmen vor Scheuern und Hitze.
  Suche: `split corrugated tube 7mm`
- [ ] **1 Rolle Gewebeband (Kabelbaumband)** · Phase 6
  Bündelt die Kabel sauber zum Kabelbaum.
  Suche: `wire harness cloth tape`
- [ ] **Kabelbinder schwarz, UV-beständig, Sortiment** · Phase 6
  Befestigt Kabel und Wellrohr am Rahmen.
  Suche: `UV resistant cable ties black`

## 9. Platine und Kleinteile

- [ ] **2× Lochrasterplatine (Streifenraster) ca. 100 × 80 mm** · Phase 3
  Trägt Stromversorgung, Drehzahl-Aufbereitung und steckbare Module. Eine für Tischtests, eine für den Einbau.
  Suche: `stripboard 10x8cm`
- [ ] **Buchsenleisten 2,54 mm, 3× 40-polig** · Phase 3
  Die Module werden aufgesteckt statt eingelötet, so lassen sie sich einzeln tauschen.
  Suche: `female pin header 2.54 40pin`
- [ ] **Stiftleisten 2,54 mm, 3× 40-polig** · Phase 3
  Für die Module, falls nicht beigelegt, und für Messpunkte.
  Suche: `male pin header 2.54 40pin`
- [ ] **Schraubklemmen Raster 5 mm, je 5× 2- und 3-polig** · Phase 3
  Anschlüsse für die dickeren Kabel auf der Platine.
  Suche: `PCB screw terminal 5mm 2pin 3pin`
- [ ] **Widerstandssortiment 1/4 W (10 Ω–1 MΩ)** · Phase 3
  Für Spannungsteiler (Bordspannung), Pull-ups, Schutz der Eingänge und die Schalter-Logik.
  Suche: `resistor kit 1/4W`
- [ ] **Keramikkondensator-Sortiment (10 pF–100 nF)** · Phase 3
  Entstörung und Filter, z. B. am Drehzahl-Eingang und an jedem IC.
  Suche: `ceramic capacitor kit`
- [ ] **Elko-Sortiment (1–470 µF, mind. 25 V)** · Phase 3
  Glättung der Versorgung und der Zeitkondensator für den Erschütterungsschalter.
  Suche: `electrolytic capacitor kit 25V`
- [ ] **Dioden: 10× 1N4148, 10× 1N4007** · Phase 3
  1N4148 schützen den Drehzahl-Eingang und verknüpfen die Einschalt-Signale. 1N4007 für Schutz in der Versorgung.
  Suche: `1N4148` und `1N4007`
- [ ] **Abstandsbolzen-Sortiment M3 und M2,5** · Phase 7
  Befestigen Platine und Module im Gehäuse, ohne dass Lötstellen aufliegen.
  Suche: `M3 M2.5 nylon standoff kit`

## 10. Gehäuse und Halter (3D-Druck)

- [ ] **1 kg ASA-Filament, schwarz** · Phase 7
  Material für Lampenschale, Tasterpod und Halter. UV- und wetterfest, bleicht nicht aus und hält mehr Wärme aus als PLA oder PETG.
  Suche: `ASA filament 1.75mm black`
- [ ] **250 g TPU-Filament 95A** · Phase 7
  Gummiartige Dichtungen für Displayrahmen und Deckel.
  Suche: `TPU filament 95A 1.75mm`
- [ ] **20× Gewindeeinsätze M3 zum Einschmelzen** · Phase 7
  Werden mit dem Lötkolben ins Druckteil gedrückt. Ergeben stabile Metallgewinde, die oft geöffnet werden können.
  Suche: `M3 heat set insert`
- [ ] **Edelstahl-Schrauben M3: je 10× 8, 12, 16 mm** · Phase 7
  Gehäuse, Deckel, Lenkerschelle und Befestigung an den Lampenhaltern der Gabel.
  Suche: `M3 stainless button head screw kit`
- [ ] **4× Schrauben M2 × 6 mm, Edelstahl** · Phase 7
  Halten das Display im Gehäuse (Befestigungslöcher Ø 2,3 mm am Displayrahmen).
  Suche: `M2 stainless screw kit`
- [ ] **1× Druckausgleichselement M12 × 1,5** · Phase 7
  Lässt Luft, aber kein Wasser durch. Verhindert, dass das Display von innen beschlägt, wenn sich das Gehäuse erwärmt und abkühlt.
  Suche: `M12 breather vent waterproof`
- [ ] **1× Alu-Blech 0,5–1 mm, ca. 100 × 100 mm** · Phase 7
  Hitzeschild zwischen Scheinwerferbirne und Elektronik. Ein Streifen davon wird zum Halter für den PT1000 am Zylinderkopf gebogen.
  Suche: `aluminum sheet 1mm 100x100`
- [ ] **1× Doppelseitiges Klebeband, Typ VHB** · Phase 7
  Hält GPS-Antenne und Lautsprecher vibrationsfest im Gehäuse.
  Suche: `VHB double sided tape`
- [ ] **1× Neutralvernetzendes Silikon, transparent** · Phase 7
  Dichtet Kabelführungen und Fugen ab. „Neutralvernetzend“, weil saures Silikon Elektronik angreift.
  Suche: `neutral cure silicone sealant`
- [ ] **1× Moosgummi 2 mm, selbstklebend** · Phase 7
  Zwischen Tasterpod-Schelle und Lenker, damit nichts verrutscht oder klappert.
  Suche: `EVA foam sheet 2mm adhesive`

Vom Moped übernommen, nicht neu kaufen: Scheinwerfereinsatz Ø 140 mm mit Lampenring und Haltefeder.

## 11. Optional

- [ ] **PN532-NFC-Modul (V3) + 2× NFC-Schlüsselanhänger NTAG215**
  Entschärfen des Alarms durch kurzes Hinhalten des Anhängers an die Lampe.
  Suche: `PN532 NFC module V3` und `NTAG215 key fob`
- [ ] **Näherungssensor NJK-5002C** (M12, NPN, Schließer, 6–36 V) **+ 2× Neodym-Magnet 10 × 3 mm + 2K-Epoxidkleber**
  Misst die Geschwindigkeit direkt am Vorderrad, schneller als GPS und auch im Tunnel.
  Suche: `NJK-5002C hall sensor` und `neodymium magnet 10x3mm`
- [ ] **12-V-Piezosirene, wasserfest + 1× N-Kanal-MOSFET IRLZ44N**
  Deutlich lauterer Alarm als der Lautsprecher.
  Suche: `12V piezo siren waterproof` und `IRLZ44N`

## 12. Werkzeug und Hilfsmittel

Wird nicht verbaut, aber gebraucht.

- [ ] **Lötstation und Lötzinn 0,8 mm** · zum Aufbau der Platine
  Suche: `soldering station` und `solder wire 0.8mm`
- [ ] **Multimeter** · Spannungen prüfen, Step-down auf 5,0 V einstellen, Ruhestrom messen
  Suche: `digital multimeter`
- [ ] **Abisolierzange** · Kabel sauber abisolieren
  Suche: `automatic wire stripper`
- [ ] **Seitenschneider** · Kabel und Bauteilbeine kürzen
  Suche: `flush cutter`
- [ ] **Crimpzange für isolierte Kabelschuhe** · Ringkabelschuhe an der Batterie
  Suche: `crimping tool insulated terminals`
- [ ] **Heißluftföhn** · Schrumpfschlauch und Lötverbinder
  Suche: `heat gun`
- [ ] **Steckbrett und Dupont-Kabel-Set** · Tischtests in Phase 3–4, bevor gelötet wird
  Suche: `breadboard 830 jumper wire kit`
- [ ] **12-V-Netzteil mind. 1 A (oder Labornetzteil)** · Tischtests der Stromversorgung in Phase 5
  Suche: `12V 2A power adapter`
- [ ] **3D-Drucker mit geschlossenem Bauraum** · ASA verzieht sich ohne geschlossenen Bauraum
- [ ] **PC mit VS Code und PlatformIO** · Software aufspielen
