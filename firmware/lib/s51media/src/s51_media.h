// Musik und Uhrzeit vom Handy: Auswerten der Bluetooth-Daten, ohne Bluetooth selbst.
//
// - Apple Media Service (AMS, nur iPhone): Titel, Interpret, Album, Länge,
//   Wiedergabe-Zustand, Position, Lautstärke. Aufbau der Nachrichten:
//   Apple „Apple Media Service Specification“, Kurzfassung in docs/datenblaetter.md.
// - Current Time Service (CTS, Bluetooth-Standard, iPhone): Uhrzeit und Datum.
//
// Reines C++ ohne Arduino-Abhängigkeit, am PC getestet (firmware/hosttest/media_main.cpp).
// Die Verbindung selbst (NimBLE) steht in firmware/src/bluetooth.cpp.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

#include "s51_values.h"

namespace s51 {

// AMS: Nummern aus der Apple-Spezifikation
namespace ams {
enum Entity : uint8_t { kPlayer = 0, kQueue = 1, kTrack = 2 };
enum PlayerAttr : uint8_t { kPlayerName = 0, kPlaybackInfo = 1, kVolume = 2 };
enum TrackAttr : uint8_t { kArtist = 0, kAlbum = 1, kTitle = 2, kDuration = 3 };
enum Command : uint8_t {
  kPlay = 0, kPause = 1, kTogglePlayPause = 2, kNextTrack = 3, kPreviousTrack = 4, kVolumeUp = 5, kVolumeDown = 6
};
constexpr const char* kServiceUuid = "89D3502B-0F36-433A-8EF4-C502AD55F8DC";
constexpr const char* kRemoteCommandUuid = "9B3C81D8-57B1-4A8A-B8DF-0E56F7CA51C2";
constexpr const char* kEntityUpdateUuid = "2F7CABCE-808D-411F-9A0C-BB92BA96C102";
constexpr const char* kEntityAttributeUuid = "C6B2F38C-23AB-46D8-A6AB-A3A870BBD5D7";
}  // namespace ams

struct MediaState {
  bool connected = false;      // Handy per Bluetooth verbunden
  bool mediaInfo = false;      // AMS vorhanden (iPhone): Titel usw. kommen an
  std::string phoneName;
  std::string title, artist, album;
  int playback = 0;            // 0 Pause, 1 läuft, 2 Rücklauf, 3 Vorlauf
  float rate = 0;              // Abspielgeschwindigkeit
  float elapsed = 0;           // Position in s zum Zeitpunkt elapsedAt
  uint32_t elapsedAt = 0;      // ms
  float duration = -1;         // Länge in s, -1 unbekannt
  float volume = -1;           // 0 … 1, -1 unbekannt

  bool timeValid = false;      // Uhrzeit vom Handy (CTS)
  int64_t epoch = 0;           // Sekunden seit 1.1.1970, Ortszeit, zum Zeitpunkt timeAt
  uint32_t timeAt = 0;         // ms

  float position(uint32_t nowMs) const;   // jetzige Position in s
};

// Wertet eine Benachrichtigung der AMS-Eigenschaft „Entity Update“ aus.
// Gibt false zurück, wenn die Nachricht zu kurz oder unbekannt ist.
bool amsApplyUpdate(MediaState& st, const uint8_t* data, size_t len, uint32_t nowMs);

// Wertet den Wert der CTS-Eigenschaft „Current Time“ (0x2A2B) aus.
bool ctsApply(MediaState& st, const uint8_t* data, size_t len, uint32_t nowMs);

// Ortszeit jetzt, aus der Uhrzeit vom Handy. false: keine Zeit bekannt.
bool mediaClock(const MediaState& st, uint32_t nowMs, int& year, int& month, int& day, int& hour, int& minute,
                int& second);

// Schreibt die Musik-Quellen (Songtitel … Lautstärke, Handy verbunden, Musik läuft)
// und die Uhrzeit in die Werte. Ohne Verbindung sind sie leer bzw. aus.
void mediaToValues(const MediaState& st, Values& v, uint32_t nowMs);

// Sekunden als m:ss, ab einer Stunde h:mm:ss
std::string formatDuration(float seconds);

// Ersetzt Zeichen, die die Schriften des Tachos nicht haben: Buchstaben mit Akzent
// werden zum Grundbuchstaben (é → e), andere Zeichen zu „?“, Emojis entfallen.
std::string fitCharset(const std::string& text);

}  // namespace s51
