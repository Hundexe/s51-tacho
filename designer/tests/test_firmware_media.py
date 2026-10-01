"""Prüft, wie die Firmware Musik- und Uhrzeitdaten vom Handy auswertet.

Kompiliert firmware/hosttest/media_main.cpp mit firmware/lib/s51media und
spielt Nachrichten so durch, wie ein iPhone sie schickt (Apple Media Service,
Current Time Service). Übersprungen ohne g++.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.normpath(os.path.join(HERE, "..", "..", "firmware"))


def ams(entity, attr, text, flags=0):
    return "ams " + bytes([entity, attr, flags]).hex() + text.encode("utf-8").hex()


def cts(y, mo, d, h, mi, s):
    return "cts " + bytes([y & 0xFF, y >> 8, mo, d, h, mi, s, 4, 0, 1]).hex()


@unittest.skipIf(shutil.which("g++") is None, "g++ nicht vorhanden")
class MediaFromPhone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = os.path.join(cls.tmp.name, "media")
        lib = lambda *p: os.path.join(FW, "lib", *p)  # noqa: E731
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-I", lib("s51layout", "src"), "-I", lib("s51render", "src"), "-I", lib("s51media", "src"),
                        os.path.join(FW, "hosttest", "media_main.cpp"), lib("s51media", "src", "s51_media.cpp"),
                        lib("s51render", "src", "s51_values.cpp"), lib("s51layout", "src", "s51_layout.cpp"),
                        "-o", cls.exe], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_script(self, lines):
        out = subprocess.run([self.exe], input=("\n".join(lines) + "\n").encode("utf-8"), check=True,
                             capture_output=True).stdout.decode("utf-8")
        return out.splitlines()

    def test_not_connected(self):
        self.assertEqual(self.run_script(["show"]), ["0||0||||||-|-|--"])

    def test_android_without_media_service(self):
        self.assertEqual(self.run_script(["connect Pixel 8", "show"]), ["1|Pixel 8|0||||||-|-|--"])

    def test_iphone_track_and_position(self):
        out = self.run_script([
            "t 1000", "connect Mein iPhone",
            ams(2, 2, "Schwalbenflug"), ams(2, 0, "Testband"), ams(2, 1, "Mopedtour"), ams(2, 3, "221.5"),
            ams(0, 2, "0.625"), ams(0, 1, "1,1.0,80.2"),
            "show",
            "t 4000", "show",                       # läuft 3 s weiter
            ams(0, 1, "0,0.0,83.9"), "t 60000", "show",   # Pause: Position bleibt
            "t 61000", ams(0, 1, "1,1.0,221.0"), "t 70000", "show",   # nicht über die Länge hinaus
        ])
        self.assertEqual(out, [
            "1|Mein iPhone|1|Schwalbenflug|Testband|Mopedtour|1:20|3:41|36|63|--",
            "1|Mein iPhone|1|Schwalbenflug|Testband|Mopedtour|1:23|3:41|38|63|--",
            "1|Mein iPhone|0|Schwalbenflug|Testband|Mopedtour|1:23|3:41|38|63|--",
            "1|Mein iPhone|1|Schwalbenflug|Testband|Mopedtour|3:41|3:41|100|63|--",
        ])

    def test_no_player(self):
        out = self.run_script(["connect iPhone", ams(0, 1, ""), "show"])
        self.assertEqual(out, ["1|iPhone|0||||||-|-|--"])

    def test_long_track(self):
        out = self.run_script(["connect iPhone", ams(2, 3, "4000"), ams(0, 1, "0,0.0,3725"), "show"])
        self.assertEqual(out, ["1|iPhone|0||||1:02:05|1:06:40|93|-|--"])

    def test_clock_from_iphone(self):
        out = self.run_script(["t 5000", "connect iPhone", cts(2026, 12, 31, 23, 59, 50), "show",
                               "t 25000", "show"])
        self.assertEqual(out[0].split("|")[-1], "2026-12-31 23:59:50")
        self.assertEqual(out[1].split("|")[-1], "2027-01-01 00:00:10")   # über Mitternacht und Jahreswechsel

    def test_rejects_short_and_invalid(self):
        self.assertEqual(self.run_script(["ams 0001", "cts 0102", "cts e90713200000000000"]),
                         ["abgelehnt", "abgelehnt", "abgelehnt"])

    def test_fit_charset(self):
        cases = {
            "Café del Mar": "Cafe del Mar",
            "Für Elise – Größe": "Für Elise – Größe",
            "Mötley Crüe ÆØÅ": "Mötley Crüe AEOA",
            "Łódź, Škoda, ğüzel": "Lodz, Skoda, güzel",
            "Song 🎸 mit Emoji 🔥": "Song  mit Emoji",
            "Москва": "??????",
            "é": "e",
            "Rock’n’Roll “live”": "Rock’n’Roll “live”",
        }
        out = self.run_script([f"fit {k}" for k in cases])
        self.assertEqual(out, list(cases.values()))


if __name__ == "__main__":
    unittest.main()
