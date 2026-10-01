// Prüft das Auswerten der Bluetooth-Daten vom Handy (lib/s51media) am PC.
// Liest Befehle zeilenweise von der Standardeingabe:
//   t <ms>            Laufzeit setzen
//   connect <Name>    Handy verbunden
//   disconnect        Verbindung getrennt
//   ams <hex>         Benachrichtigung „Entity Update“ des Apple Media Service
//   cts <hex>         Wert „Current Time“
//   fit <Text>        Text an die Schriften anpassen und ausgeben
//   show              Werte ausgeben, wie das Layout sie bekommt
// Der Test designer/tests/test_firmware_media.py vergleicht die Ausgabe.
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include "s51_media.h"

static std::vector<uint8_t> hexBytes(const std::string& h) {
  std::vector<uint8_t> out;
  for (size_t i = 0; i + 1 < h.size(); i += 2) out.push_back(uint8_t(std::stoul(h.substr(i, 2), nullptr, 16)));
  return out;
}

int main() {
  s51::MediaState st;
  uint32_t now = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    size_t sp = line.find(' ');
    std::string cmd = line.substr(0, sp), arg = sp == std::string::npos ? "" : line.substr(sp + 1);
    if (cmd == "t") {
      now = uint32_t(std::stoul(arg));
    } else if (cmd == "connect") {
      st = s51::MediaState();
      st.connected = true;
      st.phoneName = arg;
    } else if (cmd == "disconnect") {
      st = s51::MediaState();
    } else if (cmd == "ams" || cmd == "cts") {
      auto b = hexBytes(arg);
      bool ok = cmd == "ams" ? s51::amsApplyUpdate(st, b.data(), b.size(), now) : s51::ctsApply(st, b.data(), b.size(), now);
      if (!ok) std::cout << "abgelehnt\n";
    } else if (cmd == "fit") {
      std::cout << s51::fitCharset(arg) << "\n";
    } else if (cmd == "show") {
      s51::Values v;
      s51::mediaToValues(st, v, now);
      using S = s51::Source;
      char time[32] = "--";
      int y, mo, d, h, mi, s;
      if (s51::mediaClock(st, now, y, mo, d, h, mi, s)) snprintf(time, sizeof(time), "%04d-%02d-%02d %02d:%02d:%02d", y, mo, d, h, mi, s);
      char num[64];
      snprintf(num, sizeof(num), "%s|%s", v.hasNumber(S::SongProgress) ? std::to_string(int(v.get(S::SongProgress) + 0.5f)).c_str() : "-",
               v.hasNumber(S::Volume) ? std::to_string(int(v.get(S::Volume))).c_str() : "-");
      std::cout << (v.getFlag(S::BtConnected) ? 1 : 0) << "|" << v.getText(S::PhoneName) << "|"
                << (v.getFlag(S::MusicPlaying) ? 1 : 0) << "|" << v.getText(S::SongTitle) << "|"
                << v.getText(S::SongArtist) << "|" << v.getText(S::SongAlbum) << "|" << v.getText(S::SongPosition)
                << "|" << v.getText(S::SongLength) << "|" << num << "|" << time << "\n";
    }
  }
  return 0;
}
