// ERZEUGT von designer/tools/gen_cpp_header.py aus designer/s51design/schema.py.
// Nicht von Hand ändern.

#pragma once
#include <cstddef>
#include <cstdint>
#include <string>

namespace s51 {

struct Color {
  uint8_t r, g, b;
  uint16_t to565() const { return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)); }
  bool operator==(const Color& o) const { return r == o.r && g == o.g && b == o.b; }
};

constexpr char kMagic[4] = {'S', '5', '1', 'L'};
constexpr uint8_t kVersionMajor = 1;
constexpr uint8_t kVersionMinor = 3;
constexpr uint16_t kHeaderSize = 16;
constexpr uint16_t kDisplayWidth = 480;
constexpr uint16_t kDisplayHeight = 320;
constexpr uint32_t kMaxFileSize = 1048576;
constexpr uint8_t kMaxScreens = 16;
constexpr uint16_t kMaxWidgetsPerScreen = 96;
constexpr uint8_t kRolePage = 0;
constexpr uint8_t kRoleNight = 1;
constexpr uint8_t kRoleStartup = 2;
constexpr uint8_t kNoPage = 0xFF;
constexpr uint8_t kNoImage = 0xFF;
constexpr uint8_t kMaxImages = 32;
constexpr uint16_t kMaxImageSide = 480;
constexpr uint8_t kImageFormatRaw = 1;
constexpr uint8_t kImageFormatRle = 2;
constexpr uint8_t kImageFlagAlpha = 0x01;
constexpr uint8_t kFlagHidden = 0x01;
constexpr uint8_t kFlagLocked = 0x02;
constexpr uint8_t kMetaName = 1;
constexpr uint8_t kMetaAuthor = 2;
constexpr uint8_t kMetaCreated = 3;
constexpr uint8_t kMetaTool = 4;

enum class WidgetType : uint8_t {
  Text = 1,  // Text
  Value = 2,  // Wert
  Bar = 3,  // Balken
  Gauge = 4,  // Rundinstrument
  Indicator = 5,  // Kontrollleuchte
  Rect = 6,  // Fläche / Linie
  Image = 7,  // Bild
  Button = 8,  // Taste
};

constexpr bool isKnownWidgetType(uint8_t c) {
  return c == 1 || c == 2 || c == 3 || c == 4 || c == 5 || c == 6 || c == 7 || c == 8;
}

enum class Source : uint8_t {
  None = 0,  // Keine
  Speed = 1,  // Geschwindigkeit
  Rpm = 2,  // Drehzahl
  Gear = 3,  // Gang
  Odometer = 4,  // Gesamtkilometer
  TripA = 5,  // Tageskilometer A
  TripB = 6,  // Tageskilometer B
  HeadTemp = 7,  // Zylinderkopftemperatur
  Voltage = 8,  // Bordspannung
  OutsideTemp = 9,  // Außentemperatur
  HousingTemp = 10,  // Temperatur in der Lampe
  Lean = 11,  // Schräglage
  LeanMax = 12,  // Schräglage maximal
  Time = 13,  // Uhrzeit
  SpeedMax = 14,  // Höchstgeschwindigkeit
  SpeedAvg = 15,  // Durchschnitt
  RideTime = 16,  // Fahrzeit
  TankKm = 17,  // Kilometer seit Tanken
  SongTitle = 18,  // Songtitel
  SongArtist = 19,  // Interpret
  ServiceKm = 20,  // Kilometer bis Wartung
  SongAlbum = 21,  // Album
  SongPosition = 22,  // Titel-Position (m:ss)
  SongLength = 23,  // Titellänge (m:ss)
  SongProgress = 24,  // Titel-Fortschritt
  Volume = 25,  // Lautstärke am Handy
  PhoneName = 26,  // Name des Handys
  BlinkerLeft = 64,  // Blinker links
  BlinkerRight = 65,  // Blinker rechts
  HighBeam = 66,  // Fernlicht
  Neutral = 67,  // Leerlauf
  Light = 68,  // Licht an
  AlarmArmed = 69,  // Alarm scharf
  GpsFix = 70,  // GPS-Empfang
  BtConnected = 71,  // Handy verbunden
  ShiftLight = 72,  // Schaltblitz
  Warning = 73,  // Eine Warnung aktiv
  MusicPlaying = 74,  // Musik läuft
};

