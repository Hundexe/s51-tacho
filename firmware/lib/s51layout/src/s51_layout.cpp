#include "s51_layout.h"

#include <cstring>

namespace s51 {

namespace {

uint16_t readU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
int16_t readI16(const uint8_t* p) { return static_cast<int16_t>(readU16(p)); }
uint32_t readU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
float readF32(const uint8_t* p) {
  uint32_t u = readU32(p);
  float f;
  std::memcpy(&f, &u, sizeof f);
  return f;
}

}  // namespace

}  // namespace s51

#include "s51_props.inc"

namespace s51 {

namespace {

constexpr size_t kWidgetHead = 12;
constexpr size_t kChunkHead = 8;

DecodeError decodeWidget(const uint8_t* d, size_t end, size_t& pos, WidgetData& w) {
  if (pos + kWidgetHead > end) return DecodeError::Truncated;
  w = WidgetData();
  w.typeCode = d[pos];
  w.type = static_cast<WidgetType>(d[pos]);
  w.known = isKnownWidgetType(w.typeCode);
  uint8_t flags = d[pos + 1];
  w.hidden = (flags & kFlagHidden) != 0;
  w.x = readI16(d + pos + 2);
  w.y = readI16(d + pos + 4);
  w.w = readU16(d + pos + 6);
  w.h = readU16(d + pos + 8);
  uint16_t plen = readU16(d + pos + 10);
  pos += kWidgetHead;
  if (pos + plen > end) return DecodeError::Truncated;
  w.propsSet[0] = w.propsSet[1] = 0;
  applyDefaults(w);
  size_t p = pos, pend = pos + plen;
  while (p < pend) {
    if (p + 2 > pend) return DecodeError::Truncated;
    uint8_t code = d[p], len = d[p + 1];
    p += 2;
    if (p + len > pend) return DecodeError::Truncated;
    if (!decodeProp(code, d + p, len, w)) return DecodeError::BadProperty;
    p += len;
  }
  pos = pend;
  return DecodeError::None;
}

// Läuft einmal über die Pixeldaten. Mit Zielpuffern werden sie dabei entpackt,
// ohne Puffer werden sie nur geprüft.
bool walkPixels(const ImageData& img, uint16_t* rgb, uint8_t* alpha) {
  const size_t n = static_cast<size_t>(img.width) * img.height;
  const size_t step = img.hasAlpha ? 3 : 2;
  const uint8_t* d = img.data.data();
  const size_t len = img.data.size();
  auto put = [&](size_t idx, size_t pos) {
    if (rgb) rgb[idx] = static_cast<uint16_t>(d[pos] | (d[pos + 1] << 8));
    if (alpha) alpha[idx] = img.hasAlpha ? d[pos + 2] : 255;
  };
  if (img.format == kImageFormatRaw) {
    if (len != n * step) return false;
    if (rgb || alpha)
      for (size_t i = 0; i < n; ++i) put(i, i * step);
    return true;
  }
  if (img.format != kImageFormatRle) return false;
  size_t pos = 0, idx = 0;
  while (idx < n) {
    if (pos >= len) return false;
    uint8_t b = d[pos++];
    size_t count = static_cast<size_t>(b & 0x7F) + 1;
    if (idx + count > n) return false;
    if (b & 0x80) {
      if (pos + step > len) return false;
      for (size_t k = 0; k < count; ++k) put(idx++, pos);
      pos += step;
    } else {
      if (pos + count * step > len) return false;
      for (size_t k = 0; k < count; ++k) {
        put(idx++, pos);
        pos += step;
      }
    }
  }
  return pos == len;
}

DecodeError decodeImage(const uint8_t* d, size_t len, ImageData& img) {
  if (len < 9) return DecodeError::Truncated;
  img.id = d[0];
  img.format = d[1];
  img.hasAlpha = (d[2] & kImageFlagAlpha) != 0;
  img.width = readU16(d + 4);
  img.height = readU16(d + 6);
  uint8_t nlen = d[8];
  size_t pos = 9;
  if (pos + nlen + 4 > len) return DecodeError::Truncated;
  img.name.assign(reinterpret_cast<const char*>(d + pos), nlen);
  pos += nlen;
  uint32_t dlen = readU32(d + pos);
  pos += 4;
  if (pos + dlen != len) return DecodeError::BadImage;
  if (img.id == kNoImage || img.width < 1 || img.width > kMaxImageSide || img.height < 1 ||
      img.height > kMaxImageSide)
    return DecodeError::BadImage;
  img.data.assign(d + pos, d + pos + dlen);
  if (!walkPixels(img, nullptr, nullptr)) return DecodeError::BadImage;
  return DecodeError::None;
}

DecodeError decodeScreen(const uint8_t* d, size_t len, ScreenData& s) {
  if (len < 10) return DecodeError::Truncated;
  s.id = d[0];
  s.role = (d[1] == kRoleNight || d[1] == kRoleStartup) ? d[1] : kRolePage;
  s.night = s.role == kRoleNight;
  s.nightOf = s.night ? d[2] : kNoPage;
  s.bg = Color{d[4], d[5], d[6]};
  uint8_t nlen = d[7];
  size_t pos = 8;
  if (pos + nlen + 2 > len) return DecodeError::Truncated;
  s.name.assign(reinterpret_cast<const char*>(d + pos), nlen);
  pos += nlen;
  uint16_t count = readU16(d + pos);
  pos += 2;
  if (count > kMaxWidgetsPerScreen) return DecodeError::TooManyWidgets;
  s.widgets.resize(count);
  for (uint16_t i = 0; i < count; ++i) {
    DecodeError e = decodeWidget(d, len, pos, s.widgets[i]);
    if (e != DecodeError::None) return e;
  }
  return DecodeError::None;
}

}  // namespace

uint32_t crc32(const uint8_t* data, size_t len) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
  }
  return ~crc;
}

