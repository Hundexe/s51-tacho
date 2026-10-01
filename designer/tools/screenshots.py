"""Macht Bildschirmfotos des Designers für die Doku.

Aufruf im Ordner designer/ unter Linux mit X-Server (z. B. Xvfb):
    xvfb-run -s "-screen 0 1440x900x24" python3 tools/screenshots.py <Zielordner>

Braucht ImageMagick (Befehl „import“) für die Aufnahme. Läuft in GitHub
Actions (.github/workflows/designer-screenshots.yml), kann aber auch lokal
benutzt werden.
"""

import os
import subprocess
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import app as A          # noqa: E402
from s51design import images as I       # noqa: E402


def settle(root, seconds=0.4):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.02)


def shot(root, out_dir, name):
    settle(root)
    path = os.path.join(out_dir, name)
    subprocess.run(["import", "-window", "root", path], check=True)
    print("geschrieben:", path)


def select_first(app, wtype):
    for i, w in enumerate(app.ed.screen.widgets):
        if w.type == wtype:
            app.ed.selected = i
            app.refresh_all()
            return w
    return None


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "screenshots"
    os.makedirs(out_dir, exist_ok=True)
    A.SETTINGS_PATH = os.path.join(out_dir, ".settings.json")
    root = tk.Tk()
    root.geometry("1440x860+0+0")
    app = A.App(root)
    settle(root, 1.0)
    app.refresh_all()

    shot(root, out_dir, "designer-start.png")

    select_first(app, "gauge") or select_first(app, "value")
    shot(root, out_dir, "designer-eigenschaften.png")

    startup = next(i for i, s in enumerate(app.ed.layout.screens) if s.role == "startup")
    app.ed.select_screen(startup)
    app.refresh_all()
    shot(root, out_dir, "designer-startbild-seite.png")
    select_first(app, "image")
    shot(root, out_dir, "designer-bild.png")

    app.ed.new("Alle Elemente")
    app.refresh_all()
    app.zoom.set(1)
    app._zoom_changed()
    for i, s in enumerate(app.ed.layout.screens):
        app.ed.select_screen(i)
        app.refresh_all()
        shot(root, out_dir, f"designer-alle-{i + 1}.png")

    app.ed.new("Klar")
    app.zoom.set(2)
    app.preview.set(True)
    app.refresh_all()
    shot(root, out_dir, "designer-vorschau.png")
    app.preview.set(False)

    # eigenes Bild laden
    w, h = 300, 200
    rgba = bytearray()
    for y in range(h):
        for x in range(w):
            rgba += bytes([x * 255 // w, y * 255 // h, 160, 255])
    png = os.path.join(out_dir, "verlauf.png")
    with open(png, "wb") as f:
        f.write(I.png_encode(w, h, bytes(rgba)))
    app.ed.select_screen(0)
    app.ed.selected = None
    app.import_image(png)
    os.remove(png)
    shot(root, out_dir, "designer-bild-geladen.png")

    cfg = app.open_config()
    shot(root, out_dir, "designer-konfiguration.png")
    cfg.top.destroy()
    wl = app.open_wireless()
    shot(root, out_dir, "designer-drahtlos.png")
    wl.top.destroy()
    root.destroy()


if __name__ == "__main__":
    main()
