# Dateiformat für Layouts (.s51)

Ein Layout beschreibt, was der Tacho anzeigt: welche Seiten es gibt und welche Elemente wo auf jeder Seite liegen. Layouts entstehen im PC-Programm [S51 Designer](../designer/README.md) und kommen über die SD-Karte oder per WLAN auf den Tacho.

**Formatversion:** 1.2 (1.1 ergänzt Bilder und die Startbild-Seite, 1.2 die Eigenschaft `from_zero`)

**Quellen im Code:**
- Alle Nummern: `designer/s51design/schema.py`. Diese Datei ist die einzige Quelle. Der C++-Header der Firmware wird daraus erzeugt.
- Encoder und Decoder in Python: `designer/s51design/layout_format.py`
- Decoder in C++ (Firmware): `firmware/lib/s51layout/src/s51_layout.cpp`
- Tests, die beide Decoder vergleichen: `designer/tests/`

---

## 1. Überblick

Die Datei ist binär, kompakt und robust gegen beschädigte Karten:

```
+----------------------+
| Kopf (16 Bytes)      |  Kennung "S51L", Version, Displaygröße
+----------------------+
| Abschnitt META       |  Name, Autor, Datum, Programm
+----------------------+
| Abschnitt IMAG       |  Bild 1 (optional, beliebig viele bis 32)
| …                    |
+----------------------+
| Abschnitt SCRN       |  Seite 1 mit ihren Elementen
| Abschnitt SCRN       |  Seite 2 …
| …                    |
+----------------------+
| CRC32 (4 Bytes)      |  Prüfsumme über alles davor
+----------------------+
```

Grundregeln:
- Alle Zahlen sind **Little-Endian** (niedrigstes Byte zuerst), wie im ESP32 und am PC.
- Texte sind **UTF-8**, höchstens 255 Bytes, ohne Nullbyte am Ende.
- Farben sind **3 Bytes R, G, B** (0–255). Die Firmware rechnet sie in das Displayformat RGB565 um.
- Die ganze Datei darf höchstens **1 MiB (1 048 576 Bytes)** groß sein. Bis Version 1.0 waren es 65 536 Bytes.

Typen in den Tabellen: `u8` = 1 Byte ohne Vorzeichen, `u16`/`i16` = 2 Bytes ohne/mit Vorzeichen, `u32` = 4 Bytes ohne Vorzeichen, `f32` = 4 Bytes Gleitkommazahl (IEEE 754).

## 2. Kopf

| Versatz | Größe | Typ | Inhalt |
|---|---|---|---|
| 0 | 4 | Zeichen | Kennung `S51L` |
| 4 | 1 | u8 | Hauptversion, derzeit 1 |
| 5 | 1 | u8 | Unterversion, derzeit 2 |
| 6 | 2 | u16 | Größe des Kopfs in Bytes, derzeit 16. Abschnitte beginnen an diesem Versatz |
| 8 | 2 | u16 | Displaybreite in Pixeln (480) |
| 10 | 2 | u16 | Displayhöhe in Pixeln (320) |
| 12 | 4 | u32 | reserviert, 0 |

## 3. Abschnitte

Nach dem Kopf folgen Abschnitte bis 4 Bytes vor Dateiende. Jeder Abschnitt:

| Größe | Typ | Inhalt |
|---|---|---|
| 4 | Zeichen | Art des Abschnitts, z. B. `META` |
| 4 | u32 | Länge der Nutzdaten in Bytes |
| Länge | Bytes | Nutzdaten |

Unbekannte Abschnitte werden übersprungen. So können spätere Versionen neue Abschnitte ergänzen, ohne dass ältere Firmware die Datei ablehnt. Die Reihenfolge der Abschnitte ist beliebig. Der Designer schreibt META, dann alle IMAG, dann alle SCRN.

### 3.1 META: Angaben zur Datei

Liste von Einträgen im Format **Nummer (u8), Länge (u8), Daten**:

