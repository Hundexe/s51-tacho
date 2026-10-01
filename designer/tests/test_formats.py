"""Tests für Layout-Format, Konfiguration und Übertragung.

Start im Ordner designer/:  python -m unittest discover -s tests -v
"""

import os
import struct
import sys
import tempfile
import threading
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from s51design import config_format, layout_format, mock_tacho, presets, transfer  # noqa: E402
from s51design import schema as S  # noqa: E402
from s51design.layout_format import Layout, LayoutError, Screen, Widget  # noqa: E402


class LayoutRoundTrip(unittest.TestCase):
    def test_preset_roundtrip(self):
        for name, make in presets.PRESETS.items():
            with self.subTest(name):
                layout = make()
                data = layout_format.encode(layout)
                back = layout_format.decode(data)
                self.assertEqual(layout_format.to_dict(back)["screens"], layout_format.to_dict(layout)["screens"])
                self.assertEqual(back.name, name)
                # erneut kodiert muss es bitgleich sein (created bleibt erhalten)
                self.assertEqual(layout_format.encode(back, tool=back.tool), data)

    def test_presets_stay_on_screen(self):
        for name, make in presets.PRESETS.items():
            for s in make().screens:
                for w in s.widgets:
                    with self.subTest(name=name, screen=s.name, widget=w.type):
                        self.assertGreaterEqual(w.x, 0)
                        self.assertGreaterEqual(w.y, 0)
                        self.assertLessEqual(w.x + w.w, S.DISPLAY_WIDTH)
                        self.assertLessEqual(w.y + w.h, S.DISPLAY_HEIGHT)
                        for key in w.props:
                            self.assertIn(key, S.WTYPE_BY_KEY[w.type].props)

    def test_all_widget_types_and_props(self):
        scr = Screen(0, "Alle")
        for wt in S.WIDGET_TYPES:
            scr.widgets.append(Widget.new(wt.key, 10, 20))
        layout = Layout(name="Test", screens=[scr], created=1)
        back = layout_format.decode(layout_format.encode(layout))
        for a, b in zip(scr.widgets, back.screens[0].widgets):
            self.assertEqual(a.type, b.type)
            for k, v in a.props.items():
                if isinstance(v, float):
                    self.assertAlmostEqual(v, b.props[k], places=4)
                else:
                    self.assertEqual(v, b.props[k], k)

    def test_header_layout(self):
        data = layout_format.encode(presets.klar())
        self.assertEqual(data[:4], b"S51L")
        self.assertEqual(data[4], S.VERSION_MAJOR)
        hsize, w, h = struct.unpack_from("<HHH", data, 6)
        self.assertEqual((hsize, w, h), (16, 480, 320))
        self.assertEqual(data[16:20], b"META")
        crc = struct.unpack_from("<I", data, len(data) - 4)[0]
        self.assertEqual(crc, zlib.crc32(data[:-4]) & 0xFFFFFFFF)

    def test_negative_coordinates_and_umlauts(self):
        w = Widget.new("text", -5, -7)
        w.props["text"] = "Glätte Äöü °C"
        back = layout_format.decode(layout_format.encode(Layout(screens=[Screen(0, "Größe", widgets=[w])])))
        bw = back.screens[0].widgets[0]
        self.assertEqual((bw.x, bw.y), (-5, -7))
        self.assertEqual(bw.props["text"], "Glätte Äöü °C")
        self.assertEqual(back.screens[0].name, "Größe")

    def test_corrupted_crc(self):
        data = bytearray(layout_format.encode(presets.klar()))
        data[40] ^= 0xFF
        with self.assertRaises(LayoutError):
            layout_format.decode(bytes(data))

    def test_truncated(self):
        data = layout_format.encode(presets.klar())
        for cut in (3, 10, 20, len(data) // 2):
            with self.assertRaises(LayoutError):
                layout_format.decode(data[:cut])

    def test_wrong_magic_and_version(self):
        data = bytearray(layout_format.encode(presets.klar()))
        bad = bytearray(data)
        bad[0:4] = b"XXXX"
        with self.assertRaises(LayoutError):
            layout_format.decode(bytes(bad))
        bad = bytearray(data)
        bad[4] = 2
        body = bytes(bad[:-4])
        bad[-4:] = struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)
        with self.assertRaises(LayoutError):
            layout_format.decode(bytes(bad))

    def test_unknown_prop_chunk_and_type_survive(self):
        layout = presets.klar()
        layout.screens[0].widgets[0].props["#200"] = "0102"
        layout.screens[0].widgets.append(Widget("#99", 1, 2, 3, 4, props={"#201": "ff"}))
        layout.unknown_chunks.append((b"IMGS", b"\x01\x02\x03"))
        back = layout_format.decode(layout_format.encode(layout))
        self.assertEqual(back.screens[0].widgets[0].props["#200"], "0102")
        self.assertEqual(back.screens[0].widgets[-1].type, "#99")
        self.assertEqual(back.unknown_chunks, [(b"IMGS", b"\x01\x02\x03")])

    def test_limits(self):
        scr = Screen(0, "Voll", widgets=[Widget.new("rect") for _ in range(S.MAX_WIDGETS_PER_SCREEN + 1)])
        with self.assertRaises(LayoutError):
            layout_format.encode(Layout(screens=[scr]))
        with self.assertRaises(LayoutError):
            layout_format.encode(Layout(screens=[]))
        with self.assertRaises(LayoutError):
            layout_format.encode(Layout(screens=[Screen(0), Screen(0)]))
        w = Widget.new("text")
        w.props["text"] = "x" * 300
        with self.assertRaises(LayoutError):
            layout_format.encode(Layout(screens=[Screen(0, widgets=[w])]))

    def test_json_roundtrip(self):
        layout = presets.klar()
        layout.created = 1700000000
        d = layout_format.to_dict(layout)
        self.assertEqual(layout_format.encode(layout_format.from_dict(d)), layout_format.encode(layout))


