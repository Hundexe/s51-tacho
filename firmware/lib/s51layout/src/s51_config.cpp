#include "s51_config.h"

#include <cctype>
#include <cstdlib>
#include <cstring>

namespace s51 {

namespace {

constexpr size_t kCount = static_cast<size_t>(CfgKey::Count);

std::string trim(const std::string& s) {
  size_t a = 0, b = s.size();
  while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
  while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
  return s.substr(a, b - a);
}

std::string lower(std::string s) {
  for (auto& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return s;
}

bool parseBool(const std::string& v, bool& out) {
  std::string l = lower(v);
  if (l == "ja" || l == "true" || l == "1" || l == "an" || l == "yes") { out = true; return true; }
  if (l == "nein" || l == "false" || l == "0" || l == "aus" || l == "no") { out = false; return true; }
  return false;
}

bool parseNumber(std::string v, bool isInt, float& out) {
  for (auto& c : v) if (c == ',') c = '.';
  if (v.empty()) return false;
  char* end = nullptr;
  if (isInt) {
    long n = std::strtol(v.c_str(), &end, 10);
    if (*end != '\0') return false;
    out = static_cast<float>(n);
  } else {
    float f = std::strtof(v.c_str(), &end);
    if (*end != '\0') return false;
    out = f;
  }
  return true;
}

bool choiceAllowed(const char* choices, const std::string& v) {
  std::string all(choices);
  size_t start = 0;
  while (start <= all.size()) {
    size_t bar = all.find('|', start);
    if (bar == std::string::npos) bar = all.size();
    if (all.compare(start, bar - start, v) == 0) return true;
    start = bar + 1;
  }
  return false;
}

}  // namespace

Config::Config() { reset(); }

void Config::reset() {
  for (size_t i = 0; i < kCount; ++i) {
    std::string err;
    num_[i] = 0;
    str_[i].clear();
    setValue(i, kConfigDefs[i].defaultValue, err);
  }
}

bool Config::setValue(size_t i, const std::string& rawIn, std::string& error) {
  const CfgDef& d = kConfigDefs[i];
  std::string v = trim(rawIn);
  if (v.size() >= 2 && v.front() == '"' && v.back() == '"') v = v.substr(1, v.size() - 2);
  switch (d.type) {
    case CfgType::Bool: {
      bool b;
      if (!parseBool(v, b)) { error = "erwartet ja oder nein"; return false; }
      num_[i] = b ? 1.0f : 0.0f;
      return true;
    }
    case CfgType::Int:
    case CfgType::Float: {
      float f;
      if (!parseNumber(v, d.type == CfgType::Int, f)) { error = "keine gueltige Zahl"; return false; }
      if (d.min != d.max && (f < d.min || f > d.max)) { error = "Wert ausserhalb des Bereichs"; return false; }
      num_[i] = f;
      return true;
    }
    case CfgType::Enum: {
      std::string l = lower(v);
      if (!choiceAllowed(d.choices, l)) { error = std::string("erlaubt sind ") + d.choices; return false; }
      str_[i] = l;
      return true;
    }
    case CfgType::Str:
      str_[i] = v;
      return true;
  }
  return false;
}

void Config::parse(const char* text, size_t len, std::vector<Warning>* warnings) {
  auto warn = [&](int line, const std::string& t) {
    if (warnings) warnings->push_back(Warning{line, t});
  };
  std::string section;
  bool sectionKnown = false;
  int lineNo = 0;
  size_t pos = 0;
  if (len >= 3 && std::memcmp(text, "\xEF\xBB\xBF", 3) == 0) pos = 3;   // UTF-8-BOM
  while (pos < len) {
    size_t eol = pos;
    while (eol < len && text[eol] != '\n') ++eol;
    std::string line = trim(std::string(text + pos, eol - pos));
    pos = eol + 1;
    ++lineNo;
    if (line.empty() || line[0] == '#' || line[0] == ';') continue;
    if (line.front() == '[' && line.back() == ']') {
      section = lower(trim(line.substr(1, line.size() - 2)));
      sectionKnown = false;
      for (size_t i = 0; i < kCount; ++i)
        if (section == kConfigDefs[i].section) { sectionKnown = true; break; }
      if (!sectionKnown) warn(lineNo, "Unbekannter Abschnitt [" + section + "]");
      continue;
    }
    size_t eq = line.find('=');
    if (eq == std::string::npos) { warn(lineNo, "Zeile ohne '='"); continue; }
    std::string key = lower(trim(line.substr(0, eq)));
    std::string raw = trim(line.substr(eq + 1));
    if (!raw.empty() && raw[0] == '"') {
      size_t close = raw.find('"', 1);
      if (close != std::string::npos) raw = raw.substr(0, close + 1);
    } else {
      size_t c1 = raw.find(" #"), c2 = raw.find(" ;");
      size_t c = c1 < c2 ? c1 : c2;
      if (c != std::string::npos) raw = trim(raw.substr(0, c));
    }
    if (section.empty()) { warn(lineNo, key + " steht vor dem ersten Abschnitt"); continue; }
    size_t found = kCount;
    for (size_t i = 0; i < kCount; ++i) {
      if (section == kConfigDefs[i].section && key == kConfigDefs[i].key) { found = i; break; }
    }
    if (found == kCount) {
      if (sectionKnown) warn(lineNo, "Unbekannter Schluessel " + key + " in [" + section + "]");
      continue;
    }
    std::string err;
    std::string before = str_[found];
    float beforeNum = num_[found];
    if (!setValue(found, raw, err)) {
      str_[found] = before;
      num_[found] = beforeNum;
      warn(lineNo, section + "." + key + ": " + err + ", Standard wird verwendet");
    }
  }
}

}  // namespace s51
