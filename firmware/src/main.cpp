// S51-Tacho – Phase 2: Layouts aus dem S51 Designer anzeigen, Menüs und Sperre
//
// Ablauf beim Start (docs/dateiformat-layout.md, Abschnitt 7):
//   1. tacho.cfg von der SD-Karte lesen (fehlt sie: interne Kopie, sonst Standardwerte)
//   2. Design wählen: am Tacho ausgewähltes Design, sonst das Standard-Design aus
//      der tacho.cfg (layout_datei), sonst das erste .s51 im Ordner s51, sonst die
//      interne Kopie, sonst das eingebaute Layout „Klar“
//   3. Startbild-Seite zeigen (oder startbild_text)
//   4. Sperrbildschirm, wenn Sicherheitsstufe 2, Alarm an und eine PIN festgelegt ist.
//      Bis die Zündung angeschlossen ist (Phase 5), gilt jeder Start als „Zündung an“.
//   5. Fahrseiten
//
// Bedienung: Wischen nach links/rechts oder Tippen an den linken/rechten Rand
// wechselt die Seite. Lange drücken öffnet das Menü (firmware/README.md).
// Sensoren gibt es noch nicht, die meisten Werte sind Demo-Werte wie im Designer.

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <SD.h>
#include <SPI.h>
#include <Wire.h>
#include <mbedtls/md.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "lgfx_sc01plus.h"
#include "pins.h"
#include "s51_config.h"
#include "s51_filename.h"
#include "s51_layout.h"
#include "s51_menu.h"
#include "s51_picker.h"
#include "s51_render.h"
#include "s51_values.h"
#include "transfer.h"
#include "version.h"

// Eingebettete Dateien (platformio.ini: board_build.embed_files)
extern const uint8_t fontsStart[] asm("_binary_data_s51fonts_bin_start");
extern const uint8_t fontsEnd[] asm("_binary_data_s51fonts_bin_end");
extern const uint8_t klarStart[] asm("_binary_data_klar_s51_start");
extern const uint8_t klarEnd[] asm("_binary_data_klar_s51_end");

static LGFX_SC01Plus tft;
static LGFX_Sprite canvas(&tft);
static LGFX_Sprite previewSprite;           // volle Seite für die Vorschau in der Auswahl
static SPIClass sdSpi(HSPI);
static Preferences prefs;
static s51::Renderer renderer;
static s51::Config cfg;
static s51::LayoutData layout;              // angezeigtes Design
static s51::LayoutData previewLayout;       // markiertes Design in der Auswahl
static s51::Values values;
static s51::Picker picker;
static bool previewOk = false;

static std::vector<std::string> notes;      // Hinweise für die Infozeile beim Start
static std::vector<std::string> cfgNotes;   // Hinweise beim Lesen der tacho.cfg (Menü Einstellungen)
static bool cfgFound = false;
static std::vector<uint8_t> pages;          // Nummern der Tagseiten in Reihenfolge
static size_t pageIndex = 0;
static uint32_t pageChangedAt = 0;
static uint32_t notesUntil = 0;
static bool sdOk = false;
static bool fsOk = false;
static bool nfcFound = false;
static uint32_t bootCount = 0;
static std::string currentSource;           // Datei im Ordner s51, kIntern oder kBuiltin
static std::vector<uint8_t> currentRaw;     // Inhalt der angezeigten Layout-Datei

// Werte aus dem NVS und das Protokoll, beim Start gelesen. Menü und Anzeige fragen sie
// in jeder Runde ab, deshalb nicht jedes Mal aus dem Flash lesen.
static struct {
  bool pin = false;
  uint8_t alarm = 2, alarmCfg = 2;          // 2: am Tacho nichts gewählt
  float maintLast[3] = {0, 0, 0};
  float odoKm = 0;
  int pinFailures = 0;
  std::vector<std::string> log;             // älteste zuerst
} stored;

constexpr const char* kFlashCopy = "/layout.s51";
constexpr const char* kCfgCopy = "/tacho.cfg";
constexpr const char* kCfgPath = "/s51/tacho.cfg";
constexpr const char* kLogPath = "/alarm.log";
constexpr size_t kLogMax = 50;
constexpr const char* kIntern = "@intern";
constexpr const char* kBuiltin = "";
constexpr const char* kDir = "/s51";
static const s51::Color kText{241, 239, 232};
static const s51::Color kDim{136, 135, 128};
static const s51::Color kGreen{29, 158, 117};

// ---------------------------------------------------------------------------
// Dateien
// ---------------------------------------------------------------------------

static bool readAll(fs::FS& fs, const char* path, std::vector<uint8_t>& out, size_t maxLen) {
  File f = fs.open(path, "r");
  if (!f || f.isDirectory()) return false;
  size_t n = f.size();
  if (n == 0 || n > maxLen) {
    f.close();
    return false;
  }
  out.resize(n);
  bool ok = f.read(out.data(), n) == n;
  f.close();
  return ok;
}

