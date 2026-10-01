// Zeichnet Seiten eines Layouts (.s51) in ein LovyanGFX-Sprite.
// Regeln: docs/dateiformat-layout.md, Abschnitt „Darstellung“.
// Läuft auf dem Tacho und am PC (firmware/hosttest/render_main.cpp).
#pragma once

#define LGFX_USE_V1
#include <LovyanGFX.hpp>

#include <map>
#include <string>
#include <vector>

#include "s51_layout.h"
#include "s51_text.h"
#include "s51_values.h"

namespace s51 {

class Renderer {
 public:
  Renderer() = default;
  ~Renderer();
  bool begin(const uint8_t* fontBlob, size_t len) { return fonts_.begin(fontBlob, len); }

  // Neues Layout: leert den Bild-Zwischenspeicher. Das Layout muss so lange leben,
  // wie damit gezeichnet wird.
  void setLayout(const LayoutData* layout);

  // Zeichnet die ganze Seite. ms = Laufzeit für das Blinken. pressed: Taste, die gerade
  // gedrückt wird (heller gezeichnet), oder nullptr.
  void drawScreen(LGFX_Sprite& g, const ScreenData& screen, const Values& v, uint32_t ms,
                  const WidgetData* pressed = nullptr);

  // Text mittig in einem Rahmen, z. B. für Meldungen ohne Layout
  void drawLabel(LGFX_Sprite& g, const std::string& text, int x, int y, int w, int h, Font font, int size,
                 Color color, Align align = Align::Center);

 private:
  struct Decoded {
    uint16_t* rgb = nullptr;     // RGB565
    uint8_t* alpha = nullptr;    // nullptr: Bild ohne Alpha
    bool failed = false;
  };

  void drawWidget(LGFX_Sprite& g, const WidgetData& w, const Values& v, uint32_t ms, bool pressed);
  void drawText(LGFX_Sprite& g, const WidgetData& w, const std::string& text, Color color, bool wrap);
  void drawTextBox(LGFX_Sprite& g, const std::string& text, float x, float y, float w, float h, Font font,
                   float size, Color color, Align align, bool wrap, bool clipToBox);
  Canvas565 canvas(LGFX_Sprite& g);
  void drawBar(LGFX_Sprite& g, const WidgetData& w, const Values& v);
  void drawGauge(LGFX_Sprite& g, const WidgetData& w, const Values& v);
  void drawIcon(LGFX_Sprite& g, Icon icon, float x, float y, float w, float h, Color color);
  void drawPlate(LGFX_Sprite& g, const WidgetData& w, Color color);
  void drawRect(LGFX_Sprite& g, const WidgetData& w);
  void drawButton(LGFX_Sprite& g, const WidgetData& w, const Values& v, bool pressed);
  void drawImage(LGFX_Sprite& g, const WidgetData& w);
  const Decoded* decoded(uint8_t imageId);
  void clearImages();

  FontSet fonts_;
  const LayoutData* layout_ = nullptr;
  std::map<uint8_t, Decoded> images_;
};

}  // namespace s51
