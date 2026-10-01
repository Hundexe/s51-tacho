"""Vergleicht den C++-Decoder der Firmware mit dem Python-Decoder.

Kompiliert firmware/hosttest/dump_main.cpp mit g++ (Test wird übersprungen,
wenn kein g++ vorhanden ist), dekodiert dieselben Dateien mit beiden
Decodern und vergleicht die Ausgabe Zeile für Zeile.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

from s51design import config_format, layout_format, presets  # noqa: E402
from s51design import schema as S  # noqa: E402
from s51design.layout_format import Layout, LayoutError, Screen, Widget  # noqa: E402
import gen_cpp_header  # noqa: E402

FW = os.path.normpath(os.path.join(HERE, "..", "..", "firmware"))
SRC = os.path.join(FW, "lib", "s51layout", "src")
MAIN = os.path.join(FW, "hosttest", "dump_main.cpp")

PROP_ORDER = [p.key for p in S.PROPS]


def py_value(widget, key):
    prop = S.PROP_BY_KEY[key]
    wt = S.WTYPE_BY_KEY.get(widget.type)
    v = widget.props.get(key, S.prop_default(wt, key) if wt else prop.default)
    t = prop.type
    if t == "f32":
        return f"{float(v):.4f}"
    if t == "bool":
        return "1" if v else "0"
    if t.startswith("enum:"):
        return str(S.enum_code(t[5:], v))
    return str(v)


def py_dump(data, cfg_text=None):
    out = []
    try:
        L = layout_format.decode(data)
        out.append(f"LAYOUT {L.name}|{L.author}|{L.tool}|{L.created}|{L.width}|{L.height}|{len(L.screens)}")
        for img in L.images:
            flat = bytearray()
            for k, v in enumerate(img.pixels):
                flat += bytes((v & 0xFF, v >> 8, img.alpha[k] if img.alpha is not None else 255))
            crc = zlib.crc32(bytes(flat)) & 0xFFFFFFFF
            out.append(f"IMAGE {img.id}|{img.name}|{img.width}|{img.height}|{1 if img.has_alpha else 0}|{crc:08x}|1")
        roles = {"page": S.ROLE_PAGE, "night": S.ROLE_NIGHT, "startup": S.ROLE_STARTUP}
        for s in L.screens:
            night = s.role == "night"
            out.append(f"SCREEN {s.id}|{roles[s.role]}|{s.night_of if night else S.NO_PAGE}|{s.bg}|{s.name}|{len(s.widgets)}")
            for w in s.widgets:
                code = int(w.type[1:]) if w.type.startswith("#") else S.WTYPE_BY_KEY[w.type].code
                out.append(f"WIDGET {code}|{1 if w.hidden else 0}|{w.x}|{w.y}|{w.w}|{w.h}")
                for key in PROP_ORDER:
                    out.append(f" {key}={py_value(w, key)}")
    except LayoutError:
        out.append("ERROR")
    if cfg_text is not None:
        values, warnings = config_format.parse(cfg_text)
        for c in S.CONFIG:
            v = values[(c.section, c.key)]
            if c.type == "float":
                v = f"{float(v):.4f}"
            elif c.type == "bool":
                v = "ja" if v else "nein"
            out.append(f"CFG {c.section}.{c.key}={v}")
        out.append(f"CFGWARNINGS {len(warnings)}")
    return out


@unittest.skipIf(shutil.which("g++") is None, "g++ nicht vorhanden")
class CppDecoderMatchesPython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = os.path.join(cls.tmp.name, "dump")
        srcs = [os.path.join(SRC, f) for f in os.listdir(SRC) if f.endswith(".cpp")]
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", SRC, MAIN, *srcs,
                        "-o", cls.exe], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cpp(self, data, cfg_text=None):
        lp = os.path.join(self.tmp.name, "l.s51")
        with open(lp, "wb") as f:
            f.write(data)
        args = [self.exe, lp]
        if cfg_text is not None:
            cp = os.path.join(self.tmp.name, "t.cfg")
            with open(cp, "wb") as f:
                f.write(cfg_text.encode("utf-8"))
            args.append(cp)
        out = subprocess.run(args, check=True, capture_output=True).stdout.decode("utf-8")
        lines = out.splitlines()
        return ["ERROR" if ln.startswith("ERROR") else ln for ln in lines]

    def compare(self, data, cfg_text=None):
        self.assertEqual(self.run_cpp(data, cfg_text), py_dump(data, cfg_text))

    def test_presets(self):
        for name, make in presets.PRESETS.items():
            with self.subTest(name):
                self.compare(layout_format.encode(make()))

    def test_all_types_with_unknown_parts(self):
        scr = Screen(3, "Alle Typen äöü")
        for wt in S.WIDGET_TYPES:
            w = Widget.new(wt.key, -3, 7)
            w.hidden = wt.code % 2 == 0
            scr.widgets.append(w)
        scr.widgets[0].props["#250"] = "0a0b"
        scr.widgets.append(Widget("#77", 1, 2, 3, 4, props={"#200": "00"}))   # unbekannter Typ
        night = Screen(4, "Nacht", role="night", night_of=3, bg="#101010",
                       widgets=[Widget("value", 0, 0, 10, 10, props={"source": "rpm"})])
        layout = Layout(name="Test", author="A", created=123, screens=[scr, night],
                        unknown_chunks=[(b"ZZZZ", b"abc")])
        self.compare(layout_format.encode(layout, tool="t"))

    def test_images_and_startup(self):
        import random
        from s51design import images as I
        rnd = random.Random(5)
        w, h, rgba = I.make_logo(64)
        logo = I.from_rgba(0, "Logo", w, h, rgba)                     # mit Alpha, wird lauflängenkodiert
        noise = I.from_rgba(7, "Rauschen", 9, 5, bytes(rnd.randrange(256) if k % 4 != 3 else 255
                                                       for k in range(9 * 5 * 4)))   # ohne Alpha, roh
        start = Screen(5, "Start", role="startup",
                       widgets=[Widget("image", 10, 10, 64, 64, props={"image": 0})])
        layout = Layout(name="Bilder", created=1, images=[logo, noise], screens=[Screen(0, "Fahrt"), start])
        data = layout_format.encode(layout)
        self.compare(data)
        # Bilddaten beschädigen (Prüfsumme danach korrigieren): beide Decoder müssen ablehnen
        broken = bytearray(data)
        idx = broken.index(b"IMAG") + 8 + 9 + len("Logo") + 4 + 3
        broken[idx] ^= 0xFF
        broken[-4:] = (zlib.crc32(bytes(broken[:-4])) & 0xFFFFFFFF).to_bytes(4, "little")
        self.compare(bytes(broken))

    def test_corrupt_files(self):
        data = layout_format.encode(presets.klar())
        broken = bytearray(data)
        broken[30] ^= 0x55
        for d in (bytes(broken), data[:10], b"XXXX" + data[4:], b""):
            self.compare(d)

    def test_config(self):
        cfg = "\n".join([
            "﻿# Kommentar",
            "[fahrzeug]",
            "radumfang_mm = 1765 ; gemessen",
            "hall_sensor = JA",
            "magnete = 0",
            "[anzeige]",
            'startbild_text = "  Hallo # Welt "',
            "nachtmodus = Aus",
            "[warnungen]",
            "spannung_min = 11,8",
            "glaette_unter = abc",
            "[unbekannt]",
            "x = 1",
            "[wlan]",
            "ssid = Mein Netz",
            "foo = bar",
        ])
        self.compare(layout_format.encode(presets.klar()), cfg)
        self.compare(layout_format.encode(presets.klar()), config_format.dump())


class GeneratedHeaderIsCurrent(unittest.TestCase):
    def test_up_to_date(self):
        for name, text in gen_cpp_header.generated_files().items():
            with open(os.path.join(SRC, name), encoding="utf-8") as f:
                self.assertEqual(f.read(), text,
                                 f"{name} ist veraltet: python tools/gen_cpp_header.py ausführen")


if __name__ == "__main__":
    unittest.main()
