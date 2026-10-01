#include "s51_picker.h"

#include <algorithm>

namespace s51 {

namespace {
const Color kBg{14, 17, 16};
const Color kPanel{23, 28, 25};
const Color kHi{31, 58, 49};
const Color kAccent{29, 158, 117};
const Color kText{241, 239, 232};
const Color kDim{136, 135, 128};
const Color kBorder{44, 48, 45};
const Color kInk{13, 36, 30};
const Color kRed{226, 75, 74};

constexpr int kW = 480;
constexpr int kRight = 248;            // linke Kante der rechten Spalte
constexpr int kButtonY = 266, kButtonH = 44;
constexpr int kCloseX = 432, kCloseW = 48, kHeaderH = 48;
}  // namespace

void downscaleInto(LGFX_Sprite& src, LGFX_Sprite& dst, int dx, int dy, int dw, int dh) {
  const uint16_t* s = static_cast<const uint16_t*>(src.getBuffer());
  uint16_t* d = static_cast<uint16_t*>(dst.getBuffer());
  if (!s || !d || dw <= 0 || dh <= 0) return;
  const int sw = src.width(), sh = src.height(), dwid = dst.width();
  for (int y = 0; y < dh; y++) {
    const int ty = dy + y;
    if (ty < 0 || ty >= dst.height()) continue;
    const int y0 = y * sh / dh, y1 = std::max(y0 + 1, (y + 1) * sh / dh);
    for (int x = 0; x < dw; x++) {
      const int tx = dx + x;
      if (tx < 0 || tx >= dwid) continue;
      const int x0 = x * sw / dw, x1 = std::max(x0 + 1, (x + 1) * sw / dw);
      int r = 0, g = 0, b = 0, n = 0;
      for (int yy = y0; yy < y1; yy++) {
        for (int xx = x0; xx < x1; xx++) {
          uint16_t p = s[yy * sw + xx];
          p = uint16_t((p >> 8) | (p << 8));
          r += (p >> 11) & 31;
          g += (p >> 5) & 63;
          b += p & 31;
          n++;
        }
      }
      uint16_t p = uint16_t(((r / n) << 11) | ((g / n) << 5) | (b / n));
      d[ty * dwid + tx] = uint16_t((p >> 8) | (p << 8));
    }
  }
}

void Picker::open(std::vector<DesignEntry> list, int active) {
  list_ = std::move(list);
  active_ = std::max(0, std::min<int>(active, int(list_.size()) - 1));
  highlight_ = active_;
  scroll_ = 0;
  open_ = true;
  // markierten Eintrag sichtbar machen
  int rows = visibleRows(screenH_);
  if (highlight_ >= rows) scroll_ = highlight_ - rows + 1;
  clampScroll();
}

void Picker::clampScroll() {
  int maxScroll = std::max(0, int(list_.size()) - visibleRows(screenH_));
  scroll_ = std::max(0, std::min(scroll_, maxScroll));
}

void Picker::scroll(int dy) {
  scroll_ -= dy / kRowH == 0 ? (dy > 0 ? 1 : -1) : dy / kRowH;
  clampScroll();
}

Picker::Action Picker::tap(int x, int y) {
  if (!open_) return Action::None;
  if (y < kHeaderH && x >= kCloseX) {
    open_ = false;
    return Action::Close;
  }
  if (x < kListW && y >= kListTop) {
    int i = scroll_ + (y - kListTop) / kRowH;
    if (i >= 0 && i < int(list_.size()) && i != highlight_) {
      highlight_ = i;
      return Action::Highlight;
    }
    return Action::None;
  }
  if (x >= kRight && y >= kButtonY && y < kButtonY + kButtonH && highlight_ != active_ &&
      list_[highlight_].ok) {
    active_ = highlight_;
    open_ = false;
    return Action::Apply;
  }
  return Action::None;
}

void Picker::draw(LGFX_Sprite& g, Renderer& r, LGFX_Sprite* preview) {
  screenH_ = g.height();
  clampScroll();
  g.fillScreen(kBg.to565());

  // Kopfzeile
  r.drawLabel(g, "Design wählen", 16, 0, 300, kHeaderH, Font::SansBold, 20, kText, Align::Left);
  g.fillSmoothCircle(kCloseX + kCloseW / 2, kHeaderH / 2, 16, kPanel.to565());
  r.drawLabel(g, "\xC3\x97", kCloseX, 0, kCloseW, kHeaderH, Font::Sans, 26, kText);   // ×
  g.drawFastHLine(0, kHeaderH, kW, kBorder.to565());

  // Liste
  int rows = visibleRows(g.height());
  for (int k = 0; k < rows; k++) {
    int i = scroll_ + k;
    if (i >= int(list_.size())) break;
    const DesignEntry& e = list_[i];
    int y = kListTop + k * kRowH;
    if (i == highlight_) {
      g.fillSmoothRoundRect(8, y, kListW - 8, kRowH - 6, 8, kHi.to565());
      g.fillRect(8, y + 10, 4, kRowH - 26, kAccent.to565());
    }
    std::string name = e.name.empty() ? e.file : e.name;
    r.drawLabel(g, name, 22, y + 4, kListW - 60, 24, Font::SansBold, 16, e.ok ? kText : kRed, Align::Left);
    std::string sub = e.file.empty() ? "eingebaut" : e.file;
    if (!e.ok) sub += " \xC2\xB7 beschädigt";
    r.drawLabel(g, sub, 22, y + 26, kListW - 30, 18, Font::Sans, 12, kDim, Align::Left);
    if (i == active_) {
      g.fillSmoothRoundRect(kListW - 50, y + 8, 40, 18, 9, kAccent.to565());
      r.drawLabel(g, "aktiv", kListW - 50, y + 8, 40, 18, Font::SansBold, 11, kInk);
    }
  }
  // Bildlaufanzeige
  if (int(list_.size()) > rows) {
    int trackH = g.height() - kListTop - 8;
    int barH = std::max(20, trackH * rows / int(list_.size()));
    int barY = kListTop + (trackH - barH) * scroll_ / std::max(1, int(list_.size()) - rows);
    g.fillSmoothRoundRect(kListW + 2, barY, 4, barH, 2, kBorder.to565());
  }

  // Rechte Spalte: Vorschau und Angaben
  if (list_.empty()) return;
  const DesignEntry& e = list_[highlight_];
  g.fillRect(kRight - 2, kListTop - 2, kPreviewW + 4, kPreviewH + 4, kBorder.to565());
  if (preview && e.ok) {
    downscaleInto(*preview, g, kRight, kListTop, kPreviewW, kPreviewH);
  } else {
    g.fillRect(kRight, kListTop, kPreviewW, kPreviewH, kPanel.to565());
    r.drawLabel(g, e.ok ? "keine Vorschau" : e.error, kRight + 8, kListTop, kPreviewW - 16, kPreviewH, Font::Sans, 13,
                e.ok ? kDim : kRed);
  }
  if (!e.ok) {
    g.fillSmoothRoundRect(kRight, kButtonY, kPreviewW, kButtonH, 10, kPanel.to565());
    r.drawLabel(g, "Nicht lesbar", kRight, kButtonY, kPreviewW, kButtonH, Font::SansBold, 17, kDim);
    return;
  }
  std::string info = std::to_string(e.pages) + (e.pages == 1 ? " Seite" : " Seiten");
  if (e.hasNight) info += " \xC2\xB7 Nacht";
  if (e.hasStartup) info += " \xC2\xB7 Startbild";
  r.drawLabel(g, info, kRight, kListTop + kPreviewH + 6, kPreviewW, 20, Font::Sans, 13, kDim, Align::Left);
  if (!e.author.empty()) {
    r.drawLabel(g, "von " + e.author, kRight, kListTop + kPreviewH + 28, kPreviewW, 20, Font::Sans, 13, kDim,
                Align::Left);
  }

  // Knopf
  bool canApply = highlight_ != active_ && e.ok;
  g.fillSmoothRoundRect(kRight, kButtonY, kPreviewW, kButtonH, 10, (canApply ? kAccent : kPanel).to565());
  r.drawLabel(g, canApply ? "Übernehmen" : (highlight_ == active_ ? "Ist aktiv" : "Nicht lesbar"), kRight, kButtonY,
              kPreviewW, kButtonH, Font::SansBold, 17, canApply ? kInk : kDim);
}

}  // namespace s51
