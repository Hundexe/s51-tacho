"""Erzeugt PNG-Vorschaubilder von Layouts, ohne Fenster.

Nutzt denselben Zeichencode wie der Designer (s51design/render.py), nur auf
ein Pillow-Bild statt auf eine Tk-Canvas. Braucht das Paket Pillow.

Aufruf im Ordner designer/:
  python tools/preview_png.py beispiele/klar.s51            # alle Seiten
  python tools/preview_png.py --preset Retro --out vorschau  # mitgeliefertes Layout
"""

import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import layout_format, presets, render  # noqa: E402
from s51design import images as I  # noqa: E402
from s51design import values as V  # noqa: E402

FONT_FILES = {
    ("normal", False): ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf"],
    ("bold", False): ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"],
    ("bold", True): ["DejaVuSansMono-Bold.ttf", "consolab.ttf", "Courier New Bold.ttf"],
    ("normal", True): ["DejaVuSansMono.ttf", "consola.ttf", "Courier New.ttf"],
}
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts", "/Library/Fonts",
             "/System/Library/Fonts/Supplemental"]
_font_cache = {}


def _font(family, px, weight):
    mono = family.lower() in ("consolas", "courier new", "courier")
    key = (weight if weight == "bold" else "normal", mono, px)
    if key in _font_cache:
        return _font_cache[key]
    font = None
    for name in FONT_FILES[key[:2]]:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                font = ImageFont.truetype(p, px)
                break
        if font:
            break
    font = font or ImageFont.load_default()
    _font_cache[key] = font
    return font


def _chaikin(points, rounds=3):
    pts = list(points)
    for _ in range(rounds):
        out = []
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        pts = out
    return pts


