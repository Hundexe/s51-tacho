"""Erzeugt die Symbole des Designers als eingebettete PNG-Daten.

Aufruf im Ordner designer/:  python tools/make_icons.py
Schreibt s51design/icons.py. Braucht Pillow, aber nur hier beim Erzeugen.
Der Designer selbst lädt die fertigen PNG-Daten ohne Zusatzpakete.
"""

import base64
import io
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "s51design", "icons.py")

S = 4                      # Überabtastung für weiche Kanten
FG = (214, 222, 218, 255)
ACCENT = (95, 179, 155, 255)
FONT_BOLD = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                              "C:/Windows/Fonts/arialbd.ttf") if os.path.exists(p)), None)


def canvas(size):
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def finish(img, size):
    return img.resize((size, size), Image.LANCZOS)


def P(*pts):
    return [(x * S, y * S) for x, y in pts]


def line(d, pts, col, w=1.6):
    d.line(P(*pts), fill=col, width=int(w * S), joint="curve")
    for x, y in pts:                       # runde Enden
        r = w * S / 2
        d.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=col)


def rect(d, x0, y0, x1, y1, col, w=1.6, r=2, fill=None):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, outline=col,
                        width=int(w * S), fill=fill)


def arc(d, cx, cy, rad, a0, a1, col, w=1.6):
    d.arc([(cx - rad) * S, (cy - rad) * S, (cx + rad) * S, (cy + rad) * S], a0, a1, fill=col, width=int(w * S))


def text(d, x, y, s, size, col):
    font = ImageFont.truetype(FONT_BOLD, int(size * S)) if FONT_BOLD else ImageFont.load_default()
    d.text((x * S, y * S), s, font=font, fill=col, anchor="mm")


# ---------------------------------------------------------------------------
# Symbolleiste, 20 px
# ---------------------------------------------------------------------------

def ic_new(d, c):
    line(d, [(5, 3), (12, 3), (15, 6), (15, 17), (5, 17), (5, 3)], c)
    line(d, [(10, 9), (10, 14)], c)
    line(d, [(7.5, 11.5), (12.5, 11.5)], c)


def ic_open(d, c):
    line(d, [(3, 5), (8, 5), (10, 7), (17, 7), (17, 16), (3, 16), (3, 5)], c)
    line(d, [(3, 10), (17, 10)], c)


def ic_save(d, c):
    line(d, [(4, 3), (14, 3), (17, 6), (17, 17), (4, 17), (4, 3)], c)
    rect(d, 7, 3, 13, 7.5, c, r=0.5)
    rect(d, 7, 11, 14, 17, c, r=0.5)


def ic_undo(d, c):
    arc(d, 11, 11, 5.5, 180, 360 + 70, c)
    line(d, [(5.5, 11), (3, 8)], c)
    line(d, [(5.5, 11), (8.5, 9)], c)


def ic_redo(d, c):
    arc(d, 9, 11, 5.5, 110, 360, c)
    line(d, [(14.5, 11), (17, 8)], c)
    line(d, [(14.5, 11), (11.5, 9)], c)


def ic_duplicate(d, c):
    rect(d, 3, 3, 12, 12, c)
    rect(d, 8, 8, 17, 17, c, fill=(0, 0, 0, 0))


def ic_delete(d, c):
    line(d, [(3, 5.5), (17, 5.5)], c)
    line(d, [(8, 5.5), (8, 3), (12, 3), (12, 5.5)], c)
    line(d, [(5, 5.5), (6, 17), (14, 17), (15, 5.5)], c)
    line(d, [(8.5, 9), (8.5, 14)], c)
    line(d, [(11.5, 9), (11.5, 14)], c)


def ic_front(d, c):
    rect(d, 7, 7, 17, 17, c, w=1.2)
    rect(d, 3, 3, 13, 13, c, fill=c)


def ic_back(d, c):
    rect(d, 3, 3, 13, 13, c, w=1.2)
    rect(d, 7, 7, 17, 17, c, fill=c)


def ic_sd(d, c):
    line(d, [(5, 2.5), (12, 2.5), (15.5, 6), (15.5, 17.5), (5, 17.5), (5, 2.5)], c)
    for x in (8, 10.5, 13):
        line(d, [(x, 5), (x, 8)], c, w=1.3)


def ic_wifi(d, c):
    for rad in (11, 7, 3.2):
        arc(d, 10, 16, rad, 225, 315, c)
    d.ellipse([9 * S, 15 * S, 11 * S, 17 * S], fill=c)


def ic_settings(d, c):
    for k in range(8):
        a = k * math.pi / 4
        line(d, [(10 + math.cos(a) * 5.5, 10 + math.sin(a) * 5.5), (10 + math.cos(a) * 8, 10 + math.sin(a) * 8)],
             c, w=2.2)
    arc(d, 10, 10, 5.5, 0, 360, c)
    arc(d, 10, 10, 2.2, 0, 360, c)


