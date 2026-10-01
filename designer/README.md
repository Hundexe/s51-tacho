# S51 Designer

PC-Programm zum Gestalten der Tacho-Anzeige. Elemente wie Geschwindigkeit, Drehzahlbalken, Kontrollleuchten oder Texte lassen sich frei auf dem 480 × 320 Pixel großen Display verteilen. Das Ergebnis kommt per SD-Karte oder WLAN auf den Tacho.

Läuft unter Windows, macOS und Linux. Braucht nur Python, keine Zusatzpakete.

## Installieren und starten

1. **Python 3.9 oder neuer** installieren: https://www.python.org/downloads/
   Unter Windows im Installer „Add python.exe to PATH“ anhaken. Tkinter (für die Oberfläche) ist beim Installer von python.org dabei.
2. Repo herunterladen.
3. Starten:
   - **Windows:** Doppelklick auf `designer/S51-Designer.pyw`
   - **Alle Systeme:** im Ordner `designer/` den Befehl `python -m s51design` ausführen

Unter Linux muss Tkinter eventuell nachinstalliert werden (`sudo apt install python3-tk`).

### Fertige .exe für Windows

Unter **Releases** auf der GitHub-Seite des Projekts liegt `S51-Designer.exe` zum Herunterladen. Sie läuft ohne installiertes Python. Die exe ist nicht signiert: Bei der Windows-Warnung auf „Weitere Informationen“ und „Trotzdem ausführen“ klicken.

Die exe wird bei jeder Änderung im Ordner `designer/` automatisch auf GitHub gebaut (`.github/workflows/designer-release.yml`). Ein Release entsteht, wenn die Versionsnummer neu ist und es Versionshinweise in `designer/release-notes/<Version>.md` gibt.

Selbst bauen: Doppelklick auf `designer/build_exe.bat`. Das lädt PyInstaller und baut `designer/dist/S51-Designer.exe`.

### Neue Version veröffentlichen

1. Version in `designer/s51design/__init__.py` erhöhen.
2. `designer/release-notes/<Version>.md` anlegen.
3. Commit auf `main` hochladen. GitHub baut die exe, legt den Tag `designer-v<Version>` an und veröffentlicht den Release.

## Bedienen

| Bereich | Funktion |
|---|---|
| Links oben | **Seiten:** anlegen, kopieren, löschen, Reihenfolge ändern |
| Links Mitte | **Element hinzufügen:** Text, Wert, Balken, Rundinstrument, Kontrollleuchte, Fläche/Linie |
| Links unten | Alle Elemente der Seite, zum Auswählen auch verdeckter Elemente |
| Mitte | Display in Originalgröße × Zoom. Element anklicken und ziehen, Punkt unten rechts ändert die Größe |
| Rechts | **Eigenschaften** des gewählten Elements, ohne Auswahl die Eigenschaften der Seite |

Tastatur (wenn das Display angeklickt ist):

| Taste | Wirkung |
|---|---|
| Pfeiltasten | Element 1 Pixel verschieben, mit Umschalt 10 Pixel |
| Entf | Element löschen |
| Strg+D | Element duplizieren |
| Strg+Z / Strg+Y | Rückgängig / Wiederholen |
| Strg+S / Strg+O | Speichern / Öffnen |

Weitere Hinweise:
- **Am Raster ausrichten** rastet Position und Größe auf 4 Pixel ein.
- **Vorschau wie am Tacho** blendet Auswahl, Raster und versteckte Elemente aus.
- **Demo-Werte bewegen** lässt Geschwindigkeit, Drehzahl, Blinker usw. laufen, damit Warnfarben und Balken sichtbar werden.
- **Nachtversion:** Seite anlegen, rechts „Art“ auf „Nachtversion einer Seite“ stellen und die Tagseite wählen. Im Nachtmodus zeigt der Tacho dann diese Seite.
- Die Vorschau zeigt Positionen, Größen, Farben und Werte genau. Die Schriften am PC sehen etwas anders aus als auf dem Tacho.

