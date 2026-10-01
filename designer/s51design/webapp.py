"""S51 Designer: Oberfläche im Browserfenster.

Startet einen kleinen Webserver nur für diesen Rechner (127.0.0.1) und öffnet
die Oberfläche in einem eigenen Fenster von Edge oder Chrome (App-Modus, ohne
Adressleiste). Die Oberfläche selbst liegt in s51design/web/ (HTML, CSS,
JavaScript ohne Zusatzpakete). Alles, was Dateiformate betrifft, macht weiter
Python: Encoder, Decoder, Konfiguration und Übertragung.

Start:  python -m s51design            (im Ordner designer/)
        python -m s51design --kein-fenster   (nur Server, Adresse wird angezeigt)

Das Programm endet, wenn das Fenster geschlossen wird.
"""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__, config_format, layout_format, presets, transfer
from . import images as I
from . import schema as S

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")
PING_TIMEOUT = 20          # Sekunden ohne Lebenszeichen der Seite, dann Ende


def display_fonts_dir():
    """Schriften des Tachos (DejaVu). In der exe mitgeliefert, sonst aus firmware/fonts."""
    base = getattr(sys, "_MEIPASS", None)
    if base and os.path.isdir(os.path.join(base, "display_fonts")):
        return os.path.join(base, "display_fonts")
    return os.path.normpath(os.path.join(HERE, "..", "..", "firmware", "fonts"))


# ---------------------------------------------------------------------------
# Daten für die Oberfläche
# ---------------------------------------------------------------------------

def schema_info():
    return {
        "version": __version__,
        "format": f"{S.VERSION_MAJOR}.{S.VERSION_MINOR}",
        "display": [S.DISPLAY_WIDTH, S.DISPLAY_HEIGHT],
        "limits": {"file": S.MAX_FILE_SIZE, "screens": S.MAX_SCREENS, "widgets": S.MAX_WIDGETS_PER_SCREEN,
                   "images": S.MAX_IMAGES, "image_side": S.MAX_IMAGE_SIDE},
        "no_page": S.NO_PAGE, "no_image": S.NO_IMAGE,
        "sources": [{"code": s.code, "key": s.key, "label": s.label, "unit": s.unit, "kind": s.kind,
                     "demo": [s.demo_min, s.demo_max]} for s in S.SOURCES],
        "props": [{"code": p.code, "key": p.key, "label": p.label, "type": p.type, "default": p.default}
                  for p in S.PROPS],
        "widget_types": [{"code": t.code, "key": t.key, "label": t.label, "props": list(t.props),
                          "size": list(t.default_size), "overrides": t.overrides} for t in S.WIDGET_TYPES],
        "enums": {k: [list(e) for e in v] for k, v in S.ENUMS.items()},
        "config": [{"section": c.section, "key": c.key, "type": c.type, "default": c.default,
                    "description": c.description, "min": c.min, "max": c.max, "choices": list(c.choices)}
                   for c in S.CONFIG],
        "config_sections": list(S.CONFIG_SECTIONS),
        "presets": list(presets.PRESETS),
        "default_host": transfer.DEFAULT_HOST,
    }


def cfg_to_json(values):
    return {f"{s}.{k}": v for (s, k), v in values.items()}


def cfg_from_json(d):
    out = config_format.defaults()
    for c in S.CONFIG:
        name = f"{c.section}.{c.key}"
        if name in d:
            out[(c.section, c.key)] = d[name]
    return out


_image_cache = {}
_image_lock = threading.Lock()


def layout_from_json(d):
    """Wie layout_format.from_dict, aber Bilder werden zwischengespeichert (das Umrechnen ist langsam)."""
    imgs = d.get("images", [])
    d = dict(d, images=[])
    layout = layout_format.from_dict(d)
    for idd in imgs:
        key = (idd["id"], idd.get("name", ""), idd["width"], idd["height"], bool(idd.get("alpha")),
               hashlib.sha1(idd["raw"].encode("ascii")).hexdigest())
        with _image_lock:
            img = _image_cache.get(key)
            if img is None:
                pixels, alpha = I.decode_pixels(S.IMAGE_FORMAT_RAW, bool(idd.get("alpha")), idd["width"],
                                                idd["height"], base64.b64decode(idd["raw"]))
                img = I.Image(idd["id"], idd.get("name", ""), idd["width"], idd["height"], pixels, alpha)
                if len(_image_cache) > 200:
                    _image_cache.clear()
                _image_cache[key] = img
        layout.images.append(img)
    return layout