constexpr bool isBoolSource(Source s) { return static_cast<uint8_t>(s) >= 64 && static_cast<uint8_t>(s) < 128; }

enum class SourceKind : uint8_t { Number, Bool, Text, Time };

// Art jeder Datenquelle und der Bereich der Demo-Werte (wie im Designer)
struct SourceDef {
  Source source;
  SourceKind kind;
  float demoMin;
  float demoMax;
};

constexpr SourceDef kSourceDefs[] = {
  {Source::None, SourceKind::Number, 0.0f, 0.0f},
  {Source::Speed, SourceKind::Number, 0.0f, 65.0f},
  {Source::Rpm, SourceKind::Number, 1200.0f, 7500.0f},
  {Source::Gear, SourceKind::Number, 0.0f, 4.0f},
  {Source::Odometer, SourceKind::Number, 12345.0f, 12346.0f},
  {Source::TripA, SourceKind::Number, 0.0f, 150.0f},
  {Source::TripB, SourceKind::Number, 0.0f, 999.0f},
  {Source::HeadTemp, SourceKind::Number, 60.0f, 240.0f},
  {Source::Voltage, SourceKind::Number, 11.5f, 14.4f},
  {Source::OutsideTemp, SourceKind::Number, 2.0f, 28.0f},
  {Source::HousingTemp, SourceKind::Number, 15.0f, 55.0f},
  {Source::Lean, SourceKind::Number, -35.0f, 35.0f},
  {Source::LeanMax, SourceKind::Number, 38.0f, 38.0f},
  {Source::Time, SourceKind::Time, 0.0f, 0.0f},
  {Source::SpeedMax, SourceKind::Number, 62.0f, 62.0f},
  {Source::SpeedAvg, SourceKind::Number, 34.0f, 34.0f},
  {Source::RideTime, SourceKind::Number, 0.0f, 90.0f},
  {Source::TankKm, SourceKind::Number, 0.0f, 180.0f},
  {Source::SongTitle, SourceKind::Text, 0.0f, 0.0f},
  {Source::SongArtist, SourceKind::Text, 0.0f, 0.0f},
  {Source::ServiceKm, SourceKind::Number, 0.0f, 800.0f},
  {Source::SongAlbum, SourceKind::Text, 0.0f, 0.0f},
  {Source::SongPosition, SourceKind::Text, 0.0f, 0.0f},
  {Source::SongLength, SourceKind::Text, 0.0f, 0.0f},
  {Source::SongProgress, SourceKind::Number, 38.0f, 38.0f},
  {Source::Volume, SourceKind::Number, 60.0f, 60.0f},
  {Source::PhoneName, SourceKind::Text, 0.0f, 0.0f},
  {Source::BlinkerLeft, SourceKind::Bool, 0.0f, 0.0f},
  {Source::BlinkerRight, SourceKind::Bool, 0.0f, 0.0f},
  {Source::HighBeam, SourceKind::Bool, 0.0f, 0.0f},
  {Source::Neutral, SourceKind::Bool, 0.0f, 0.0f},
  {Source::Light, SourceKind::Bool, 0.0f, 0.0f},
  {Source::AlarmArmed, SourceKind::Bool, 0.0f, 0.0f},
  {Source::GpsFix, SourceKind::Bool, 0.0f, 0.0f},
  {Source::BtConnected, SourceKind::Bool, 0.0f, 0.0f},
  {Source::ShiftLight, SourceKind::Bool, 0.0f, 0.0f},
  {Source::Warning, SourceKind::Bool, 0.0f, 0.0f},
  {Source::MusicPlaying, SourceKind::Bool, 0.0f, 0.0f},
};

constexpr size_t kSourceCount = 38;

