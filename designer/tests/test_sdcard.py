"""Tests für das Schreiben auf die SD-Karte (s51design/sdcard.py)."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import config_format, sdcard  # noqa: E402


class SdCardTests(unittest.TestCase):
    def test_file_names(self):
        self.assertEqual(sdcard.file_name_for("Klar"), "klar.s51")
        self.assertEqual(sdcard.file_name_for("Mein Ölstand Design!"), "mein-oelstand-design.s51")
        self.assertEqual(sdcard.file_name_for("   "), "design.s51")
        self.assertEqual(sdcard.clean_file_name("abend"), "abend.s51")
        self.assertEqual(sdcard.clean_file_name("Tag_1.S51"), "Tag_1.S51")
        for bad in ("", "a b", "ä.s51", "x" * 41):
            with self.assertRaises(ValueError):
                sdcard.clean_file_name(bad)

    def test_export_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = sdcard.target_dir(tmp)
            self.assertEqual(d, os.path.join(tmp, "s51"))
            self.assertEqual(sdcard.target_dir(d), d)
            self.assertEqual(sdcard.list_designs(d), [])
            sdcard.export(d, b"eins", "b.s51", "b.s51")
            sdcard.export(d, b"zwei", "a.s51", "b.s51")
            self.assertEqual(sdcard.list_designs(d), ["a.s51", "b.s51"])
            values, warnings = config_format.load(os.path.join(d, "tacho.cfg"))
            self.assertEqual((values[("anzeige", "layout_datei")], warnings), ("b.s51", []))
            # eigene Einstellungen aus dem Designer gehen vor
            cfg = config_format.defaults()
            cfg[("fahrzeug", "magnete")] = 6
            sdcard.export(d, b"drei", "a.s51", "a.s51", cfg)
            values, _ = config_format.load(os.path.join(d, "tacho.cfg"))
            self.assertEqual(values[("fahrzeug", "magnete")], 6)
            self.assertEqual(values[("anzeige", "layout_datei")], "a.s51")
            with open(os.path.join(d, "a.s51"), "rb") as f:
                self.assertEqual(f.read(), b"drei")


if __name__ == "__main__":
    unittest.main()
