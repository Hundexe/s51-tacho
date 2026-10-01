# Konfigurationsdatei (tacho.cfg)

Die Konfiguration enthält alle Einstellungen des Tachos, die nicht zum Aussehen gehören: Radumfang, Warnschwellen, Alarm, WLAN und mehr. Das Aussehen steht in der Layout-Datei ([dateiformat-layout.md](dateiformat-layout.md)).

Bewusst ein anderes Format als das Layout: eine einfache **Textdatei**, die sich auch ohne den Designer mit jedem Editor (z. B. Notepad) bearbeiten lässt.

**Quellen im Code:**
- Alle Schlüssel mit Standardwerten und Grenzen: `designer/s51design/schema.py` (Liste `CONFIG`)
- Lesen und Schreiben in Python: `designer/s51design/config_format.py`
- Lesen in C++ (Firmware): `firmware/lib/s51layout/src/s51_config.cpp`

---

## 1. Speicherort

`/s51/tacho.cfg` auf der SD-Karte, oder per WLAN übertragen ([uebertragung.md](uebertragung.md)). Der Tacho liest die Datei beim Start und nach jeder Übertragung. Er hält eine Kopie im internen Speicher und nutzt sie, wenn keine SD-Karte steckt.

Fehlt die Datei, gelten alle Standardwerte. Eine Vorlage mit allen Einträgen und Erklärungen erzeugt der Designer (Einstellungen → Konfiguration speichern unter) oder die Kommandozeile:

```
cd designer
python -m s51design.cli config-new tacho.cfg
```

## 2. Aufbau

```
# Kommentar
[fahrzeug]
radumfang_mm = 1720
hall_sensor = nein   # Kommentar am Zeilenende

[anzeige]
startbild_text = "Meine S51"
```

Regeln:
- Kodierung **UTF-8** (ein BOM am Anfang wird ignoriert), Zeilenenden LF oder CRLF.
- **Abschnitte** stehen in eckigen Klammern. Jeder Schlüssel gehört zu dem Abschnitt darüber.
- **Einträge:** `schluessel = wert`. Leerzeichen um das `=` sind egal. Groß- und Kleinschreibung bei Abschnitten und Schlüsseln ist egal.
- **Kommentare** beginnen am Zeilenanfang mit `#` oder `;`. Hinter einem Wert beginnt ein Kommentar mit Leerzeichen und `#` oder `;`.
- **Texte** dürfen in Anführungszeichen stehen. Das ist nötig, wenn sie `#` oder `;` enthalten oder mit Leerzeichen beginnen oder enden.
- **Ja/Nein-Werte:** `ja`, `an`, `true`, `1` oder `nein`, `aus`, `false`, `0`.
- **Kommazahlen** mit Punkt oder Komma: `12.5` und `12,5` sind gleich.
- **Auswahlwerte** sind klein geschrieben und nur aus der angegebenen Liste.

Fehlertoleranz: Ein unbekannter Schlüssel, ein unbekannter Abschnitt oder ein ungültiger Wert führt **nicht** zum Abbruch. Der betroffene Eintrag behält seinen Standardwert, alles andere wird übernommen. Der Tacho zeigt die Hinweise im Menü „Einstellungen“ an. Der Designer und `python -m s51design.cli config-check tacho.cfg` melden sie mit Zeilennummer. Steht ein Schlüssel mehrfach in der Datei, gilt der letzte gültige Wert.

## 3. Alle Einträge

### [fahrzeug]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `radumfang_mm` | Zahl | 1720 | 1000–2500 | Abrollumfang des Vorderrads in mm. Wird mit GPS nachgelernt, wenn `radumfang_lernen = ja` |
| `radumfang_lernen` | Ja/Nein | ja | | Radumfang bei gutem GPS-Empfang selbst nachlernen |
| `hall_sensor` | Ja/Nein | nein | | Hall-Sensor am Vorderrad verbaut. Bei nein kommt die Geschwindigkeit nur vom GPS |
| `magnete` | Zahl | 2 | 1–8 | Anzahl Magnete am Rad |
| `impulse_pro_umdrehung` | Zahl | 1 | 1–4 | Zündimpulse pro Kurbelwellenumdrehung. Zweitakter mit einem Zylinder: 1 |
| `gaenge` | Zahl | 4 | 3–6 | Anzahl Gänge |
| `tankreichweite_km` | Zahl | 150 | 0–1000 | Ab dieser Strecke seit dem Tanken erscheint die Reserve-Warnung. 0 = aus |

### [anzeige]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `layout_datei` | Text | design.s51 | | Standard-Design: Name der Layout-Datei im Ordner `s51`. Der Designer setzt den Wert beim Export auf die SD-Karte. Am Tacho lässt sich durch langes Drücken ein anderes Design wählen, siehe [dateiformat-layout.md](dateiformat-layout.md), Abschnitt 7 |
| `startseite` | Zahl | 0 | 0–15 | Nummer (`id`) der Tagseite, die nach dem Start gezeigt wird. Gibt es sie nicht, die erste Tagseite |
| `startbild_dauer_s` | Zahl | 2 | 0–10 | Wie lange die Startbild-Seite des Layouts beim Einschalten zu sehen ist, in Sekunden. 0 = aus |
| `startbild_text` | Text | S51 | | Text beim Einschalten, falls das Layout keine Startbild-Seite hat. Leer = nichts anzeigen |
| `helligkeit_tag` | Zahl | 100 | 5–100 | Helligkeit am Tag in % |
| `helligkeit_nacht` | Zahl | 30 | 5–100 | Helligkeit nachts in % |
| `helligkeit_auto` | Ja/Nein | ja | | Helligkeit über den Lichtsensor regeln |
| `nachtmodus` | Auswahl | auto | auto, an, aus | auto = mit Licht bzw. Lichtsensor. Bis Licht und Lichtsensor angeschlossen sind (Phase 3), verhält sich auto wie aus |