// Schreibt erst in eine Hilfsdatei und benennt dann um, damit nie eine halbe Datei bleibt
static bool writeAll(fs::FS& fs, const char* path, const uint8_t* data, size_t n) {
  std::string tmp = std::string(path) + ".tmp";
  File f = fs.open(tmp.c_str(), "w");
  if (!f) return false;
  bool ok = f.write(data, n) == n;
  f.close();
  if (!ok) {
    fs.remove(tmp.c_str());
    return false;
  }
  fs.remove(path);
  return fs.rename(tmp.c_str(), path);
}

static void warningsToNotes(const std::vector<s51::Config::Warning>& warnings) {
  cfgNotes.clear();
  for (const auto& w : warnings) {
    cfgNotes.push_back(w.line ? "Zeile " + std::to_string(w.line) + ": " + w.text : w.text);
  }
}

static void loadConfig() {
  std::vector<uint8_t> text;
  bool fromSd = sdOk && readAll(SD, kCfgPath, text, 64 * 1024);
  if (!fromSd && !(fsOk && readAll(LittleFS, kCfgCopy, text, 64 * 1024))) {
    Serial.println("keine tacho.cfg, Standardwerte");
    return;
  }
  std::vector<s51::Config::Warning> warnings;
  cfg.parse(reinterpret_cast<const char*>(text.data()), text.size(), &warnings);
  cfgFound = true;
  warningsToNotes(warnings);
  Serial.printf("tacho.cfg gelesen (%s), %u Hinweise\n", fromSd ? "SD-Karte" : "interne Kopie",
                unsigned(warnings.size()));
  for (const auto& n : cfgNotes) Serial.printf("  %s\n", n.c_str());
  if (!cfgNotes.empty()) notes.push_back("tacho.cfg: " + std::to_string(cfgNotes.size()) + " Hinweise, siehe Menü Einstellungen");
  if (!fromSd) {
    notes.push_back("tacho.cfg aus interner Kopie");
  } else if (fsOk) {
    std::vector<uint8_t> old;
    if (!readAll(LittleFS, kCfgCopy, old, 64 * 1024) || old != text) writeAll(LittleFS, kCfgCopy, text.data(), text.size());
  }
}

static bool endsWithS51(const std::string& n) {
  if (n.size() < 4) return false;
  std::string ext = n.substr(n.size() - 4);
  std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
  return ext == ".s51";
}

// Alle .s51-Dateien im Ordner s51, alphabetisch
static std::vector<std::string> listDesignFiles() {
  std::vector<std::string> out;
  if (!sdOk) return out;
  File dir = SD.open(kDir);
  if (!dir || !dir.isDirectory()) return out;
  for (File f = dir.openNextFile(); f; f = dir.openNextFile()) {
    std::string name = f.name();
    size_t slash = name.find_last_of('/');
    if (slash != std::string::npos) name = name.substr(slash + 1);
    if (!f.isDirectory() && endsWithS51(name) && name[0] != '.') out.push_back(name);
    f.close();
  }
  std::sort(out.begin(), out.end());
  return out;
}

// Liest ein Design: Dateiname im Ordner s51, kIntern oder kBuiltin
static s51::DecodeError readDesign(const std::string& source, s51::LayoutData& out, std::vector<uint8_t>* raw = nullptr) {
  std::vector<uint8_t> data;
  if (source == kBuiltin) {
    data.assign(klarStart, klarEnd);
  } else if (source == kIntern) {
    if (!fsOk || !readAll(LittleFS, kFlashCopy, data, s51::kMaxFileSize)) return s51::DecodeError::TooSmall;
  } else {
    std::string path = std::string(kDir) + "/" + source;
    if (!sdOk || !readAll(SD, path.c_str(), data, s51::kMaxFileSize)) return s51::DecodeError::TooSmall;
  }
  s51::LayoutData tmp;
  s51::DecodeError e = s51::decodeLayout(data.data(), data.size(), tmp);
  if (e == s51::DecodeError::None) {
    out = std::move(tmp);
    if (raw) *raw = std::move(data);
  }
  return e;
}

static void buildPages() {
  pages.clear();
  for (const auto& s : layout.screens) {
    if (s.role == s51::kRolePage) pages.push_back(s.id);
  }
  int wanted = cfg.getInt(s51::CfgKey::AnzeigeStartseite);
  pageIndex = 0;
  for (size_t i = 0; i < pages.size(); i++) {
    if (pages[i] == wanted) pageIndex = i;
  }
}

// Macht ein Design zum angezeigten. Designs von der SD-Karte werden intern gesichert.
static bool useDesign(const std::string& source) {
  s51::LayoutData tmp;
  std::vector<uint8_t> raw;
  s51::DecodeError e = readDesign(source, tmp, &raw);
  if (e != s51::DecodeError::None) {
    Serial.printf("Design „%s“ nicht lesbar: %s\n", source.c_str(), s51::errorText(e));
    return false;
  }
  layout = std::move(tmp);
  renderer.setLayout(&layout);
  currentSource = source;
  buildPages();
  Serial.printf("Design „%s“ (%s), %u Seiten, %u Bilder\n", layout.name.c_str(),
                source.empty() ? "eingebaut" : source.c_str(), unsigned(layout.screens.size()),
                unsigned(layout.images.size()));
  if (source != kBuiltin && source != kIntern && fsOk) {
    std::vector<uint8_t> old;
    if (!readAll(LittleFS, kFlashCopy, old, s51::kMaxFileSize) || old != raw) {
      writeAll(LittleFS, kFlashCopy, raw.data(), raw.size());
    }
  }
  currentRaw = std::move(raw);
  return true;
}