| Nummer | Daten | Inhalt |
|---|---|---|
| 1 | Text | Name des Layouts |
| 2 | Text | Autor |
| 3 | u32 | Erstellt (Unix-Zeit in Sekunden) |
| 4 | Text | Programm und Version, das die Datei geschrieben hat |

### 3.2 SCRN: eine Seite

Für jede Seite ein eigener Abschnitt, höchstens 16. Die Reihenfolge in der Datei ist die Reihenfolge beim Blättern.

| Größe | Typ | Inhalt |
|---|---|---|
| 1 | u8 | Nummer der Seite (0–15, eindeutig in der Datei) |
| 1 | u8 | Art: 0 = Tagseite, 1 = Nachtversion, 2 = Startbild. Unbekannte Werte gelten als Tagseite |
| 1 | u8 | Bei Nachtversion: Nummer der Tagseite, die sie ersetzt. Sonst 255 |
| 1 | u8 | reserviert, 0 |
| 3 | Farbe | Hintergrundfarbe |
| 1 | u8 | Länge des Namens |
| n | Text | Name der Seite |
| 2 | u16 | Anzahl Elemente (höchstens 96) |
| … | | Elemente, siehe 3.3 |

Elemente werden in der Reihenfolge der Datei gezeichnet. Spätere Elemente liegen also über früheren.

**Nachtversionen:** Ist der Nachtmodus an, zeigt der Tacho statt einer Tagseite deren Nachtversion, falls es eine gibt. Beim Blättern zählen nur Tagseiten.

**Startbild:** Höchstens eine Seite darf die Art 2 haben. Der Tacho zeigt sie beim Einschalten so lange, wie in der Konfiguration unter `startbild_dauer_s` steht, danach die Startseite. Typischer Inhalt: ein Logo als Bild-Element und ein Text. Ohne Startbild-Seite zeigt der Tacho `startbild_text` aus der Konfiguration. Startbild-Seiten erscheinen nicht beim Blättern.

### 3.3 Element

| Größe | Typ | Inhalt |
|---|---|---|
| 1 | u8 | Typ (Tabelle 4.1) |
| 1 | u8 | Schalter: Bit 0 = versteckt, Bit 1 = gesperrt (nur für den Designer). Übrige Bits 0 |
| 2 | i16 | X, linke Kante in Pixeln (darf negativ sein) |
| 2 | i16 | Y, obere Kante |
| 2 | u16 | Breite |
| 2 | u16 | Höhe |
| 2 | u16 | Länge der Eigenschaftsliste in Bytes |
| … | | Eigenschaften im Format **Nummer (u8), Länge (u8), Daten** (Tabelle 4.3) |

Regeln für Eigenschaften:
- Fehlt eine Eigenschaft, gilt ihr Standardwert. Manche Typen haben eigene Standardwerte (Tabelle 4.4).
- Unbekannte Nummern werden übersprungen. Der Designer behält sie beim Speichern unverändert bei.
- Passt die Länge nicht zum Datentyp (z. B. Farbe nicht 3 Bytes), ist die Datei ungültig.
- Eigenschaften, die ein Typ nicht benutzt, werden ignoriert.

Ein Element mit unbekanntem Typ wird nicht gezeichnet, die Datei bleibt aber gültig.

### 3.4 IMAG: ein Bild

Bilder werden einmal in der Datei gespeichert und von Bild-Elementen über ihre Nummer benutzt. Höchstens 32 Bilder, jede Seite höchstens 480 Pixel.

| Größe | Typ | Inhalt |
|---|---|---|
| 1 | u8 | Nummer des Bilds (0–254, eindeutig in der Datei) |
| 1 | u8 | Kodierung: 1 = unkomprimiert, 2 = lauflängenkodiert |
| 1 | u8 | Schalter: Bit 0 = jedes Pixel hat ein Alpha-Byte. Übrige Bits 0 |
| 1 | u8 | reserviert, 0 |
| 2 | u16 | Breite in Pixeln (1–480) |
| 2 | u16 | Höhe in Pixeln (1–480) |
| 1 | u8 | Länge des Namens |
| n | Text | Name des Bilds (für den Designer) |
| 4 | u32 | Länge der Pixeldaten in Bytes |
| … | | Pixeldaten, füllen den Abschnitt bis zum Ende |

