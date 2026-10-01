// Decoder für S51-Layout-Dateien (.s51)
// Format: docs/dateiformat-layout.md
// Reines C++ ohne Arduino-Abhängigkeit, damit es auch am PC getestet werden kann.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "s51_schema.h"

namespace s51 {

struct WidgetData {
  WidgetType type;
  uint8_t typeCode;   // Rohwert, auch für unbekannte Typen aus neueren Dateien
  bool known;         // false: Typ unbekannt, wird nicht gezeichnet
  bool hidden;
  int16_t x, y;
  uint16_t w, h;
  S51_WIDGET_FIELDS

  bool isSet(Prop p) const {
    uint8_t c = static_cast<uint8_t>(p);
    return (propsSet[c / 32] >> (c % 32)) & 1u;
  }
};

struct ScreenData {
  uint8_t id = 0;
  uint8_t role = kRolePage;    // kRolePage, kRoleNight oder kRoleStartup
  bool night = false;          // Nachtversion einer Seite
  uint8_t nightOf = kNoPage;   // bei night: Nummer der Tagseite
  Color bg{0, 0, 0};
  std::string name;
  std::vector<WidgetData> widgets;
};

struct ImageData {
  uint8_t id = 0;
  uint8_t format = 0;          // kImageFormatRaw oder kImageFormatRle
  bool hasAlpha = false;
  uint16_t width = 0, height = 0;
  std::string name;
  std::vector<uint8_t> data;   // kodierte Pixel, wie in der Datei

  // Entpackt die Pixel. rgb565 braucht width*height Einträge, alpha (optional)
  // width*height Bytes. Ohne Alpha im Bild wird alpha mit 255 gefüllt.
  bool decodePixels(uint16_t* rgb565, uint8_t* alpha) const;
};

struct LayoutData {
  uint16_t width = 0, height = 0;
  std::string name, author, tool;
  uint32_t created = 0;
  uint32_t crc = 0;            // Prüfsumme der Datei
  std::vector<ScreenData> screens;
  std::vector<ImageData> images;

  const ImageData* findImage(uint8_t id) const;
  const ScreenData* startupScreen() const;

  const ScreenData* findScreen(uint8_t id) const;
  // Nachtversion einer Seite oder die Seite selbst, wenn es keine gibt
  const ScreenData* screenFor(uint8_t id, bool nightMode) const;
};

enum class DecodeError : uint8_t {
  None = 0,
  TooSmall,
  TooLarge,
  BadMagic,
  BadVersion,
  BadCrc,
  BadHeader,
  Truncated,
  TooManyScreens,
  TooManyWidgets,
  NoScreens,
  BadProperty,
  BadImage,
  TooManyImages,
};

const char* errorText(DecodeError e);

uint32_t crc32(const uint8_t* data, size_t len);

// Dekodiert eine komplette Datei. Bei Fehler bleibt `out` leer.
DecodeError decodeLayout(const uint8_t* data, size_t len, LayoutData& out);

}  // namespace s51
