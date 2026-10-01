// Gibt für jede Zeile der Standardeingabe den Dateinamen aus, den die Firmware
// einem per WLAN empfangenen Design gibt (s51::designFileName).
// Der Test designer/tests/test_firmware_render.py vergleicht mit sdcard.file_name_for().
#include <iostream>
#include <string>

#include "s51_filename.h"

int main() {
  std::string line;
  while (std::getline(std::cin, line)) std::cout << s51::designFileName(line) << "\n";
  return 0;
}
