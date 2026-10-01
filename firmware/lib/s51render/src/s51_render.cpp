#include "s51_render.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <utility>

#if defined(ESP_PLATFORM)
#include <esp_heap_caps.h>
static void* bigAlloc(size_t n) {
  void* p = heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return p ? p : malloc(n);
}
#else
static void* bigAlloc(size_t n) { return malloc(n); }
#endif

namespace s51 {

// ---------------------------------------------------------------------------
// Hilfen
// ---------------------------------------------------------------------------

static inline int rnd(float v) { return static_cast<int>(std::lround(v)); }
static inline uint16_t c565(Color c) { return c.to565(); }
static inline uint32_t c888(Color c) { return (uint32_t(c.r) << 16) | (uint32_t(c.g) << 8) | c.b; }

// Rechteck zwischen Gleitkomma-Kanten, wie Tk es rundet
static void fillRectF(LGFX_Sprite& g, float x0, float y0, float x1, float y1, uint16_t col) {
  int a = rnd(x0), b = rnd(y0), c = rnd(x1), d = rnd(y1);
  if (c > a && d > b) g.fillRect(a, b, c - a, d - b, col);
}

static void fillRoundRectF(LGFX_Sprite& g, float x0, float y0, float x1, float y1, float r, uint16_t col) {
  r = std::max(0.0f, std::min({r, (x1 - x0) / 2, (y1 - y0) / 2}));
  int a = rnd(x0), b = rnd(y0), c = rnd(x1), d = rnd(y1);
  if (c <= a || d <= b) return;
  if (r < 1) {
    g.fillRect(a, b, c - a, d - b, col);
  } else {
    g.fillSmoothRoundRect(a, b, c - a, d - b, rnd(r), col);
  }
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

Renderer::~Renderer() { clearImages(); }

void Renderer::clearImages() {
  for (auto& kv : images_) {
    free(kv.second.rgb);
    free(kv.second.alpha);
  }
  images_.clear();
}

void Renderer::setLayout(const LayoutData* layout) {
  clearImages();
  layout_ = layout;
}

void Renderer::drawScreen(LGFX_Sprite& g, const ScreenData& screen, const Values& v, uint32_t ms) {
  g.fillScreen(c565(screen.bg));
  for (const auto& w : screen.widgets) {
    if (!w.known || w.hidden) continue;
    drawWidget(g, w, v, ms);
  }
}

void Renderer::drawWidget(LGFX_Sprite& g, const WidgetData& w, const Values& v, uint32_t ms) {
  switch (w.type) {
    case WidgetType::Text:
      drawText(g, w, w.text, w.color, true);
      break;
    case WidgetType::Value: {
      Source s = w.source;
      bool has = s != Source::None && kindOf(s) == SourceKind::Number && v.hasNumber(s);
      drawText(g, w, displayText(w, v), thresholdColor(w, has, has ? v.get(s) : 0, w.color), false);
      break;
    }
    case WidgetType::Bar:
      drawBar(g, w, v);
      break;
    case WidgetType::Gauge:
      drawGauge(g, w, v);
      break;
    case WidgetType::Indicator:
      drawIcon(g, w, indicatorOn(w, v, ms) ? w.onColor : w.offColor);
      break;
    case WidgetType::Rect:
      drawRect(g, w);
      break;
    case WidgetType::Image:
      drawImage(g, w);
      break;
  }
}

// -- Text --------------------------------------------------------------------

Canvas565 Renderer::canvas(LGFX_Sprite& g) {
  Canvas565 cv;
  cv.buf = g.getColorDepth() == 16 ? static_cast<uint16_t*>(g.getBuffer()) : nullptr;
  cv.width = g.width();
  cv.height = g.height();
  cv.clipAll();
  return cv;
}

void Renderer::drawText(LGFX_Sprite& g, const WidgetData& w, const std::string& text, Color color, bool wrap) {
  drawTextBox(g, text, w.x, w.y, w.w, w.h, w.font, w.size, color, w.align, wrap, true);
}

void Renderer::drawLabel(LGFX_Sprite& g, const std::string& text, int x, int y, int w, int h, Font font, int size,
                         Color color, Align align) {
  drawTextBox(g, text, x, y, w, h, font, size, color, align, true, false);
}

void Renderer::drawTextBox(LGFX_Sprite& g, const std::string& text, float x, float y, float w, float h, Font font,
                           float size, Color color, Align align, bool wrap, bool clipToBox) {
  if (text.empty() || size < 1) return;
  FontSet::Choice ch = fonts_.pick(font, size, isDigitText(text));
  if (!ch.face) return;
  Canvas565 cv = canvas(g);
  if (clipToBox) cv.clip(rnd(x), rnd(y), rnd(w), rnd(h));

  // Zeilen bilden: Zeilenumbrüche im Text, bei wrap zusätzlich an Leerzeichen
  std::vector<std::string> lines;
  size_t start = 0;
  while (true) {
    size_t nl = text.find('\n', start);
    std::string para = text.substr(start, nl == std::string::npos ? std::string::npos : nl - start);
    if (!wrap) {
      lines.push_back(para);
    } else {
      std::string line;
      size_t i = 0;
      while (true) {
        size_t sp = para.find(' ', i);
        std::string word = para.substr(i, sp == std::string::npos ? std::string::npos : sp - i);
        std::string trial = line.empty() ? word : line + " " + word;
        if (!line.empty() && FontSet::textWidth(ch, trial) > w) {
          lines.push_back(line);
          line = word;
        } else {
          line = trial;
        }
        if (sp == std::string::npos) break;
        i = sp + 1;
      }
      lines.push_back(line);
    }
    if (nl == std::string::npos) break;
    start = nl + 1;
  }

  // Einzeilig: mittig nach Zeilenhöhe (Ascent + Descent der Schrift).
  // Mehrzeilig: Zeilenabstand 1,2 × Größe, alle Zeilen zusammen mittig.
  float lineH = lines.size() > 1 ? 1.2f * size : ch.ascent() + ch.descent();
  float total = lineH * (lines.size() - 1) + ch.ascent() + ch.descent();
  float top = y + h / 2 - total / 2;
  for (size_t k = 0; k < lines.size(); k++) {
    float tw = FontSet::textWidth(ch, lines[k]);
    float tx = align == Align::Left ? x : (align == Align::Right ? x + w - tw : x + w / 2 - tw / 2);
    float base = top + k * lineH + ch.ascent();
    FontSet::draw(cv, ch, lines[k], std::round(tx), std::round(base), color);
  }
}

// -- Balken -----------------------------------------------------------------

void Renderer::drawBar(LGFX_Sprite& g, const WidgetData& w, const Values& v) {
  Source s = w.source;
  bool has = s != Source::None && v.hasNumber(s);
  float value = has ? v.get(s) : 0;
  float f = fraction(w, has, value);
  bool vertical = w.orientation == Orientation::Vertical;
  int n = w.segments;
  float x0 = w.x, y0 = w.y, x1 = w.x + w.w, y1 = w.y + w.h;
  if (n <= 0) {
    fillRoundRectF(g, x0, y0, x1, y1, w.radius, c565(w.bgColor));
    uint16_t col = c565(thresholdColor(w, has, value, w.color));
    if (f > 0) {
      if (vertical) {
        fillRoundRectF(g, x0, y0 + w.h * (1 - f), x1, y1, w.radius, col);
      } else {
        fillRoundRectF(g, x0, y0, x0 + w.w * f, y1, w.radius, col);
      }
    }
    return;
  }
  const float gap = 2;
  float length = vertical ? w.h : w.w;
  float seg = (length - gap * (n - 1)) / n;
  int lit = rnd(f * n);
  for (int i = 0; i < n; i++) {
    float segValue = w.min + (w.max - w.min) * (i + 1) / n;
    Color col = i < lit ? thresholdColor(w, true, segValue, w.color) : w.bgColor;
    float a = i * (seg + gap);
    if (vertical) {
      fillRectF(g, x0, y1 - a - seg, x1, y1 - a, c565(col));
    } else {
      fillRectF(g, x0 + a, y0, x0 + a + seg, y1, c565(col));
    }
  }
}

// -- Rundinstrument ----------------------------------------------------------

static void fillArcBand(LGFX_Sprite& g, float cx, float cy, float r0, float r1, float a0, float a1, uint16_t col) {
  if (a1 - a0 <= 0.01f) return;
  // Winkel auf 0..360 bringen, Bögen über 360° in zwei Teile zerlegen
  while (a0 >= 360) { a0 -= 360; a1 -= 360; }
  while (a0 < 0) { a0 += 360; a1 += 360; }
  if (a1 > 360) {
    g.fillArc(rnd(cx), rnd(cy), rnd(r0), rnd(r1), a0, 360, col);
    g.fillArc(rnd(cx), rnd(cy), rnd(r0), rnd(r1), 0, a1 - 360, col);
  } else {
    g.fillArc(rnd(cx), rnd(cy), rnd(r0), rnd(r1), a0, a1, col);
  }
}

void Renderer::drawGauge(LGFX_Sprite& g, const WidgetData& w, const Values& v) {
  float th = w.thickness;
  float size = std::min<float>(w.w, w.h);
  float cx = w.x + w.w / 2.0f, cy = w.y + w.h / 2.0f;
  float r = size / 2 - th / 2;
  float a0 = w.startAngle, a1 = w.endAngle;
  if (a1 < a0) std::swap(a0, a1);
  float r0 = std::max(0.0f, r - th / 2), r1 = r + th / 2 - 1;
  fillArcBand(g, cx, cy, r0, r1, a0, a1, c565(w.bgColor));
  Source s = w.source;
  bool has = s != Source::None && v.hasNumber(s);
  float value = has ? v.get(s) : 0;
  float f = fraction(w, has, value);
  if (f > 0) {
    fillArcBand(g, cx, cy, r0, r1, a0, a0 + (a1 - a0) * f, c565(thresholdColor(w, has, value, w.color)));
  }
}

// -- Kontrollleuchten --------------------------------------------------------

void Renderer::drawIcon(LGFX_Sprite& g, const WidgetData& w, Color color) {
  const uint16_t col = c565(color);
  const float x0 = w.x, y0 = w.y, x1 = w.x + w.w, y1 = w.y + w.h;
  const float cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const float s = std::min<float>(w.w, w.h);
  auto tri = [&](float ax, float ay, float bx, float by, float qx, float qy) {
    g.fillTriangle(rnd(ax), rnd(ay), rnd(bx), rnd(by), rnd(qx), rnd(qy), col);
  };
  auto thickLine = [&](float ax, float ay, float bx, float by, float width) {
    g.drawWideLine(rnd(ax), rnd(ay), rnd(bx), rnd(by), std::max(0.5f, width / 2), c888(color));
  };
  switch (w.icon) {
    case Icon::ArrowLeft:
      tri(x0, cy, cx, y0 + s * 0.1f, cx, y1 - s * 0.1f);
      fillRectF(g, cx - 1, cy - s * 0.18f, x1, cy + s * 0.18f, col);
      break;
    case Icon::ArrowRight:
      tri(x1, cy, cx, y0 + s * 0.1f, cx, y1 - s * 0.1f);
      fillRectF(g, x0, cy - s * 0.18f, cx + 1, cy + s * 0.18f, col);
      break;
    case Icon::HighBeam: {
      float ex = cx + s * 0.2f, rx = s * 0.3f, ry = (y1 - y0 - s * 0.3f) / 2;
      g.fillEllipseArc(rnd(ex), rnd(cy), 0, rnd(rx), 0, rnd(ry), 90, 270, col);
      for (int k = 0; k < 4; k++) {
        float yy = y0 + s * (0.25f + 0.17f * k);
        fillRectF(g, x0 + s * 0.05f, yy - 1, cx - s * 0.15f, yy + 1, col);
      }
      break;
    }
    case Icon::Neutral:
      fillRoundRectF(g, x0 + 1, y0 + 1, x1 - 1, y1 - 1, s * 0.2f, col);
      drawTextBox(g, "N", x0, y0, w.w, w.h, Font::SansBold, s * 0.7f, Color{0, 0, 0}, Align::Center, false, false);
      break;
    case Icon::Light:
      g.fillSmoothCircle(rnd(cx), rnd(cy), rnd(s * 0.22f), col);
      for (int k = 0; k < 8; k++) {
        float a = k * 3.14159265f / 4;
        thickLine(cx + std::cos(a) * s * 0.3f, cy + std::sin(a) * s * 0.3f, cx + std::cos(a) * s * 0.45f,
                  cy + std::sin(a) * s * 0.45f, 2);
      }
      break;
    case Icon::Battery: {
      int a = rnd(x0 + s * 0.1f), b = rnd(cy - s * 0.25f), c = rnd(x1 - s * 0.1f), d = rnd(cy + s * 0.3f);
      g.drawRect(a, b, c - a, d - b, col);
      g.drawRect(a + 1, b + 1, c - a - 2, d - b - 2, col);
      fillRectF(g, x0 + s * 0.25f, cy - s * 0.35f, x0 + s * 0.35f, cy - s * 0.25f, col);
      fillRectF(g, x1 - s * 0.35f, cy - s * 0.35f, x1 - s * 0.25f, cy - s * 0.25f, col);
      break;
    }
    case Icon::Temp:
      thickLine(cx, y0 + s * 0.1f, cx, y1 - s * 0.35f, s * 0.15f);
      g.fillSmoothCircle(rnd(cx), rnd(y1 - s * 0.23f), rnd(s * 0.17f), col);
      break;
    case Icon::Lock: {
      fillRectF(g, x0 + s * 0.2f, cy - s * 0.05f, x1 - s * 0.2f, y1 - s * 0.1f, col);
      float ecy = ((y0 + s * 0.1f) + (cy + s * 0.15f)) / 2, er = s * 0.2f, ery = ((cy + s * 0.15f) - (y0 + s * 0.1f)) / 2;
      g.fillEllipseArc(rnd(cx), rnd(ecy), rnd(er - 2), rnd(er), rnd(ery - 2), rnd(ery), 180, 360, col);
      break;
    }
    case Icon::Warning:
      tri(cx, y0 + s * 0.08f, x1 - s * 0.05f, y1 - s * 0.1f, x0 + s * 0.05f, y1 - s * 0.1f);
      drawTextBox(g, "!", cx - s / 2, cy + s * 0.12f - s / 2, s, s, Font::SansBold, s * 0.5f, Color{0, 0, 0},
                  Align::Center, false, false);
      break;
    case Icon::Gps:
      drawTextBox(g, "GPS", x0, y0, w.w, w.h, Font::SansBold, s * 0.4f, color, Align::Center, false, false);
      break;
    case Icon::Bluetooth:
      drawTextBox(g, "BT", x0, y0, w.w, w.h, Font::SansBold, s * 0.4f, color, Align::Center, false, false);
      break;
    case Icon::Music:
      drawTextBox(g, "\xE2\x99\xAA", x0, y0, w.w, w.h, Font::SansBold, s * 0.7f, color, Align::Center, false, false);
      break;
    default:
      g.fillSmoothCircle(rnd(cx), rnd(cy), rnd(s * 0.2f), col);
      break;
  }
}

// -- Fläche ------------------------------------------------------------------

void Renderer::drawRect(LGFX_Sprite& g, const WidgetData& w) {
  float x0 = w.x, y0 = w.y, x1 = w.x + w.w, y1 = w.y + w.h;
  int bw = w.borderWidth;
  if (bw > 0) {
    // Rahmen liegt innerhalb der Fläche
    fillRoundRectF(g, x0, y0, x1, y1, w.radius, c565(w.borderColor));
    if (w.w > 2 * bw && w.h > 2 * bw) {
      fillRoundRectF(g, x0 + bw, y0 + bw, x1 - bw, y1 - bw, std::max(0, int(w.radius) - bw), c565(w.color));
    }
  } else {
    fillRoundRectF(g, x0, y0, x1, y1, w.radius, c565(w.color));
  }
}

// -- Bild --------------------------------------------------------------------

const Renderer::Decoded* Renderer::decoded(uint8_t imageId) {
  auto it = images_.find(imageId);
  if (it != images_.end()) return &it->second;
  Decoded d;
  const ImageData* img = layout_ ? layout_->findImage(imageId) : nullptr;
  if (!img) {
    d.failed = true;
  } else {
    size_t n = size_t(img->width) * img->height;
    d.rgb = static_cast<uint16_t*>(bigAlloc(n * 2));
    if (img->hasAlpha) d.alpha = static_cast<uint8_t*>(bigAlloc(n));
    if (!d.rgb || (img->hasAlpha && !d.alpha) || !img->decodePixels(d.rgb, d.alpha)) {
      free(d.rgb);
      free(d.alpha);
      d.rgb = nullptr;
      d.alpha = nullptr;
      d.failed = true;
    }
  }
  return &(images_[imageId] = d);
}

void Renderer::drawImage(LGFX_Sprite& g, const WidgetData& w) {
  const ImageData* img = layout_ ? layout_->findImage(w.image) : nullptr;
  if (!img) return;
  const Decoded* d = decoded(w.image);
  if (d->failed) return;
  // Sichtbarer Bereich: Bild ∩ Rahmen ∩ Sprite
  Canvas565 cv = canvas(g);
  if (!cv.buf) return;
  cv.clip(w.x, w.y, std::min<int>(w.w, img->width), std::min<int>(w.h, img->height));
  const int sx0 = cv.clipX, sy0 = cv.clipY, sx1 = cv.clipX + cv.clipW, sy1 = cv.clipY + cv.clipH;
  if (sx1 <= sx0 || sy1 <= sy0) return;
  uint16_t* buf = cv.buf;
  const int stride = cv.width;
  for (int y = sy0; y < sy1; y++) {
    const int iy = y - w.y;
    const uint16_t* src = d->rgb + size_t(iy) * img->width;
    const uint8_t* al = d->alpha ? d->alpha + size_t(iy) * img->width : nullptr;
    uint16_t* dst = buf + size_t(y) * stride;
    for (int x = sx0; x < sx1; x++) {
      const int ix = x - w.x;
      uint16_t p = src[ix];
      uint8_t a = al ? al[ix] : 255;
      if (a == 0) continue;
      if (a < 255) {
        uint16_t q = dst[x];
        q = uint16_t((q >> 8) | (q << 8));
        int r = ((p >> 11) & 31) * a + ((q >> 11) & 31) * (255 - a);
        int gg = ((p >> 5) & 63) * a + ((q >> 5) & 63) * (255 - a);
        int b = (p & 31) * a + (q & 31) * (255 - a);
        p = uint16_t(((r / 255) << 11) | ((gg / 255) << 5) | (b / 255));
      }
      dst[x] = uint16_t((p >> 8) | (p << 8));
    }
  }
}

}  // namespace s51