static void rememberDesign(const std::string& source) {
  prefs.putString("design", source.c_str());
  prefs.putString("design_cfg", cfg.getStr(s51::CfgKey::AnzeigeLayoutDatei).c_str());
}

// Startwahl. Die Auswahl am Tacho gilt, solange in der tacho.cfg noch dasselbe
// Standard-Design steht wie beim Auswählen. Wird im Designer ein neuer Standard
// festgelegt, gilt dieser.
static void chooseStartDesign() {
  const std::string cfgDefault = cfg.getStr(s51::CfgKey::AnzeigeLayoutDatei);
  std::string chosen = prefs.getString("design", "\x01").c_str();
  std::string chosenWith = prefs.getString("design_cfg", "").c_str();
  if (chosen != "\x01" && chosenWith == cfgDefault) {
    if (useDesign(chosen)) return;
    notes.push_back("Gewähltes Design „" + chosen + "“ fehlt");
  } else if (chosen != "\x01") {
    Serial.println("neues Standard-Design in der tacho.cfg, Auswahl am Tacho zurückgesetzt");
    prefs.remove("design");
    prefs.remove("design_cfg");
  }
  if (sdOk && useDesign(cfgDefault)) return;
  for (const auto& f : listDesignFiles()) {
    if (useDesign(f)) {
      if (sdOk) notes.push_back("Kein " + cfgDefault + ", stattdessen " + f);
      return;
    }
  }
  if (useDesign(kIntern)) {
    notes.push_back("Design aus interner Kopie");
    return;
  }
  useDesign(kBuiltin);
  notes.push_back("Eingebautes Design „Klar“");
}

// ---------------------------------------------------------------------------
// PIN (nur im internen Speicher, als SHA-256 mit Zufallssalz)
// ---------------------------------------------------------------------------

static void pinHash(const uint8_t salt[16], const std::string& pin, uint8_t out[32]) {
  std::string data(reinterpret_cast<const char*>(salt), 16);
  data += pin;
  const mbedtls_md_info_t* md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md(md, reinterpret_cast<const unsigned char*>(data.data()), data.size(), out);
  for (int i = 0; i < 999; i++) {
    uint8_t tmp[32];
    memcpy(tmp, out, 32);
    mbedtls_md(md, tmp, 32, out);
  }
}

static bool pinSet() { return stored.pin; }

static bool pinCheck(const std::string& pin) {
  if (!stored.pin) return false;
  uint8_t salt[16], want[32], got[32];
  prefs.getBytes("pin_salt", salt, 16);
  prefs.getBytes("pin_hash", want, 32);
  pinHash(salt, pin, got);
  uint8_t diff = 0;
  for (int i = 0; i < 32; i++) diff |= uint8_t(want[i] ^ got[i]);
  return diff == 0;
}

static void pinStore(const std::string& pin) {
  if (pin.empty()) {
    prefs.remove("pin_hash");
    prefs.remove("pin_salt");
    stored.pin = false;
    return;
  }
  uint8_t salt[16], hash[32];
  for (int i = 0; i < 16; i += 4) {
    uint32_t r = esp_random();
    memcpy(salt + i, &r, 4);
  }
  pinHash(salt, pin, hash);
  prefs.putBytes("pin_salt", salt, 16);
  prefs.putBytes("pin_hash", hash, 32);
  stored.pin = true;
}

// ---------------------------------------------------------------------------
// Alarm-Protokoll (LittleFS, eine Zeile je Eintrag, älteste zuerst)
// ---------------------------------------------------------------------------

static std::vector<std::string> readLogFile() {
  std::vector<std::string> lines;
  std::vector<uint8_t> raw;
  if (!fsOk || !readAll(LittleFS, kLogPath, raw, 64 * 1024)) return lines;
  std::string cur;
  for (uint8_t c : raw) {
    if (c == '\n') {
      if (!cur.empty()) lines.push_back(cur);
      cur.clear();
    } else {
      cur += char(c);
    }
  }
  if (!cur.empty()) lines.push_back(cur);
  return lines;
}

static void addLog(const std::string& text) {
  uint32_t min = millis() / 60000;
  char when[80];
  snprintf(when, sizeof(when), "Start %u, %u:%02u h nach dem Einschalten: ", unsigned(bootCount), unsigned(min / 60),
           unsigned(min % 60));
  std::string line = when + text;
  Serial.printf("Protokoll: %s\n", line.c_str());
  std::vector<std::string>& lines = stored.log;
  lines.push_back(line);
  if (lines.size() > kLogMax) lines.erase(lines.begin(), lines.end() - kLogMax);
  if (!fsOk) return;
  std::string all;
  for (const auto& l : lines) all += l + "\n";
  writeAll(LittleFS, kLogPath, reinterpret_cast<const uint8_t*>(all.data()), all.size());
}

// ---------------------------------------------------------------------------
// Alarm, Wartung, Kilometerstand
// ---------------------------------------------------------------------------

