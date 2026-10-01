"""Encoder und Decoder für Layout-Dateien (.s51).

Aufbau der Datei: siehe docs/dateiformat-layout.md.
Alle Zahlen sind Little-Endian.
"""

import base64
import struct
import time
import zlib
from dataclasses import dataclass, field

from . import images as I
from . import schema as S


WIDGET_HEAD_SIZE = struct.calcsize("<BBhhHHH")   # 12 Bytes
SCREEN_HEAD_SIZE = 8                              # vor dem Namen


class LayoutError(Exception):
    """Datei ist beschädigt oder entspricht nicht dem Format."""


@dataclass
class Widget:
    type: str
    x: int = 0
    y: int = 0
    w: int = 100
    h: int = 40
    hidden: bool = False
    locked: bool = False
    props: dict = field(default_factory=dict)

    @staticmethod
    def new(type_key, x=0, y=0):
        wt = S.WTYPE_BY_KEY[type_key]
        w, h = wt.default_size
        props = {k: S.prop_default(wt, k) for k in wt.props}
        return Widget(type_key, x, y, w, h, props=props)

    def get(self, key):
        if key in self.props:
            return self.props[key]
        wt = S.WTYPE_BY_KEY.get(self.type)
        if wt is None:
            return S.PROP_BY_KEY[key].default
        return S.prop_default(wt, key)


@dataclass
class Screen:
    id: int = 0
    name: str = "Seite"
    role: str = "page"           # page | night | startup
    night_of: int = S.NO_PAGE    # bei role == night: Nummer der Tagseite
    bg: str = "#000000"
    widgets: list = field(default_factory=list)


@dataclass
class Layout:
    width: int = S.DISPLAY_WIDTH
    height: int = S.DISPLAY_HEIGHT
    name: str = "Neues Layout"
    author: str = ""
    created: int = 0
    tool: str = ""
    screens: list = field(default_factory=list)
    images: list = field(default_factory=list)           # images.Image
    unknown_chunks: list = field(default_factory=list)   # (fourcc, bytes), unverändert durchgereicht


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def color_to_bytes(c):
    if not (isinstance(c, str) and len(c) == 7 and c.startswith("#")):
        raise LayoutError(f"Ungültige Farbe {c!r}, erwartet #RRGGBB")
    return bytes.fromhex(c[1:])


def bytes_to_color(b):
    return "#" + b.hex().upper()


def _str_bytes(s):
    b = s.encode("utf-8")
    if len(b) > S.MAX_STRING_BYTES:
        raise LayoutError(f"Text zu lang ({len(b)} Bytes, höchstens {S.MAX_STRING_BYTES}): {s[:30]!r}…")
    return b


def encode_prop(prop, value):
    t = prop.type
    if t == "color":
        return color_to_bytes(value)
    if t == "u8":
        v = int(value)
        if not 0 <= v <= 255:
            raise LayoutError(f"{prop.key} muss zwischen 0 und 255 liegen, ist {v}")
        return struct.pack("<B", v)
    if t == "bool":
        return struct.pack("<B", 1 if value else 0)
    if t == "i16":
        v = int(value)
        if not -32768 <= v <= 32767:
            raise LayoutError(f"{prop.key} außerhalb des Bereichs: {v}")
        return struct.pack("<h", v)
    if t == "f32":
        return struct.pack("<f", float(value))
    if t == "str":
        return _str_bytes(str(value))
    if t.startswith("enum:"):
        return struct.pack("<B", S.enum_code(t[5:], value))
    raise LayoutError(f"Unbekannter Eigenschaftstyp {t}")


def decode_prop(prop, data):
    t = prop.type
    try:
        if t == "color":
            if len(data) != 3:
                raise ValueError
            return bytes_to_color(data)
        if t == "u8":
            return struct.unpack("<B", data)[0]
        if t == "bool":
            return struct.unpack("<B", data)[0] != 0
        if t == "i16":
            return struct.unpack("<h", data)[0]
        if t == "f32":
            return round(struct.unpack("<f", data)[0], 6)
        if t == "str":
            return data.decode("utf-8")
        if t.startswith("enum:"):
            code = struct.unpack("<B", data)[0]
            key = S.enum_key(t[5:], code)
            return key if key is not None else f"#{code}"
    except (struct.error, ValueError, UnicodeDecodeError):
        raise LayoutError(f"Eigenschaft {prop.key}: ungültige Daten ({data.hex()})")
    raise LayoutError(f"Unbekannter Eigenschaftstyp {t}")


def _tlv(code, payload):
    if len(payload) > 255:
        raise LayoutError(f"Eintrag {code} zu lang ({len(payload)} Bytes)")
    return struct.pack("<BB", code, len(payload)) + payload


