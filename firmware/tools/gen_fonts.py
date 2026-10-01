"""Erzeugt data/s51fonts.bin: alle Schriften des Tachos in einer Datei.

Aufruf im Ordner firmware/:   python tools/gen_fonts.py
Braucht Pillow (pip install pillow). Die fertige Datei liegt im Repo, zum
Bauen der Firmware ist Pillow also nicht nötig.

Jede Schrift ist eine VLW-Datei (Format von Processing): je Zeichen ein
Graustufenbild mit 8 Bit Deckung, dadurch kantengeglättet. Größe = Pixelgröße
wie im Designer (Eigenschaft „Schriftgröße (px)“). Gezeichnet wird mit
firmware/lib/s51render/src/s51_text.cpp.

Aufbau von s51fonts.bin (Little Endian):
    0   4  Kennung "S51F"
    4   2  Version (1)
    6   2  Anzahl Schriften n
    8   n × 12 Byte Verzeichnis:
           u8  Familie (0 = Normal, 1 = Fett, 2 = 7-Segment, wie im Layout-Format)
           u8  Zeichensatz (0 = alle Zeichen, 1 = nur Ziffern und Zahlzeichen)
           u16 Größe in Pixel
           u32 Start der VLW-Daten (ab Dateianfang)
           u32 Länge der VLW-Daten
    danach die VLW-Daten
"""

import os
import struct

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "data", "s51fonts.bin")

FAMILIES = [
    (0, "DejaVuSans.ttf"),
    (1, "DejaVuSans-Bold.ttf"),
    (2, "DejaVuSansMono-Bold.ttf"),
]

# Alle Zeichen: ASCII und was in deutschen Texten und Einheiten vorkommt
FULL = [chr(c) for c in range(32, 127)] + list("°²³µ·×äöüÄÖÜß–—‘’‚“”„…€♪•←↑→↓")
# Große Größen nur für Zahlen (Geschwindigkeit, Gang, Uhrzeit)
DIGITS = list(" 0123456789.,:-–+°%/")

# Größen mit allen Zeichen und Größen nur mit Ziffern. Bis 22 px gibt es jede
# Größe genau, darüber rechnet die Firmware aus der nächstgrößeren Schrift herunter
# (Flächenmittelung) und über der größten hinauf.
SIZES_FULL = list(range(8, 23)) + [26, 34, 46]
SIZES_DIGITS = [64, 100, 160]


def vlw(ttf, size, chars):
    font = ImageFont.truetype(ttf, size)
    ascent, descent = font.getmetrics()
    glyphs = []
    for ch in sorted(set(chars), key=ord):
        if ord(ch) != 32 and font.getmask(ch).getbbox() is None:
            continue                                  # Zeichen fehlt in der Schrift
        l, t, r, b = font.getbbox(ch)                 # Ursprung: links, Oberkante Ascent
        exact = font.getlength(ch)
        adv = int(round(exact))
        fine = int(round(exact * 64))                 # genaue Vorschubbreite in 1/64 Pixel
        if ch == " " or r <= l or b <= t:
            glyphs.append((ord(ch), 0, 0, adv, 0, 0, fine, b""))
            continue
        w, h = r - l, b - t
        img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(img).text((-l, -t), ch, font=font, fill=255)
        if w > 255 or adv > 255 or not -128 <= l <= 127:
            raise ValueError(f"Zeichen {ch!r} in Größe {size} zu breit für VLW")
        glyphs.append((ord(ch), h, w, adv, ascent - t, l, fine, img.tobytes()))
    head = struct.pack(">6I", len(glyphs), 11, size, 0, ascent, descent)
    # Das 7. Feld ist in VLW unbenutzt. Hier steht die genaue Vorschubbreite in 1/64 Pixel,
    # damit Textbreiten am Tacho genauso herauskommen wie im Designer.
    meta = b"".join(struct.pack(">7i", u, h, w, adv, dy, dx, fine) for u, h, w, adv, dy, dx, fine, _ in glyphs)
    return head + meta + b"".join(g[7] for g in glyphs)


def main():
    entries = []
    for fam, name in FAMILIES:
        ttf = os.path.join(ROOT, "fonts", name)
        for size in SIZES_FULL:
            entries.append((fam, 0, size, vlw(ttf, size, FULL)))
        for size in SIZES_DIGITS:
            entries.append((fam, 1, size, vlw(ttf, size, DIGITS)))
    offset = 8 + 12 * len(entries)
    index, blobs = b"", b""
    for fam, subset, size, data in entries:
        index += struct.pack("<BBHII", fam, subset, size, offset + len(blobs), len(data))
        blobs += data
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(b"S51F" + struct.pack("<HH", 1, len(entries)) + index + blobs)
    print(f"geschrieben: {os.path.relpath(OUT)} ({len(entries)} Schriften, {(len(index) + len(blobs)) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
