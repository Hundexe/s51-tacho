# S51 Designer

PC-Programm zum Gestalten der Tacho-Anzeige. Elemente wie Geschwindigkeit, Drehzahlbalken, Kontrollleuchten oder Texte lassen sich frei auf dem 480 × 320 Pixel großen Display verteilen. Das Ergebnis kommt per SD-Karte oder WLAN auf den Tacho.

Läuft unter Windows, macOS und Linux. Braucht nur Python. Optional Pillow (`pip install pillow`), damit sich auch JPG- und BMP-Bilder laden lassen. Ohne Pillow gehen nur PNG-Bilder. In der fertigen exe ist Pillow enthalten.

![S51 Designer](../docs/bilder/designer/designer-start.png)

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
| Oben | **Symbolleiste:** Neu, Öffnen, Speichern, Rückgängig, Wiederholen, Element duplizieren, löschen, ganz nach vorn oder hinten, Bild laden, Tacho-Konfiguration. Rechts **Auf SD-Karte** und **Drahtlos senden**. Jedes Symbol erklärt sich beim Darüberfahren mit der Maus |
| Links oben | **Elemente:** Kachel anklicken fügt Text, Wert, Balken, Rundinstrument, Kontrollleuchte, Fläche/Linie oder Bild in der Mitte ein |
| Links Mitte | **Seiten:** anlegen (+), kopieren, löschen, Reihenfolge ändern |
| Links unten | **Ebenen:** alle Elemente der Seite, das vorderste oben. Zum Auswählen auch verdeckter Elemente |
| Mitte | Display mit Rahmen. Element anklicken und ziehen, Punkt unten rechts ändert die Größe. Darunter Zoom (1×, 1,5×, 2×, 3×) und die Schalter Raster, Einrasten, Vorschau, Demo-Werte |
| Rechts | **Eigenschaften** des gewählten Elements, nach Gruppen (Daten, Text, Form, Farben, Warnschwellen). Ohne Auswahl: Seite, Layout und die Bilder im Layout |
| Unten | Status und Dateigröße des Layouts (höchstens 1 MiB) |

Farben: auf das Farbfeld klicken öffnet die Farbauswahl. Daneben lässt sich der Wert als `#RRGGBB` eintippen.

Tastatur (wenn das Display angeklickt ist):

| Taste | Wirkung |
|---|---|
| Pfeiltasten | Element 1 Pixel verschieben, mit Umschalt 10 Pixel |
| Entf | Element löschen |
| Strg+D | Element duplizieren |
| Strg+Z / Strg+Y | Rückgängig / Wiederholen |
| Strg+S / Strg+O | Speichern / Öffnen |

Weitere Hinweise:
- **Einrasten** rastet Position und Größe auf 4 Pixel ein.
- **Vorschau** blendet Auswahl, Raster und versteckte Elemente aus, so wie am Tacho.
- **Demo-Werte** lässt Geschwindigkeit, Drehzahl, Blinker usw. laufen, damit Warnfarben und Balken sichtbar werden.
- **Versteckt** und **Gesperrt** (in den Eigenschaften): versteckte Elemente zeigt nur der Designer blass an, gesperrte lassen sich nicht aus Versehen verschieben.
- **Nachtversion:** Seite anlegen, rechts „Art“ auf „Nachtversion“ stellen und unter „Nacht für“ die Tagseite wählen. Im Nachtmodus zeigt der Tacho dann diese Seite.
- Die Vorschau zeigt Positionen, Größen, Farben und Werte genau. Die Schriften am PC sehen etwas anders aus als auf dem Tacho.

### Bilder und Startbild

- **Bild laden** (Symbolleiste, Menü Bearbeiten oder rechts bei den Eigenschaften) liest PNG, JPG oder BMP. Ohne ausgewähltes Bild-Element entsteht ein neues Element in der Mitte. Bilder größer als das Display werden verkleinert. Ist ein Bild-Element ausgewählt, wird das neue Bild genau in dessen Rahmen eingepasst.
- Ein Bild kann von mehreren Elementen benutzt werden. Auswahl im Feld „Bild“ des Elements. **Originalgröße** setzt den Rahmen auf die Größe des Bildes.
- Der Tacho zeichnet Bilder immer in Originalgröße ab der linken oberen Ecke des Rahmens. Durchsichtige Stellen (PNG mit Alpha) bleiben durchsichtig.
- Höchstens 32 Bilder pro Layout, jedes höchstens 480 × 480 Pixel. Gespeichert werden sie mit 65 536 Farben (RGB565), einfarbige Flächen werden komprimiert. Große Fotos machen die Datei schnell groß, die Größe steht unten rechts.
- Ohne Auswahl stehen rechts alle Bilder des Layouts mit Vorschau und wie oft sie benutzt werden. Dort lassen sie sich auch löschen.
- **Startbild:** Eine Seite auf die Art „Startbild“ stellen. Diese Seite zeigt der Tacho beim Einschalten, so lange wie in der Konfiguration unter `anzeige.startbild_dauer_s` eingestellt. Ein Layout hat höchstens eine Startbild-Seite.

