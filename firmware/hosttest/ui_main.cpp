// Zeichnet die Design-Auswahl der Firmware am PC (wie in src/main.cpp).
// Aufruf: ui <s51fonts.bin> <Zielordner> <design1.s51> [design2.s51 ...]
// Ergebnis: auswahl-1.ppm (erstes Design markiert), auswahl-2.ppm (zweites markiert,
// mit einem beschädigten Eintrag am Ende der Liste).

#include <cstdio>
#include <string>
#include <vector>

#include "s51_picker.h"

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

static void writePpm(LGFX_Sprite& g, const std::string& path) {
  FILE* o = fopen(path.c_str(), "wb");
  if (!o) return;
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

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  std::vector<uint8_t> fonts;
  if (!readFile(argv[1], fonts)) return 1;
  s51::Renderer r;
  if (!r.begin(fonts.data(), fonts.size())) return 1;

  std::vector<s51::LayoutData> layouts;
  std::vector<s51::DesignEntry> list;
  for (int i = 3; i < argc; i++) {
    std::vector<uint8_t> data;
    s51::LayoutData L;
    if (!readFile(argv[i], data) || s51::decodeLayout(data.data(), data.size(), L) != s51::DecodeError::None) continue;
    s51::DesignEntry e;
    std::string p = argv[i];
    e.file = p.substr(p.find_last_of('/') + 1);
    e.name = L.name;
    e.author = L.author;
    for (const auto& s : L.screens) {
      if (s.role == s51::kRolePage) e.pages++;
      if (s.role == s51::kRoleNight) e.hasNight = true;
      if (s.role == s51::kRoleStartup) e.hasStartup = true;
    }
    list.push_back(e);
    layouts.push_back(std::move(L));
  }
  if (list.empty()) return 1;

  s51::Values v;
  s51::demoValues(v, 0, false);
  LGFX_Sprite g, preview;
  g.setColorDepth(16);
  preview.setColorDepth(16);
  g.createSprite(480, 320);
  preview.createSprite(480, 320);

  auto renderPreview = [&](int i) {
    const s51::ScreenData* s = &layouts[i].screens[0];
    for (const auto& sc : layouts[i].screens) {
      if (sc.role == s51::kRolePage) {
        s = &sc;
        break;
      }
    }
    r.setLayout(&layouts[i]);
    r.drawScreen(preview, *s, v, 100);
  };

  s51::Picker picker;
  picker.open(list, 0);
  renderPreview(0);
  picker.draw(g, r, &preview);
  writePpm(g, std::string(argv[2]) + "/auswahl-1.ppm");

  s51::DesignEntry broken;
  broken.file = "kaputt.s51";
  broken.ok = false;
  broken.error = "Prüfsumme falsch";
  list.push_back(broken);
  picker.open(list, 0);
  picker.tap(100, 56 + 52 + 10);       // zweiten Eintrag antippen
  renderPreview(picker.highlighted());
  picker.draw(g, r, &preview);
  writePpm(g, std::string(argv[2]) + "/auswahl-2.ppm");

  picker.scroll(-400);                  // ans Ende der Liste wischen
  picker.tap(100, 56 + 52 * 4 + 10);
  picker.draw(g, r, picker.entries()[picker.highlighted()].ok ? &preview : nullptr);
  writePpm(g, std::string(argv[2]) + "/auswahl-3.ppm");
  return 0;
}
