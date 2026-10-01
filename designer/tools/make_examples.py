"""Schreibt alle mitgelieferten Layouts nach designer/beispiele/ und
Vorschaubilder nach docs/bilder/.

Aufruf im Ordner designer/:  python tools/make_examples.py
Die Vorschaubilder brauchen Pillow (pip install pillow). Ohne Pillow
werden nur die .s51-Dateien geschrieben.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import layout_format, presets  # noqa: E402

EXAMPLES = os.path.join(HERE, "..", "beispiele")
IMAGES = os.path.join(HERE, "..", "..", "docs", "bilder")
CREATED = 1790812800      # festes Datum, damit die Dateien bei jedem Lauf gleich sind


def slug(name):
    return (name.lower().replace(" ", "-").replace("ä", "ae").replace("ö", "oe")
            .replace("ü", "ue").replace("ß", "ss"))


def main():
    try:
        import preview_png
    except ImportError:
        preview_png = None
        print("Pillow fehlt, Vorschaubilder werden übersprungen")
    os.makedirs(EXAMPLES, exist_ok=True)
    os.makedirs(IMAGES, exist_ok=True)
    for name, make in presets.PRESETS.items():
        layout = make()
        layout.created = CREATED
        path = os.path.join(EXAMPLES, slug(name) + ".s51")
        n = layout_format.save(layout, path, tool="S51 Designer")
        print(f"{os.path.relpath(path)}: {n} Bytes")
        if preview_png:
            img = os.path.join(IMAGES, f"vorlage-{slug(name)}.png")
            preview_png.contact_sheet(layout, z=1).save(img, optimize=True)
            print(os.path.relpath(img))


if __name__ == "__main__":
    main()
