# Hinweise für die Arbeit an diesem Repo

## Grundregel: nachbaubar nur aus dem Repo

Jemand ohne Vorwissen und ohne Zugang zu Chats, Notizen oder anderen Quellen muss das Projekt allein mit diesem Repo nachbauen können. Daraus folgt:

- Jede Entscheidung, jedes Maß und jede Pinbelegung steht im Repo, nicht nur im Gespräch.
- Wer Hardware ändert, aktualisiert im selben Commit `docs/stueckliste.md`, `docs/bauplan.md` und die Schaltpläne in `hardware/`.
- Wer Pins ändert, ändert sie nur in `firmware/include/pins.h` und passt `docs/bauplan.md` Abschnitt 2 an.
- Software-Abhängigkeiten sind in `firmware/platformio.ini` auf exakte Versionen gepinnt.
- Alle Nummern der Dateiformate (Element-Typen, Datenquellen, Eigenschaften, Konfigurationsschlüssel) stehen nur in `designer/s51design/schema.py`. Nach jeder Änderung `python tools/gen_cpp_header.py` im Ordner `designer/` ausführen und die Doku in `docs/` anpassen. Vorhandene Nummern nie umbelegen.
- Vor jedem Commit die Tests laufen lassen: `python -m unittest discover -s tests` im Ordner `designer/`.
- CAD-Dateien liegen als Quelle (bearbeitbar) und als STL/STEP in `cad/`, mit Druckeinstellungen in einer README daneben.
- Die Statustabelle in `README.md` sagt ehrlich, was getestet ist und was nicht. Ungetestetes wird als ungetestet markiert.
- Keine fremden Datenblätter oder sonstigen Dateien ohne passende Lizenz ins Repo legen. Stattdessen verlinken (`docs/datenblaetter.md`) und das Wichtigste selbst zusammenfassen.
- Neue Code-Dateien stehen unter MIT, alles andere unter CC BY-SA 4.0 (siehe `LICENSE.md`).
- Keine persönlichen Bezüge in der Doku („du“, „deine Lampe“). Die Doku richtet sich an jeden, der nachbaut.

## Sprache und Stil

- Doku, Kommentare und Commit-Nachrichten auf Deutsch.
- Code-Bezeichner auf Englisch, außer bei fahrzeugspezifischen Begriffen (Blinker, Leerlauf, Zündung).

## Aufbau

| Pfad | Inhalt |
|---|---|
| `docs/bauplan.md` | Was gebaut wird und warum, Ablauf, Phasen |
| `docs/stueckliste.md` | Alle Teile mit Menge, Zweck, Phase |
| `docs/datenblaetter.md` | Links zu den Datenblättern der Hauptteile |
| `docs/dateiformat-layout.md`, `docs/konfiguration.md`, `docs/uebertragung.md` | Dateiformate und WLAN-Protokoll |
| `designer/` | PC-Programm S51 Designer, Encoder/Decoder in Python, Tests |
| `firmware/` | PlatformIO-Projekt |
| `firmware/lib/s51layout/` | Decoder für Layout und Konfiguration in C++ |
| `hardware/` | Schaltpläne und Verdrahtung |
| `cad/` | Gehäuse und Halter |
