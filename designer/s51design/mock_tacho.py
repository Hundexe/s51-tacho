"""Simulierter Tacho für Tests der drahtlosen Übertragung am PC.

Verhält sich wie die Gegenstelle in der Firmware (docs/uebertragung.md),
prüft empfangene Layouts mit dem Decoder und legt sie in einem Ordner ab.

Start:  python -m s51design.mock_tacho --port 8051 --code 123456 --ordner ./sd
Im Designer dann als Adresse "localhost:8051" und den Code eingeben.
"""

import argparse
import json
import os
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config_format, layout_format
from . import schema as S
from .transfer import API

FIRMWARE = "simulator"


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "S51-Tacho-Sim/1"

        def log_message(self, fmt, *args):
            if state.get("verbose"):
                super().log_message(fmt, *args)

        def _send(self, status, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
                ctype = "application/json; charset=utf-8"
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            if not state["open"]:
                self._send(403, {"ok": False, "fehler": "Übertragungsmodus ist aus"})
                return False
            if self.headers.get("X-S51-Code", "") != state["code"]:
                state["fails"] += 1
                self._send(401, {"ok": False, "fehler": "Falscher Code"})
                return False
            return True

        def _path(self, name):
            return os.path.join(state["dir"], name)

        def do_GET(self):
            if self.path == API + "/info":
                lp = self._path("design.s51")
                layout = None
                if os.path.exists(lp):
                    data = _read(lp)
                    layout = {"crc32": f"{zlib.crc32(data) & 0xFFFFFFFF:08x}", "groesse": len(data)}
                self._send(200, {
                    "geraet": "S51-Tacho", "firmware": FIRMWARE,
                    "format": f"{S.VERSION_MAJOR}.{S.VERSION_MINOR}",
                    "layout": layout,
                    "config": os.path.exists(self._path("tacho.cfg")),
                    "uebertragung_offen": state["open"],
                })
                return
            if self.path in (API + "/layout", API + "/config"):
                if not self._authorized():
                    return
                name = "design.s51" if self.path.endswith("layout") else "tacho.cfg"
                p = self._path(name)
                if not os.path.exists(p):
                    self._send(404, {"ok": False, "fehler": f"{name} nicht vorhanden"})
                    return
                ctype = "application/octet-stream" if name.endswith("s51") else "text/plain; charset=utf-8"
                self._send(200, _read(p), ctype)
                return
            self._send(404, {"ok": False, "fehler": "Unbekannter Pfad"})

        def do_PUT(self):
            if self.path not in (API + "/layout", API + "/config"):
                self._send(404, {"ok": False, "fehler": "Unbekannter Pfad"})
                return
            if not self._authorized():
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > S.MAX_FILE_SIZE:
                self._send(413, {"ok": False, "fehler": f"höchstens {S.MAX_FILE_SIZE} Bytes"})
                return
            body = self.rfile.read(length)
            if self.path.endswith("layout"):
                try:
                    layout_format.decode(body)
                except layout_format.LayoutError as e:
                    self._send(400, {"ok": False, "fehler": str(e)})
                    return
                with open(self._path("design.s51"), "wb") as f:
                    f.write(body)
                self._send(200, {"ok": True, "crc32": f"{zlib.crc32(body) & 0xFFFFFFFF:08x}"})
            else:
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError:
                    self._send(400, {"ok": False, "fehler": "Konfiguration ist kein UTF-8-Text"})
                    return
                _, warnings = config_format.parse(text)
                with open(self._path("tacho.cfg"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                self._send(200, {"ok": True, "warnungen": [str(w) for w in warnings]})

    return Handler


def serve(port=8051, code="123456", folder="./sd", open_=True, verbose=True):
    os.makedirs(folder, exist_ok=True)
    state = {"code": code, "dir": folder, "open": open_, "fails": 0, "verbose": verbose}
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state))
    return httpd, state


def main():
    ap = argparse.ArgumentParser(description="Simulierter S51-Tacho für Übertragungstests")
    ap.add_argument("--port", type=int, default=8051)
    ap.add_argument("--code", default="123456")
    ap.add_argument("--ordner", default="./sd-simulator")
    args = ap.parse_args()
    httpd, _ = serve(args.port, args.code, args.ordner)
    print(f"Simulierter Tacho läuft auf localhost:{args.port}, Code {args.code}, Dateien in {args.ordner}")
    print("Beenden mit Strg+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
