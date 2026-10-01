"""Bilder im Layout: Umrechnung, Kodierung (RGB565, Alpha, Lauflänge) und PNG.

Kommt ohne Zusatzpakete aus. Ist Pillow installiert, kann der Designer
zusätzlich JPG, BMP und andere Formate einlesen.

Kodierung der Pixel: siehe docs/dateiformat-layout.md, Abschnitt 3.4.
"""

import math
import struct
import zlib
from dataclasses import dataclass

from . import schema as S


class ImageError(Exception):
    pass


@dataclass
class Image:
    id: int
    name: str
    width: int
    height: int
    pixels: list                 # RGB565 je Pixel, zeilenweise von oben links
    alpha: bytes = None          # 0–255 je Pixel, None = undurchsichtig

    @property
    def has_alpha(self):
        return self.alpha is not None

    # Bilder werden nie verändert, sondern nur ersetzt. Kopien (z. B. für
    # Rückgängig) dürfen daher dasselbe Objekt benutzen, das spart Speicher.
    def __deepcopy__(self, memo):
        return self

    def __copy__(self):
        return self


# ---------------------------------------------------------------------------
# Farben
# ---------------------------------------------------------------------------

def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb565_to_rgb(v):
    r, g, b = (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def from_rgba(img_id, name, width, height, rgba):
    """RGBA-Bytes (4 je Pixel) -> Image. Alpha wird nur gespeichert, wenn nötig."""
    if not (1 <= width <= S.MAX_IMAGE_SIDE and 1 <= height <= S.MAX_IMAGE_SIDE):
        raise ImageError(f"Bild {width}×{height} zu groß, höchstens {S.MAX_IMAGE_SIDE}×{S.MAX_IMAGE_SIDE}")
    if len(rgba) != width * height * 4:
        raise ImageError("Pixeldaten passen nicht zur Bildgröße")
    pixels = [rgb_to_565(rgba[i], rgba[i + 1], rgba[i + 2]) for i in range(0, len(rgba), 4)]
    alpha = bytes(rgba[3::4])
    if all(a == 255 for a in alpha):
        alpha = None
    return Image(img_id, name, width, height, pixels, alpha)


def to_rgba(img):
    out = bytearray(img.width * img.height * 4)
    for i, v in enumerate(img.pixels):
        r, g, b = rgb565_to_rgb(v)
        out[i * 4:i * 4 + 4] = bytes((r, g, b, img.alpha[i] if img.alpha is not None else 255))
    return bytes(out)


# ---------------------------------------------------------------------------
# Kodierung im Layout
# ---------------------------------------------------------------------------

def _pixel_bytes(img, i):
    v = img.pixels[i]
    if img.alpha is None:
        return bytes((v & 0xFF, v >> 8))
    return bytes((v & 0xFF, v >> 8, img.alpha[i]))


def encode_raw(img):
    return b"".join(_pixel_bytes(img, i) for i in range(len(img.pixels)))


def encode_rle(img):
    """Lauflänge: Steuerbyte b. b >= 128: (b-127) gleiche Pixel, ein Pixel folgt.
    b < 128: (b+1) einzelne Pixel folgen."""
    n = len(img.pixels)
    key = (lambda i: (img.pixels[i], img.alpha[i])) if img.alpha is not None else (lambda i: img.pixels[i])
    out = bytearray()
    i = 0
    while i < n:
        j = i
        while j + 1 < n and j + 1 - i < 128 and key(j + 1) == key(i):
            j += 1
        run = j - i + 1
        if run >= 2:
            out.append(0x80 | (run - 1))
            out += _pixel_bytes(img, i)
            i = j + 1
            continue
        start = i
        while i < n and i - start < 128:
            if i + 2 < n and key(i) == key(i + 1) == key(i + 2):
                break
            i += 1
        if i == start:          # passiert nicht, Absicherung gegen Endlosschleife
            i += 1
        out.append(i - start - 1)
        for k in range(start, i):
            out += _pixel_bytes(img, k)
    return bytes(out)


def encode_pixels(img):
    """Wählt die kleinere Kodierung. Gibt (Format, Daten) zurück. Das Ergebnis
    wird am Bild zwischengespeichert, weil Bilder nicht verändert werden."""
    cached = getattr(img, "_encoded", None)
    if cached is None:
        raw, rle = encode_raw(img), encode_rle(img)
        cached = (S.IMAGE_FORMAT_RLE, rle) if len(rle) < len(raw) else (S.IMAGE_FORMAT_RAW, raw)
        img._encoded = cached
    return cached


def decode_pixels(fmt, has_alpha, width, height, data):
    n = width * height
    step = 3 if has_alpha else 2
    pixels = [0] * n
    alpha = bytearray(n) if has_alpha else None

    def put(idx, pos):
        pixels[idx] = data[pos] | (data[pos + 1] << 8)
        if has_alpha:
            alpha[idx] = data[pos + 2]

    if fmt == S.IMAGE_FORMAT_RAW:
        if len(data) != n * step:
            raise ImageError("Bilddaten haben die falsche Länge")
        for i in range(n):
            put(i, i * step)
    elif fmt == S.IMAGE_FORMAT_RLE:
        pos, idx = 0, 0
        while idx < n:
            if pos >= len(data):
                raise ImageError("Bilddaten abgeschnitten")
            b = data[pos]
            pos += 1
            if b & 0x80:
                count = (b & 0x7F) + 1
                if pos + step > len(data) or idx + count > n:
                    raise ImageError("Bilddaten fehlerhaft")
                for _ in range(count):
                    put(idx, pos)
                    idx += 1
                pos += step
            else:
                count = b + 1
                if pos + count * step > len(data) or idx + count > n:
                    raise ImageError("Bilddaten fehlerhaft")
                for _ in range(count):
                    put(idx, pos)
                    idx += 1
                    pos += step
        if pos != len(data):
            raise ImageError("Bilddaten länger als das Bild")
    else:
        raise ImageError(f"Unbekanntes Bildformat {fmt}")
    return pixels, (bytes(alpha) if has_alpha else None)


# ---------------------------------------------------------------------------
# Größe ändern
# ---------------------------------------------------------------------------

def fit_size(width, height, max_w, max_h):
    """Größe innerhalb max_w × max_h, Seitenverhältnis bleibt."""
    f = min(max_w / width, max_h / height)
    return max(1, round(width * f)), max(1, round(height * f))


def resize_rgba(width, height, rgba, new_w, new_h):
    """Flächenmittelung beim Verkleinern, nächster Nachbar beim Vergrößern.
    Farben werden mit Alpha gewichtet, damit transparente Ränder nicht dunkel werden."""
    if (new_w, new_h) == (width, height):
        return bytes(rgba)
    out = bytearray(new_w * new_h * 4)
    sx, sy = width / new_w, height / new_h
    for y in range(new_h):
        y0 = int(y * sy)
        y1 = max(y0 + 1, min(height, int(math.ceil((y + 1) * sy))))
        for x in range(new_w):
            x0 = int(x * sx)
            x1 = max(x0 + 1, min(width, int(math.ceil((x + 1) * sx))))
            r = g = b = a = cnt = 0
            for yy in range(y0, y1):
                row = yy * width
                for xx in range(x0, x1):
                    p = (row + xx) * 4
                    pa = rgba[p + 3]
                    r += rgba[p] * pa
                    g += rgba[p + 1] * pa
                    b += rgba[p + 2] * pa
                    a += pa
                    cnt += 1
            o = (y * new_w + x) * 4
            if a:
                out[o:o + 4] = bytes((r // a, g // a, b // a, a // cnt))
    return bytes(out)


# ---------------------------------------------------------------------------
# PNG lesen und schreiben (ohne Zusatzpakete)
# ---------------------------------------------------------------------------

def png_encode(width, height, rgba):
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def png_decode(data):
    """PNG mit 8 Bit je Kanal (Grau, RGB, Palette, mit/ohne Alpha) -> (Breite, Höhe, RGBA)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ImageError("Keine PNG-Datei")
    pos, idat, palette, trns = 8, b"", None, None
    width = height = depth = ctype = interlace = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype_name = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype_name == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif ctype_name == b"PLTE":
            palette = body
        elif ctype_name == b"tRNS":
            trns = body
        elif ctype_name == b"IDAT":
            idat += body
        elif ctype_name == b"IEND":
            break
    if depth != 8 or interlace:
        raise ImageError("Nur PNG mit 8 Bit je Kanal und ohne Interlacing. Bitte mit installiertem Pillow öffnen "
                         "oder das Bild in einem Bildprogramm neu speichern.")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        raise ImageError("PNG-Farbtyp wird nicht unterstützt")
    raw = zlib.decompress(idat)
    stride = width * channels
    prev = bytearray(stride)
    out = bytearray(width * height * 4)
    p = 0
    for y in range(height):
        ftype = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
            elif ftype == 4:
                line[i] = (line[i] + _paeth(a, b, c)) & 0xFF
        prev = line
        for x in range(width):
            o = (y * width + x) * 4
            px = line[x * channels:(x + 1) * channels]
            if ctype == 0:
                out[o:o + 4] = bytes((px[0], px[0], px[0], 255))
            elif ctype == 4:
                out[o:o + 4] = bytes((px[0], px[0], px[0], px[1]))
            elif ctype == 2:
                out[o:o + 4] = bytes((px[0], px[1], px[2], 255))
            elif ctype == 6:
                out[o:o + 4] = bytes(px)
            else:
                k = px[0]
                if palette is None or k * 3 + 2 >= len(palette):
                    raise ImageError("PNG-Palette fehlt oder ist zu kurz")
                a = trns[k] if trns is not None and k < len(trns) else 255
                out[o:o + 4] = bytes((palette[k * 3], palette[k * 3 + 1], palette[k * 3 + 2], a))
    return width, height, bytes(out)


def load_rgba(path):
    """Bilddatei -> (Breite, Höhe, RGBA). Nutzt Pillow, wenn vorhanden, sonst nur PNG."""
    try:
        from PIL import Image as PILImage
    except ImportError:
        PILImage = None
    if PILImage is not None:
        with PILImage.open(path) as im:
            im = im.convert("RGBA")
            return im.width, im.height, im.tobytes()
    with open(path, "rb") as f:
        return png_decode(f.read())


# ---------------------------------------------------------------------------
# Mitgeliefertes Logo (wird berechnet, damit keine Bilddatei nötig ist)
# ---------------------------------------------------------------------------

def make_logo(size=160, ring=(29, 158, 117), needle=(239, 159, 39)):
    """Rundes Tacho-Symbol mit Skala und Zeiger, weich gezeichnet, transparenter Hintergrund."""
    out = bytearray(size * size * 4)
    c = (size - 1) / 2
    r_out, r_in = size * 0.48, size * 0.40
    ang_needle = math.radians(-35)

    def seg_dist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - ax - t * dx, py - ay - t * dy)

    nx, ny = c + math.cos(ang_needle) * r_in * 0.92, c + math.sin(ang_needle) * r_in * 0.92
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(dy, dx)) % 360
            in_arc = not (45 < ang < 135)            # unten offen
            ring_a = max(0.0, min(1.0, min(d - r_in, r_out - d) + 0.5)) if in_arc else 0.0
            tick_a = 0.0
            if in_arc and r_in * 0.78 < d < r_in * 0.92:
                rel = ((ang - 135) % 360) / 270 * 8
                tick_a = max(0.0, 1.0 - abs(rel - round(rel)) * d * 0.9)
            needle_a = max(0.0, min(1.0, size * 0.035 - seg_dist(x, y, c, c, nx, ny) + 0.5))
            hub_a = max(0.0, min(1.0, size * 0.07 - d + 0.5))
            col, a = (0, 0, 0), 0.0
            for layer_col, la in ((ring, ring_a), ((200, 196, 186), tick_a), (needle, needle_a), (needle, hub_a)):
                if la > 0:
                    col = tuple(int(col[k] * (1 - la) + layer_col[k] * la) if a else layer_col[k] for k in range(3))
                    a = la + a * (1 - la)
            o = (y * size + x) * 4
            out[o:o + 4] = bytes((*col, int(round(a * 255))))
    return size, size, bytes(out)
