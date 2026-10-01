// Kantengeglättete Schrift für den Tacho.
// Liest die Schriften aus data/s51fonts.bin (erzeugt von firmware/tools/gen_fonts.py)
// und zeichnet Text direkt in ein 16-Bit-Bild (RGB565 mit vertauschten Bytes,
// wie in einem LovyanGFX-Sprite). Größen zwischen den gespeicherten Größen werden
// beim Verkleinern über die Fläche gemittelt und beim Vergrößern weich interpoliert.
// Reines C++ ohne Arduino-Abhängigkeit.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "s51_schema.h"

namespace s51 {

// Zielbild für Text und Bilder
struct Canvas565 {
  uint16_t* buf = nullptr;   // Pixel mit vertauschten Bytes (swap565)
  int width = 0, height = 0;
  int clipX = 0, clipY = 0, clipW = 0, clipH = 0;
  void clipAll() { clipX = 0; clipY = 0; clipW = width; clipH = height; }
  void clip(int x, int y, int w, int h);   // Schnitt mit dem ganzen Bild
};

class FontSet {
 public:
  bool begin(const uint8_t* blob, size_t len);
  size_t count() const { return faces_.size(); }

  struct Glyph {
    uint32_t code;
    uint16_t w, h;
    float advance;             // Vorschub in Pixel (genau, aus dem 7. Feld der VLW-Daten)
    int16_t dy, dx;            // dy: Oberkante über der Grundlinie, dx: Versatz nach rechts
    const uint8_t* bitmap;
  };
  struct Face {
    uint8_t family, subset;
    uint16_t size;
    int ascent, descent;
    std::vector<Glyph> glyphs;   // nach code sortiert
    const Glyph* find(uint32_t code) const;
  };
  struct Choice {
    const Face* face = nullptr;
    float scale = 1.0f;
    float ascent() const { return face ? face->ascent * scale : 0; }
    float descent() const { return face ? face->descent * scale : 0; }
  };

  // Schrift für Familie und Pixelgröße. digitsOnly: Text besteht nur aus Ziffern
  // und Zahlzeichen, dann sind auch die großen Ziffern-Schriften erlaubt.
  Choice pick(Font family, float sizePx, bool digitsOnly) const;

  static float textWidth(const Choice& c, const std::string& utf8);
  // Zeichnet ab x (links) auf der Grundlinie baseline
  static void draw(Canvas565& cv, const Choice& c, const std::string& utf8, float x, float baseline, Color color);

 private:
  std::vector<Face> faces_;
};

// Kantengeglätteter Kreisbogen (Ring zwischen r0 und r1) von Winkel a0 bis a1 in Grad.
// 0° = rechts, im Uhrzeigersinn. a1 - a0 bis 360°. Enden gerade abgeschnitten.
void fillArcAA(Canvas565& cv, float cx, float cy, float r0, float r1, float a0, float a1, Color color);

uint32_t nextCodepoint(const std::string& s, size_t& i);
bool isDigitText(const std::string& s);

}  // namespace s51
