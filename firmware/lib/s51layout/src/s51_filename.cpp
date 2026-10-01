#include "s51_filename.h"

#include <cstdint>

namespace s51 {

namespace {
// Grundbuchstaben für U+00C0 … U+00FF nach Unicode-Zerlegung (NFKD), 0: entfällt.
// Ä, Ö, Ü, ß werden vorher ausgeschrieben.
const char kLatin1[64] = {
    'a', 'a', 'a', 'a', 0,   'a', 0,   'c', 'e', 'e', 'e', 'e', 'i', 'i', 'i', 'i',   // À … Ï
    0,   'n', 'o', 'o', 'o', 'o', 0,   0,   0,   'u', 'u', 'u', 0,   'y', 0,   0,     // Ð … ß
    'a', 'a', 'a', 'a', 0,   'a', 0,   'c', 'e', 'e', 'e', 'e', 'i', 'i', 'i', 'i',   // à … ï
    0,   'n', 'o', 'o', 'o', 'o', 0,   0,   0,   'u', 'u', 'u', 0,   'y', 0,   'y',   // ð … ÿ
};

// Nächstes Zeichen aus UTF-8, bei ungültigen Folgen das einzelne Byte
uint32_t next(const std::string& s, size_t& i, size_t end) {
  unsigned char c = s[i];
  int len = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 1;
  if (i + len > end) len = 1;
  uint32_t cp = len == 1 ? c : len == 2 ? (c & 0x1F) : len == 3 ? (c & 0x0F) : (c & 0x07);
  for (int k = 1; k < len; k++) cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
  i += len;
  return cp;
}
}  // namespace

std::string designFileName(const std::string& layoutName) {
  size_t a = 0, b = layoutName.size();
  auto space = [](unsigned char c) { return c == ' ' || (c >= 9 && c <= 13); };
  while (a < b && space(layoutName[a])) a++;
  while (b > a && space(layoutName[b - 1])) b--;

  // Buchstaben und Ziffern bleiben, jede Folge anderer Zeichen wird ein „-“
  std::string s;
  bool gap = false;
  auto put = [&](const char* t) {
    if (gap && !s.empty()) s += '-';
    gap = false;
    s += t;
  };
  for (size_t i = a; i < b;) {
    uint32_t cp = next(layoutName, i, b);
    if (cp >= 'A' && cp <= 'Z') cp += 32;
    if ((cp >= 'a' && cp <= 'z') || (cp >= '0' && cp <= '9')) {
      char t[2] = {char(cp), 0};
      put(t);
    } else if (cp < 0x80) {
      gap = true;
    } else if (cp == 0xE4 || cp == 0xC4) {
      put("ae");
    } else if (cp == 0xF6 || cp == 0xD6) {
      put("oe");
    } else if (cp == 0xFC || cp == 0xDC) {
      put("ue");
    } else if (cp == 0xDF) {
      put("ss");
    } else if (cp >= 0xC0 && cp <= 0xFF) {
      if (kLatin1[cp - 0xC0]) {
        char t[2] = {kLatin1[cp - 0xC0], 0};
        put(t);
      }
    } else {
      // Zeichen, die sich in ASCII-Zeichen zerlegen lassen; alle anderen entfallen
      switch (cp) {
        case 0xA0: case 0xA8: case 0xAF: case 0xB4: case 0xB8: case 0x2026: gap = true; break;   // Leerzeichen, Punkte
        case 0xAA: put("a"); break;
        case 0xBA: put("o"); break;
        case 0xB2: put("2"); break;
        case 0xB3: put("3"); break;
        case 0xB9: put("1"); break;
        case 0xBC: put("14"); break;
        case 0xBD: put("12"); break;
        case 0xBE: put("34"); break;
        default: break;
      }
    }
  }
  if (s.size() > kMaxFileStem) s.resize(kMaxFileStem);
  while (!s.empty() && s.back() == '-') s.pop_back();
  return (s.empty() ? std::string("design") : s) + ".s51";
}

}  // namespace s51