def _iter_tlv(data):
    pos = 0
    while pos < len(data):
        if pos + 2 > len(data):
            raise LayoutError("Eigenschaftsliste abgeschnitten")
        code, length = data[pos], data[pos + 1]
        pos += 2
        if pos + length > len(data):
            raise LayoutError("Eigenschaft länger als die Liste")
        yield code, data[pos:pos + length]
        pos += length


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

def _encode_widget(w):
    if w.type.startswith("#"):            # unbekannter Typ aus einer neueren Datei
        tcode = int(w.type[1:])
    else:
        wt = S.WTYPE_BY_KEY.get(w.type)
        if wt is None:
            raise LayoutError(f"Unbekannter Element-Typ {w.type!r}")
        tcode = wt.code
    props = b""
    for key, value in w.props.items():
        if key.startswith("#"):          # unbekannte Eigenschaft aus einer neueren Datei
            code = int(key[1:])
            props += _tlv(code, bytes.fromhex(value))
            continue
        prop = S.PROP_BY_KEY.get(key)
        if prop is None:
            raise LayoutError(f"Unbekannte Eigenschaft {key!r}")
        props += _tlv(prop.code, encode_prop(prop, value))
    flags = (S.WFLAG_HIDDEN if w.hidden else 0) | (S.WFLAG_LOCKED if w.locked else 0)
    head = struct.pack("<BBhhHHH", tcode, flags, int(w.x), int(w.y), int(w.w), int(w.h), len(props))
    return head + props


def _encode_screen(s):
    if len(s.widgets) > S.MAX_WIDGETS_PER_SCREEN:
        raise LayoutError(f"Seite {s.name!r} hat mehr als {S.MAX_WIDGETS_PER_SCREEN} Elemente")
    role = ROLES.get(s.role)
    if role is None:
        raise LayoutError(f"Unbekannte Seitenart {s.role!r}")
    name = _str_bytes(s.name)
    out = struct.pack("<BBBB", s.id, role, s.night_of if role == S.ROLE_NIGHT else S.NO_PAGE, 0)
    out += color_to_bytes(s.bg)
    out += struct.pack("<B", len(name)) + name
    out += struct.pack("<H", len(s.widgets))
    for w in s.widgets:
        out += _encode_widget(w)
    return out


ROLES = {"page": S.ROLE_PAGE, "night": S.ROLE_NIGHT, "startup": S.ROLE_STARTUP}
ROLE_NAMES = {v: k for k, v in ROLES.items()}


def _encode_image(img):
    if not (0 <= img.id < S.NO_IMAGE):
        raise LayoutError(f"Ungültige Bildnummer {img.id}")
    if not (1 <= img.width <= S.MAX_IMAGE_SIDE and 1 <= img.height <= S.MAX_IMAGE_SIDE):
        raise LayoutError(f"Bild {img.name!r} ist zu groß ({img.width}×{img.height})")
    if len(img.pixels) != img.width * img.height:
        raise LayoutError(f"Bild {img.name!r}: Pixelanzahl passt nicht zur Größe")
    fmt, data = I.encode_pixels(img)
    name = _str_bytes(img.name)
    flags = S.IMAGE_FLAG_ALPHA if img.has_alpha else 0
    return (struct.pack("<BBBBHHB", img.id, fmt, flags, 0, img.width, img.height, len(name)) + name
            + struct.pack("<I", len(data)) + data)


def _decode_image(payload):
    if len(payload) < 9:
        raise LayoutError("Bild abgeschnitten")
    img_id, fmt, flags, _, w, h, nlen = struct.unpack_from("<BBBBHHB", payload, 0)
    pos = 9
    if pos + nlen + 4 > len(payload):
        raise LayoutError("Bild abgeschnitten")
    name = payload[pos:pos + nlen].decode("utf-8", errors="replace")
    pos += nlen
    dlen = struct.unpack_from("<I", payload, pos)[0]
    pos += 4
    if pos + dlen != len(payload):
        raise LayoutError(f"Bild {name!r}: Länge der Pixeldaten stimmt nicht")
    if img_id == S.NO_IMAGE or not (1 <= w <= S.MAX_IMAGE_SIDE and 1 <= h <= S.MAX_IMAGE_SIDE):
        raise LayoutError(f"Bild {name!r}: ungültige Nummer oder Größe")
    try:
        pixels, alpha = I.decode_pixels(fmt, bool(flags & S.IMAGE_FLAG_ALPHA), w, h, payload[pos:])
    except I.ImageError as e:
        raise LayoutError(f"Bild {name!r}: {e}")
    return I.Image(img_id, name, w, h, pixels, alpha)


def _chunk(fourcc, payload):
    return fourcc + struct.pack("<I", len(payload)) + payload


