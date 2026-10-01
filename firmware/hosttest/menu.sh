#!/bin/sh
# Prüft die eingebauten Menüs und den Sperrbildschirm der Firmware am PC und
# zeichnet jede Seite (menue-*.ppm, mit Pillow zusätzlich als .png).
#
#   firmware/hosttest/menu.sh <Zielordner>
#
# Endet mit Fehler, wenn ein Ablauf (PIN, Sperre, Wartung …) nicht stimmt.
# Braucht g++ und git (lädt LovyanGFX, siehe build.sh).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/build.sh"
mkdir -p "$1"
"$HERE/.build/menu" "$HERE/../data/s51fonts.bin" "$1"
python3 - "$1" <<'PY' || true
import glob, os, sys
try:
    from PIL import Image
except ImportError:
    sys.exit(0)
for p in glob.glob(os.path.join(sys.argv[1], "menue-*.ppm")):
    Image.open(p).save(p[:-4] + ".png")
PY
