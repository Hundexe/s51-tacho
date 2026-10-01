// S51-Tacho – Phase 2: Layouts aus dem S51 Designer anzeigen
//
// Ablauf beim Start (docs/dateiformat-layout.md, Abschnitt 7):
//   1. tacho.cfg von der SD-Karte lesen (fehlt sie: Standardwerte)
//   2. Layout von der SD-Karte lesen und intern sichern. Fehlt es oder ist es
//      beschädigt: interne Kopie, sonst das eingebaute Layout „Klar“
//   3. Startbild-Seite zeigen (oder startbild_text), danach die Fahrseiten
//
// Bedienung: Wischen nach links/rechts oder Tippen an den linken/rechten Rand
// wechselt die Seite. Sensoren gibt es noch nicht, alle Werte sind Demo-Werte
// wie in der Vorschau des Designers.

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>
#include <SD.h>
#include <SPI.h>

#include <string>
#include <vector>

#include "lgfx_sc01plus.h"
#include "pins.h"
#include "s51_config.h"
#include "s51_layout.h"
#include "s51_render.h"
#include "s51_values.h"
#include "version.h"

// Eingebettete Dateien (platformio.ini: board_build.embed_files)
extern const uint8_t fontsStart[] asm("_binary_data_s51fonts_bin_start");
extern const uint8_t fontsEnd[] asm("_binary_data_s51fonts_bin_end");
extern const uint8_t klarStart[] asm("_binary_data_klar_s51_start");
extern const uint8_t klarEnd[] asm("_binary_data_klar_s51_end");

static LGFX_SC01Plus tft;
static LGFX_Sprite canvas(&tft);
static SPIClass sdSpi(HSPI);
static s51::Renderer renderer;
static s51::Config cfg;
static s51::LayoutData layout;
static s51::Values values;

static std::vector<std::string> notes;     // Hinweise für die Infozeile beim Start
static std::vector<uint8_t> pages;         // Nummern der Tagseiten in Reihenfolge
static size_t pageIndex = 0;
static uint32_t pageChangedAt = 0;
static bool sdOk = false;

constexpr const char* kFlashCopy = "/layout.s51";
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

static void loadConfig() {
  std::vector<uint8_t> text;
  if (sdOk && readAll(SD, "/s51/tacho.cfg", text, 64 * 1024)) {
    std::vector<s51::Config::Warning> warnings;
    cfg.parse(reinterpret_cast<const char*>(text.data()), text.size(), &warnings);
    Serial.printf("tacho.cfg gelesen, %u Hinweise\n", unsigned(warnings.size()));
    for (const auto& w : warnings) Serial.printf("  Zeile %d: %s\n", w.line, w.text.c_str());
    if (!warnings.empty()) notes.push_back("tacho.cfg: " + std::to_string(warnings.size()) + " Hinweise, siehe serielle Ausgabe");
  } else {
    Serial.println("keine tacho.cfg, Standardwerte");
  }
}

static bool tryDecode(const std::vector<uint8_t>& data, const char* what) {
  s51::LayoutData tmp;
  s51::DecodeError e = s51::decodeLayout(data.data(), data.size(), tmp);
  if (e != s51::DecodeError::None) {
    Serial.printf("%s ungültig: %s\n", what, s51::errorText(e));
    notes.push_back(std::string(what) + " ungültig: " + s51::errorText(e));
    return false;
  }
  layout = std::move(tmp);
  Serial.printf("Layout „%s“ aus %s, %u Seiten, %u Bilder\n", layout.name.c_str(), what,
                unsigned(layout.screens.size()), unsigned(layout.images.size()));
  return true;
}

static void loadLayout() {
  std::vector<uint8_t> data;
  std::string sdPath = "/s51/" + cfg.getStr(s51::CfgKey::AnzeigeLayoutDatei);
  bool haveFs = LittleFS.begin(true);

  if (sdOk && readAll(SD, sdPath.c_str(), data, s51::kMaxFileSize)) {
    if (tryDecode(data, "SD-Karte")) {
      // Interne Kopie aktualisieren, wenn sie fehlt oder anders ist
      std::vector<uint8_t> old;
      if (haveFs && (!readAll(LittleFS, kFlashCopy, old, s51::kMaxFileSize) || old != data)) {
        File f = LittleFS.open(kFlashCopy, "w");
        if (f) {
          f.write(data.data(), data.size());
          f.close();
          Serial.println("Layout intern gesichert");
        }
      }
      return;
    }
  } else if (sdOk) {
    notes.push_back("Keine Datei " + sdPath + " auf der SD-Karte");
  }

  if (haveFs && readAll(LittleFS, kFlashCopy, data, s51::kMaxFileSize) && tryDecode(data, "interner Kopie")) {
    notes.push_back("Layout aus interner Kopie");
    return;
  }

  std::vector<uint8_t> klar(klarStart, klarEnd);
  tryDecode(klar, "eingebautem Layout");
  notes.push_back("Eingebautes Layout „Klar“");
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
}

static void drawNotes() {
  if (notes.empty()) return;
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

static void nextPage(int dir) {
  if (pages.size() < 2) return;
  pageIndex = (pageIndex + pages.size() + dir) % pages.size();
  pageChangedAt = millis();
  Serial.printf("Seite %u\n", unsigned(pages[pageIndex]));
}

// Wischen oder Tippen an den Rand wechselt die Seite
static void handleTouch() {
  static bool down = false;
  static int32_t startX = 0, lastX = 0;
  lgfx::touch_point_t tp;
  bool now = tft.getTouch(&tp);
  if (now) {
    if (!down) startX = tp.x;
    lastX = tp.x;
    down = true;
    return;
  }
  if (!down) return;
  down = false;
  int dx = lastX - startX;
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

  loadConfig();
  loadLayout();
  renderer.setLayout(&layout);
  buildPages();
  applyBrightness();
  showStartup();
  pageChangedAt = millis();
}

void loop() {
  static uint32_t notesUntil = millis() + 6000;
  handleTouch();
  updateValues();
  if (!pages.empty()) {
    const s51::ScreenData* s = layout.screenFor(pages[pageIndex], nightMode());
    if (s) renderer.drawScreen(canvas, *s, values, millis());
  } else {
    canvas.fillScreen(TFT_BLACK);
    renderer.drawLabel(canvas, "Das Layout hat keine Fahrseite", 0, 0, canvas.width(), canvas.height(),
                       s51::Font::SansBold, 20, kText);
  }
  if (millis() < notesUntil) drawNotes();
  drawPageDots();
  canvas.pushSprite(0, 0);
  delay(10);
}
