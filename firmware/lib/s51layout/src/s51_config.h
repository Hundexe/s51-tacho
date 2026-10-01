// Leser für die Konfigurationsdatei tacho.cfg
// Format: docs/konfiguration.md
// Reines C++ ohne Arduino-Abhängigkeit.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "s51_schema.h"

namespace s51 {

class Config {
 public:
  struct Warning {
    int line;           // 0 = ohne Zeilenbezug
    std::string text;
  };

  Config();                          // alle Werte auf Standard
  void reset();
  // Liest den Text einer tacho.cfg. Fehlende oder ungültige Werte bleiben auf Standard.
  void parse(const char* text, size_t len, std::vector<Warning>* warnings = nullptr);

  int32_t getInt(CfgKey k) const { return static_cast<int32_t>(num_[idx(k)]); }
  float getFloat(CfgKey k) const { return num_[idx(k)]; }
  bool getBool(CfgKey k) const { return num_[idx(k)] != 0.0f; }
  const std::string& getStr(CfgKey k) const { return str_[idx(k)]; }   // für Str und Enum

  static const CfgDef& def(CfgKey k) { return kConfigDefs[idx(k)]; }

 private:
  static size_t idx(CfgKey k) { return static_cast<size_t>(k); }
  bool setValue(size_t i, const std::string& raw, std::string& error);

  float num_[static_cast<size_t>(CfgKey::Count)];
  std::string str_[static_cast<size_t>(CfgKey::Count)];
};

}  // namespace s51
