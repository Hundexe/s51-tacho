"""Vergleicht Designer-Vorschau und Firmware-Renderer für alle Vorlagen.

Aufruf im Ordner firmware/:   python hosttest/compare.py <Zielordner>

Zeichnet jede Seite jeder Vorlage aus designer/beispiele/ zweimal: links mit
der Vorschau des Designers (designer/tools/preview_png.py), rechts mit dem
Renderer der Firmware (hosttest/render.sh). Schreibt je Vorlage ein PNG.
Braucht Pillow, g++ und git.
"""

import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.join(HERE, "..")
DESIGNER = os.path.join(FW, "..", "designer")
sys.path.insert(0, DESIGNER)
sys.path.insert(0, os.path.join(DESIGNER, "tools"))

from PIL import Image, ImageDraw  # noqa: E402

from s51design import layout_format  # noqa: E402
from s51design import values as V  # noqa: E402
import preview_png  # noqa: E402

FIXED_TIME = (14, 27)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "vergleich"
    os.makedirs(out, exist_ok=True)
    # gleiche Uhrzeit in beiden Bildern
    real_localtime = time.localtime
    V.time.localtime = lambda *a: time.struct_time((2026, 1, 1, FIXED_TIME[0], FIXED_TIME[1], 0, 3, 1, 0))
    try:
        beispiele = os.path.join(DESIGNER, "beispiele")
        for name in sorted(f for f in os.listdir(beispiele) if f.endswith(".s51")):
            path = os.path.join(beispiele, name)
            layout = layout_format.load(path)
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run([os.path.join(HERE, "render.sh"), path, tmp, "%02d:%02d" % FIXED_TIME],
                               check=True, stdout=subprocess.DEVNULL)
                rows = []
                for s in layout.screens:
                    left = preview_png.render_screen(layout, s, z=1).convert("RGB")
                    right = Image.open(os.path.join(tmp, f"seite-{s.id}.ppm")).convert("RGB")
                    rows.append((s, left, right))
            w, h, pad, lab = layout.width, layout.height, 12, 20
            sheet = Image.new("RGB", (2 * w + 3 * pad, len(rows) * (h + lab + pad) + pad), "#3a3a38")
            d = ImageDraw.Draw(sheet)
            for i, (s, left, right) in enumerate(rows):
                y = pad + i * (h + lab + pad)
                d.text((pad, y + 3), f"{s.name}: Designer", fill="#F1EFE8")
                d.text((2 * pad + w, y + 3), f"{s.name}: Tacho (Firmware)", fill="#F1EFE8")
                sheet.paste(left, (pad, y + lab))
                sheet.paste(right, (2 * pad + w, y + lab))
            target = os.path.join(out, name.replace(".s51", ".png"))
            sheet.save(target)
            print("geschrieben:", target)
    finally:
        V.time.localtime = real_localtime


if __name__ == "__main__":
    main()
