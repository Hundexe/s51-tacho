"""Prüft, dass die Oberfläche (JavaScript) Werte nach denselben Regeln zeigt wie
Designer-Vorschau (Python) und Firmware (C++).

Läuft tests/js/rules_main.mjs mit Node.js (übersprungen, wenn node fehlt) und
vergleicht die Ausgabe mit den Regeln aus values.py.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from s51design import layout_format, presets, webapp  # noqa: E402
from test_firmware_render import py_lines  # noqa: E402


@unittest.skipIf(shutil.which("node") is None, "node nicht vorhanden")
class JsRulesMatchPython(unittest.TestCase):
    def run_js(self, layout):
        with tempfile.TemporaryDirectory() as tmp:
            info, lay = os.path.join(tmp, "info.json"), os.path.join(tmp, "layout.json")
            with open(info, "w", encoding="utf-8") as f:
                json.dump(webapp.schema_info(), f)
            with open(lay, "w", encoding="utf-8") as f:
                json.dump(layout_format.to_dict(layout), f)
            out = subprocess.run(["node", os.path.join(HERE, "js", "rules_main.mjs"), info, lay],
                                 check=True, capture_output=True)
            return out.stdout.decode("utf-8").splitlines()

    def test_presets(self):
        for name, make in presets.PRESETS.items():
            with self.subTest(name):
                layout = layout_format.decode(layout_format.encode(make()))
                self.assertEqual(self.run_js(layout), py_lines(layout))


if __name__ == "__main__":
    unittest.main()