def _wrap(text, font, width):
    """Bricht an Leerzeichen um wie Tk bei create_text(width=…)."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = word if not cur else cur + " " + word
            if font.getlength(test) <= width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


class PilCanvas:
    """Bildet die Teile der Tk-Canvas nach, die render.py benutzt."""

    def __init__(self, width, height):
        self.img = Image.new("RGB", (width, height), "#000000")
        self.d = ImageDraw.Draw(self.img)
        self._id = 0

    def _next(self):
        self._id += 1
        return self._id

    def delete(self, *a):
        pass

    def create_rectangle(self, x0, y0, x1, y1, fill="", outline="", width=1, **kw):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        self.d.rectangle([x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)], fill=fill or None,
                         outline=outline or None, width=max(1, int(round(width))) if outline else 0)
        return self._next()

    def create_polygon(self, points, fill="", outline="", smooth=False, width=1, **kw):
        pts = list(zip(points[0::2], points[1::2]))
        if smooth:
            pts = _chaikin(pts)
        self.d.polygon(pts, fill=fill or None, outline=outline or None)
        return self._next()

    def create_oval(self, x0, y0, x1, y1, fill="", outline="", **kw):
        self.d.ellipse([x0, y0, x1, y1], fill=fill or None, outline=outline or None)
        return self._next()

    def create_line(self, x0, y0, x1, y1, fill="", width=1, **kw):
        self.d.line([x0, y0, x1, y1], fill=fill, width=max(1, int(round(width))))
        return self._next()

    def create_arc(self, x0, y0, x1, y1, start=0, extent=90, style="arc", outline="", fill="", width=1, **kw):
        # Tk: Grad gegen den Uhrzeigersinn ab 3 Uhr. Pillow: im Uhrzeigersinn.
        a, b = -start, -(start + extent)
        lo, hi = min(a, b), max(a, b)
        if style == "chord":
            self.d.chord([x0, y0, x1, y1], lo, hi, fill=fill or None, outline=outline or None)
        else:
            # Tk zeichnet die Linie mittig auf dem Kreis, Pillow nach innen ab dem Rand
            wd = max(1, int(round(width)))
            h = wd / 2
            self.d.arc([x0 - h, y0 - h, x1 + h, y1 + h], lo, hi, fill=outline, width=wd)
        return self._next()

    def create_text(self, x, y, text="", fill="", font=None, anchor="center", width=0, justify="left", **kw):
        family, size, weight = font if font else ("Arial", -12, "normal")
        px = abs(int(size))
        f = _font(family, px, weight)
        if width:
            lines = _wrap(text, f, width)
            step = px * 1.2
            top = y - step * (len(lines) - 1) / 2
            for i, line in enumerate(lines):
                if anchor == "w":
                    lx, a = x, "lm"
                elif anchor == "e":
                    lx, a = x, "rm"
                else:
                    lx, a = x, "mm"
                self.d.text((lx, top + i * step), line, fill=fill, font=f, anchor=a)
            return self._next()
        pil_anchor = {"center": "mm", "w": "lm", "e": "rm", "nw": "la", "n": "ma", "ne": "ra"}.get(anchor, "mm")
        self.d.text((x, y), text, fill=fill, font=f, anchor=pil_anchor)
        return self._next()

    def tag_raise(self, *a):
        pass

    def create_image(self, x, y, image=None, anchor="nw", **kw):
        if image is not None:
            self.img.paste(image, (int(round(x)), int(round(y))), image)
        return self._next()


def pil_images(layout):
    """Bildnummer, Zoom -> Pillow-Bild (RGBA) für render.draw_screen."""
    cache = {}
    by_id = {img.id: img for img in layout.images}

    def image_for(img_id, z):
        img = by_id.get(img_id)
        if img is None:
            return None
        key = (img_id, z)
        if key not in cache:
            im = Image.frombytes("RGBA", (img.width, img.height), I.to_rgba(img))
            if z != 1:
                im = im.resize((img.width * z, img.height * z), Image.NEAREST)
            cache[key] = im
        return cache[key]
    return image_for


def render_screen(layout, screen, z=2, animate_t=None):
    vals = V.demo_values(t=animate_t, animate=animate_t is not None)
    c = PilCanvas(layout.width * z, layout.height * z)
    render.draw_screen(c, screen, z, vals, (layout.width, layout.height), show_hidden=False, t=0.1,
                       image_for=pil_images(layout))
    return c.img


def contact_sheet(layout, z=1, cols=2, pad=16, label=True):
    imgs = [render_screen(layout, s, z) for s in layout.screens]
    w, h = layout.width * z, layout.height * z
    rows = math.ceil(len(imgs) / cols)
    lab = 24 if label else 0
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * (h + lab) + (rows + 1) * pad), "#3a3a38")
    d = ImageDraw.Draw(sheet)
    f = _font("Arial", 16, "bold")
    for i, (img, s) in enumerate(zip(imgs, layout.screens)):
        x = pad + (i % cols) * (w + pad)
        y = pad + (i // cols) * (h + lab + pad)
        if label:
            role = "  (Nachtversion)" if s.role == "night" else ""
            d.text((x, y), f"{s.id}: {s.name}{role}", fill="#F1EFE8", font=f)
        sheet.paste(img, (x, y + lab))
    return sheet


def main():
    ap = argparse.ArgumentParser(description="PNG-Vorschau von S51-Layouts")
    ap.add_argument("datei", nargs="?")
    ap.add_argument("--preset")
    ap.add_argument("--out", default=".")
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--sheet", action="store_true", help="alle Seiten in einem Bild")
    args = ap.parse_args()
    layout = presets.PRESETS[args.preset]() if args.preset else layout_format.load(args.datei)
    os.makedirs(args.out, exist_ok=True)
    base = (args.preset or os.path.splitext(os.path.basename(args.datei))[0]).lower()
    if args.sheet:
        p = os.path.join(args.out, f"{base}.png")
        contact_sheet(layout, z=1).save(p)
        print(p)
        return
    for s in layout.screens:
        p = os.path.join(args.out, f"{base}-{s.id}.png")
        render_screen(layout, s, args.zoom).save(p)
        print(p)


if __name__ == "__main__":
    main()