### [warnungen]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `kopftemp_warnung` | Zahl | 200 | 50–400 | Zylinderkopf: gelbe Warnung ab °C |
| `kopftemp_kritisch` | Zahl | 240 | 50–400 | Zylinderkopf: rote Warnung ab °C |
| `spannung_min` | Kommazahl | 12 | 9–15 | Warnung unter dieser Bordspannung (V) |
| `spannung_max` | Kommazahl | 15 | 12–18 | Warnung über dieser Bordspannung (V) |
| `glaette_unter` | Kommazahl | 3 | −10–10 | Glättewarnung unter dieser Außentemperatur (°C) |
| `schaltblitz_drehzahl` | Zahl | 6500 | 0–15000 | Schaltblitz ab dieser Drehzahl. 0 = aus |

Die Kopftemperatur wird mit dem PT1000 am Zylinderkopf gemessen, nicht direkt unter der Zündkerze. Die Schwellen bei den ersten Fahrten an die eigenen Werte anpassen.

### [wartung]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `getriebeoel_km` | Zahl | 0 | 0–100000 | Erinnerung Getriebeöl alle x km. 0 = aus |
| `zuendkerze_km` | Zahl | 0 | 0–100000 | Erinnerung Zündkerze alle x km. 0 = aus |
| `kette_km` | Zahl | 0 | 0–100000 | Erinnerung Kette schmieren alle x km. 0 = aus |

Abstände aus dem Handbuch des eigenen Fahrzeugs eintragen. Bestätigt wird eine erledigte Wartung am Tacho im Menü Wartung („Erledigt“), danach zählt der Abstand ab dem jetzigen Kilometerstand neu. Die Datenquelle „Kilometer bis Wartung“ zeigt den kleinsten Rest aller eingestellten Abstände.

### [alarm]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `aktiv` | Ja/Nein | ja | | Bewegungsalarm einschalten. Lässt sich am Tacho im Menü Alarm umschalten. Die Wahl am Tacho gilt, bis hier ein anderer Wert eingetragen wird |
| `stufe` | Zahl | 2 | 1–2 | 1 = Zündschlüssel entschärft. 2 = nach „Zündung an“ PIN oder NFC-Tag nötig. Der Sperrbildschirm erscheint nur, wenn am Tacho eine PIN festgelegt ist |
| `empfindlichkeit` | Zahl | 3 | 1–5 | 1 = unempfindlich bis 5 = sehr empfindlich |
| `dauer_s` | Zahl | 30 | 5–180 | Dauer des Alarmtons in Sekunden |
| `entsperrzeit_s` | Zahl | 30 | 10–120 | Zeit für PIN oder Tag nach „Zündung an“ (Stufe 2) |

**PIN und NFC-Tags stehen absichtlich nicht in dieser Datei.** Wer die SD-Karte zieht, könnte sie sonst lesen oder ändern. Beides wird am Tacho selbst eingestellt und nur im internen Speicher abgelegt.

### [gps]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `messrate_hz` | Zahl | 10 | 1–10 | Messungen pro Sekunde. NEO-6M: höchstens 5 |
| `zeitzone` | Text | Europe/Berlin | | Zeitzone für die Uhrzeit, mit Sommerzeit |

### [bluetooth]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `aktiv` | Ja/Nein | ja | | Bluetooth für Musik und Uhrzeit vom iPhone |
| `name` | Text | S51-Tacho | | Name, unter dem der Tacho am Handy erscheint |

### [wlan]

| Schlüssel | Art | Standard | Bereich | Bedeutung |
|---|---|---|---|---|
| `modus` | Auswahl | hotspot | hotspot, heimnetz | hotspot = Tacho öffnet ein eigenes WLAN. heimnetz = Tacho verbindet sich mit `ssid` |
| `ssid` | Text | S51-Tacho | | Name des WLANs |
| `passwort` | Text | simson51 | | WLAN-Passwort, mindestens 8 Zeichen |
| `hostname` | Text | s51-tacho | | Name im Heimnetz, erreichbar als `s51-tacho.local` |

**Das Standard-Passwort steht in dieser öffentlichen Doku. Beim Einrichten unbedingt ändern.** WLAN ist nur aktiv, solange am Tacho der Übertragungsmodus offen ist.

## 4. Konfiguration erweitern

1. Eintrag in `CONFIG` in `designer/s51design/schema.py` ergänzen (Abschnitt, Schlüssel, Art, Standard, Bereich, Beschreibung).
2. `python tools/gen_cpp_header.py` im Ordner `designer/` ausführen. Die Firmware bekommt dadurch den neuen Schlüssel `s51::CfgKey::<Abschnitt><Schluessel>`.
3. Tabelle oben ergänzen. Ein Test prüft, dass jeder Schlüssel hier vorkommt.
