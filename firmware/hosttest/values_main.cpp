// Gibt für jedes Element einer Layout-Datei aus, was die Firmware anzeigen würde:
// Text, Farbe nach Warnregeln, Anteil für Balken und Rundinstrument, Kontrollleuchte an/aus.
// Die Tests in designer/tests/test_firmware_render.py vergleichen das mit den
// Regeln des Designers (designer/s51design/values.py).
//
// Aufruf: values <layout.s51>     (Demo-Werte fest, Uhrzeit 14:27:00)

#include <cstdio>
#include <vector>

#include "s51_values.h"

static void hex(char* out, s51::Color c) { snprintf(out, 8, "#%02X%02X%02X", c.r, c.g, c.b); }

int main(int argc, char** argv) {
  if (argc < 2) return 2;
  FILE* f = fopen(argv[1], "rb");
  if (!f) return 1;
  std::vector<uint8_t> data;
  int c;
  while ((c = fgetc(f)) != EOF) data.push_back(static_cast<uint8_t>(c));
  fclose(f);
  s51::LayoutData L;
  if (s51::decodeLayout(data.data(), data.size(), L) != s51::DecodeError::None) return 1;

  s51::Values v;
  s51::demoValues(v, 0, false);
  v.timeValid = true;
  v.hour = 14;
  v.minute = 27;
  v.second = 0;

  for (const auto& s : L.screens) {
    int i = 0;
    for (const auto& w : s.widgets) {
      char col[8] = "-";
      std::string text = "-";
      float frac = 0;
      int on = 0;
      bool has = w.source != s51::Source::None && s51::kindOf(w.source) == s51::SourceKind::Number &&
                 v.hasNumber(w.source);
      float value = has ? v.get(w.source) : 0;
      switch (w.type) {
        case s51::WidgetType::Text:
        case s51::WidgetType::Value:
          text = s51::displayText(w, v);
          hex(col, w.type == s51::WidgetType::Value ? s51::thresholdColor(w, has, value, w.color) : w.color);
          break;
        case s51::WidgetType::Bar:
        case s51::WidgetType::Gauge:
          frac = s51::fraction(w, has, value);
          hex(col, s51::thresholdColor(w, has, value, w.color));
          break;
        case s51::WidgetType::Indicator:
          on = s51::indicatorOn(w, v, 100) ? 1 : 0;
          break;
        default:
          break;
      }
      printf("%u|%d|%s|%s|%.3f|%d\n", unsigned(s.id), i, text.c_str(), col, frac, on);
      i++;
    }
  }
  return 0;
}
