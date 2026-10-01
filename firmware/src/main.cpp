// S51-Tacho – Phase 2: Layouts aus dem S51 Designer anzeigen
//
// Ablauf beim Start (docs/dateiformat-layout.md, Abschnitt 7):
//   1. tacho.cfg von der SD-Karte lesen (fehlt sie: Standardwerte)
//   2. Design wählen: am Tacho ausgewähltes Design, sonst das Standard-Design aus
//      der tacho.cfg (layout_datei), sonst das erste .s51 im Ordner s51, sonst die
//      interne Kopie, sonst das eingebaute Layout „Klar“
//   3. Startbild-Seite zeigen (oder startbild_text), danach die Fahrseiten
//
// Bedienung: Wischen nach links/rechts oder Tippen an den linken/rechten Rand
// wechselt die Seite. Lange drücken öffnet die Design-Auswahl.
// Sensoren gibt es noch nicht, alle Werte sind Demo-Werte wie im Designer.

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <SD.h>
#include <SPI.h>

#include <algorithm>
#include <string>
#include <vector>

#include "lgfx_sc01plus.h"
#include "pins.h"
#include "s51_config.h"
#include "s51_layout.h"
#include "s51_picker.h"
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
static std::vector<uint8_t> pages;          // Nummern der Tagseiten in Reihenfolge
static size_t pageIndex = 0;
static uint32_t pageChangedAt = 0;
static uint32_t notesUntil = 0;
static bool sdOk = false;
static bool fsOk = false;
static std::string currentSource;           // Datei im Ordner s51, kIntern oder kBuiltin

constexpr const char* kFlashCopy = "/layout.s51";
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
      File f = LittleFS.open(kFlashCopy, "w");
      if (f) {
        f.write(raw.data(), raw.size());
        f.close();
      }
    }
  }
  return true;
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
    prefs.putString("design", source.c_str());
    prefs.putString("design_cfg", cfg.getStr(s51::CfgKey::AnzeigeLayoutDatei).c_str());
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

// Wischen oder Tippen an den Rand wechselt die Seite, lange drücken öffnet die Auswahl
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
    if (!consumed && !picker.isOpen() && still && millis() - downAt > 900) {
      consumed = true;
      openPicker();
    }
    return;
  }
  if (!down) return;
  down = false;
  if (consumed) return;
  int dx = lastX - startX, dy = lastY - startY;
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

  loadConfig();
  chooseStartDesign();
  if (listDesignFiles().size() > 1) notes.push_back("Lange drücken: Design wählen");
  applyBrightness();
  showStartup();
  pageChangedAt = millis();
  notesUntil = millis() + 6000;
}

void loop() {
  handleTouch();
  updateValues();
  if (picker.isOpen()) {
    picker.draw(canvas, renderer, previewOk ? &previewSprite : nullptr);
  } else if (!pages.empty()) {
    const s51::ScreenData* s = layout.screenFor(pages[pageIndex], nightMode());
    if (s) renderer.drawScreen(canvas, *s, values, millis());
    drawNotes();
    drawPageDots();
  } else {
    canvas.fillScreen(TFT_BLACK);
    renderer.drawLabel(canvas, "Das Layout hat keine Fahrseite. Lange drücken: Design wählen", 20, 0,
                       canvas.width() - 40, canvas.height(), s51::Font::SansBold, 20, kText);
  }
  canvas.pushSprite(0, 0);
  delay(10);
}