// Die Wahl am Tacho gilt, solange alarm.aktiv in der tacho.cfg unverändert ist
static bool alarmArmedNow() {
  bool fromCfg = cfg.getBool(s51::CfgKey::AlarmAktiv);
  if (stored.alarm != 2 && stored.alarmCfg == uint8_t(fromCfg)) return stored.alarm == 1;
  return fromCfg;
}

static float odometerKm() {
  // Zählt ab Phase 4 (GPS). Bis dahin steht hier der gespeicherte Wert, anfangs 0.
  return stored.odoKm;
}

static const s51::CfgKey kMaintKeys[3] = {s51::CfgKey::WartungGetriebeoelKm, s51::CfgKey::WartungZuendkerzeKm,
                                          s51::CfgKey::WartungKetteKm};
static const char* const kMaintNames[3] = {"Getriebeöl", "Zündkerze", "Kette schmieren"};

static std::vector<s51::MaintenanceItem> maintenanceItems() {
  std::vector<s51::MaintenanceItem> items;
  for (int i = 0; i < 3; i++) {
    s51::MaintenanceItem m;
    m.name = kMaintNames[i];
    m.intervalKm = cfg.getInt(kMaintKeys[i]);
    m.lastKm = stored.maintLast[i];
    items.push_back(m);
  }
  return items;
}

static bool lockRequired() {
  return cfg.getInt(s51::CfgKey::AlarmStufe) >= 2 && alarmArmedNow() && pinSet();
}

// ---------------------------------------------------------------------------
// Verbindung der Menüs zum Tacho
// ---------------------------------------------------------------------------

static std::string kb(uint32_t bytes) { return s51::formatNumber(bytes / 1024, 0) + " KB"; }

class TachoHost : public s51::MenuHost {
 public:
  std::string designName() override {
    if (currentSource == kBuiltin) return layout.name + " (eingebaut)";
    return layout.name;
  }
  float odometerKm() override { return ::odometerKm(); }
  std::vector<s51::MaintenanceItem> maintenance() override { return maintenanceItems(); }
  void maintenanceDone(int i) override {
    char key[8];
    snprintf(key, sizeof(key), "wart%d", i);
    prefs.putFloat(key, ::odometerKm());
    stored.maintLast[i] = ::odometerKm();
    Serial.printf("Wartung %s bestätigt bei %.0f km\n", kMaintNames[i], ::odometerKm());
  }
  bool alarmArmed() override { return alarmArmedNow(); }
  void setAlarmArmed(bool on) override {
    stored.alarm = on ? 1 : 0;
    stored.alarmCfg = cfg.getBool(s51::CfgKey::AlarmAktiv) ? 1 : 0;
    prefs.putUChar("alarm", stored.alarm);
    prefs.putUChar("alarm_cfg", stored.alarmCfg);
    addLog(on ? "Alarm am Tacho eingeschaltet" : "Alarm am Tacho ausgeschaltet");
  }
  int securityLevel() override { return cfg.getInt(s51::CfgKey::AlarmStufe); }
  bool hasPin() override { return pinSet(); }
  bool checkPin(const std::string& pin) override { return pinCheck(pin); }
  void setPin(const std::string& pin) override {
    pinStore(pin);
    addLog(pin.empty() ? "PIN entfernt" : "PIN geändert");
  }
  int pinFailures() override { return stored.pinFailures; }
  void setPinFailures(int n) override {
    if (n == stored.pinFailures) return;
    stored.pinFailures = n;
    prefs.putInt("pin_fail", n);
  }
  void alarm(const std::string& reason) override {
    // Alarmton über den Verstärker des Boards folgt in Phase 5
    addLog("Alarm, " + reason);
  }
  void log(const std::string& text) override { addLog(text); }
  std::vector<std::string> alarmLog() override {
    return std::vector<std::string>(stored.log.rbegin(), stored.log.rend());
  }
  void clearAlarmLog() override {
    stored.log.clear();
    if (fsOk) LittleFS.remove(kLogPath);
  }
  bool nfcReader() override { return nfcFound; }
  bool configFound() override { return cfgFound; }
  std::vector<std::string> configNotes() override { return cfgNotes; }
  std::vector<std::pair<std::string, std::string>> about() override {
    std::vector<std::pair<std::string, std::string>> r;
    r.push_back({"Firmware", FW_VERSION});
    r.push_back({"Layout-Format", "bis " + std::to_string(s51::kVersionMajor) + "." + std::to_string(s51::kVersionMinor)});
    std::string file = currentSource == kBuiltin ? "eingebaut" : currentSource == kIntern ? "interne Kopie" : currentSource;
    r.push_back({"Design", layout.name + " (" + file + ")"});
    if (sdOk) {
      double gb = SD.cardSize() / 1e9;
      r.push_back({"SD-Karte", "gefunden, " + s51::formatNumber(gb, 1) + " GB"});
    } else {
      r.push_back({"SD-Karte", "keine"});
    }
    r.push_back({"tacho.cfg", !cfgFound ? "fehlt, Standardwerte"
                              : cfgNotes.empty() ? "gelesen"
                                                 : "gelesen, " + std::to_string(cfgNotes.size()) + " Hinweise"});
    r.push_back({"Speicher frei", kb(ESP.getFreePsram()) + " PSRAM, " + kb(ESP.getFreeHeap()) + " RAM"});
    r.push_back({"PIN", pinSet() ? "festgelegt" : "keine"});
    r.push_back({"NFC-Leser", nfcFound ? "gefunden" : "nicht angeschlossen"});
    r.push_back({"Starts", std::to_string(bootCount)});
    uint32_t min = millis() / 60000;
    char buf[16];
    snprintf(buf, sizeof(buf), "%u:%02u h", unsigned(min / 60), unsigned(min % 60));
    r.push_back({"Laufzeit", buf});
    return r;
  }
  void transferOpen(bool open) override {
    if (!open) {
      ::transfer::close();
      return;
    }
    ::transfer::Settings s;
    s.hotspot = cfg.getStr(s51::CfgKey::WlanModus) != "heimnetz";
    s.ssid = cfg.getStr(s51::CfgKey::WlanSsid);
    s.password = cfg.getStr(s51::CfgKey::WlanPasswort);
    s.hostname = cfg.getStr(s51::CfgKey::WlanHostname);
    ::transfer::open(s);
  }
  s51::TransferInfo transfer() override { return ::transfer::info(); }
};