const char* errorText(DecodeError e) {
  switch (e) {
    case DecodeError::None: return "OK";
    case DecodeError::TooSmall: return "Datei zu kurz";
    case DecodeError::TooLarge: return "Datei zu gross";
    case DecodeError::BadMagic: return "Keine S51-Layout-Datei";
    case DecodeError::BadVersion: return "Formatversion nicht unterstuetzt";
    case DecodeError::BadCrc: return "Pruefsumme falsch, Datei beschaedigt";
    case DecodeError::BadHeader: return "Ungueltiger Dateikopf";
    case DecodeError::Truncated: return "Datei abgeschnitten";
    case DecodeError::TooManyScreens: return "Zu viele Seiten";
    case DecodeError::TooManyWidgets: return "Zu viele Elemente auf einer Seite";
    case DecodeError::NoScreens: return "Keine Seite in der Datei";
    case DecodeError::BadProperty: return "Ungueltige Eigenschaft";
    case DecodeError::BadImage: return "Bilddaten fehlerhaft";
    case DecodeError::TooManyImages: return "Zu viele Bilder";
  }
  return "Unbekannter Fehler";
}

DecodeError decodeLayout(const uint8_t* d, size_t len, LayoutData& out) {
  out = LayoutData();
  if (len > kMaxFileSize) return DecodeError::TooLarge;
  if (len < kHeaderSize + 4) return DecodeError::TooSmall;
  if (std::memcmp(d, kMagic, 4) != 0) return DecodeError::BadMagic;
  uint32_t stored = readU32(d + len - 4);
  uint32_t crc = crc32(d, len - 4);
  if (stored != crc) return DecodeError::BadCrc;
  if (d[4] != kVersionMajor) return DecodeError::BadVersion;
  uint16_t hsize = readU16(d + 6);
  if (hsize < kHeaderSize || hsize > len - 4) return DecodeError::BadHeader;

  LayoutData L;
  L.width = readU16(d + 8);
  L.height = readU16(d + 10);
  L.crc = crc;
  size_t pos = hsize, end = len - 4;
  while (pos < end) {
    if (pos + kChunkHead > end) return DecodeError::Truncated;
    const uint8_t* fourcc = d + pos;
    uint32_t clen = readU32(d + pos + 4);
    pos += kChunkHead;
    if (clen > end - pos) return DecodeError::Truncated;
    const uint8_t* payload = d + pos;
    if (std::memcmp(fourcc, "META", 4) == 0) {
      size_t p = 0;
      while (p < clen) {
        if (p + 2 > clen) return DecodeError::Truncated;
        uint8_t code = payload[p], l = payload[p + 1];
        p += 2;
        if (p + l > clen) return DecodeError::Truncated;
        const char* s = reinterpret_cast<const char*>(payload + p);
        if (code == kMetaName) L.name.assign(s, l);
        else if (code == kMetaAuthor) L.author.assign(s, l);
        else if (code == kMetaTool) L.tool.assign(s, l);
        else if (code == kMetaCreated && l == 4) L.created = readU32(payload + p);
        p += l;
      }
    } else if (std::memcmp(fourcc, "IMAG", 4) == 0) {
      if (L.images.size() >= kMaxImages) return DecodeError::TooManyImages;
      L.images.emplace_back();
      DecodeError e = decodeImage(payload, clen, L.images.back());
      if (e != DecodeError::None) return e;
    } else if (std::memcmp(fourcc, "SCRN", 4) == 0) {
      if (L.screens.size() >= kMaxScreens) return DecodeError::TooManyScreens;
      L.screens.emplace_back();
      DecodeError e = decodeScreen(payload, clen, L.screens.back());
      if (e != DecodeError::None) return e;
    }
    // unbekannte Abschnitte werden übersprungen
    pos += clen;
  }
  if (L.screens.empty()) return DecodeError::NoScreens;
  out = std::move(L);
  return DecodeError::None;
}

const ScreenData* LayoutData::findScreen(uint8_t id) const {
  for (const auto& s : screens)
    if (s.role == kRolePage && s.id == id) return &s;
  return nullptr;
}

const ScreenData* LayoutData::startupScreen() const {
  for (const auto& s : screens)
    if (s.role == kRoleStartup) return &s;
  return nullptr;
}

const ImageData* LayoutData::findImage(uint8_t id) const {
  for (const auto& i : images)
    if (i.id == id) return &i;
  return nullptr;
}

bool ImageData::decodePixels(uint16_t* rgb565, uint8_t* alpha) const {
  return walkPixels(*this, rgb565, alpha);
}

const ScreenData* LayoutData::screenFor(uint8_t id, bool nightMode) const {
  if (nightMode) {
    for (const auto& s : screens)
      if (s.night && s.nightOf == id) return &s;
  }
  return findScreen(id);
}

}  // namespace s51
