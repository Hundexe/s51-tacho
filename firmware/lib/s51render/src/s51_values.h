// Werte der Datenquellen und die Regeln, wie sie angezeigt werden.
// Gleiche Regeln wie im Designer (designer/s51design/values.py),
// beschrieben in docs/dateiformat-layout.md, Abschnitt „Darstellung“.
// Reines C++ ohne Arduino-Abhängigkeit, damit es am PC getestet werden kann.
#pragma once

#include <cstdint>
#include <string>

#include "s51_layout.h"

namespace s51 {

struct Values {
  float number[128];      // Zahlenquellen, Index = Nummer der Quelle
  bool has[128];          // false: Wert unbekannt, Anzeige „–“
  bool flag[128];         // Ja/Nein-Quellen
  std::string text[64];   // Textquellen (Songtitel, Interpret …), Index = Nummer der Quelle
  bool timeValid = false;
  uint8_t hour = 0, minute = 0, second = 0;

  Values() { clear(); }
  void clear();
  void set(Source s, float v) { number[idx(s)] = v; has[idx(s)] = true; }
  void unset(Source s) { has[idx(s)] = false; }
  void setFlag(Source s, bool on) { flag[idx(s)] = on; }
  bool hasNumber(Source s) const { return has[idx(s)]; }
  float get(Source s) const { return number[idx(s)]; }
  bool getFlag(Source s) const { return flag[idx(s)]; }
  void setText(Source s, const std::string& t) { text[idx(s) & 63] = t; }
  const std::string& getText(Source s) const { return text[idx(s) & 63]; }
  static size_t idx(Source s) { return static_cast<uint8_t>(s) & 0x7F; }
};

SourceKind kindOf(Source s);

// Zahl mit Tausenderpunkt und Dezimalkomma, z. B. "12.345" oder "13,8"
std::string formatNumber(double value, int decimals);
// Uhrzeit nach Format mit HH, MM, SS. Unbekannte Zeit: "--"
std::string formatTime(const Values& v, const std::string& fmt);
// Text, den ein Element vom Typ Text oder Wert zeigt
std::string displayText(const WidgetData& w, const Values& v);
// Farbe nach Warn- und Kritisch-Schwelle
Color thresholdColor(const WidgetData& w, bool hasValue, float value, Color normal);
// Anteil 0..1 für Balken und Rundinstrument
float fraction(const WidgetData& w, bool hasValue, float value);
// Gefüllter Bereich [a, b] als Anteile 0..1. Normal von 0 bis zum Anteil des Werts,
// mit from_zero von der Stelle des Werts 0 bis zum Wert.
void fillRange(const WidgetData& w, bool hasValue, float value, float& a, float& b);
// Wert für die Warnfarben von Balken und Rundinstrument (mit from_zero der Betrag)
float fillValue(const WidgetData& w, float value);
// Leuchtet Segment i von n? segValue: Wert, nach dem das Segment gefärbt wird
bool segmentLit(const WidgetData& w, bool hasValue, float value, int i, int n, float& segValue);
// Gezeichnetes Symbol: PlayPause wird zu Pause, solange Musik läuft, sonst Play
Icon resolveIcon(Icon icon, const Values& v);
// Rahmen für Symbol und Text einer Taste (x, y, w, h). Gibt zurück, welche es gibt.
struct ButtonBoxes {
  bool hasIcon = false, hasText = false;
  float ix = 0, iy = 0, is = 0;              // Symbol: quadratisch
  float tx = 0, ty = 0, tw = 0, th = 0;      // Text
};
ButtonBoxes buttonBoxes(const WidgetData& w);
// Kontrollleuchte an? ms = Laufzeit in Millisekunden (für das Blinken mit 2 Hz)
bool indicatorOn(const WidgetData& w, const Values& v, uint32_t ms);

// Demo-Werte wie in der Vorschau des Designers. t in Sekunden.
// animate = false: feste Werte wie in den Vorschaubildern.
void demoValues(Values& v, float t, bool animate = true);

}  // namespace s51