**Ein Pixel** besteht aus der Farbe im Displayformat **RGB565** als u16 (Little-Endian: erst das niedrige Byte) und, wenn Bit 0 gesetzt ist, einem **Alpha-Byte** (0 = durchsichtig, 255 = deckend). Also 2 oder 3 Bytes je Pixel. Pixel laufen zeilenweise von oben links nach unten rechts.

RGB565 aus 8-Bit-Farben: `((R & 0xF8) << 8) | ((G & 0xFC) << 3) | (B >> 3)`.

**Kodierung 1, unkomprimiert:** alle Pixel hintereinander. Länge = Breite × Höhe × (2 oder 3).

**Kodierung 2, lauflängenkodiert:** Folge von Blöcken, jeder beginnt mit einem Steuerbyte `b`:
- `b` ≥ 128: **Wiederholung**. Es folgt genau ein Pixel, das (`b` − 127) Mal gesetzt wird, also 2 bis 128 Mal.
- `b` < 128: **Einzelpixel**. Es folgen (`b` + 1) Pixel, also 1 bis 128.

Die Blöcke ergeben zusammen genau Breite × Höhe Pixel, und die Pixeldaten enden genau mit dem letzten Block. Sonst ist die Datei ungültig. Der Designer nimmt die jeweils kleinere der beiden Kodierungen. Logos mit einfarbigen Flächen werden dadurch meist viel kleiner, Fotos bleiben unkomprimiert.

Platzbedarf: Ein Vollbild 480 × 320 ohne Alpha braucht unkomprimiert 300 KB.

## 4. Nummern

### 4.1 Element-Typen

| Nummer | Schlüssel | Name | Benutzte Eigenschaften |
|---|---|---|---|
| 1 | `text` | Text | `text`, `color`, `font`, `size`, `align` |
| 2 | `value` | Wert | `source`, `color`, `font`, `size`, `align`, `decimals`, `unit`, `format`, `warn_above`, `warn_color`, `crit_above`, `crit_color` |
| 3 | `bar` | Balken | `source`, `min`, `max`, `segments`, `orientation`, `color`, `bg_color`, `radius`, `warn_above`, `warn_color`, `crit_above`, `crit_color` |
| 4 | `gauge` | Rundinstrument | `source`, `min`, `max`, `start_angle`, `end_angle`, `thickness`, `color`, `bg_color`, `warn_above`, `warn_color`, `crit_above`, `crit_color` |
| 5 | `indicator` | Kontrollleuchte | `source`, `icon`, `on_color`, `off_color`, `blink` |
| 6 | `rect` | Fläche / Linie | `color`, `radius`, `border_color`, `border_width` |
| 7 | `image` | Bild | `image` |

### 4.2 Datenquellen (`source`)

1–63 sind Zahlen, Texte oder die Uhrzeit, 64–127 sind Ja/Nein-Zustände.

