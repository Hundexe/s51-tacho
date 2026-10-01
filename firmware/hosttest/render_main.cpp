// Zeichnet alle Seiten einer Layout-Datei mit dem Renderer der Firmware am PC.
// Ergebnis: eine PPM-Datei je Seite. So lässt sich prüfen, ob der Tacho ein
// Layout so zeigt wie die Vorschau im Designer.
//
// Bauen und starten: firmware/hosttest/render.sh (braucht g++ und den
// Quelltext von LovyanGFX in der Version aus platformio.ini).
//
// Aufruf: render <s51fonts.bin> <layout.s51> <Zielordner> [HH:MM]

#include <cstdio>
#include <string>
#include <vector>

#include "s51_render.h"

static bool readFile(const char* path, std::vector<uint8_t>& out) {
  FILE* f = fopen(path, "rb");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  out.resize(n);
  bool ok = fread(out.data(), 1, n, f) == static_cast<size_t>(n);
  fclose(f);
  return ok;
}

int main(int argc, char** argv) {
  if (argc < 4) {
    fprintf(stderr, "Aufruf: render <s51fonts.bin> <layout.s51> <Zielordner> [HH:MM]\n");
    return 2;
  }
  std::vector<uint8_t> fonts, file;
  if (!readFile(argv[1], fonts) || !readFile(argv[2], file)) {
    fprintf(stderr, "Datei nicht lesbar\n");
    return 1;
  }
  s51::LayoutData layout;
  s51::DecodeError err = s51::decodeLayout(file.data(), file.size(), layout);
  if (err != s51::DecodeError::None) {
    fprintf(stderr, "Layout ungültig: %s\n", s51::errorText(err));
    return 1;
  }
  s51::Renderer r;
  if (!r.begin(fonts.data(), fonts.size())) {
    fprintf(stderr, "Schriften ungültig\n");
    return 1;
  }
  r.setLayout(&layout);

  s51::Values v;
  s51::demoValues(v, 0, false);
  if (argc > 4) {
    int h = 0, m = 0;
    if (sscanf(argv[4], "%d:%d", &h, &m) == 2) {
      v.timeValid = true;
      v.hour = h;
      v.minute = m;
    }
  }

  LGFX_Sprite g;
  g.setColorDepth(16);
  if (!g.createSprite(layout.width, layout.height)) return 1;
  for (const auto& s : layout.screens) {
    r.drawScreen(g, s, v, 100);
    std::string path = std::string(argv[3]) + "/seite-" + std::to_string(s.id) + ".ppm";
    FILE* o = fopen(path.c_str(), "wb");
    if (!o) return 1;
    fprintf(o, "P6\n%d %d\n255\n", g.width(), g.height());
    for (int y = 0; y < g.height(); y++) {
      for (int x = 0; x < g.width(); x++) {
        uint16_t c = g.readPixel(x, y);
        uint8_t px[3] = {uint8_t((c >> 11) << 3 | (c >> 13)), uint8_t(((c >> 5) & 63) << 2 | ((c >> 9) & 3)),
                         uint8_t((c & 31) << 3 | ((c >> 2) & 7))};
        fwrite(px, 1, 3, o);
      }
    }
    fclose(o);
    printf("%s\n", path.c_str());
  }
  return 0;
}
