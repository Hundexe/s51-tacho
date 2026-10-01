"""Prüft, dass die Firmware Layouts nach denselben Regeln zeigt wie der Designer.

- Werteformat, Warnfarben, Balkenanteil und Kontrollleuchten: kompiliert
  firmware/hosttest/values_main.cpp mit g++ und vergleicht mit values.py
  (übersprungen ohne g++).
- Schriften: data/s51fonts.bin ist gültig und enthält jedes Zeichen, das in
  den Vorlagen vorkommt.
- Das eingebaute Layout der Firmware (firmware/data/klar.s51) ist die
  aktuelle Vorlage „Klar“.

Das Zeichnen selbst prüft firmware/hosttest/compare.py (Bildvergleich, braucht
den Quelltext von LovyanGFX), siehe firmware/README.md.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import layout_format, presets  # noqa: E402
from s51design import schema as S  # noqa: E402
from s51design import values as V  # noqa: E402

FW = os.path.normpath(os.path.join(HERE, "..", "..", "firmware"))
FONTS = os.path.join(FW, "data", "s51fonts.bin")
DIGITS = set(" 0123456789.,:-–+°%/")


def read_fonts():
    with open(FONTS, "rb") as f:
        d = f.read()
    assert d[:4] == b"S51F"
    n = struct.unpack_from("<H", d, 6)[0]
    faces = []
    for i in range(n):
        fam, subset, size, off, length = struct.unpack_from("<BBHII", d, 8 + 12 * i)
        count = struct.unpack_from(">I", d, off)[0]
        codes = {struct.unpack_from(">I", d, off + 24 + 28 * k)[0] for k in range(count)}
        faces.append((fam, subset, size, codes))
    return faces


def py_lines(layout):
    real = time.localtime
    V.time.localtime = lambda *a: time.struct_time((2026, 1, 1, 14, 27, 0, 3, 1, 0))
    try:
        vals = V.demo_values(animate=False)
    finally:
        V.time.localtime = real
    out = []
    for s in layout.screens:
        for i, w in enumerate(s.widgets):
            text, col, frac, on = "-", "-", 0.0, 0
            src = S.SOURCE_BY_KEY.get(w.get("source")) if w.type in ("value", "bar", "gauge", "indicator") else None
            raw = vals.get(src.key) if src else None
            num = raw if src is not None and src.kind == "number" else None
            if w.type in ("text", "value"):
                text = V.display_text(w, vals)
                col = V.threshold_color(w, num, w.get("color")) if w.type == "value" else w.get("color")
            elif w.type in ("bar", "gauge"):
                frac = V.fraction(w, num)
                col = V.threshold_color(w, num, w.get("color"))
            elif w.type == "indicator":
                on = 1 if V.indicator_on(w, vals, t=0.1) else 0
            out.append(f"{s.id}|{i}|{text}|{col.upper() if col != '-' else col}|{frac:.3f}|{on}")
    return out


@unittest.skipIf(shutil.which("g++") is None, "g++ nicht vorhanden")
class ValuesMatchDesigner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = os.path.join(cls.tmp.name, "values")
        srcs = [os.path.join(FW, "lib", "s51layout", "src", f) for f in ("s51_layout.cpp",)]
        srcs.append(os.path.join(FW, "lib", "s51render", "src", "s51_values.cpp"))
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-I", os.path.join(FW, "lib", "s51layout", "src"),
                        "-I", os.path.join(FW, "lib", "s51render", "src"),
                        os.path.join(FW, "hosttest", "values_main.cpp"), *srcs, "-o", cls.exe], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_presets(self):
        for name, make in presets.PRESETS.items():
            with self.subTest(name):
                layout = make()
                path = os.path.join(self.tmp.name, "l.s51")
                layout_format.save(layout, path)
                cpp = subprocess.run([self.exe, path], check=True, capture_output=True).stdout.decode("utf-8")
                self.assertEqual(cpp.splitlines(), py_lines(layout_format.load(path)))

    def test_number_format_edge_cases(self):
        layout = layout_format.Layout(screens=[layout_format.Screen(0, "T")])
        cases = [("speed", 0, ""), ("odometer", 0, " km"), ("voltage", 1, " V"), ("head_temp", 2, "°"),
                 ("lean", 1, "°"), ("none", 0, ""), ("time", 0, ""), ("song_title", 0, ""), ("gps_fix", 0, "")]
        for src, dec, unit in cases:
            w = layout_format.Widget.new("value")
            w.props.update(source=src, decimals=dec, unit=unit, warn_above=30.0, crit_above=60.0)
            layout.screens[0].widgets.append(w)
        for fmt in ("HH:MM:SS", "MM", "Uhr HH"):
            w = layout_format.Widget.new("value")
            w.props.update(source="time", format=fmt)
            layout.screens[0].widgets.append(w)
        path = os.path.join(self.tmp.name, "e.s51")
        layout_format.save(layout, path)
        cpp = subprocess.run([self.exe, path], check=True, capture_output=True).stdout.decode("utf-8")
        self.assertEqual(cpp.splitlines(), py_lines(layout_format.load(path)))


class FontsAndDefaultLayout(unittest.TestCase):
    def test_fonts_cover_presets(self):
        faces = read_fonts()
        families = {0: "sans", 1: "sans_bold", 2: "segment"}
        full = {families[f]: c for f, sub, size, c in faces if sub == 0}
        self.assertEqual(set(full), set(families.values()))
        needed = set(V.format_number(12345.6, 1)) | set("–") | set("N!GPSBT♪")
        for name, make in presets.PRESETS.items():
            for s in make().screens:
                for w in s.widgets:
                    if w.type == "text":
                        needed |= set(w.get("text").replace("\n", ""))
                    elif w.type == "value":
                        needed |= set(w.get("unit")) | set(w.get("format"))
        missing = {ch for ch in needed for fam in full.values() if ord(ch) not in fam}
        self.assertEqual(missing, set(), "Zeichen fehlen in data/s51fonts.bin (tools/gen_fonts.py)")
        for f, sub, size, codes in faces:
            if sub == 1:
                self.assertTrue({ord(c) for c in DIGITS} <= codes)

    def test_default_layout_is_klar(self):
        with open(os.path.join(FW, "data", "klar.s51"), "rb") as f:
            data = f.read()
        built = layout_format.decode(data)
        current = presets.PRESETS["Klar"]()
        a, b = layout_format.to_dict(built), layout_format.to_dict(current)
        for key in ("screens", "images", "name"):
            self.assertEqual(a[key], b[key], "firmware/data/klar.s51 veraltet: python tools/make_examples.py ausführen")


if __name__ == "__main__":
    unittest.main()