static TachoHost host;
static s51::Menu menu(host);

// ---------------------------------------------------------------------------
// Anfragen vom Designer (docs/uebertragung.md), bearbeitet in loop()
// ---------------------------------------------------------------------------

static std::string crcHex(const std::vector<uint8_t>& data) {
  char buf[12];
  snprintf(buf, sizeof(buf), "%08x", unsigned(s51::crc32(data.data(), data.size())));
  return buf;
}

static bool validUtf8(const std::string& s) {
  for (size_t i = 0; i < s.size();) {
    unsigned char c = s[i];
    int n = c < 0x80 ? 0 : (c >> 5) == 6 ? 1 : (c >> 4) == 14 ? 2 : (c >> 3) == 30 ? 3 : -1;
    if (n < 0 || i + n >= s.size()) return false;
    for (int k = 1; k <= n; k++) {
      if ((static_cast<unsigned char>(s[i + k]) & 0xC0) != 0x80) return false;
    }
    i += n + 1;
  }
  return true;
}

static void applyBrightness();

static void reply(transfer::Request& r, int status, const std::string& json) {
  r.status = status;
  r.type = "application/json; charset=utf-8";
  r.answer = json;
}

static void replyError(transfer::Request& r, int status, const std::string& text) {
  reply(r, status, "{\"ok\": false, \"fehler\": " + transfer::jsonString(text) + "}");
}

static void onTransfer(transfer::Request& r) {
  using K = transfer::Request::Kind;
  switch (r.kind) {
    case K::Info: {
      bool hasCfg = (sdOk && SD.exists(kCfgPath)) || (fsOk && LittleFS.exists(kCfgCopy));
      std::string l = currentRaw.empty() ? "null"
                                         : "{\"crc32\": \"" + crcHex(currentRaw) + "\", \"groesse\": " +
                                               std::to_string(currentRaw.size()) + "}";
      reply(r, 200,
            "{\"geraet\": \"S51-Tacho\", \"firmware\": \"" FW_VERSION "\", \"format\": \"" +
                std::to_string(s51::kVersionMajor) + "." + std::to_string(s51::kVersionMinor) + "\", \"layout\": " +
                l + ", \"config\": " + (hasCfg ? "true" : "false") + ", \"uebertragung_offen\": " +
                (transfer::isOpen() ? "true" : "false") + "}");
      break;
    }
    case K::GetLayout:
      if (currentRaw.empty()) {
        replyError(r, 404, "Kein Layout gespeichert");
        break;
      }
      r.status = 200;
      r.type = "application/octet-stream";
      r.answer.assign(currentRaw.begin(), currentRaw.end());
      break;
    case K::PutLayout: {
      s51::LayoutData tmp;
      auto* data = reinterpret_cast<const uint8_t*>(r.body.data());
      s51::DecodeError e = s51::decodeLayout(data, r.body.size(), tmp);
      if (e != s51::DecodeError::None) {
        replyError(r, 400, s51::errorText(e));
        break;
      }
      std::string file = s51::designFileName(tmp.name);
      std::string source;
      if (sdOk) {
        if (!SD.exists(kDir)) SD.mkdir(kDir);
        std::string path = std::string(kDir) + "/" + file;
        if (!writeAll(SD, path.c_str(), data, r.body.size())) {
          replyError(r, 500, "Schreiben auf die SD-Karte fehlgeschlagen");
          break;
        }
        source = file;
      } else {
        if (!fsOk || !writeAll(LittleFS, kFlashCopy, data, r.body.size())) {
          replyError(r, 500, "Keine SD-Karte und interner Speicher nicht beschreibbar");
          break;
        }
        source = kIntern;
      }
      if (!useDesign(source)) {
        replyError(r, 500, "Gespeichert, aber nicht wieder lesbar");
        break;
      }
      rememberDesign(source);
      pageChangedAt = millis();
      transfer::setMessage("Design „" + tmp.name + "“ empfangen");
      reply(r, 200, "{\"ok\": true, \"crc32\": \"" + crcHex(currentRaw) + "\", \"datei\": " +
                        transfer::jsonString(sdOk ? file : "interne Kopie") + "}");
      break;
    }
    case K::GetConfig: {
      std::vector<uint8_t> text;
      if (!(sdOk && readAll(SD, kCfgPath, text, 64 * 1024)) && !(fsOk && readAll(LittleFS, kCfgCopy, text, 64 * 1024))) {
        replyError(r, 404, "tacho.cfg nicht vorhanden");
        break;
      }
      r.status = 200;
      r.type = "text/plain; charset=utf-8";
      r.answer.assign(text.begin(), text.end());
      break;
    }
    case K::PutConfig: {
      if (!validUtf8(r.body)) {
        replyError(r, 400, "Konfiguration ist kein UTF-8-Text");
        break;
      }
      if (r.body.size() > 64 * 1024) {
        replyError(r, 413, "tacho.cfg größer als 64 KB");
        break;
      }
      auto* data = reinterpret_cast<const uint8_t*>(r.body.data());
      bool saved = false;
      if (sdOk) {
        if (!SD.exists(kDir)) SD.mkdir(kDir);
        saved = writeAll(SD, kCfgPath, data, r.body.size());
      }
      if (fsOk) saved = writeAll(LittleFS, kCfgCopy, data, r.body.size()) || saved;
      if (!saved) {
        replyError(r, 500, "tacho.cfg ließ sich nicht speichern");
        break;
      }
      s51::Config fresh;
      std::vector<s51::Config::Warning> warnings;
      fresh.parse(r.body.data(), r.body.size(), &warnings);
      cfg = fresh;
      cfgFound = true;
      warningsToNotes(warnings);
      applyBrightness();
      transfer::setMessage("Einstellungen empfangen" +
                           (cfgNotes.empty() ? std::string() : ", " + std::to_string(cfgNotes.size()) + " Hinweise"));
      std::string list = "[";
      for (size_t i = 0; i < cfgNotes.size(); i++) list += (i ? ", " : "") + transfer::jsonString(cfgNotes[i]);
      reply(r, 200, "{\"ok\": true, \"warnungen\": " + list + "]}");
      break;
    }
  }
}