| Nummer | Schlüssel | Bedeutung | Einheit | Art |
|---|---|---|---|---|
| 0 | `none` | Keine | – | Zahl |
| 1 | `speed` | Geschwindigkeit | km/h | Zahl |
| 2 | `rpm` | Drehzahl | U/min | Zahl |
| 3 | `gear` | Gang (0 = Leerlauf) | – | Zahl |
| 4 | `odometer` | Gesamtkilometer | km | Zahl |
| 5 | `trip_a` | Tageskilometer A | km | Zahl |
| 6 | `trip_b` | Tageskilometer B | km | Zahl |
| 7 | `head_temp` | Zylinderkopftemperatur | °C | Zahl |
| 8 | `voltage` | Bordspannung | V | Zahl |
| 9 | `outside_temp` | Außentemperatur | °C | Zahl |
| 10 | `housing_temp` | Temperatur in der Lampe | °C | Zahl |
| 11 | `lean` | Schräglage (links negativ) | ° | Zahl |
| 12 | `lean_max` | Schräglage maximal | ° | Zahl |
| 13 | `time` | Uhrzeit | – | Uhrzeit |
| 14 | `speed_max` | Höchstgeschwindigkeit | km/h | Zahl |
| 15 | `speed_avg` | Durchschnitt | km/h | Zahl |
| 16 | `ride_time` | Fahrzeit | min | Zahl |
| 17 | `tank_km` | Kilometer seit Tanken | km | Zahl |
| 18 | `song_title` | Songtitel | – | Text |
| 19 | `song_artist` | Interpret | – | Text |
| 20 | `service_km` | Kilometer bis zur nächsten Wartung | km | Zahl |
| 64 | `blinker_left` | Blinker links | – | Ja/Nein |
| 65 | `blinker_right` | Blinker rechts | – | Ja/Nein |
| 66 | `high_beam` | Fernlicht | – | Ja/Nein |
| 67 | `neutral` | Leerlauf | – | Ja/Nein |
| 68 | `light` | Licht an | – | Ja/Nein |
| 69 | `alarm_armed` | Alarm scharf | – | Ja/Nein |
| 70 | `gps_fix` | GPS-Empfang | – | Ja/Nein |
| 71 | `bt_connected` | iPhone verbunden | – | Ja/Nein |
| 72 | `shift_light` | Schaltblitz | – | Ja/Nein |
| 73 | `warning` | Eine Warnung aktiv | – | Ja/Nein |

### 4.3 Eigenschaften

| Nummer | Schlüssel | Bedeutung | Daten | Standard |
|---|---|---|---|---|
| 1 | `source` | Datenquelle | u8, Liste 4.2 | none |
| 2 | `color` | Farbe | Farbe | #F1EFE8 |
| 3 | `bg_color` | Hintergrund (unbeleuchteter Teil) | Farbe | #000000 |
| 4 | `font` | Schrift | u8, Liste 4.5 | sans |
| 5 | `size` | Schriftgröße in Pixeln (Höhe der Großbuchstaben etwa 0,7 × Wert) | u8 | 24 |
| 6 | `align` | Ausrichtung im Rahmen | u8, Liste 4.5 | center |
| 7 | `text` | Text | Text | (leer) |
| 8 | `decimals` | Nachkommastellen | u8 | 0 |
| 9 | `unit` | Einheit, wird an die Zahl angehängt (Leerzeichen selbst einfügen) | Text | (leer) |
| 10 | `min` | Wert für 0 % | f32 | 0 |
| 11 | `max` | Wert für 100 % | f32 | 100 |
| 12 | `warn_above` | Warnfarbe ab diesem Wert, 0 = aus | f32 | 0 |
| 13 | `warn_color` | Warnfarbe | Farbe | #EF9F27 |
| 14 | `crit_above` | Kritisch-Farbe ab diesem Wert, 0 = aus | f32 | 0 |
| 15 | `crit_color` | Kritisch-Farbe | Farbe | #E24B4A |
| 16 | `segments` | Anzahl Segmente, 0 = durchgehender Balken | u8 | 0 |
| 17 | `orientation` | Richtung des Balkens | u8, Liste 4.5 | horizontal |
| 18 | `start_angle` | Startwinkel in Grad | i16 | 135 |
| 19 | `end_angle` | Endwinkel in Grad | i16 | 405 |
| 20 | `thickness` | Dicke des Bogens in Pixeln | u8 | 12 |
| 21 | `radius` | Eckenradius in Pixeln | u8 | 0 |
| 22 | `icon` | Symbol | u8, Liste 4.5 | none |
| 23 | `on_color` | Farbe, wenn an | Farbe | #639922 |
| 24 | `off_color` | Farbe, wenn aus | Farbe | #2C2C2A |
| 25 | `blink` | Blinkt, solange an (u8: 0 oder 1) | u8 | 0 |
| 26 | `format` | Format der Uhrzeit: `HH`, `MM`, `SS` werden ersetzt | Text | HH:MM |
| 27 | `border_color` | Rahmenfarbe | Farbe | #000000 |
| 28 | `border_width` | Rahmenbreite in Pixeln, 0 = kein Rahmen | u8 | 0 |
| 29 | `image` | Nummer des Bilds aus einem IMAG-Abschnitt, 255 = kein Bild | u8 | 255 |
| 30 | `from_zero` | Balken und Rundinstrument füllen sich ab dem Wert 0 statt ab `min` (u8: 0 oder 1), z. B. für die Schräglage | u8 | 0 |

