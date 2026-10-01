"""Drahtlose Übertragung vom Designer zum Tacho über WLAN (HTTP).

Protokoll: siehe docs/uebertragung.md.
Nutzt nur die Standardbibliothek, damit der Designer ohne Zusatzpakete läuft.
"""

import json
import urllib.error
import urllib.request

API = "/api/v1"
DEFAULT_HOST = "192.168.4.1"
TIMEOUT_S = 8


class TransferError(Exception):
    pass


def _url(host, path):
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host + API + path


def _request(method, host, path, code=None, body=None, content_type=None):
    req = urllib.request.Request(_url(host, path), data=body, method=method)
    if code:
        req.add_header("X-S51-Code", str(code).strip())
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        msg = _error_text(e.code, raw)
        raise TransferError(msg) from None
    except urllib.error.URLError as e:
        raise TransferError(
            f"Tacho nicht erreichbar unter {host} ({e.reason}). "
            "Ist der PC mit dem WLAN des Tachos verbunden und der Übertragungsmodus am Tacho an?") from None
    except TimeoutError:
        raise TransferError(f"Keine Antwort von {host} innerhalb von {TIMEOUT_S} s.") from None


def _error_text(status, raw):
    detail = ""
    try:
        detail = json.loads(raw.decode("utf-8")).get("fehler", "")
    except (ValueError, UnicodeDecodeError, AttributeError):
        pass
    base = {
        401: "Der Freigabe-Code stimmt nicht. Den Code vom Display des Tachos eingeben.",
        403: "Übertragung am Tacho nicht freigegeben. Im Stand das Menü „Übertragung“ öffnen.",
        413: "Datei zu groß für den Tacho.",
        400: "Der Tacho hat die Datei abgelehnt.",
    }.get(status, f"Fehler {status} vom Tacho.")
    return f"{base} {detail}".strip()


def info(host):
    _, _, raw = _request("GET", host, "/info")
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise TransferError("Antwort des Tachos ist kein gültiges JSON")


def send_layout(host, code, data):
    _, _, raw = _request("PUT", host, "/layout", code, data, "application/octet-stream")
    return json.loads(raw.decode("utf-8"))


def fetch_layout(host, code):
    _, _, raw = _request("GET", host, "/layout", code)
    return raw


def send_config(host, code, text):
    _, _, raw = _request("PUT", host, "/config", code, text.encode("utf-8"), "text/plain; charset=utf-8")
    return json.loads(raw.decode("utf-8"))


def fetch_config(host, code):
    _, _, raw = _request("GET", host, "/config", code)
    return raw.decode("utf-8")