## Auf den Tacho bringen

**SD-Karte:** Datei → Auf SD-Karte exportieren, Laufwerk der Karte wählen. Der Designer legt den Ordner `s51` an und schreibt `design.s51` und `tacho.cfg` hinein. Liegt dort schon eine `tacho.cfg`, fragt er, ob sie überschrieben werden soll.

**WLAN:** Datei → Drahtlos übertragen. Ablauf und Protokoll: [docs/uebertragung.md](../docs/uebertragung.md).

**Einstellungen** (Radumfang, Warnschwellen, Alarm, WLAN …): Einstellungen → Tacho-Konfiguration bearbeiten. Erklärung aller Werte: [docs/konfiguration.md](../docs/konfiguration.md).

## Dateien

| Datei | Inhalt | Beschreibung |
|---|---|---|
| `*.s51` | Layout (binär) | [docs/dateiformat-layout.md](../docs/dateiformat-layout.md) |
| `tacho.cfg` | Einstellungen (Text) | [docs/konfiguration.md](../docs/konfiguration.md) |
| `beispiele/klar.s51` | Mitgeliefertes Layout „Klar“ | |

Die `.s51`-Datei ist zugleich die Projektdatei. Es gibt kein separates Projektformat.

## Kommandozeile

Für Fehlersuche und Automatisierung, im Ordner `designer/`:

```
python -m s51design.cli decode datei.s51            # Layout als JSON anzeigen
python -m s51design.cli encode layout.json datei.s51 # JSON -> .s51
python -m s51design.cli check datei.s51             # nur prüfen
python -m s51design.cli preset Klar datei.s51       # mitgeliefertes Layout schreiben
python -m s51design.cli config-check tacho.cfg      # Konfiguration prüfen
python -m s51design.cli config-new tacho.cfg        # Vorlage mit allen Einträgen
```

## Aufbau des Codes

| Datei | Aufgabe |
|---|---|
| `s51design/schema.py` | **Einzige Quelle** aller Nummern (Element-Typen, Datenquellen, Eigenschaften, Konfiguration) |
| `s51design/layout_format.py` | Encoder und Decoder für `.s51` |
| `s51design/config_format.py` | Lesen und Schreiben von `tacho.cfg` |
| `s51design/transfer.py` | WLAN-Übertragung |
| `s51design/mock_tacho.py` | Simulierter Tacho zum Testen der Übertragung |
| `s51design/editor.py` | Bearbeitungslogik ohne Oberfläche (Auswahl, Ziehen, Rückgängig) |
| `s51design/values.py` | Demo-Werte und Anzeigeregeln (Zahlenformat, Warnfarben) |
| `s51design/render.py` | Zeichnen der Vorschau |
| `s51design/app.py` | Oberfläche |
| `s51design/presets.py` | Mitgelieferte Layouts |
| `tools/gen_cpp_header.py` | Erzeugt den C++-Teil des Schemas für die Firmware |

## Tests

```
cd designer
python -m unittest discover -s tests -v
```

Die Tests prüfen:
- Encoder und Decoder in beide Richtungen, auch mit beschädigten Dateien
- Konfiguration lesen und schreiben, auch mit Fehlern in der Datei
- Übertragung gegen den simulierten Tacho
- dass der C++-Decoder der Firmware genau dasselbe liest wie der Python-Decoder (braucht `g++`, sonst übersprungen)
- dass der erzeugte C++-Header zum Schema passt
- dass die Doku alle Nummern und Schlüssel enthält
- die Logik der Oberfläche mit nachgebildetem Tkinter (ohne echtes Fenster)

Was die Tests **nicht** abdecken: wie die Oberfläche tatsächlich auf dem Bildschirm aussieht. Das muss am PC von Hand geprüft werden.