// ---------------------------------------------------------------------------
// Design-Auswahl
// ---------------------------------------------------------------------------

static std::vector<std::string> pickerSources;

static s51::DesignEntry describe(const std::string& source) {
  s51::DesignEntry e;
  e.file = source == kIntern ? "interne Kopie" : source;
  s51::LayoutData tmp;
  s51::DecodeError err = readDesign(source, tmp);
  if (err != s51::DecodeError::None) {
    e.ok = false;
    e.error = s51::errorText(err);
    return e;
  }
  e.name = tmp.name;
  e.author = tmp.author;
  for (const auto& s : tmp.screens) {
    if (s.role == s51::kRolePage) e.pages++;
    if (s.role == s51::kRoleNight) e.hasNight = true;
    if (s.role == s51::kRoleStartup) e.hasStartup = true;
  }
  if (source == kBuiltin) e.name = tmp.name + " (eingebaut)";
  return e;
}

static void renderPreview() {
  previewOk = false;
  int i = picker.highlighted();
  if (i < 0 || i >= int(pickerSources.size())) return;
  if (readDesign(pickerSources[i], previewLayout) != s51::DecodeError::None) return;
  const s51::ScreenData* s = nullptr;
  for (const auto& sc : previewLayout.screens) {
    if (sc.role == s51::kRolePage) {
      s = &sc;
      break;
    }
  }
  if (!s && !previewLayout.screens.empty()) s = &previewLayout.screens[0];
  if (!s || !previewSprite.getBuffer()) return;
  renderer.setLayout(&previewLayout);
  renderer.drawScreen(previewSprite, *s, values, millis());
  renderer.setLayout(&layout);     // Bild-Zwischenspeicher des angezeigten Designs neu füllen
  previewLayout = s51::LayoutData();
  previewOk = true;
}

static void openPicker() {
  pickerSources.clear();
  std::vector<s51::DesignEntry> list;
  for (const auto& f : listDesignFiles()) pickerSources.push_back(f);
  if (!sdOk && fsOk && LittleFS.exists(kFlashCopy)) pickerSources.push_back(kIntern);
  if (currentSource == kIntern &&
      std::find(pickerSources.begin(), pickerSources.end(), std::string(kIntern)) == pickerSources.end()) {
    pickerSources.push_back(kIntern);
  }
  pickerSources.push_back(kBuiltin);
  int active = 0;
  for (size_t i = 0; i < pickerSources.size(); i++) {
    list.push_back(describe(pickerSources[i]));
    if (pickerSources[i] == currentSource) active = i;
  }
  if (!previewSprite.getBuffer()) {
    previewSprite.setColorDepth(16);
    previewSprite.setPsram(true);
    previewSprite.createSprite(canvas.width(), canvas.height());
  }
  picker.open(list, active);
  renderPreview();
  Serial.printf("Design-Auswahl, %u Designs\n", unsigned(list.size()));
}