def encode(layout, tool="S51 Designer"):
    """Layout -> Bytes."""
    if len(layout.screens) == 0:
        raise LayoutError("Das Layout braucht mindestens eine Seite")
    if len(layout.screens) > S.MAX_SCREENS:
        raise LayoutError(f"Höchstens {S.MAX_SCREENS} Seiten erlaubt")
    ids = [s.id for s in layout.screens]
    if len(set(ids)) != len(ids):
        raise LayoutError("Seitennummern sind doppelt vergeben")
    if sum(1 for s in layout.screens if s.role == "startup") > 1:
        raise LayoutError("Es darf nur eine Startbild-Seite geben")
    if len(layout.images) > S.MAX_IMAGES:
        raise LayoutError(f"Höchstens {S.MAX_IMAGES} Bilder erlaubt")
    img_ids = [i.id for i in layout.images]
    if len(set(img_ids)) != len(img_ids):
        raise LayoutError("Bildnummern sind doppelt vergeben")

    header = S.MAGIC + struct.pack("<BBHHHI", S.VERSION_MAJOR, S.VERSION_MINOR,
                                   S.HEADER_SIZE, layout.width, layout.height, 0)
    created = layout.created or int(time.time())
    meta = (_tlv(S.META_NAME, _str_bytes(layout.name)) +
            _tlv(S.META_AUTHOR, _str_bytes(layout.author)) +
            _tlv(S.META_CREATED, struct.pack("<I", created)) +
            _tlv(S.META_TOOL, _str_bytes(tool)))
    body = header + _chunk(S.CHUNK_META, meta)
    for img in layout.images:
        body += _chunk(S.CHUNK_IMAGE, _encode_image(img))
    for s in layout.screens:
        body += _chunk(S.CHUNK_SCREEN, _encode_screen(s))
    for fourcc, payload in layout.unknown_chunks:
        body += _chunk(fourcc, payload)
    data = body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)
    if len(data) > S.MAX_FILE_SIZE:
        raise LayoutError(f"Datei zu groß ({len(data)} Bytes, höchstens {S.MAX_FILE_SIZE})")
    return data


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

def _decode_widget(data, pos, end):
    if pos + WIDGET_HEAD_SIZE > end:
        raise LayoutError("Element abgeschnitten")
    tcode, flags, x, y, w, h, plen = struct.unpack_from("<BBhhHHH", data, pos)
    pos += WIDGET_HEAD_SIZE
    if pos + plen > end:
        raise LayoutError("Eigenschaften eines Elements abgeschnitten")
    wt = S.WTYPE_BY_CODE.get(tcode)
    props = {}
    for code, raw in _iter_tlv(data[pos:pos + plen]):
        prop = S.PROP_BY_CODE.get(code)
        if prop is None:
            props[f"#{code}"] = raw.hex()     # aus neuerer Version, unverändert behalten
        else:
            props[prop.key] = decode_prop(prop, raw)
    pos += plen
    widget = Widget(wt.key if wt else f"#{tcode}", x, y, w, h,
                    hidden=bool(flags & S.WFLAG_HIDDEN), locked=bool(flags & S.WFLAG_LOCKED),
                    props=props)
    return widget, pos


def _decode_screen(data):
    if len(data) < 10:
        raise LayoutError("Seite abgeschnitten")
    sid, role, night_of, _ = struct.unpack_from("<BBBB", data, 0)
    bg = bytes_to_color(data[4:7])
    nlen = data[7]
    pos = 8
    if pos + nlen + 2 > len(data):
        raise LayoutError("Seitenname abgeschnitten")
    name = data[pos:pos + nlen].decode("utf-8", errors="replace")
    pos += nlen
    count = struct.unpack_from("<H", data, pos)[0]
    pos += 2
    if count > S.MAX_WIDGETS_PER_SCREEN:
        raise LayoutError(f"Seite {name!r} hat {count} Elemente, erlaubt sind {S.MAX_WIDGETS_PER_SCREEN}")
    widgets = []
    for _ in range(count):
        wdg, pos = _decode_widget(data, pos, len(data))
        widgets.append(wdg)
    role_name = ROLE_NAMES.get(role, "page")     # unbekannte Art wie eine normale Seite behandeln
    return Screen(sid, name, role_name, night_of if role_name == "night" else S.NO_PAGE, bg, widgets)