enum class Icon : uint8_t {
  None = 0,  // Kein Symbol
  ArrowLeft = 1,  // Pfeil links
  ArrowRight = 2,  // Pfeil rechts
  HighBeam = 3,  // Fernlicht
  Neutral = 4,  // Leerlauf (N)
  Light = 5,  // Licht
  Battery = 6,  // Batterie
  Temp = 7,  // Thermometer
  Gps = 8,  // GPS
  Bluetooth = 9,  // Bluetooth
  Lock = 10,  // Schloss
  Warning = 11,  // Warndreieck
  Music = 12,  // Musik
  Play = 13,  // Abspielen
  Pause = 14,  // Pause
  PlayPause = 15,  // Abspielen/Pause (wechselt mit „Musik läuft“)
  Next = 16,  // Nächster Titel
  Previous = 17,  // Voriger Titel
  VolumeUp = 18,  // Lauter
  VolumeDown = 19,  // Leiser
  Menu = 20,  // Menü
};

enum class Font : uint8_t {
  Sans = 0,  // Normal
  SansBold = 1,  // Fett
  Segment = 2,  // 7-Segment
};

enum class Align : uint8_t {
  Left = 0,  // Links
  Center = 1,  // Mitte
  Right = 2,  // Rechts
};

enum class Orientation : uint8_t {
  Horizontal = 0,  // Waagerecht
  Vertical = 1,  // Senkrecht
};

enum class Action : uint8_t {
  None = 0,  // Keine
  PlayPause = 1,  // Abspielen/Pause
  NextTrack = 2,  // Nächster Titel
  PreviousTrack = 3,  // Voriger Titel
  VolumeUp = 4,  // Lauter
  VolumeDown = 5,  // Leiser
  PageNext = 6,  // Nächste Seite
  PagePrevious = 7,  // Vorige Seite
  Menu = 8,  // Menü öffnen
  NightMode = 9,  // Nachtmodus umschalten
  Lock = 10,  // Sperren (mit PIN)
  TripReset = 11,  // Tageskilometer A zurücksetzen
};

// Aktionen mit ihrem Namen in der tacho.cfg (Abschnitt [taster])
struct ActionDef {
  Action action;
  const char* cfgKey;
};

constexpr ActionDef kActionDefs[] = {
  {Action::None, "keine"},
  {Action::PlayPause, "play_pause"},
  {Action::NextTrack, "naechster_titel"},
  {Action::PreviousTrack, "voriger_titel"},
  {Action::VolumeUp, "lauter"},
  {Action::VolumeDown, "leiser"},
  {Action::PageNext, "seite_vor"},
  {Action::PagePrevious, "seite_zurueck"},
  {Action::Menu, "menue"},
  {Action::NightMode, "nachtmodus"},
  {Action::Lock, "sperren"},
  {Action::TripReset, "trip_zuruecksetzen"},
};

enum class Prop : uint8_t {
  Source = 1,  // Datenquelle (enum:source)
  Color = 2,  // Farbe (color)
  BgColor = 3,  // Hintergrund (color)
  Font = 4,  // Schrift (enum:font)
  Size = 5,  // Schriftgröße (px) (u8)
  Align = 6,  // Ausrichtung (enum:align)
  Text = 7,  // Text (str)
  Decimals = 8,  // Nachkommastellen (u8)
  Unit = 9,  // Einheit (str)
  Min = 10,  // Minimum (f32)
  Max = 11,  // Maximum (f32)
  WarnAbove = 12,  // Warnung ab (f32)
  WarnColor = 13,  // Warnfarbe (color)
  CritAbove = 14,  // Kritisch ab (f32)
  CritColor = 15,  // Kritisch-Farbe (color)
  Segments = 16,  // Segmente (0 = durchgehend) (u8)
  Orientation = 17,  // Richtung (enum:orientation)
  StartAngle = 18,  // Startwinkel (°) (i16)
  EndAngle = 19,  // Endwinkel (°) (i16)
  Thickness = 20,  // Dicke (px) (u8)
  Radius = 21,  // Eckenradius (px) (u8)
  Icon = 22,  // Symbol (enum:icon)
  OnColor = 23,  // Farbe an (color)
  OffColor = 24,  // Farbe aus (color)
  Blink = 25,  // Blinken, wenn an (bool)
  Format = 26,  // Format (str)
  BorderColor = 27,  // Rahmenfarbe (color)
  BorderWidth = 28,  // Rahmenbreite (px) (u8)
  Image = 29,  // Bild (u8)
  FromZero = 30,  // Ab 0 füllen (bool)
  Action = 31,  // Aktion beim Antippen (enum:action)
};