def image_to_json(img):
    return {"id": img.id, "name": img.name, "width": img.width, "height": img.height, "alpha": img.has_alpha,
            "raw": base64.b64encode(I.encode_raw(img)).decode("ascii")}


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = "S51Designer"

    def log_message(self, fmt, *args):     # leise
        if self.server.verbose:
            super().log_message(fmt, *args)

    # -- Antworten -----------------------------------------------------------

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 64 * 1024 * 1024:
            raise ApiError("Anfrage zu groß", 413)
        return self.rfile.read(n) if n else b""

    def _body_json(self):
        try:
            return json.loads(self._body().decode("utf-8") or "{}")
        except ValueError:
            raise ApiError("Ungültige Anfrage")

    # -- Routen --------------------------------------------------------------

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            return self._api("GET", url)
        self._static(url.path)

    def do_POST(self):
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            return self._send(404, b"", "text/plain")
        self._api("POST", url)

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        if path.startswith("/fonts/display/"):
            base, rel = display_fonts_dir(), path[len("/fonts/display/"):]
        else:
            base, rel = WEB_DIR, path.lstrip("/")
        full = os.path.normpath(os.path.join(base, rel))
        if not full.startswith(os.path.normpath(base) + os.sep) or not os.path.isfile(full):
            return self._send(404, "Nicht gefunden".encode("utf-8"), "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        if full.endswith(".js"):
            ctype = "text/javascript; charset=utf-8"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def _api(self, method, url):
        # Schutz: nur die eigene Seite kennt das Kennwort (steht in der Adresse beim Start)
        if self.headers.get("X-S51-Token") != self.server.token:
            return self._json({"error": "Kein Zugriff"}, 403)
        self.server.last_ping = time.monotonic()
        route = url.path[len("/api/"):]
        try:
            fn = getattr(self, f"api_{route.replace('/', '_')}", None)
            if fn is None:
                raise ApiError("Unbekannte Anfrage", 404)
            result = fn(method, parse_qs(url.query))
            if isinstance(result, bytes):
                self._send(200, result, "application/octet-stream")
            elif result is not None:
                self._json(result)
        except ApiError as e:
            self._json({"error": str(e)}, e.status)
        except (layout_format.LayoutError, I.ImageError, ValueError, KeyError, TypeError) as e:
            self._json({"error": str(e) or e.__class__.__name__}, 400)
        except transfer.TransferError as e:
            self._json({"error": str(e)}, 502)

    # -- Schnittstelle -------------------------------------------------------

    def api_info(self, method, q):
        return schema_info()

    def api_ping(self, method, q):
        return {"ok": True}

    def api_quit(self, method, q):
        self.server.quit_requested = True
        return {"ok": True}

    def api_preset(self, method, q):
        name = q.get("name", [""])[0]
        if name not in presets.PRESETS:
            raise ApiError(f"Unbekannte Vorlage {name}", 404)
        return layout_format.to_dict(presets.PRESETS[name]())

    def api_decode(self, method, q):
        return layout_format.to_dict(layout_format.decode(self._body()))

    def api_encode(self, method, q):
        return layout_format.encode(layout_from_json(self._body_json()), tool=f"S51 Designer {__version__}")

    def api_check(self, method, q):
        try:
            data = layout_format.encode(layout_from_json(self._body_json()), tool=f"S51 Designer {__version__}")
        except layout_format.LayoutError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "size": len(data)}

    def api_image(self, method, q):
        """RGBA-Pixel aus dem Browser -> Bild im Format des Tachos (RGB565, Alpha nur wenn nötig)."""
        d = self._body_json()
        w, h = int(d["width"]), int(d["height"])
        rgba = base64.b64decode(d["rgba"])
        img = I.from_rgba(int(d["id"]), str(d.get("name", "Bild"))[:60], w, h, rgba)
        return image_to_json(img)

    def api_config_defaults(self, method, q):
        return {"values": cfg_to_json(config_format.defaults())}

    def api_config_parse(self, method, q):
        values, warnings = config_format.parse(self._body_json().get("text", ""))
        return {"values": cfg_to_json(values), "warnings": [str(w) for w in warnings]}

    def api_config_dump(self, method, q):
        return {"text": config_format.dump(cfg_from_json(self._body_json().get("values", {})))}

    def api_config_validate(self, method, q):
        """Werte als Text aus dem Formular prüfen und umwandeln."""
        raw = self._body_json().get("values", {})
        values, errors = {}, {}
        for c in S.CONFIG:
            name = f"{c.section}.{c.key}"
            v = raw.get(name, c.default)
            try:
                if c.type == "bool":
                    values[name] = bool(v)
                elif c.type == "str":
                    values[name] = str(v)
                else:
                    values[name] = config_format.parse_value(c, str(v))
            except ValueError as e:
                errors[name] = str(e)
        if len(values.get("wlan.passwort", "")) < 8:
            errors["wlan.passwort"] = "mindestens 8 Zeichen"
        return {"values": values, "errors": errors}

    def api_wireless(self, method, q):
        d = self._body_json()
        host, code, action = d.get("host", "").strip(), d.get("code", "").strip(), d.get("action")
        if not host:
            raise ApiError("Adresse fehlt")
        if action == "info":
            return transfer.info(host)
        if action == "send_layout":
            data = layout_format.encode(layout_from_json(d["layout"]), tool=f"S51 Designer {__version__}")
            transfer.send_layout(host, code, data)
            return {"ok": True, "size": len(data)}
        if action == "send_config":
            return transfer.send_config(host, code, config_format.dump(cfg_from_json(d["values"]))) or {"ok": True}
        if action == "fetch_layout":
            return layout_format.to_dict(layout_format.decode(transfer.fetch_layout(host, code)))
        raise ApiError("Unbekannte Aktion")


class DesignerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=0, verbose=False):
        super().__init__(("127.0.0.1", port), Handler)
        self.token = secrets.token_urlsafe(18)
        self.verbose = verbose
        self.last_ping = None
        self.quit_requested = False

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}/?t={self.token}"


# ---------------------------------------------------------------------------
# Fenster
# ---------------------------------------------------------------------------

def find_browser():
    """Edge oder Chrome für den App-Modus. None, wenn keiner gefunden wird."""
    candidates = []
    if sys.platform.startswith("win"):
        for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                               os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                       "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                       "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser", "msedge", "chrome"):
        p = shutil.which(name)
        if p:
            candidates.append(p)
    return next((c for c in candidates if c and os.path.isfile(c)), None)


def profile_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "S51-Designer", "fenster")
    os.makedirs(path, exist_ok=True)
    return path


def open_window(url):
    """Öffnet das Fenster. Gibt den Prozess zurück, wenn er das Fenster gehört, sonst None."""
    browser = find_browser()
    if browser:
        try:
            return subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={profile_dir()}",
                                     "--no-first-run", "--no-default-browser-check", "--window-size=1440,900"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
    webbrowser.open(url)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="s51design", description="S51 Designer")
    ap.add_argument("--kein-fenster", action="store_true", help="nur den Server starten")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--laut", action="store_true", help="Anfragen protokollieren")
    args = ap.parse_args(argv)

    server = DesignerServer(args.port, verbose=args.laut)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if sys.stdout:                     # in der exe ohne Konsole gibt es keine Ausgabe
        print(f"S51 Designer {__version__}: {server.url}", flush=True)
    proc = None if args.kein_fenster else open_window(server.url)
    started = time.monotonic()
    try:
        while True:
            time.sleep(0.5)
            if server.quit_requested:
                break
            if proc is not None and proc.poll() is not None:
                if time.monotonic() - started < 8:
                    proc = None    # Browser lief schon und hat das Fenster übernommen: Lebenszeichen abwarten
                else:
                    break          # Fenster geschlossen
            if not args.kein_fenster and proc is None:
                last = server.last_ping
                if last is None and time.monotonic() - started > 120:
                    break      # Seite wurde nie geöffnet
                if last is not None and time.monotonic() - last > PING_TIMEOUT:
                    break      # Browser-Tab geschlossen
    except KeyboardInterrupt:
        pass
    server.shutdown()


if __name__ == "__main__":
    main()
