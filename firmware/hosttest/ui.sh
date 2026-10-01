#!/bin/sh
# Zeichnet die Design-Auswahl der Firmware am PC, mit allen Vorlagen aus
# designer/beispiele/ als Designs auf der SD-Karte.
#
#   firmware/hosttest/ui.sh <Zielordner>
#
# Braucht g++ und git (lädt LovyanGFX, siehe build.sh).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/build.sh"
mkdir -p "$1"
"$HERE/.build/ui" "$HERE/../data/s51fonts.bin" "$1" "$HERE"/../../designer/beispiele/*.s51
