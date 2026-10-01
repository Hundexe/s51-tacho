// Design-Auswahl auf dem Display: Liste aller Layouts mit Vorschau.
// Nur Zeichnen und Antippen, keine Dateizugriffe (die macht src/main.cpp).
// Läuft auch am PC (firmware/hosttest/ui_main.cpp).
#pragma once

#include <string>
#include <vector>

#include "s51_render.h"

namespace s51 {

struct DesignEntry {
  std::string file;      // Dateiname im Ordner s51, leer beim eingebauten Layout
  std::string name;      // Name aus dem Layout
  std::string author;
  int pages = 0;         // Tagseiten
  bool hasStartup = false;
  bool hasNight = false;
  bool ok = true;        // false: Datei beschädigt
  std::string error;
};

// Verkleinert ein 16-Bit-Sprite (Flächenmittelung) in einen Bereich eines anderen
void downscaleInto(LGFX_Sprite& src, LGFX_Sprite& dst, int dx, int dy, int dw, int dh);

class Picker {
 public:
  static constexpr int kPreviewW = 216;
  static constexpr int kPreviewH = 144;

  enum class Action { None, Close, Highlight, Apply };

  void open(std::vector<DesignEntry> list, int active);
  void close() { open_ = false; }
  bool isOpen() const { return open_; }
  int highlighted() const { return highlight_; }
  int active() const { return active_; }
  const std::vector<DesignEntry>& entries() const { return list_; }

  Action tap(int x, int y);
  void scroll(int dy);   // Wischen in der Liste, dy in Pixel

  // preview: Vorschau der markierten Seite in kPreviewW × kPreviewH, oder nullptr
  void draw(LGFX_Sprite& g, Renderer& r, LGFX_Sprite* preview);

 private:
  static constexpr int kListTop = 56;
  static constexpr int kRowH = 52;
  static constexpr int kListW = 232;

  int visibleRows(int screenH) const { return (screenH - kListTop) / kRowH; }
  void clampScroll();

  std::vector<DesignEntry> list_;
  int highlight_ = 0, active_ = 0, scroll_ = 0;
  int screenH_ = 320;
  bool open_ = false;
};

}  // namespace s51