enum class CfgType : uint8_t { Int, Float, Bool, Str, Enum };

enum class CfgKey : uint16_t {
  FahrzeugRadumfangMm,
  FahrzeugRadumfangLernen,
  FahrzeugHallSensor,
  FahrzeugMagnete,
  FahrzeugImpulseProUmdrehung,
  FahrzeugGaenge,
  FahrzeugTankreichweiteKm,
  AnzeigeLayoutDatei,
  AnzeigeStartseite,
  AnzeigeStartbildDauerS,
  AnzeigeStartbildText,
  AnzeigeHelligkeitTag,
  AnzeigeHelligkeitNacht,
  AnzeigeHelligkeitAuto,
  AnzeigeNachtmodus,
  WarnungenKopftempWarnung,
  WarnungenKopftempKritisch,
  WarnungenSpannungMin,
  WarnungenSpannungMax,
  WarnungenGlaetteUnter,
  WarnungenSchaltblitzDrehzahl,
  WartungGetriebeoelKm,
  WartungZuendkerzeKm,
  WartungKetteKm,
  AlarmAktiv,
  AlarmStufe,
  AlarmEmpfindlichkeit,
  AlarmDauerS,
  AlarmEntsperrzeitS,
  GpsMessrateHz,
  GpsZeitzone,
  BluetoothAktiv,
  BluetoothName,
  TasterTaster1Kurz,
  TasterTaster1Lang,
  TasterTaster2Kurz,
  TasterTaster2Lang,
  TasterTaster3Kurz,
  TasterTaster3Lang,
  WlanModus,
  WlanSsid,
  WlanPasswort,
  WlanHostname,
  Count
};

struct CfgDef {
  const char* section;
  const char* key;
  CfgType type;
  const char* defaultValue;
  float min;
  float max;
  const char* choices;  // durch | getrennt
};

// Felder eines Elements, eines je Eigenschaft (in WidgetData verwendet)
#define S51_WIDGET_FIELDS \
  Source source; \
  Color color; \
  Color bgColor; \
  Font font; \
  uint8_t size; \
  Align align; \
  std::string text; \
  uint8_t decimals; \
  std::string unit; \
  float min; \
  float max; \
  float warnAbove; \
  Color warnColor; \
  float critAbove; \
  Color critColor; \
  uint8_t segments; \
  Orientation orientation; \
  int16_t startAngle; \
  int16_t endAngle; \
  uint8_t thickness; \
  uint8_t radius; \
  Icon icon; \
  Color onColor; \
  Color offColor; \
  bool blink; \
  std::string format; \
  Color borderColor; \
  uint8_t borderWidth; \
  uint8_t image; \
  bool fromZero; \
  Action action; \
  uint32_t propsSet[2];

