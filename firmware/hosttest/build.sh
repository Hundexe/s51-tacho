#!/bin/sh
# Baut die Firmware-Teile zum Zeichnen für den PC: .build/render, .build/ui und .build/menu.
# Wird von render.sh, ui.sh und menu.sh aufgerufen.
#
# Braucht g++ und den Quelltext von LovyanGFX. Liegt er nicht unter
# $LGFX_SRC, wird LovyanGFX in der Version aus platformio.ini nach
# firmware/hosttest/.build/ geladen (git clone).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
FW="$HERE/.."
BUILD="$HERE/.build"
VERSION=$(sed -n 's/.*lovyan03\/LovyanGFX @ *\([0-9.]*\).*/\1/p' "$FW/platformio.ini")
mkdir -p "$BUILD"
if [ -z "$LGFX_SRC" ]; then
  if [ ! -d "$BUILD/LovyanGFX-$VERSION" ]; then
    git clone -q --depth 1 --branch "$VERSION" https://github.com/lovyan03/LovyanGFX.git "$BUILD/LovyanGFX-$VERSION"
  fi
  LGFX_SRC="$BUILD/LovyanGFX-$VERSION/src"
fi

# LovyanGFX einmal als Bibliothek bauen (Plattform „framebuffer“ für Linux)
LIB="$BUILD/liblgfx-$VERSION.a"
if [ ! -f "$LIB" ]; then
  mkdir -p "$BUILD/obj"
  rm -f "$BUILD"/obj/*.o
  i=0
  for f in $(find "$LGFX_SRC/lgfx" -name '*.cpp' | grep -v /platforms/) "$LGFX_SRC"/lgfx/v1/platforms/framebuffer/*.cpp; do
    i=$((i + 1)); g++ -std=c++17 -O2 -w -I"$LGFX_SRC" -c "$f" -o "$BUILD/obj/cpp$i.o" &
    [ $((i % 8)) -eq 0 ] && wait
  done
  for f in $(find "$LGFX_SRC/lgfx" -name '*.c'); do
    i=$((i + 1)); gcc -O2 -w -I"$LGFX_SRC" -c "$f" -o "$BUILD/obj/c$i.o" &
    [ $((i % 8)) -eq 0 ] && wait
  done
  wait
  ar rcs "$LIB" "$BUILD"/obj/*.o
fi

INC="-I$LGFX_SRC -I$FW/lib/s51layout/src -I$FW/lib/s51render/src -I$FW/lib/s51ui/src"
LIBS="$FW/lib/s51layout/src/*.cpp $FW/lib/s51render/src/*.cpp $FW/lib/s51ui/src/*.cpp"
g++ -std=c++17 -O1 -Wall -Wno-unused-function $INC "$HERE/render_main.cpp" "$HERE/lgfx_host_stubs.cpp" $LIBS "$LIB" -o "$BUILD/render"
g++ -std=c++17 -O1 -Wall -Wno-unused-function $INC "$HERE/ui_main.cpp" "$HERE/lgfx_host_stubs.cpp" $LIBS "$LIB" -o "$BUILD/ui"
g++ -std=c++17 -O1 -Wall -Wno-unused-function $INC "$HERE/menu_main.cpp" "$HERE/lgfx_host_stubs.cpp" $LIBS "$LIB" -o "$BUILD/menu"