static void closePicker() {
  picker.close();
  previewSprite.deleteSprite();
  previewOk = false;
}

static void applyPicked() {
  const std::string& source = pickerSources[picker.active()];
  if (useDesign(source)) {
    rememberDesign(source);
    pageChangedAt = millis();
  }
  closePicker();
}

// ---------------------------------------------------------------------------
// Anzeige
// ---------------------------------------------------------------------------

static bool nightMode() {
  // „auto“ braucht Lichtsensor oder Lichtschalter (Phase 3), bis dahin wie „aus“
  return cfg.getStr(s51::CfgKey::AnzeigeNachtmodus) == "an";
}

static void applyBrightness() {
  int pct = cfg.getInt(nightMode() ? s51::CfgKey::AnzeigeHelligkeitNacht : s51::CfgKey::AnzeigeHelligkeitTag);
  tft.setBrightness(static_cast<uint8_t>(pct * 255 / 100));
}

static void updateValues() {
  s51::demoValues(values, millis() / 1000.0f, true);
  values.timeValid = false;   // Uhrzeit kommt später von GPS oder iPhone (Phase 4)
  // Schon echt: Alarm scharf und Kilometer bis zur nächsten Wartung
  values.setFlag(s51::Source::AlarmArmed, alarmArmedNow());
  float odo = odometerKm(), best = 0;
  bool any = false;
  for (const auto& m : maintenanceItems()) {
    if (m.intervalKm <= 0) continue;
    float left = m.intervalKm - (odo - m.lastKm);
    if (!any || left < best) best = left;
    any = true;
  }
  if (any) {
    values.set(s51::Source::ServiceKm, std::max(0.0f, best));
  } else {
    values.unset(s51::Source::ServiceKm);
  }
}

static void drawNotes() {
  if (notes.empty() || millis() > notesUntil) return;
  int h = 22 * notes.size() + 8;
  canvas.fillRect(0, canvas.height() - h, canvas.width(), h, tft.color565(30, 30, 28));
  for (size_t i = 0; i < notes.size(); i++) {
    renderer.drawLabel(canvas, notes[i], 10, canvas.height() - h + 4 + 22 * i, canvas.width() - 20, 22,
                       s51::Font::Sans, 14, kText, s51::Align::Left);
  }
}

static void drawPageDots() {
  if (pages.size() < 2 || millis() - pageChangedAt > 1500) return;
  int n = pages.size(), gap = 16, x0 = canvas.width() / 2 - (n - 1) * gap / 2, y = canvas.height() - 10;
  for (int i = 0; i < n; i++) {
    canvas.fillSmoothCircle(x0 + i * gap, y, 4, size_t(i) == pageIndex ? kGreen.to565() : kDim.to565());
  }
}

static void showStartup() {
  int seconds = cfg.getInt(s51::CfgKey::AnzeigeStartbildDauerS);
  if (seconds <= 0) return;
  const s51::ScreenData* start = layout.startupScreen();
  const std::string& text = cfg.getStr(s51::CfgKey::AnzeigeStartbildText);
  if (!start && text.empty()) return;
  uint32_t until = millis() + seconds * 1000u;
  while (millis() < until) {
    updateValues();
    if (start) {
      renderer.drawScreen(canvas, *start, values, millis());
    } else {
      canvas.fillScreen(TFT_BLACK);
      renderer.drawLabel(canvas, text, 0, 0, canvas.width(), canvas.height() - 30, s51::Font::SansBold, 48, kText);
    }
    renderer.drawLabel(canvas, "Firmware " FW_VERSION, 0, canvas.height() - 24, canvas.width() - 8, 20,
                       s51::Font::Sans, 11, kDim, s51::Align::Right);
    canvas.pushSprite(0, 0);
    delay(30);
  }
}

static void nextPage(int dir) {
  if (pages.size() < 2) return;
  pageIndex = (pageIndex + pages.size() + dir) % pages.size();
  pageChangedAt = millis();
  Serial.printf("Seite %u\n", unsigned(pages[pageIndex]));
}

