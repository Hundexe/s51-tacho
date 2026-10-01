#include "s51_text.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <iterator>

namespace s51 {

void Canvas565::clip(int x, int y, int w, int h) {
  int x0 = std::max(0, x), y0 = std::max(0, y);
  int x1 = std::min(width, x + w), y1 = std::min(height, y + h);
  clipX = x0;
  clipY = y0;
  clipW = std::max(0, x1 - x0);
  clipH = std::max(0, y1 - y0);
}

uint32_t nextCodepoint(const std::string& s, size_t& i) {
  uint8_t c = s[i++];
  if (c < 0x80) return c;
  int extra = (c >= 0xF0) ? 3 : (c >= 0xE0) ? 2 : (c >= 0xC0) ? 1 : 0;
  uint32_t cp = c & (0x3F >> extra);
  while (extra-- > 0 && i < s.size()) cp = (cp << 6) | (uint8_t(s[i++]) & 0x3F);
  return cp;
}

bool isDigitText(const std::string& s) {
  // Muss zu DIGITS in firmware/tools/gen_fonts.py passen
  static const uint32_t allowed[] = {' ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', ',', ':', '-',
                                     '+', 0xB0, '%', '/', 0x2013};
  size_t i = 0;
  while (i < s.size()) {
    uint32_t cp = nextCodepoint(s, i);
    if (std::find(std::begin(allowed), std::end(allowed), cp) == std::end(allowed)) return false;
  }
  return true;
}

static uint32_t be32(const uint8_t* p) {
  return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16) | (uint32_t(p[2]) << 8) | p[3];
}
static uint32_t le32(const uint8_t* p) {
  return p[0] | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

const FontSet::Glyph* FontSet::Face::find(uint32_t code) const {
  auto it = std::lower_bound(glyphs.begin(), glyphs.end(), code,
                             [](const Glyph& g, uint32_t c) { return g.code < c; });
  return (it != glyphs.end() && it->code == code) ? &*it : nullptr;
}

bool FontSet::begin(const uint8_t* blob, size_t len) {
  faces_.clear();
  if (!blob || len < 8 || memcmp(blob, "S51F", 4) != 0) return false;
  uint16_t n = blob[6] | (blob[7] << 8);
  if (len < 8u + 12u * n) return false;
  for (uint16_t i = 0; i < n; i++) {
    const uint8_t* e = blob + 8 + 12 * i;
    uint32_t off = le32(e + 4), flen = le32(e + 8);
    if (off + flen > len || flen < 24) return false;
    const uint8_t* d = blob + off;
    Face f;
    f.family = e[0];
    f.subset = e[1];
    f.size = e[2] | (e[3] << 8);
    uint32_t count = be32(d);
    f.ascent = static_cast<int>(be32(d + 16));
    f.descent = static_cast<int>(be32(d + 20));
    if (24u + 28u * count > flen) return false;
    const uint8_t* bmp = d + 24 + 28 * count;
    for (uint32_t k = 0; k < count; k++) {
      const uint8_t* r = d + 24 + 28 * k;
      Glyph gl;
      gl.code = be32(r);
      gl.h = static_cast<uint16_t>(be32(r + 4));
      gl.w = static_cast<uint16_t>(be32(r + 8));
      int32_t fine = static_cast<int32_t>(be32(r + 24));
      gl.advance = fine ? fine / 64.0f : static_cast<float>(static_cast<int32_t>(be32(r + 12)));
      gl.dy = static_cast<int16_t>(be32(r + 16));
      gl.dx = static_cast<int16_t>(be32(r + 20));
      gl.bitmap = bmp;
      bmp += size_t(gl.w) * gl.h;
      if (bmp > d + flen) return false;
      f.glyphs.push_back(gl);
    }
    std::sort(f.glyphs.begin(), f.glyphs.end(), [](const Glyph& a, const Glyph& b) { return a.code < b.code; });
    faces_.push_back(std::move(f));
  }
  return !faces_.empty();
}

FontSet::Choice FontSet::pick(Font family, float sizePx, bool digitsOnly) const {
  // Bevorzugt: genau passend, sonst die kleinste größere Schrift (herunterrechnen),
  // sonst die größte vorhandene (hinaufrechnen).
  Choice c;
  const Face* larger = nullptr;
  const Face* largest = nullptr;
  for (const auto& f : faces_) {
    if (f.family != static_cast<uint8_t>(family) || (f.subset == 1 && !digitsOnly)) continue;
    if (f.size == sizePx) {
      c.face = &f;
      c.scale = 1.0f;
      return c;
    }
    if (f.size > sizePx && (!larger || f.size < larger->size)) larger = &f;
    if (!largest || f.size > largest->size) largest = &f;
  }
  c.face = larger ? larger : largest;
  if (c.face) c.scale = sizePx / c.face->size;
  return c;
}

float FontSet::textWidth(const Choice& c, const std::string& s) {
  if (!c.face) return 0;
  float w = 0;
  size_t i = 0;
  while (i < s.size()) {
    const Glyph* g = c.face->find(nextCodepoint(s, i));
    if (g) w += g->advance * c.scale;
  }
  return w;
}

static inline void blend(uint16_t& dst, uint16_t col, uint8_t a) {
  if (a == 0) return;
  if (a == 255) {
    dst = uint16_t((col >> 8) | (col << 8));
    return;
  }
  uint16_t q = uint16_t((dst >> 8) | (dst << 8));
  int r = ((col >> 11) & 31) * a + ((q >> 11) & 31) * (255 - a);
  int g = ((col >> 5) & 63) * a + ((q >> 5) & 63) * (255 - a);
  int b = (col & 31) * a + (q & 31) * (255 - a);
  uint16_t p = uint16_t(((r + 127) / 255) << 11 | ((g + 127) / 255) << 5 | ((b + 127) / 255));
  dst = uint16_t((p >> 8) | (p << 8));
}

static void drawGlyph(Canvas565& cv, const FontSet::Glyph& gl, float pen, float baseline, float s, uint16_t col) {
  if (gl.w == 0 || gl.h == 0) return;
  const float fx0 = pen + gl.dx * s, fy0 = baseline - gl.dy * s;
  int px0 = static_cast<int>(std::floor(fx0)), py0 = static_cast<int>(std::floor(fy0));
  int px1 = static_cast<int>(std::ceil(fx0 + gl.w * s)), py1 = static_cast<int>(std::ceil(fy0 + gl.h * s));
  px0 = std::max(px0, cv.clipX);
  py0 = std::max(py0, cv.clipY);
  px1 = std::min(px1, cv.clipX + cv.clipW);
  py1 = std::min(py1, cv.clipY + cv.clipH);
  if (px1 <= px0 || py1 <= py0) return;
  const uint8_t* src = gl.bitmap;
  const int W = gl.w, H = gl.h;
  auto at = [&](int x, int y) -> int { return (x < 0 || y < 0 || x >= W || y >= H) ? 0 : src[y * W + x]; };

  if (s == 1.0f && fx0 == std::floor(fx0) && fy0 == std::floor(fy0)) {
    // genau passende Größe: Deckung direkt übernehmen
    const int ox = static_cast<int>(fx0), oy = static_cast<int>(fy0);
    for (int py = py0; py < py1; py++) {
      uint16_t* row = cv.buf + size_t(py) * cv.width;
      for (int px = px0; px < px1; px++) blend(row[px], col, src[(py - oy) * W + (px - ox)]);
    }
    return;
  }
  if (s > 1.0f) {
    // vergrößern: bilinear
    const float inv = 1.0f / s;
    for (int py = py0; py < py1; py++) {
      uint16_t* row = cv.buf + size_t(py) * cv.width;
      float sy = (py + 0.5f - fy0) * inv - 0.5f;
      int y0 = static_cast<int>(std::floor(sy));
      float ty = sy - y0;
      for (int px = px0; px < px1; px++) {
        float sx = (px + 0.5f - fx0) * inv - 0.5f;
        int x0 = static_cast<int>(std::floor(sx));
        float tx = sx - x0;
        float a = (at(x0, y0) * (1 - tx) + at(x0 + 1, y0) * tx) * (1 - ty) +
                  (at(x0, y0 + 1) * (1 - tx) + at(x0 + 1, y0 + 1) * tx) * ty;
        blend(row[px], col, static_cast<uint8_t>(a + 0.5f));
      }
    }
    return;
  }
  // verkleinern (oder Teilpixel-Lage): Fläche des Zielpixels in der Quelle mitteln
  const float inv = 1.0f / s;
  for (int py = py0; py < py1; py++) {
    uint16_t* row = cv.buf + size_t(py) * cv.width;
    float v0 = (py - fy0) * inv, v1 = (py + 1 - fy0) * inv;
    int iy0 = static_cast<int>(std::floor(v0)), iy1 = static_cast<int>(std::ceil(v1));
    for (int px = px0; px < px1; px++) {
      float u0 = (px - fx0) * inv, u1 = (px + 1 - fx0) * inv;
      int ix0 = static_cast<int>(std::floor(u0)), ix1 = static_cast<int>(std::ceil(u1));
      float sum = 0;
      for (int iy = iy0; iy < iy1; iy++) {
        float wy = std::min<float>(iy + 1, v1) - std::max<float>(iy, v0);
        if (iy < 0 || iy >= H || wy <= 0) continue;
        const uint8_t* r = src + iy * W;
        for (int ix = ix0; ix < ix1; ix++) {
          if (ix < 0 || ix >= W) continue;
          float wx = std::min<float>(ix + 1, u1) - std::max<float>(ix, u0);
          if (wx > 0) sum += r[ix] * wx * wy;
        }
      }
      float a = sum / ((u1 - u0) * (v1 - v0));
      blend(row[px], col, static_cast<uint8_t>(std::min(255.0f, a + 0.5f)));
    }
  }
}

void FontSet::draw(Canvas565& cv, const Choice& c, const std::string& s, float x, float baseline, Color color) {
  if (!c.face || !cv.buf) return;
  const uint16_t col = color.to565();
  float pen = x;
  size_t i = 0;
  while (i < s.size()) {
    const Glyph* g = c.face->find(nextCodepoint(s, i));
    if (!g) continue;
    // Zeichen auf ganze Pixel setzen, damit sie scharf bleiben; die Summe bleibt genau
    drawGlyph(cv, *g, std::round(pen), baseline, c.scale, col);
    pen += g->advance * c.scale;
  }
}

}  // namespace s51