def decode(data):
    """Bytes -> Layout. Wirft LayoutError bei jedem Fehler."""
    if len(data) > S.MAX_FILE_SIZE:
        raise LayoutError("Datei zu groß")
    if len(data) < S.HEADER_SIZE + 4:
        raise LayoutError("Datei zu kurz")
    if data[:4] != S.MAGIC:
        raise LayoutError("Keine S51-Layout-Datei (Kennung fehlt)")
    crc_stored = struct.unpack_from("<I", data, len(data) - 4)[0]
    if zlib.crc32(data[:-4]) & 0xFFFFFFFF != crc_stored:
        raise LayoutError("Prüfsumme falsch, Datei beschädigt")
    vmaj, vmin, hsize, width, height, _ = struct.unpack_from("<BBHHHI", data, 4)
    if vmaj != S.VERSION_MAJOR:
        raise LayoutError(f"Formatversion {vmaj}.{vmin} wird nicht unterstützt")
    if hsize < S.HEADER_SIZE or hsize > len(data) - 4:
        raise LayoutError("Ungültige Kopfgröße")

    layout = Layout(width=width, height=height)
    pos, end = hsize, len(data) - 4
    while pos < end:
        if pos + 8 > end:
            raise LayoutError("Abschnitt abgeschnitten")
        fourcc = data[pos:pos + 4]
        length = struct.unpack_from("<I", data, pos + 4)[0]
        pos += 8
        if pos + length > end:
            raise LayoutError(f"Abschnitt {fourcc!r} länger als die Datei")
        payload = data[pos:pos + length]
        pos += length
        if fourcc == S.CHUNK_META:
            for code, raw in _iter_tlv(payload):
                if code == S.META_NAME:
                    layout.name = raw.decode("utf-8", errors="replace")
                elif code == S.META_AUTHOR:
                    layout.author = raw.decode("utf-8", errors="replace")
                elif code == S.META_CREATED and len(raw) == 4:
                    layout.created = struct.unpack("<I", raw)[0]
                elif code == S.META_TOOL:
                    layout.tool = raw.decode("utf-8", errors="replace")
        elif fourcc == S.CHUNK_IMAGE:
            if len(layout.images) >= S.MAX_IMAGES:
                raise LayoutError(f"Mehr als {S.MAX_IMAGES} Bilder")
            layout.images.append(_decode_image(payload))
        elif fourcc == S.CHUNK_SCREEN:
            if len(layout.screens) >= S.MAX_SCREENS:
                raise LayoutError(f"Mehr als {S.MAX_SCREENS} Seiten")
            layout.screens.append(_decode_screen(payload))
        else:
            layout.unknown_chunks.append((fourcc, payload))
    if not layout.screens:
        raise LayoutError("Keine Seite in der Datei")
    return layout


def load(path):
    with open(path, "rb") as f:
        return decode(f.read())


def save(layout, path, tool="S51 Designer"):
    data = encode(layout, tool)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# ---------------------------------------------------------------------------
# JSON-Darstellung (für Kommandozeile und Fehlersuche)
# ---------------------------------------------------------------------------

def to_dict(layout):
    return {
        "format": f"S51L {S.VERSION_MAJOR}.{S.VERSION_MINOR}",
        "width": layout.width, "height": layout.height,
        "name": layout.name, "author": layout.author,
        "created": layout.created, "tool": layout.tool,
        "screens": [{
            "id": s.id, "name": s.name, "role": s.role,
            "night_of": s.night_of if s.role == "night" else None,
            "bg": s.bg,
            "widgets": [{
                "type": w.type, "x": w.x, "y": w.y, "w": w.w, "h": w.h,
                "hidden": w.hidden, "locked": w.locked, "props": dict(w.props),
            } for w in s.widgets],
        } for s in layout.screens],
        "images": [{
            "id": i.id, "name": i.name, "width": i.width, "height": i.height,
            "alpha": i.has_alpha, "raw": base64.b64encode(I.encode_raw(i)).decode("ascii"),
        } for i in layout.images],
        "unknown_chunks": [[f.decode("latin-1"), p.hex()] for f, p in layout.unknown_chunks],
    }


def from_dict(d):
    layout = Layout(width=d.get("width", S.DISPLAY_WIDTH), height=d.get("height", S.DISPLAY_HEIGHT),
                    name=d.get("name", ""), author=d.get("author", ""),
                    created=d.get("created", 0), tool=d.get("tool", ""))
    for sd in d["screens"]:
        night_of = sd.get("night_of")
        scr = Screen(sd["id"], sd.get("name", ""), sd.get("role", "page"),
                     S.NO_PAGE if night_of is None else night_of, sd.get("bg", "#000000"))
        for wd in sd.get("widgets", []):
            scr.widgets.append(Widget(wd["type"], wd["x"], wd["y"], wd["w"], wd["h"],
                                      wd.get("hidden", False), wd.get("locked", False),
                                      dict(wd.get("props", {}))))
        layout.screens.append(scr)
    for idd in d.get("images", []):
        pixels, alpha = I.decode_pixels(S.IMAGE_FORMAT_RAW, idd.get("alpha", False), idd["width"], idd["height"],
                                        base64.b64decode(idd["raw"]))
        layout.images.append(I.Image(idd["id"], idd.get("name", ""), idd["width"], idd["height"], pixels, alpha))
    for fourcc, hexdata in d.get("unknown_chunks", []):
        layout.unknown_chunks.append((fourcc.encode("latin-1"), bytes.fromhex(hexdata)))
    return layout
