// Host-Test: dekodiert eine Layout- und eine Konfigurationsdatei und gibt
// eine feste Textdarstellung aus. Der Python-Test (designer/tests/test_cpp_decoder.py)
// erzeugt dieselbe Darstellung mit dem Python-Decoder und vergleicht beide.
//
// Bauen von Hand (im Ordner firmware/hosttest):
//   g++ -std=c++17 -I../lib/s51layout/src dump_main.cpp ../lib/s51layout/src/*.cpp -o dump
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "s51_config.h"
#include "s51_layout.h"

using namespace s51;

static std::string hex(const Color& c) {
  char b[8];
  std::snprintf(b, sizeof b, "#%02X%02X%02X", c.r, c.g, c.b);
  return b;
}
static std::string f4(float f) {
  char b[32];
  std::snprintf(b, sizeof b, "%.4f", f);
  return b;
}
static std::string u(unsigned v) { return std::to_string(v); }
static std::string i(int v) { return std::to_string(v); }

static std::vector<uint8_t> readFile(const char* path) {
  std::ifstream f(path, std::ios::binary);
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}

static void dumpWidget(const WidgetData& w) {
  std::printf("WIDGET %u|%d|%d|%d|%u|%u\n", w.typeCode, w.hidden ? 1 : 0, w.x, w.y, w.w, w.h);
  // Reihenfolge und Formatierung wie in test_cpp_decoder.py (Reihenfolge des Schemas)
  std::printf(" source=%s\n", u(static_cast<unsigned>(w.source)).c_str());
  std::printf(" color=%s\n", hex(w.color).c_str());
  std::printf(" bg_color=%s\n", hex(w.bgColor).c_str());
  std::printf(" font=%s\n", u(static_cast<unsigned>(w.font)).c_str());
  std::printf(" size=%s\n", u(w.size).c_str());
  std::printf(" align=%s\n", u(static_cast<unsigned>(w.align)).c_str());
  std::printf(" text=%s\n", w.text.c_str());
  std::printf(" decimals=%s\n", u(w.decimals).c_str());
  std::printf(" unit=%s\n", w.unit.c_str());
  std::printf(" min=%s\n", f4(w.min).c_str());
  std::printf(" max=%s\n", f4(w.max).c_str());
  std::printf(" warn_above=%s\n", f4(w.warnAbove).c_str());
  std::printf(" warn_color=%s\n", hex(w.warnColor).c_str());
  std::printf(" crit_above=%s\n", f4(w.critAbove).c_str());
  std::printf(" crit_color=%s\n", hex(w.critColor).c_str());
  std::printf(" segments=%s\n", u(w.segments).c_str());
  std::printf(" orientation=%s\n", u(static_cast<unsigned>(w.orientation)).c_str());
  std::printf(" start_angle=%s\n", i(w.startAngle).c_str());
  std::printf(" end_angle=%s\n", i(w.endAngle).c_str());
  std::printf(" thickness=%s\n", u(w.thickness).c_str());
  std::printf(" radius=%s\n", u(w.radius).c_str());
  std::printf(" icon=%s\n", u(static_cast<unsigned>(w.icon)).c_str());
  std::printf(" on_color=%s\n", hex(w.onColor).c_str());
  std::printf(" off_color=%s\n", hex(w.offColor).c_str());
  std::printf(" blink=%d\n", w.blink ? 1 : 0);
  std::printf(" format=%s\n", w.format.c_str());
  std::printf(" border_color=%s\n", hex(w.borderColor).c_str());
  std::printf(" border_width=%s\n", u(w.borderWidth).c_str());
  std::printf(" image=%s\n", u(w.image).c_str());
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::fprintf(stderr, "Aufruf: dump <layout.s51> [tacho.cfg]\n");
    return 2;
  }
  std::vector<uint8_t> data = readFile(argv[1]);
  LayoutData L;
  DecodeError e = decodeLayout(data.data(), data.size(), L);
  if (e != DecodeError::None) {
    std::printf("ERROR %d %s\n", static_cast<int>(e), errorText(e));
  } else {
    std::printf("LAYOUT %s|%s|%s|%u|%u|%u|%zu\n", L.name.c_str(), L.author.c_str(), L.tool.c_str(),
                L.created, L.width, L.height, L.screens.size());
    for (const auto& img : L.images) {
      size_t n = static_cast<size_t>(img.width) * img.height;
      std::vector<uint16_t> rgb(n);
      std::vector<uint8_t> alpha(n);
      bool ok = img.decodePixels(rgb.data(), alpha.data());
      std::vector<uint8_t> flat;
      flat.reserve(n * 3);
      for (size_t k = 0; k < n; ++k) {
        flat.push_back(static_cast<uint8_t>(rgb[k] & 0xFF));
        flat.push_back(static_cast<uint8_t>(rgb[k] >> 8));
        flat.push_back(alpha[k]);
      }
      std::printf("IMAGE %u|%s|%u|%u|%d|%08x|%d\n", img.id, img.name.c_str(), img.width, img.height,
                  img.hasAlpha ? 1 : 0, crc32(flat.data(), flat.size()), ok ? 1 : 0);
    }
    for (const auto& s : L.screens) {
      std::printf("SCREEN %u|%u|%u|%s|%s|%zu\n", s.id, s.role, s.nightOf, hex(s.bg).c_str(),
                  s.name.c_str(), s.widgets.size());
      for (const auto& w : s.widgets) dumpWidget(w);
    }
  }
  if (argc >= 3) {
    std::vector<uint8_t> cfgText = readFile(argv[2]);
    Config cfg;
    std::vector<Config::Warning> warnings;
    cfg.parse(reinterpret_cast<const char*>(cfgText.data()), cfgText.size(), &warnings);
    for (size_t k = 0; k < static_cast<size_t>(CfgKey::Count); ++k) {
      CfgKey key = static_cast<CfgKey>(k);
      const CfgDef& d = Config::def(key);
      std::string v;
      switch (d.type) {
        case CfgType::Int: v = std::to_string(cfg.getInt(key)); break;
        case CfgType::Float: v = f4(cfg.getFloat(key)); break;
        case CfgType::Bool: v = cfg.getBool(key) ? "ja" : "nein"; break;
        default: v = cfg.getStr(key); break;
      }
      std::printf("CFG %s.%s=%s\n", d.section, d.key, v.c_str());
    }
    std::printf("CFGWARNINGS %zu\n", warnings.size());
  }
  return 0;
}
