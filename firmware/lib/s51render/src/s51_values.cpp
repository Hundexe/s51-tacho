#include "s51_values.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace s51 {

void Values::clear() {
  for (int i = 0; i < 128; i++) {
    number[i] = 0;
    has[i] = false;
    flag[i] = false;
  }
  songTitle.clear();
  songArtist.clear();
  timeValid = false;
  hour = minute = second = 0;
}

SourceKind kindOf(Source s) {
  for (const auto& d : kSourceDefs) {
    if (d.source == s) return d.kind;
  }
  return isBoolSource(s) ? SourceKind::Bool : SourceKind::Number;
}

std::string formatNumber(double value, int decimals) {
  if (decimals < 0) decimals = 0;
  if (decimals > 6) decimals = 6;
  char buf[48];
  snprintf(buf, sizeof(buf), "%.*f", decimals, value);
  std::string s(buf);
  bool neg = !s.empty() && s[0] == '-';
  if (neg) s.erase(0, 1);
  size_t dot = s.find('.');
  std::string intPart = dot == std::string::npos ? s : s.substr(0, dot);
  std::string frac = dot == std::string::npos ? "" : s.substr(dot + 1);
  std::string grouped;
  int n = static_cast<int>(intPart.size());
  for (int i = 0; i < n; i++) {
    grouped += intPart[i];
    int rest = n - 1 - i;
    if (rest > 0 && rest % 3 == 0) grouped += '.';
  }
  std::string out = neg ? "-" + grouped : grouped;
  if (!frac.empty()) out += "," + frac;
  return out;
}

static void replaceAll(std::string& s, const char* from, const std::string& to) {
  size_t pos = 0, len = strlen(from);
  while ((pos = s.find(from, pos)) != std::string::npos) {
    s.replace(pos, len, to);
    pos += to.size();
  }
}

std::string formatTime(const Values& v, const std::string& fmt) {
  std::string s = fmt;
  auto two = [](int x) {
    char b[4];
    snprintf(b, sizeof(b), "%02d", x);
    return std::string(b);
  };
  replaceAll(s, "HH", v.timeValid ? two(v.hour) : "--");
  replaceAll(s, "MM", v.timeValid ? two(v.minute) : "--");
  replaceAll(s, "SS", v.timeValid ? two(v.second) : "--");
  return s;
}

static const char* kDash = "\xE2\x80\x93";  // –

std::string displayText(const WidgetData& w, const Values& v) {
  if (w.type == WidgetType::Text) return w.text;
  Source src = w.source;
  if (src == Source::None) return kDash;
  switch (kindOf(src)) {
    case SourceKind::Time:
      return formatTime(v, w.format.empty() ? std::string("HH:MM") : w.format);
    case SourceKind::Text:
      return src == Source::SongTitle ? v.songTitle : v.songArtist;
    case SourceKind::Bool:
      return v.getFlag(src) ? "an" : "aus";
    case SourceKind::Number:
    default:
      if (!v.hasNumber(src)) return kDash;
      return formatNumber(v.get(src), w.decimals) + w.unit;
  }
}

Color thresholdColor(const WidgetData& w, bool hasValue, float value, Color normal) {
  if (!hasValue) return normal;
  if (w.critAbove != 0.0f && value >= w.critAbove) return w.critColor;
  if (w.warnAbove != 0.0f && value >= w.warnAbove) return w.warnColor;
  return normal;
}

float fraction(const WidgetData& w, bool hasValue, float value) {
  if (!hasValue || w.max == w.min) return 0.0f;
  float f = (value - w.min) / (w.max - w.min);
  return f < 0 ? 0.0f : (f > 1 ? 1.0f : f);
}

void fillRange(const WidgetData& w, bool hasValue, float value, float& a, float& b) {
  float f = fraction(w, hasValue, value);
  if (!w.fromZero) {
    a = 0;
    b = f;
    return;
  }
  if (!hasValue) {
    a = b = 0;
    return;
  }
  float f0 = fraction(w, true, 0.0f);
  a = std::min(f0, f);
  b = std::max(f0, f);
}

float fillValue(const WidgetData& w, float value) { return w.fromZero ? std::fabs(value) : value; }

bool segmentLit(const WidgetData& w, bool hasValue, float value, int i, int n, float& segValue) {
  if (!w.fromZero) {
    // wie Pythons round(): bei .5 zur geraden Zahl
    int lit = static_cast<int>(std::nearbyint(fraction(w, hasValue, value) * n));
    segValue = w.min + (w.max - w.min) * (i + 1) / n;
    return i < lit;
  }
  float a, b;
  fillRange(w, hasValue, value, a, b);
  float c = (i + 0.5f) / n;
  float f0 = fraction(w, true, 0.0f);
  float end = c >= f0 ? float(i + 1) / n : float(i) / n;
  segValue = std::fabs(w.min + (w.max - w.min) * end);
  return b > a && a <= c && c <= b;
}

bool indicatorOn(const WidgetData& w, const Values& v, uint32_t ms) {
  Source src = w.source;
  bool on = false;
  if (src != Source::None) {
    on = kindOf(src) == SourceKind::Bool ? v.getFlag(src) : (v.hasNumber(src) && v.get(src) != 0.0f);
  }
  if (on && w.blink) on = (ms / 500) % 2 == 0;
  return on;
}

void demoValues(Values& v, float t, bool animate) {
  v.clear();
  float phase = animate ? std::fmod(t, 20.0f) / 20.0f : 0.55f;
  for (const auto& d : kSourceDefs) {
    if (d.kind != SourceKind::Number || d.source == Source::None) continue;
    float val = d.demoMin;
    if (d.demoMin != d.demoMax) {
      val = d.demoMin + (d.demoMax - d.demoMin) * (0.5f - 0.5f * std::cos(phase * 2.0f * 3.14159265f));
    }
    v.set(d.source, val);
  }
  float speed = v.get(Source::Speed);
  int gear = speed < 1 ? 0 : speed < 15 ? 1 : speed < 30 ? 2 : speed < 45 ? 3 : 4;
  float inGear = std::fmod(speed, 15.0f) / 15.0f;
  v.set(Source::Gear, static_cast<float>(gear));
  v.set(Source::Rpm, gear == 0 ? 1500.0f : 3000.0f + inGear * 4500.0f);
  v.set(Source::Lean, animate ? 30.0f * std::sin(t * 0.7f) : 12.0f);
  v.songTitle = "Schwalbenflug";
  v.songArtist = "Testband";
  bool blink = animate ? static_cast<int>(t * 2) % 2 == 0 : true;
  v.setFlag(Source::BlinkerLeft, blink);
  v.setFlag(Source::BlinkerRight, false);
  v.setFlag(Source::HighBeam, true);
  v.setFlag(Source::Neutral, gear == 0);
  v.setFlag(Source::Light, true);
  v.setFlag(Source::AlarmArmed, false);
  v.setFlag(Source::GpsFix, true);
  v.setFlag(Source::BtConnected, true);
  v.setFlag(Source::ShiftLight, v.get(Source::Rpm) > 6500);
  v.setFlag(Source::Warning, v.get(Source::HeadTemp) > 200);
}

}  // namespace s51
