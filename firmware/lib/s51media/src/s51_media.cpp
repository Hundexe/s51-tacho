#include "s51_media.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace s51 {

namespace {

// Kalender ohne Zeitzonen (H. Hinnant, „chrono-compatible low-level date algorithms“)
int64_t daysFromCivil(int64_t y, unsigned m, unsigned d) {
  y -= m <= 2;
  const int64_t era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = static_cast<unsigned>(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + static_cast<int64_t>(doe) - 719468;
}

void civilFromDays(int64_t z, int& y, int& m, int& d) {
  z += 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const unsigned doe = static_cast<unsigned>(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  d = static_cast<int>(doy - (153 * mp + 2) / 5 + 1);
  m = static_cast<int>(mp < 10 ? mp + 3 : mp - 9);
  y = static_cast<int>(static_cast<int64_t>(yoe) + era * 400 + (m <= 2));
}

float toFloat(const std::string& s, float fallback) {
  if (s.empty()) return fallback;
  char* end = nullptr;
  float v = std::strtof(s.c_str(), &end);
  return end == s.c_str() ? fallback : v;
}

// Grundbuchstaben für U+00C0 … U+00FF (nullptr: kein Ersatz, ä/ö/ü/ß/× hat die Schrift selbst)
const char* const kLatin1[64] = {
    "A", "A", "A", "A", nullptr, "A", "AE", "C", "E", "E", "E", "E", "I", "I", "I", "I",
    "D", "N", "O", "O", "O", "O", nullptr, nullptr, "O", "U", "U", "U", nullptr, "Y", "Th", nullptr,
    "a", "a", "a", "a", nullptr, "a", "ae", "c", "e", "e", "e", "e", "i", "i", "i", "i",
    "d", "n", "o", "o", "o", "o", nullptr, "/", "o", "u", "u", "u", nullptr, "y", "th", "y",
};
// Grundbuchstaben für U+0100 … U+017F (Lateinisch, erweitert A)
const char kLatinA[] =
    "AaAaAaCcCcCcCcDd"
    "DdEeEeEeEeEeGgGg"
    "GgGgHhHhIiIiIiIi"
    "IiIiJjKkkLlLlLlL"
    "lLlNnNnNnnNnOoOo"
    "OoOoRrRrRrSsSsSs"
    "SsTtTtTtUuUuUuUu"
    "UuUuWwYyYZzZzZzs";

// Zeichen außerhalb von ASCII, die in den Schriften des Tachos enthalten sind
// (firmware/tools/gen_fonts.py, Liste FULL)
bool inFont(uint32_t cp) {
  switch (cp) {
    case 0xB0: case 0xB2: case 0xB3: case 0xB5: case 0xB7: case 0xD7:
    case 0xE4: case 0xF6: case 0xFC: case 0xC4: case 0xD6: case 0xDC: case 0xDF:
    case 0x2013: case 0x2014: case 0x2018: case 0x2019: case 0x201A: case 0x201C: case 0x201D: case 0x201E:
    case 0x2026: case 0x20AC: case 0x266A: case 0x2022: case 0x2190: case 0x2191: case 0x2192: case 0x2193:
      return true;
    default:
      return false;
  }
}

void appendUtf8(std::string& out, uint32_t cp) {
  if (cp < 0x80) {
    out += char(cp);
  } else if (cp < 0x800) {
    out += char(0xC0 | (cp >> 6));
    out += char(0x80 | (cp & 0x3F));
  } else if (cp < 0x10000) {
    out += char(0xE0 | (cp >> 12));
    out += char(0x80 | ((cp >> 6) & 0x3F));
    out += char(0x80 | (cp & 0x3F));
  } else {
    out += char(0xF0 | (cp >> 18));
    out += char(0x80 | ((cp >> 12) & 0x3F));
    out += char(0x80 | ((cp >> 6) & 0x3F));
    out += char(0x80 | (cp & 0x3F));
  }
}

}  // namespace

float MediaState::position(uint32_t nowMs) const {
  float p = elapsed;
  if (playback == 1) p += rate * float(nowMs - elapsedAt) / 1000.0f;
  if (duration > 0 && p > duration) p = duration;
  return p < 0 ? 0 : p;
}

bool amsApplyUpdate(MediaState& st, const uint8_t* data, size_t len, uint32_t nowMs) {
  if (len < 3) return false;
  const uint8_t entity = data[0], attr = data[1];
  // data[2]: Flags, Bit 0 = Wert gekürzt (passt nicht in eine Nachricht). Gekürzte Texte werden so gezeigt.
  std::string value(reinterpret_cast<const char*>(data + 3), len - 3);
  st.mediaInfo = true;
  if (entity == ams::kPlayer) {
    if (attr == ams::kPlaybackInfo) {
      // „Zustand,Geschwindigkeit,Position“, z. B. „1,1.0,35.264“. Leer: keine Wiedergabe-App
      if (value.empty()) {
        st.playback = 0;
        st.rate = 0;
        st.elapsed = 0;
      } else {
        size_t a = value.find(','), b = a == std::string::npos ? a : value.find(',', a + 1);
        st.playback = std::atoi(value.substr(0, a).c_str());
        st.rate = a == std::string::npos ? 0 : toFloat(value.substr(a + 1, b - a - 1), 0);
        st.elapsed = b == std::string::npos ? 0 : toFloat(value.substr(b + 1), 0);
      }
      st.elapsedAt = nowMs;
      return true;
    }
    if (attr == ams::kVolume) {
      st.volume = toFloat(value, -1);
      return true;
    }
    return attr == ams::kPlayerName;
  }
  if (entity == ams::kTrack) {
    switch (attr) {
      case ams::kArtist: st.artist = fitCharset(value); return true;
      case ams::kAlbum: st.album = fitCharset(value); return true;
      case ams::kTitle: st.title = fitCharset(value); return true;
      case ams::kDuration: st.duration = toFloat(value, -1); return true;
      default: return false;
    }
  }
  return entity == ams::kQueue;
}

bool ctsApply(MediaState& st, const uint8_t* data, size_t len, uint32_t nowMs) {
  if (len < 7) return false;
  int year = data[0] | (data[1] << 8);
  int month = data[2], day = data[3], hour = data[4], minute = data[5], second = data[6];
  if (year < 2000 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59) {
    return false;
  }
  st.epoch = daysFromCivil(year, unsigned(month), unsigned(day)) * 86400 + hour * 3600 + minute * 60 + second;
  st.timeAt = nowMs;
  st.timeValid = true;
  return true;
}

bool mediaClock(const MediaState& st, uint32_t nowMs, int& year, int& month, int& day, int& hour, int& minute,
                int& second) {
  if (!st.timeValid) return false;
  int64_t t = st.epoch + int64_t(nowMs - st.timeAt) / 1000;
  int64_t days = t >= 0 ? t / 86400 : (t - 86399) / 86400;
  int64_t rest = t - days * 86400;
  civilFromDays(days, year, month, day);
  hour = int(rest / 3600);
  minute = int(rest / 60 % 60);
  second = int(rest % 60);
  return true;
}

std::string formatDuration(float seconds) {
  if (seconds < 0) seconds = 0;
  long s = long(seconds);
  char buf[32];
  if (s >= 3600) {
    snprintf(buf, sizeof(buf), "%ld:%02ld:%02ld", s / 3600, s / 60 % 60, s % 60);
  } else {
    snprintf(buf, sizeof(buf), "%ld:%02ld", s / 60, s % 60);
  }
  return buf;
}

void mediaToValues(const MediaState& st, Values& v, uint32_t nowMs) {
  v.setFlag(Source::BtConnected, st.connected);
  v.setText(Source::PhoneName, st.connected ? st.phoneName : std::string());
  const bool info = st.connected && st.mediaInfo;
  v.setFlag(Source::MusicPlaying, info && st.playback == 1);
  v.setText(Source::SongTitle, info ? st.title : std::string());
  v.setText(Source::SongArtist, info ? st.artist : std::string());
  v.setText(Source::SongAlbum, info ? st.album : std::string());
  const bool hasTrack = info && st.duration > 0;
  const float pos = st.position(nowMs);
  v.setText(Source::SongPosition, hasTrack ? formatDuration(pos) : std::string());
  v.setText(Source::SongLength, hasTrack ? formatDuration(st.duration) : std::string());
  if (hasTrack) {
    v.set(Source::SongProgress, 100.0f * pos / st.duration);
  } else {
    v.unset(Source::SongProgress);
  }
  if (info && st.volume >= 0) {
    v.set(Source::Volume, std::round(st.volume * 100.0f));
  } else {
    v.unset(Source::Volume);
  }
  int y, mo, d, h, mi, s;
  if (mediaClock(st, nowMs, y, mo, d, h, mi, s)) {
    v.timeValid = true;
    v.hour = uint8_t(h);
    v.minute = uint8_t(mi);
    v.second = uint8_t(s);
  }
}

std::string fitCharset(const std::string& text) {
  std::string out;
  for (size_t i = 0; i < text.size();) {
    unsigned char c = text[i];
    int len = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 1;
    if (i + len > text.size()) len = 1;
    uint32_t cp = len == 1 ? c : len == 2 ? (c & 0x1F) : len == 3 ? (c & 0x0F) : (c & 0x07);
    for (int k = 1; k < len; k++) cp = (cp << 6) | (static_cast<unsigned char>(text[i + k]) & 0x3F);
    if (len == 1 && c >= 0x80) cp = '?';   // ungültiges UTF-8
    i += len;

    if (cp >= 0x20 && cp < 0x7F) {
      out += char(cp);
    } else if (cp == '\t' || cp == '\n' || cp == 0xA0) {
      out += ' ';
    } else if (inFont(cp)) {
      appendUtf8(out, cp);
    } else if (cp >= 0xC0 && cp <= 0xFF) {
      const char* base = kLatin1[cp - 0xC0];
      out += base ? base : "?";
    } else if (cp >= 0x100 && cp <= 0x17F) {
      out += kLatinA[cp - 0x100];
    } else if ((cp >= 0x300 && cp <= 0x36F) || (cp >= 0xFE00 && cp <= 0xFE0F) || cp == 0x200D || cp == 0x200B ||
               cp >= 0x1F000 || (cp >= 0x2600 && cp <= 0x27BF) || cp < 0x20) {
      // Akzente als eigene Zeichen, Varianten, Emojis, Steuerzeichen: weglassen
    } else if (cp == 0x2032 || cp == 0xB4) {
      out += '\'';
    } else {
      out += '?';
    }
  }
  // Leerzeichen am Rand entfernen (z. B. nach weggelassenen Emojis)
  size_t a = out.find_first_not_of(' '), b = out.find_last_not_of(' ');
  return a == std::string::npos ? std::string() : out.substr(a, b - a + 1);
}

}  // namespace s51