![Startbild-Seite mit Logo](../docs/bilder/designer/designer-bild.png)

## Vorlagen

Sechs Layouts sind eingebaut (Datei → Neu aus Vorlage) und liegen auch als Dateien in `beispiele/`. Sie zeigen, was der Designer kann, und sind ein guter Startpunkt für eigene Layouts.

| Vorlage | Inhalt |
|---|---|
| **Klar** | Standard-Layout des Tachos: große Geschwindigkeit, Drehzahlbalken, Infozeile, Statistikseite, Nachtversion, Startbild mit Logo |
| **Retro** | Rundinstrument im Stil des alten Simson-Tachos mit Skala, Kilometerzähler und kleinem Drehzahlmesser |
| **Rennsport** | Riesige Ganganzeige, segmentierter Drehzahlbalken mit rotem Bereich, Schaltblitz, Seite für die Schräglage |
| **Cockpit** | Viele Werte in Kacheln, Drehzahl als Ring, dazu eine Musikseite mit Songtitel vom iPhone |
| **Minimal** | Nur Geschwindigkeit, Uhrzeit, Blinker und Warnsymbol, mit gedimmter Nachtversion |
| **Alle Elemente** | Eine Seite je Element-Typ: Schriften und Ausrichtung, Balkenarten, Rundinstrumente mit verschiedenen Winkeln, alle Symbole, Flächen und Linien, versteckte und gesperrte Elemente, Nachtversion, Bilder, Startbild |

![Klar](../docs/bilder/vorlage-klar.png)
![Retro](../docs/bilder/vorlage-retro.png)
![Rennsport](../docs/bilder/vorlage-rennsport.png)
![Cockpit](../docs/bilder/vorlage-cockpit.png)
![Minimal](../docs/bilder/vorlage-minimal.png)
![Alle Elemente](../docs/bilder/vorlage-alle-elemente.png)

Die Bilder zeigen die Vorschau mit Demo-Werten. Neu erzeugen mit `python tools/make_examples.py` (braucht Pillow: `pip install pillow`).

## Auf den Tacho bringen

**SD-Karte:** Datei → Auf SD-Karte exportieren, Laufwerk der Karte wählen. Der Designer legt den Ordner `s51` an und schreibt `design.s51` und `tacho.cfg` hinein. Liegt dort schon eine `tacho.cfg`, fragt er, ob sie überschrieben werden soll.

**WLAN:** Datei → Drahtlos übertragen. Ablauf und Protokoll: [docs/uebertragung.md](../docs/uebertragung.md).

**Einstellungen** (Radumfang, Warnschwellen, Alarm, WLAN …): Einstellungen → Tacho-Konfiguration bearbeiten. Erklärung aller Werte: [docs/konfiguration.md](../docs/konfiguration.md).

## Dateien

| Datei | Inhalt | Beschreibung |
|---|---|---|
| `*.s51` | Layout (binär) | [docs/dateiformat-layout.md](../docs/dateiformat-layout.md) |
| `tacho.cfg` | Einstellungen (Text) | [docs/konfiguration.md](../docs/konfiguration.md) |
| `beispiele/*.s51` | Mitgelieferte Layouts, siehe Vorlagen | |

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
| `s51design/images.py` | Bilder: Umrechnung nach RGB565, Komprimierung, Größe ändern, PNG lesen und schreiben, mitgeliefertes Logo |
| `s51design/app.py` | Oberfläche |
| `s51design/theme.py` | Farben, Schriften und Aussehen der Oberfläche |
| `s51design/icons.py` | Symbole als eingebettete PNG-Daten (erzeugt von `tools/make_icons.py`) |
| `s51design/presets.py` | Mitgelieferte Layouts |
| `tools/gen_cpp_header.py` | Erzeugt den C++-Teil des Schemas für die Firmware |
| `tools/preview_png.py` | Vorschaubilder von Layouts als PNG, ohne Fenster (braucht Pillow) |
| `tools/make_examples.py` | Schreibt alle Vorlagen nach `beispiele/` und ihre Bilder nach `docs/bilder/` |
| `tools/make_icons.py` | Zeichnet die Symbole der Oberfläche neu (braucht Pillow) |
| `tools/screenshots.py` | Bildschirmfotos der Oberfläche nach `docs/bilder/designer/` (Linux mit Xvfb und ImageMagick) |

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

Was die Tests **nicht** abdecken: wie die Oberfläche tatsächlich aussieht. Dafür macht `.github/workflows/designer-screenshots.yml` auf GitHub Bildschirmfotos des laufenden Programms unter Linux (Actions → „Designer-Bildschirmfotos“ → Run workflow). Unter Windows und macOS sehen Schriften und Abstände etwas anders aus.
