#!/bin/sh
# Zeichnet alle Seiten eines Layouts mit dem Renderer der Firmware am PC.
#
#   firmware/hosttest/render.sh <layout.s51> <Zielordner> [HH:MM]
#
# Braucht g++ und git (lädt LovyanGFX, siehe build.sh).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/build.sh"
mkdir -p "$2"
"$HERE/.build/render" "$HERE/../data/s51fonts.bin" "$1" "$2" "$3"