class ConfigTests(unittest.TestCase):
    def test_dump_parse_defaults(self):
        values, warnings = config_format.parse(config_format.dump())
        self.assertEqual(warnings, [])
        self.assertEqual(values, config_format.defaults())

    def test_parse_values_and_warnings(self):
        text = "\n".join([
            "[fahrzeug]",
            "radumfang_mm = 1750   # gemessen",
            "hall_sensor = ja",
            "magnete = 99",
            "[warnungen]",
            "spannung_min = 11,5",
            "[anzeige]",
            'startbild_text = "Meine # S51"',
            "nachtmodus = AN",
            "unbekannt = 1",
            "[quatsch]",
            "a = b",
        ])
        values, warnings = config_format.parse(text)
        self.assertEqual(values[("fahrzeug", "radumfang_mm")], 1750)
        self.assertTrue(values[("fahrzeug", "hall_sensor")])
        self.assertEqual(values[("fahrzeug", "magnete")], 2)          # außerhalb -> Standard
        self.assertEqual(values[("warnungen", "spannung_min")], 11.5)
        self.assertEqual(values[("anzeige", "startbild_text")], "Meine # S51")
        self.assertEqual(values[("anzeige", "nachtmodus")], "an")
        self.assertEqual(len(warnings), 3)                            # magnete, unbekannt, [quatsch]

    def test_roundtrip_changed(self):
        v = config_format.defaults()
        v[("anzeige", "startbild_text")] = "  Hallo; Welt  "
        v[("warnungen", "spannung_max")] = 14.8
        back, warnings = config_format.parse(config_format.dump(v))
        self.assertEqual(warnings, [])
        self.assertEqual(back, v)


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.httpd, cls.state = mock_tacho.serve(0, "424242", cls.tmp.name, verbose=False)
        cls.host = f"localhost:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def test_send_and_fetch_layout(self):
        data = layout_format.encode(presets.klar())
        r = transfer.send_layout(self.host, "424242", data)
        self.assertTrue(r["ok"])
        self.assertEqual(transfer.fetch_layout(self.host, "424242"), data)
        info = transfer.info(self.host)
        self.assertEqual(info["layout"]["groesse"], len(data))

    def test_wrong_code(self):
        with self.assertRaises(transfer.TransferError) as cm:
            transfer.send_layout(self.host, "000000", b"x")
        self.assertIn("Code", str(cm.exception))

    def test_rejects_broken_layout(self):
        with self.assertRaises(transfer.TransferError) as cm:
            transfer.send_layout(self.host, "424242", b"S51L kaputt")
        self.assertIn("abgelehnt", str(cm.exception))

    def test_config(self):
        r = transfer.send_config(self.host, "424242", "[fahrzeug]\nmagnete = 4\n")
        self.assertEqual(r["warnungen"], [])
        self.assertIn("magnete = 4", transfer.fetch_config(self.host, "424242"))

    def test_unreachable(self):
        with self.assertRaises(transfer.TransferError):
            transfer.info("127.0.0.1:1")


if __name__ == "__main__":
    unittest.main()


class DocumentationMatchesSchema(unittest.TestCase):
    DOC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "dateiformat-layout.md")
    CFG_DOC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "konfiguration.md")

    def test_minimal_example_from_doc(self):
        body = bytes.fromhex("53 35 31 4C 01 00 10 00 E0 01 40 01 00 00 00 00"
                             "4D 45 54 41 00 00 00 00"
                             "53 43 52 4E 0A 00 00 00"
                             "00 00 FF 00 00 00 00 00 00 00")
        data = body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)
        layout = layout_format.decode(data)
        self.assertEqual(len(layout.screens), 1)
        self.assertEqual(layout.screens[0].widgets, [])

    def test_all_codes_documented(self):
        with open(self.DOC, encoding="utf-8") as f:
            doc = f.read()
        for t in S.WIDGET_TYPES:
            self.assertIn(f"| {t.code} | `{t.key}` |", doc)
        for s in S.SOURCES:
            self.assertIn(f"| {s.code} | `{s.key}` |", doc)
        for p in S.PROPS:
            self.assertIn(f"| {p.code} | `{p.key}` |", doc)
        for name in ("icon", "font", "align", "orientation"):
            for code, key, _ in S.ENUMS[name]:
                self.assertIn(f"{code} `{key}`", doc)

    def test_all_config_keys_documented(self):
        with open(self.CFG_DOC, encoding="utf-8") as f:
            doc = f.read()
        for c in S.CONFIG:
            self.assertIn(f"`{c.key}`", doc, c.key)