### 4.4 Abweichende Standardwerte je Typ

Fehlt eine Eigenschaft in der Datei, gelten für diese Typen andere Standardwerte als in 4.3:

| Typ | Standardgröße im Designer | Abweichende Standardwerte |
|---|---|---|
| `text` | 120 × 32 | `text` = „Text“ |
| `value` | 160 × 80 | `source` = speed, `size` = 64, `font` = segment |
| `bar` | 440 × 20 | `source` = rpm, `max` = 8000, `segments` = 24, `color` = #1D9E75, `bg_color` = #2C2C2A, `warn_above` = 5500, `crit_above` = 7000 |
| `gauge` | 200 × 200 | `source` = speed, `max` = 80, `color` = #1D9E75, `bg_color` = #2C2C2A |
| `indicator` | 32 × 32 | `source` = neutral, `icon` = neutral |
| `rect` | 100 × 2 | `color` = #2C2C2A |
| `image` | 64 × 64 (beim Laden eines Bilds dessen Größe) | – |

### 4.5 Listen

**Symbole (`icon`):** 0 `none` kein Symbol, 1 `arrow_left` Pfeil links, 2 `arrow_right` Pfeil rechts, 3 `high_beam` Fernlicht, 4 `neutral` Leerlauf (N), 5 `light` Licht, 6 `battery` Batterie, 7 `temp` Thermometer, 8 `gps` GPS, 9 `bluetooth` Bluetooth, 10 `lock` Schloss, 11 `warning` Warndreieck, 12 `music` Musik.

**Schrift (`font`):** 0 `sans` normal (DejaVu Sans), 1 `sans_bold` fett (DejaVu Sans Bold), 2 `segment` Ziffernschrift mit fester Zeichenbreite (DejaVu Sans Mono Bold), gut für Werte, deren Breite sich nicht ändern soll.

**Ausrichtung (`align`):** 0 `left`, 1 `center`, 2 `right`.

**Richtung (`orientation`):** 0 `horizontal` (füllt von links nach rechts), 1 `vertical` (füllt von unten nach oben).

## 5. Darstellung

Diese Regeln gelten für den Tacho und für die Vorschau im Designer (`designer/s51design/values.py`).

**Text und Wert:** Der Text wird im Rahmen des Elements waagerecht nach `align` und senkrecht mittig ausgerichtet.
- Elemente vom Typ `text` brechen an Leerzeichen in mehrere Zeilen um, wenn der Text breiter als der Rahmen ist. Ein Zeilenumbruch im Text erzwingt eine neue Zeile. Zeilenabstand 1,2 × `size`, alle Zeilen zusammen senkrecht mittig.
- Elemente vom Typ `value` brechen nicht um.
- Was danach nicht in den Rahmen passt, wird abgeschnitten.

**Zahlen:** mit `decimals` Nachkommastellen, Dezimalkomma und Tausenderpunkt, z. B. `12.345` oder `13,8`. Danach folgt `unit`. Fehlt der Wert (z. B. kein GPS-Empfang), steht `–` da.