constexpr CfgDef kConfigDefs[] = {
  {"fahrzeug", "radumfang_mm", CfgType::Int, "1720", 1000.0f, 2500.0f, ""},
  {"fahrzeug", "radumfang_lernen", CfgType::Bool, "ja", 0.0f, 0.0f, ""},
  {"fahrzeug", "hall_sensor", CfgType::Bool, "nein", 0.0f, 0.0f, ""},
  {"fahrzeug", "magnete", CfgType::Int, "2", 1.0f, 8.0f, ""},
  {"fahrzeug", "impulse_pro_umdrehung", CfgType::Int, "1", 1.0f, 4.0f, ""},
  {"fahrzeug", "gaenge", CfgType::Int, "4", 3.0f, 6.0f, ""},
  {"fahrzeug", "tankreichweite_km", CfgType::Int, "150", 0.0f, 1000.0f, ""},
  {"anzeige", "layout_datei", CfgType::Str, "design.s51", 0.0f, 0.0f, ""},
  {"anzeige", "startseite", CfgType::Int, "0", 0.0f, 15.0f, ""},
  {"anzeige", "startbild_dauer_s", CfgType::Int, "2", 0.0f, 10.0f, ""},
  {"anzeige", "startbild_text", CfgType::Str, "S51", 0.0f, 0.0f, ""},
  {"anzeige", "helligkeit_tag", CfgType::Int, "100", 5.0f, 100.0f, ""},
  {"anzeige", "helligkeit_nacht", CfgType::Int, "30", 5.0f, 100.0f, ""},
  {"anzeige", "helligkeit_auto", CfgType::Bool, "ja", 0.0f, 0.0f, ""},
  {"anzeige", "nachtmodus", CfgType::Enum, "auto", 0.0f, 0.0f, "auto|an|aus"},
  {"warnungen", "kopftemp_warnung", CfgType::Int, "200", 50.0f, 400.0f, ""},
  {"warnungen", "kopftemp_kritisch", CfgType::Int, "240", 50.0f, 400.0f, ""},
  {"warnungen", "spannung_min", CfgType::Float, "12", 9.0f, 15.0f, ""},
  {"warnungen", "spannung_max", CfgType::Float, "15", 12.0f, 18.0f, ""},
  {"warnungen", "glaette_unter", CfgType::Float, "3", -10.0f, 10.0f, ""},
  {"warnungen", "schaltblitz_drehzahl", CfgType::Int, "6500", 0.0f, 15000.0f, ""},
  {"wartung", "getriebeoel_km", CfgType::Int, "0", 0.0f, 100000.0f, ""},
  {"wartung", "zuendkerze_km", CfgType::Int, "0", 0.0f, 100000.0f, ""},
  {"wartung", "kette_km", CfgType::Int, "0", 0.0f, 100000.0f, ""},
  {"alarm", "aktiv", CfgType::Bool, "ja", 0.0f, 0.0f, ""},
  {"alarm", "stufe", CfgType::Int, "2", 1.0f, 2.0f, ""},
  {"alarm", "empfindlichkeit", CfgType::Int, "3", 1.0f, 5.0f, ""},
  {"alarm", "dauer_s", CfgType::Int, "30", 5.0f, 180.0f, ""},
  {"alarm", "entsperrzeit_s", CfgType::Int, "30", 10.0f, 120.0f, ""},
  {"gps", "messrate_hz", CfgType::Int, "10", 1.0f, 10.0f, ""},
  {"gps", "zeitzone", CfgType::Str, "Europe/Berlin", 0.0f, 0.0f, ""},
  {"bluetooth", "aktiv", CfgType::Bool, "ja", 0.0f, 0.0f, ""},
  {"bluetooth", "name", CfgType::Str, "S51-Tacho", 0.0f, 0.0f, ""},
  {"taster", "taster1_kurz", CfgType::Enum, "seite_vor", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"taster", "taster1_lang", CfgType::Enum, "trip_zuruecksetzen", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"taster", "taster2_kurz", CfgType::Enum, "play_pause", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"taster", "taster2_lang", CfgType::Enum, "keine", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"taster", "taster3_kurz", CfgType::Enum, "naechster_titel", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"taster", "taster3_lang", CfgType::Enum, "voriger_titel", 0.0f, 0.0f, "keine|play_pause|naechster_titel|voriger_titel|lauter|leiser|seite_vor|seite_zurueck|menue|nachtmodus|sperren|trip_zuruecksetzen"},
  {"wlan", "modus", CfgType::Enum, "hotspot", 0.0f, 0.0f, "hotspot|heimnetz"},
  {"wlan", "ssid", CfgType::Str, "S51-Tacho", 0.0f, 0.0f, ""},
  {"wlan", "passwort", CfgType::Str, "simson51", 0.0f, 0.0f, ""},
  {"wlan", "hostname", CfgType::Str, "s51-tacho", 0.0f, 0.0f, ""},
};

}  // namespace s51
