// Dateiname für ein Design aus dem Namen des Layouts.
// Gleiche Regel wie designer/s51design/sdcard.py, file_name_for():
// klein, ä/ö/ü/ß ausgeschrieben, Akzente weg, alles andere wird zu „-“,
// höchstens 40 Zeichen, Endung .s51. Leerer Name: design.s51.
// Reines C++ ohne Arduino-Abhängigkeit.
#pragma once

#include <string>

namespace s51 {

constexpr size_t kMaxFileStem = 40;

std::string designFileName(const std::string& layoutName);

}  // namespace s51