**Uhrzeit:** nach `format`. Ist die Zeit noch unbekannt, werden die Ziffern durch `--` ersetzt.

**Ja/Nein-Quelle in einem Wert-Element:** zeigt „an“ oder „aus“.

**Warnfarben:** Ist `crit_above` nicht 0 und der Wert ≥ `crit_above`, wird `crit_color` benutzt. Sonst, wenn `warn_above` nicht 0 und der Wert ≥ `warn_above`, `warn_color`. Sonst `color`.

**Balken:** Anteil = (Wert − `min`) / (`max` − `min`), begrenzt auf 0 bis 1.
- Ohne Segmente wird der Hintergrund in `bg_color` gezeichnet und darüber der gefüllte Teil in der Farbe nach den Warnregeln.
- Mit Segmenten: Abstand 2 Pixel. Es leuchten round(Anteil × Segmente) Segmente. Jedes leuchtende Segment bekommt die Farbe nach den Warnregeln für den Wert an seinem Ende, also `min + (max − min) × (i + 1) / Segmente`. So entsteht z. B. der rote Bereich am Ende des Drehzahlbalkens. Nicht leuchtende Segmente sind `bg_color`.

**Rundinstrument:** Ein Bogen um die Mitte des Rahmens. Durchmesser = kleinere Seite des Rahmens, Bogen mittig auf diesem Kreis mit `thickness` Dicke. Winkel: 0° = rechts (3 Uhr), positive Winkel **im Uhrzeigersinn**. Der ganze Bogen von `start_angle` bis `end_angle` wird in `bg_color` gezeichnet, darüber der Anteil des Werts in der Farbe nach den Warnregeln. 135° bis 405° ergibt einen unten offenen Dreiviertelkreis. Die Kanten werden geglättet, die Enden des Bogens sind gerade.

**Ab 0 füllen (`from_zero`):** Für Werte, die links und rechts von 0 liegen, z. B. die Schräglage von −45 bis 45. Gefüllt wird der Bereich zwischen dem Anteil des Werts 0 und dem Anteil des Werts. Mit Segmenten leuchtet ein Segment, wenn seine Mitte (`(i + 0,5) / Segmente`) in diesem Bereich liegt; gefärbt wird es nach dem Wert an seinem Ende, das weiter von 0 entfernt ist. Die Warnregeln gelten für den Betrag des Werts, also auf beiden Seiten gleich. Ohne `from_zero` gilt die Regel oben (gefüllt ab `min`).

**Kontrollleuchte:** Das Symbol füllt den Rahmen (kleinere Seite). Ist die Quelle „an“, wird `on_color` benutzt, sonst `off_color`. Mit `blink` wechselt ein eingeschaltetes Symbol im Takt von 2 Hz zwischen an und aus. Blinker-Eingänge pulsieren schon selbst und brauchen `blink` nicht.

**Fläche:** gefülltes Rechteck in `color` mit `radius` abgerundeten Ecken. Ist `border_width` größer als 0, liegt ein Rahmen in `border_color` dieser Breite innerhalb der Fläche, die Fläche wird dadurch nicht größer. Linien sind Flächen mit 1 Pixel Höhe oder Breite.

**Bild:** Das Bild wird in Originalgröße mit seiner linken oberen Ecke an X/Y gezeichnet und am Rahmen des Elements abgeschnitten. Es wird nicht skaliert. Die richtige Größe stellt der Designer beim Laden ein. Alpha wird mit dem gemischt, was darunter liegt. Fehlt das Bild mit der angegebenen Nummer, zeichnet der Tacho nichts.

**Versteckte Elemente** werden auf dem Tacho nicht gezeichnet.

## 6. Prüfungen beim Lesen