// Wischen oder Tippen an den Rand wechselt die Seite, lange drücken öffnet das Menü
static void handleTouch() {
  static bool down = false, consumed = false;
  static int32_t startX = 0, startY = 0, lastX = 0, lastY = 0;
  static uint32_t downAt = 0;
  lgfx::touch_point_t tp;
  if (tft.getTouch(&tp)) {
    if (!down) {
      startX = tp.x;
      startY = tp.y;
      downAt = millis();
      consumed = false;
    }
    lastX = tp.x;
    lastY = tp.y;
    down = true;
    bool still = abs(lastX - startX) < 15 && abs(lastY - startY) < 15;
    if (menu.isOpen()) menu.pointer(still ? startX : -1, still ? startY : -1, true);
    if (!consumed && !menu.isOpen() && !picker.isOpen() && still && millis() - downAt > 900) {
      consumed = true;
      menu.open();
    }
    return;
  }
  if (!down) return;
  down = false;
  menu.pointer(-1, -1, false);
  if (consumed) return;
  int dx = lastX - startX, dy = lastY - startY;
  if (menu.isOpen()) {
    if (abs(dy) > 25 && abs(dy) > abs(dx)) {
      menu.scroll(dy);
      return;
    }
    if (abs(dx) > 25 || abs(dy) > 25) return;
    switch (menu.tap(startX, startY, millis())) {
      case s51::Menu::Request::OpenPicker: openPicker(); break;
      case s51::Menu::Request::Unlocked:
        Serial.println("entsperrt");
        pageChangedAt = millis();
        notesUntil = millis() + 6000;
        break;
      default: break;
    }
    return;
  }
  if (picker.isOpen()) {
    if (abs(dy) > 25 && startX < 232) {
      picker.scroll(dy);
      return;
    }
    switch (picker.tap(lastX, lastY)) {
      case s51::Picker::Action::Highlight: renderPreview(); break;
      case s51::Picker::Action::Apply: applyPicked(); break;
      case s51::Picker::Action::Close: closePicker(); break;
      default: break;
    }
    return;
  }
  if (dx < -50) {
    nextPage(1);
  } else if (dx > 50) {
    nextPage(-1);
  } else if (lastX > canvas.width() * 2 / 3) {
    nextPage(1);
  } else if (lastX < canvas.width() / 3) {
    nextPage(-1);
  }
}

// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("S51-Tacho Firmware " FW_VERSION " (Phase 2)");

  tft.init();
  tft.setRotation(1);          // Querformat 480 x 320
  tft.setBrightness(200);
  tft.fillScreen(TFT_BLACK);
  canvas.setColorDepth(16);
  canvas.setPsram(true);       // 480 x 320 x 2 Byte = 300 KB im PSRAM
  if (!canvas.createSprite(tft.width(), tft.height())) {
    Serial.println("Sprite konnte nicht angelegt werden (PSRAM aktiv?)");
  }
  if (!renderer.begin(fontsStart, fontsEnd - fontsStart)) {
    Serial.println("Schriften ungültig");
  }

  sdSpi.begin(PIN_SD_CLK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  sdOk = SD.begin(PIN_SD_CS, sdSpi, 20000000);
  Serial.println(sdOk ? "SD-Karte gefunden" : "keine SD-Karte");
  if (!sdOk) notes.push_back("Keine SD-Karte");
  fsOk = LittleFS.begin(true);
  prefs.begin("s51", false);
  bootCount = prefs.getUInt("boots", 0) + 1;
  prefs.putUInt("boots", bootCount);
  stored.pin = prefs.getBytesLength("pin_hash") == 32 && prefs.getBytesLength("pin_salt") == 16;
  stored.alarm = prefs.getUChar("alarm", 2);
  stored.alarmCfg = prefs.getUChar("alarm_cfg", 2);
  stored.pinFailures = prefs.getInt("pin_fail", 0);
  stored.odoKm = prefs.getUInt("odo_m", 0) / 1000.0f;   // zählt ab Phase 4 (GPS)
  for (int i = 0; i < 3; i++) {
    char key[8];
    snprintf(key, sizeof(key), "wart%d", i);
    stored.maintLast[i] = prefs.getFloat(key, 0.0f);
  }
  stored.log = readLogFile();

  // Externer I²C-Bus: nur nachsehen, ob ein NFC-Leser antwortet (Module folgen in Phase 3)
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
  Wire.beginTransmission(I2C_ADDR_PN532);
  nfcFound = Wire.endTransmission() == 0;

  loadConfig();
  chooseStartDesign();
  for (const auto& m : maintenanceItems()) {
    if (m.intervalKm > 0 && m.intervalKm - (odometerKm() - m.lastKm) <= 0) notes.push_back("Wartung fällig: " + m.name);
  }
  if (cfg.getInt(s51::CfgKey::AlarmStufe) >= 2 && alarmArmedNow() && !pinSet()) {
    notes.push_back("Sicherheitsstufe 2 ohne PIN: im Menü Alarm festlegen");
  }
  if (bootCount <= 5) notes.push_back("Lange drücken: Menü");
  applyBrightness();
  showStartup();
  if (lockRequired()) {
    menu.lock(millis(), cfg.getInt(s51::CfgKey::AlarmEntsperrzeitS));
    Serial.println("gesperrt, warte auf PIN");
  }
  pageChangedAt = millis();
  notesUntil = millis() + 6000;
}

void loop() {
  handleTouch();
  transfer::poll(onTransfer);
  updateValues();
  uint32_t now = millis();
  if (menu.isOpen()) {
    menu.tick(now);
    menu.draw(canvas, renderer, now);
  } else if (picker.isOpen()) {
    picker.draw(canvas, renderer, previewOk ? &previewSprite : nullptr);
  } else if (!pages.empty()) {
    const s51::ScreenData* s = layout.screenFor(pages[pageIndex], nightMode());
    if (s) renderer.drawScreen(canvas, *s, values, millis());
    drawNotes();
    drawPageDots();
  } else {
    canvas.fillScreen(TFT_BLACK);
    renderer.drawLabel(canvas, "Das Layout hat keine Fahrseite. Lange drücken: Menü", 20, 0, canvas.width() - 40,
                       canvas.height(), s51::Font::SansBold, 20, kText);
  }
  canvas.pushSprite(0, 0);
  delay(10);
}
