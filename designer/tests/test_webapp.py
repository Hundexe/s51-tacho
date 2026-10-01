"""Tests für den Server der Oberfläche (s51design/webapp.py).

Startet den Server ohne Fenster und ruft die Schnittstelle so auf, wie es die
Oberfläche im Browser tut.
"""

import base64
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import config_format, layout_format, mock_tacho, presets, webapp  # noqa: E402


class WebappTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = webapp.DesignerServer(0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def req(self, path, data=None, json_body=None, token=True, raw=False):
        headers = {}
        if token:
            headers["X-S51-Token"] = self.server.token
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        r = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST" if data is not None else "GET")
        with urllib.request.urlopen(r, timeout=10) as res:
            body = res.read()
            return body if raw else json.loads(body.decode("utf-8"))

    def status(self, path, **kw):
        try:
            self.req(path, raw=True, **kw)
            return 200
        except urllib.error.HTTPError as e:
            return e.code

    def test_token_required(self):
        self.assertEqual(self.status("/api/info", token=False), 403)
        self.assertEqual(self.status("/api/info"), 200)

    def test_static_files(self):
        html = self.req("/", token=False, raw=True).decode("utf-8")
        self.assertIn("js/main.js", html)
        for path in ("/js/main.js", "/css/app.css", "/img/logo.svg", "/fonts/DejaVuSansCondensed.ttf",
                     "/fonts/display/DejaVuSans.ttf", "/fonts/display/DejaVuSansMono-Bold.ttf"):
            self.assertEqual(self.status(path, token=False), 200, path)
        for bad in ("/../webapp.py", "/js/../../webapp.py", "/fonts/display/../../README.md", "/gibtsnicht.js"):
            self.assertEqual(self.status(bad, token=False), 404, bad)

    def test_info(self):
        info = self.req("/api/info")
        self.assertEqual(info["display"], [480, 320])
        self.assertIn("Klar", info["presets"])
        self.assertTrue(any(p["key"] == "from_zero" for p in info["props"]))
        self.assertTrue(any(c["key"] == "layout_datei" for c in info["config"]))

    def test_layout_roundtrip(self):
        for name in presets.PRESETS:
            d = self.req(f"/api/preset?name={urllib.request.quote(name)}")
            data = self.req("/api/encode", json_body=d, raw=True)
            back = layout_format.decode(data)
            self.assertEqual(back.name, name)
            d2 = self.req("/api/decode", data=data)
            self.assertEqual(d2["screens"], d["screens"])
            self.assertEqual(self.req("/api/check", json_body=d)["size"], len(data))
        self.assertEqual(self.status("/api/preset?name=Gibtsnicht"), 404)
        self.assertEqual(self.status("/api/decode", data=b"kaputt"), 400)

    def test_check_reports_errors(self):
        d = self.req("/api/preset?name=Klar")
        d["screens"].append(dict(d["screens"][-1], id=d["screens"][-1]["id"]))   # doppelte Nummer
        r = self.req("/api/check", json_body=d)
        self.assertFalse(r["ok"])

    def test_image(self):
        w, h = 20, 10
        rgba = bytes([255, 0, 0, 255]) * (w * h - 1) + bytes([0, 0, 255, 128])
        img = self.req("/api/image", json_body={"id": 3, "name": "rot", "width": w, "height": h,
                                                 "rgba": base64.b64encode(rgba).decode("ascii")})
        self.assertEqual((img["id"], img["width"], img["height"], img["alpha"]), (3, w, h, True))
        d = self.req("/api/preset?name=Klar")
        d["images"].append(img)
        self.assertTrue(self.req("/api/check", json_body=d)["ok"])

    def test_config(self):
        defaults = self.req("/api/config/defaults")["values"]
        self.assertEqual(defaults["anzeige.layout_datei"], "design.s51")
        text = self.req("/api/config/dump", json_body={"values": dict(defaults, **{"fahrzeug.magnete": 5})})["text"]
        parsed = self.req("/api/config/parse", json_body={"text": text})
        self.assertEqual((parsed["values"]["fahrzeug.magnete"], parsed["warnings"]), (5, []))
        v = self.req("/api/config/validate", json_body={"values": {"fahrzeug.magnete": "abc", "warnungen.spannung_min": "11,5"}})
        self.assertIn("fahrzeug.magnete", v["errors"])
        self.assertEqual(v["values"]["warnungen.spannung_min"], 11.5)

    def test_wireless(self):
        with tempfile.TemporaryDirectory() as tmp:
            httpd, _ = mock_tacho.serve(0, "123456", tmp, verbose=False)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            host = f"localhost:{httpd.server_address[1]}"
            try:
                info = self.req("/api/wireless", json_body={"action": "info", "host": host})
                self.assertIn("firmware", info)
                d = self.req("/api/preset?name=Minimal")
                r = self.req("/api/wireless", json_body={"action": "send_layout", "host": host, "code": "123456", "layout": d})
                self.assertGreater(r["size"], 0)
                self.assertEqual(r["datei"], "minimal.s51")
                back = self.req("/api/wireless", json_body={"action": "fetch_layout", "host": host, "code": "123456"})
                self.assertEqual(back["name"], "Minimal")
                cfg = webapp.cfg_to_json(config_format.defaults())
                self.req("/api/wireless", json_body={"action": "send_config", "host": host, "code": "123456", "values": cfg})
                self.assertEqual(self.status("/api/wireless", json_body={"action": "send_layout", "host": host,
                                                                        "code": "000000", "layout": d}), 502)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