Der Decoder lehnt eine Datei ab, wenn:
- die Kennung nicht `S51L` ist,
- die Prüfsumme nicht stimmt (CRC32 nach IEEE 802.3, wie `zlib.crc32`, über alle Bytes vor den letzten 4),
- die Hauptversion nicht 1 ist,
- ein Abschnitt, ein Element oder eine Eigenschaft über das Ende hinausgeht,
- mehr als 16 Seiten oder mehr als 96 Elemente auf einer Seite enthalten sind,
- keine Seite enthalten ist,
- eine Eigenschaft eine falsche Länge hat,
- mehr als 32 Bilder enthalten sind, ein Bild Nummer 255 hat, größer als 480 Pixel ist oder seine Pixeldaten nicht genau zur Größe passen,
- die Datei größer als 1 MiB ist.

Eine höhere Unterversion (z. B. 1.3) wird gelesen. Was der Decoder nicht kennt, überspringt er.

## 7. Speicherorte

| Ort | Pfad |
|---|---|
| SD-Karte | Beliebig viele Designs als `/s51/<name>.s51`. Welches beim Start gilt, steht in der Konfiguration (`layout_datei`, Standard `design.s51`) |
| Im Tacho | Kopie des zuletzt benutzten Designs im internen Flash, dazu im NVS die Auswahl am Tacho |

**Welches Design der Tacho zeigt**, in dieser Reihenfolge:
1. Das am Tacho gewählte Design (lange auf das Display drücken, im Menü „Design“) oder das zuletzt per WLAN empfangene. Die Wahl gilt, solange in der Konfiguration noch dasselbe Standard-Design steht wie beim Auswählen. Wird im Designer ein neues Standard-Design festgelegt, gilt dieses beim nächsten Start und die Auswahl am Tacho wird zurückgesetzt.
2. Das Standard-Design aus der Konfiguration (`layout_datei`).
3. Die erste `.s51`-Datei im Ordner `s51` (alphabetisch).
4. Die interne Kopie.
5. Das eingebaute Layout „Klar“.

Beschädigte Dateien werden übersprungen. Jedes von der SD-Karte gelesene Design wird intern gesichert. Per WLAN empfangene Designs landen unter demselben Dateinamen im Ordner `s51` wie beim Export im Designer ([uebertragung.md](uebertragung.md)).

**Design-Auswahl am Tacho:** zeigt alle `.s51`-Dateien im Ordner `s51` mit Name, Dateiname, Anzahl der Seiten und einer Vorschau der ersten Tagseite, dazu das eingebaute Layout „Klar“ (und ohne SD-Karte die interne Kopie). „Übernehmen“ wechselt sofort.

## 8. Beispiel

Die kleinstmögliche gültige Datei mit einer leeren schwarzen Seite (Bytes hexadezimal). Sie ist als Version 1.0 geschrieben und wird weiterhin gelesen:

```
53 35 31 4C 01 00 10 00 E0 01 40 01 00 00 00 00   Kopf: S51L, 1.0, 16, 480, 320
4D 45 54 41 00 00 00 00                            META, Länge 0
53 43 52 4E 0A 00 00 00                            SCRN, Länge 10
00 00 FF 00 00 00 00 00 00 00                      Seite 0, Tagseite, schwarz, Name leer, 0 Elemente
xx xx xx xx                                        CRC32 über alle Bytes davor
```

Mit dem Kommandozeilenwerkzeug lässt sich jede Datei als lesbares JSON anzeigen:

```
cd designer
python -m s51design.cli decode design.s51
```

## 9. Format erweitern

1. Neue Nummer in `designer/s51design/schema.py` ergänzen. Vorhandene Nummern nie ändern oder wiederverwenden.
2. `python tools/gen_cpp_header.py` im Ordner `designer/` ausführen.
3. Diese Datei ergänzen.
4. Tests laufen lassen (`python -m unittest discover -s tests`).

Neue Eigenschaften und Abschnitte erhöhen die Unterversion. Nur Änderungen, die alte Decoder falsch lesen würden, erhöhen die Hauptversion.