def ic_play(d, c):
    d.polygon(P((6, 4), (16, 10), (6, 16)), fill=c)


def ic_grid(d, c):
    for v in (6.5, 13.5):
        line(d, [(v, 3), (v, 17)], c, w=1.2)
        line(d, [(3, v), (17, v)], c, w=1.2)


def ic_magnet(d, c):
    arc(d, 10, 9, 5.5, 180, 360, c, w=3)
    line(d, [(4.5, 9), (4.5, 15)], c, w=3)
    line(d, [(15.5, 9), (15.5, 15)], c, w=3)


def ic_eye(d, c):
    arc(d, 10, 16, 9, 220, 320, c)
    arc(d, 10, 4, 9, 40, 140, c)
    d.ellipse([7.3 * S, 7.3 * S, 12.7 * S, 12.7 * S], fill=c)


def ic_plus(d, c):
    line(d, [(10, 4), (10, 16)], c, w=1.8)
    line(d, [(4, 10), (16, 10)], c, w=1.8)


def ic_up(d, c):
    line(d, [(5, 12.5), (10, 7.5), (15, 12.5)], c, w=1.8)


def ic_down(d, c):
    line(d, [(5, 7.5), (10, 12.5), (15, 7.5)], c, w=1.8)


def ic_lock(d, c):
    rect(d, 4.5, 9, 15.5, 17, c, fill=c)
    arc(d, 10, 9, 3.6, 180, 360, c)
    line(d, [(6.4, 9), (6.4, 9.5)], c)
    line(d, [(13.6, 9), (13.6, 9.5)], c)


def ic_hidden(d, c):
    ic_eye(d, c)
    line(d, [(4, 16), (16, 4)], c, w=1.8)


def ic_image_load(d, c):
    rect(d, 3, 4, 17, 16, c)
    d.polygon(P((5, 14), (9, 9), (12, 12), (13.5, 10.5), (15, 14)), fill=c)
    d.ellipse([12 * S, 6 * S, 14.5 * S, 8.5 * S], fill=c)


# ---------------------------------------------------------------------------
# Element-Kacheln, 26 px
# ---------------------------------------------------------------------------

def el_text(d, c):
    text(d, 13, 13.5, "Aa", 12, c)


def el_value(d, c):
    text(d, 13, 13.5, "88", 13, c)


def el_bar(d, c):
    for k, x in enumerate(range(3, 23, 4)):
        col = c if k < 4 else (c[0], c[1], c[2], 90)
        d.rectangle([x * S, 10 * S, (x + 3) * S, 16 * S], fill=col)


def el_gauge(d, c):
    arc(d, 13, 15, 9, 150, 390, (c[0], c[1], c[2], 90), w=2.6)
    arc(d, 13, 15, 9, 150, 300, c, w=2.6)
    line(d, [(13, 15), (18, 9.5)], c, w=1.8)


def el_indicator(d, c):
    d.polygon(P((3, 13), (11, 6), (11, 10), (21, 10), (21, 16), (11, 16), (11, 20)), fill=c)


def el_rect(d, c):
    rect(d, 4, 6, 22, 20, c, w=1.8, r=3, fill=(c[0], c[1], c[2], 60))


def el_image(d, c):
    rect(d, 3, 5, 23, 21, c, w=1.6, r=2)
    d.polygon(P((5, 19), (10.5, 12), (14.5, 16), (17, 13.5), (21, 19)), fill=c)
    d.ellipse([16 * S, 7.5 * S, 19.5 * S, 11 * S], fill=c)


TOOL = {name[3:]: fn for name, fn in list(globals().items()) if name.startswith("ic_")}
ELEMENTS = {name[3:]: fn for name, fn in list(globals().items()) if name.startswith("el_")}


def png_b64(fn, size, col):
    img, d = canvas(size)
    fn(d, col)
    out = io.BytesIO()
    finish(img, size).save(out, "PNG", optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


def main():
    lines = ['"""Symbole des Designers als PNG (base64).', "",
             "ERZEUGT von tools/make_icons.py. Nicht von Hand ändern.", '"""', "", "TOOL = {"]
    for name, fn in TOOL.items():
        lines.append(f'    "{name}": "{png_b64(fn, 20, FG)}",')
    lines += ["}", "", "TOOL_ACCENT = {"]
    for name, fn in TOOL.items():
        lines.append(f'    "{name}": "{png_b64(fn, 20, ACCENT)}",')
    lines += ["}", "", "ELEMENTS = {"]
    for name, fn in ELEMENTS.items():
        lines.append(f'    "{name}": "{png_b64(fn, 26, ACCENT)}",')
    lines += ["}", ""]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("geschrieben:", os.path.relpath(OUT), f"({len(TOOL)} Symbole, {len(ELEMENTS)} Elemente)")


if __name__ == "__main__":
    main()
