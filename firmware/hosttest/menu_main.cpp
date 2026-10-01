// Prüft die eingebauten Menüs der Firmware am PC und zeichnet jede Seite.
// Aufruf: menu <s51fonts.bin> <Zielordner>
//
// Spielt die Abläufe mit Antippen durch (PIN festlegen, sperren, falsche PIN,
// Wartung bestätigen, Protokoll leeren) und prüft das Ergebnis. Endet mit
// Code 1, wenn etwas nicht stimmt. Bilder: menue-*.ppm im Zielordner.

#include <cstdio>
#include <string>
#include <vector>

#include "s51_menu.h"

static int failures = 0;
#define CHECK(cond)                                                    \
  do {                                                                 \
    if (!(cond)) {                                                     \
      fprintf(stderr, "Fehler Zeile %d: %s\n", __LINE__, #cond);      \
      failures++;                                                      \
    }                                                                  \
  } while (0)

static bool readFile(const char* path, std::vector<uint8_t>& out) {
  FILE* f = fopen(path, "rb");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  out.resize(n);
  bool ok = fread(out.data(), 1, n, f) == static_cast<size_t>(n);
  fclose(f);
  return ok;
}

static void writePpm(LGFX_Sprite& g, const std::string& path) {
  FILE* o = fopen(path.c_str(), "wb");
  if (!o) return;
  fprintf(o, "P6\n%d %d\n255\n", g.width(), g.height());
  for (int y = 0; y < g.height(); y++) {
    for (int x = 0; x < g.width(); x++) {
      uint16_t c = g.readPixel(x, y);
      uint8_t px[3] = {uint8_t((c >> 11) << 3 | (c >> 13)), uint8_t(((c >> 5) & 63) << 2 | ((c >> 9) & 3)),
                       uint8_t((c & 31) << 3 | ((c >> 2) & 7))};
      fwrite(px, 1, 3, o);
    }
  }
  fclose(o);
  printf("%s\n", path.c_str());
}

// Simulierter Tacho: hält alles im Speicher
struct FakeHost : s51::MenuHost {
  std::string pin;
  int failures = 0;
  bool armed = true;
  int level = 2;
  float odo = 1240;
  std::vector<s51::MaintenanceItem> items = {{"Getriebeöl", 3000, 0}, {"Zündkerze", 1000, 0}, {"Kette", 0, 0}};
  std::vector<std::string> logEntries;
  std::vector<std::string> notes;
  int alarms = 0;
  bool transferIsOpen = false;
  s51::TransferInfo info;
  s51::BluetoothInfo bt;
  int playPresses = 0;

  std::string designName() override { return "Klar"; }
  float odometerKm() override { return odo; }
  std::vector<s51::MaintenanceItem> maintenance() override { return items; }
  void maintenanceDone(int i) override { items[i].lastKm = odo; }
  bool alarmArmed() override { return armed; }
  void setAlarmArmed(bool on) override { armed = on; }
  int securityLevel() override { return level; }
  bool hasPin() override { return !pin.empty(); }
  bool checkPin(const std::string& p) override { return !pin.empty() && p == pin; }
  void setPin(const std::string& p) override { pin = p; }
  int pinFailures() override { return failures; }
  void setPinFailures(int n) override { failures = n; }
  void alarm(const std::string& reason) override {
    alarms++;
    log("Alarm: " + reason);
  }
  void log(const std::string& text) override {
    logEntries.insert(logEntries.begin(), "Start 7, " + std::to_string(3 + logEntries.size()) + " min: " + text);
  }
  std::vector<std::string> alarmLog() override { return logEntries; }
  void clearAlarmLog() override { logEntries.clear(); }
  bool nfcReader() override { return false; }
  bool configFound() override { return true; }
  std::vector<std::string> configNotes() override { return notes; }
  std::vector<std::pair<std::string, std::string>> about() override {
    return {{"Firmware", "0.5.0"},           {"Layout-Format", "bis 1.2"},
            {"Design", "Klar (klar.s51)"},   {"SD-Karte", "gefunden, 29,7 GB"},
            {"tacho.cfg", "gelesen, 2 Hinweise"}, {"Speicher frei", "7.912 KB PSRAM, 182 KB RAM"},
            {"Starts", "7"},                 {"Laufzeit", "0:03 h"},
            {"Gerät", "WT32-SC01 Plus"}};
  }
  s51::BluetoothInfo bluetooth() override { return bt; }
  void mediaPlayPause() override {
    playPresses++;
    bt.playing = !bt.playing;
  }
  void forgetBluetooth() override {
    bt.bonded = 0;
    bt.connected = false;
  }
  void transferOpen(bool open) override { transferIsOpen = open; }
  s51::TransferInfo transfer() override { return info; }
};

// Mitte der Taste: 0 … 9, 10 = löschen, 11 = OK
static void key(s51::Menu& m, LGFX_Sprite& g, s51::Renderer& r, int k, uint32_t now) {
  int i = k == 0 ? 10 : k == 10 ? 9 : k == 11 ? 11 : k - 1;
  m.draw(g, r, now);
  m.tap(240 + (i % 3) * 80 + 36, 60 + (i / 3) * 64 + 29, now);
}

static s51::Menu::Request typePin(s51::Menu& m, LGFX_Sprite& g, s51::Renderer& r, const std::string& pin,
                                  uint32_t now) {
  for (char c : pin) key(m, g, r, c - '0', now);
  m.draw(g, r, now);
  return m.tap(240 + 2 * 80 + 36, 60 + 3 * 64 + 29, now);
}

static s51::Menu::Request tapAt(s51::Menu& m, LGFX_Sprite& g, s51::Renderer& r, int x, int y, uint32_t now) {
  m.draw(g, r, now);
  return m.tap(x, y, now);
}

int main(int argc, char** argv) {
  if (argc < 3) return 2;
  std::vector<uint8_t> fonts;
  if (!readFile(argv[1], fonts)) return 1;
  s51::Renderer r;
  if (!r.begin(fonts.data(), fonts.size())) return 1;
  const std::string out = argv[2];
  LGFX_Sprite g;
  g.setColorDepth(16);
  g.createSprite(480, 320);

  FakeHost host;
  host.notes = {"Zeile 4: fahrzeug.magnete: 99 liegt außerhalb von 1–8. Standard 2 wird verwendet",
                "Zeile 12: unbekannter Schlüssel anzeige.farbe"};
  s51::Menu m(host);
  uint32_t t = 1000;

  // Hauptmenü
  m.open();
  CHECK(m.page() == s51::Menu::Page::Main);

  // Wartung: Zündkerze ist fällig (1240 km bei 1000 km Abstand)
  tapAt(m, g, r, 240, 120, t);   // Kachel Wartung (Mitte oben)
  CHECK(m.page() == s51::Menu::Page::Maintenance);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-wartung.ppm");
  tapAt(m, g, r, 400, 58 + 2 * 62 + 28, t);   // „Erledigt“ bei der Zündkerze (3. Zeile)
  CHECK(m.page() == s51::Menu::Page::Message);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-wartung-erledigt.ppm");
  tapAt(m, g, r, 400, 290, t);   // Erledigt
  CHECK(host.items[1].lastKm == 1240);
  CHECK(m.page() == s51::Menu::Page::Maintenance);
  tapAt(m, g, r, 20, 20, t);     // zurück
  CHECK(m.page() == s51::Menu::Page::Main);

  // Bluetooth: verbunden mit iPhone, Musik steuern, Kopplungen vergessen
  host.bt.enabled = true;
  host.bt.name = "S51-Tacho";
  host.bt.connected = true;
  host.bt.device = "Mein iPhone";
  host.bt.mediaInfo = true;
  host.bt.track = "Schwalbenflug – Testband";
  host.bt.playing = true;
  host.bt.bonded = 1;
  tapAt(m, g, r, 400, 250, t);    // Kachel Bluetooth (rechts unten)
  CHECK(m.page() == s51::Menu::Page::Bluetooth);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-bluetooth.ppm");
  tapAt(m, g, r, 400, 58 + 62 + 28, t);        // „Pause“
  CHECK(host.playPresses == 1);
  tapAt(m, g, r, 400, 58 + 2 * 62 + 28, t);    // „Vergessen“
  CHECK(m.page() == s51::Menu::Page::Message);
  tapAt(m, g, r, 400, 290, t);
  CHECK(host.bt.bonded == 0);
  CHECK(m.page() == s51::Menu::Page::Bluetooth);
  tapAt(m, g, r, 20, 20, t);
  CHECK(m.page() == s51::Menu::Page::Main);
  // Ohne PIN gibt es oben keinen Knopf „Sperren“
  tapAt(m, g, r, 366, 24, t);
  CHECK(m.page() == s51::Menu::Page::Main);

  // Alarm: PIN festlegen, erst falsch wiederholt, dann richtig
  tapAt(m, g, r, 400, 120, t);   // Kachel Alarm (rechts oben)
  CHECK(m.page() == s51::Menu::Page::Alarm);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-alarm.ppm");
  tapAt(m, g, r, 200, 58 + 2 * 62 + 28, t);   // PIN festlegen
  CHECK(m.page() == s51::Menu::Page::PinEntry);
  key(m, g, r, 1, t);
  key(m, g, r, 3, t);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-pin.ppm");
  key(m, g, r, 10, t);           // löschen
  key(m, g, r, 10, t);
  typePin(m, g, r, "1332", t);
  typePin(m, g, r, "1333", t);   // falsch wiederholt
  CHECK(host.pin.empty());
  typePin(m, g, r, "1332", t);
  typePin(m, g, r, "1332", t);
  CHECK(host.pin == "1332");
  CHECK(m.page() == s51::Menu::Page::Message);
  tapAt(m, g, r, 400, 290, t);   // Fertig
  CHECK(m.page() == s51::Menu::Page::Alarm);

  // Mit PIN sperrt der Knopf oben im Hauptmenü sofort, ohne Zeitlimit
  tapAt(m, g, r, 20, 20, t);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-haupt.ppm");
  tapAt(m, g, r, 366, 24, t);
  CHECK(m.isLocked());
  m.tick(t + 120000);
  CHECK(!m.alarmActive());
  CHECK(typePin(m, g, r, "1332", t + 120000) == s51::Menu::Request::Unlocked);
  m.open();
  tapAt(m, g, r, 400, 120, t);   // zurück ins Menü Alarm

  // Alarm aus- und wieder einschalten
  tapAt(m, g, r, 200, 58 + 28, t);
  CHECK(!host.armed);
  tapAt(m, g, r, 200, 58 + 28, t);
  CHECK(host.armed);

  // Einstellungen, Hinweise, Info
  tapAt(m, g, r, 20, 20, t);
  tapAt(m, g, r, 240, 250, t);   // Kachel Einstellungen (Mitte unten)
  CHECK(m.page() == s51::Menu::Page::Settings);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-einstellungen.ppm");
  tapAt(m, g, r, 200, 58 + 62 + 28, t);
  CHECK(m.page() == s51::Menu::Page::ConfigNotes);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-hinweise.ppm");
  tapAt(m, g, r, 20, 20, t);
  tapAt(m, g, r, 200, 58 + 2 * 62 + 28, t);
  CHECK(m.page() == s51::Menu::Page::About);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-info.ppm");
  tapAt(m, g, r, 20, 20, t);
  tapAt(m, g, r, 20, 20, t);

  // Übertragung öffnet und schließt das WLAN
  tapAt(m, g, r, 80, 250, t);    // Kachel Übertragung (links unten)
  CHECK(m.page() == s51::Menu::Page::Transfer);
  CHECK(host.transferIsOpen);
  host.info.state = s51::TransferInfo::State::Ready;
  host.info.network = "S51-Tacho";
  host.info.address = "192.168.4.1";
  host.info.code = "482913";
  host.info.clients = 1;
  host.info.defaultPassword = true;
  host.info.secondsLeft = 581;
  host.info.message = "Layout „Klar“ empfangen";
  m.draw(g, r, t);
  writePpm(g, out + "/menue-uebertragung.ppm");
  tapAt(m, g, r, 460, 20, t);    // schließen
  CHECK(!m.isOpen());
  CHECK(!host.transferIsOpen);

  // Sperrbildschirm mit Zeitlimit: Zeit läuft ab, Alarm, dann 3 falsche PINs
  m.lock(t, 30);
  CHECK(m.isLocked());
  m.open();                      // Menü darf nicht aufgehen
  CHECK(m.page() == s51::Menu::Page::Lock);
  key(m, g, r, 1, t + 6000);
  m.tick(t + 6000);
  m.draw(g, r, t + 6000);
  writePpm(g, out + "/menue-sperre.ppm");
  m.tick(t + 31000);
  CHECK(m.alarmActive());
  CHECK(host.alarms == 1);
  key(m, g, r, 10, t + 31000);
  typePin(m, g, r, "0000", t + 32000);
  typePin(m, g, r, "1111", t + 33000);
  CHECK(host.failures == 2);
  typePin(m, g, r, "2222", t + 34000);
  CHECK(host.failures == 3);
  CHECK(host.alarms == 2);
  CHECK(typePin(m, g, r, "1332", t + 40000) == s51::Menu::Request::None);   // gesperrt, wird ignoriert
  m.tick(t + 40000);
  m.draw(g, r, t + 40000);
  writePpm(g, out + "/menue-sperre-alarm.ppm");
  m.tick(t + 95000);
  CHECK(typePin(m, g, r, "1332", t + 95000) == s51::Menu::Request::Unlocked);
  CHECK(!m.isOpen());
  CHECK(!m.alarmActive());
  CHECK(host.failures == 0);

  // Protokoll mit Einträgen, dann leeren
  m.open();
  tapAt(m, g, r, 400, 120, t);
  int logRow = 58 + 5 * 62 + 28;   // 6. Zeile: erst nach unten wischen
  m.draw(g, r, t);
  m.scroll(-200);
  m.draw(g, r, t);
  logRow -= 2 * 62;
  tapAt(m, g, r, 200, logRow, t);
  CHECK(m.page() == s51::Menu::Page::AlarmLog);
  m.draw(g, r, t);
  writePpm(g, out + "/menue-protokoll.ppm");
  tapAt(m, g, r, 370, 24, t);     // Leeren
  CHECK(m.page() == s51::Menu::Page::Message);
  tapAt(m, g, r, 400, 290, t);
  CHECK(host.logEntries.empty());

  // Neustart während der Sperre nach 3 falschen PINs: wieder warten
  host.failures = 3;
  s51::Menu m2(host);
  m2.lock(5000, 30);
  CHECK(typePin(m2, g, r, "1332", 6000) == s51::Menu::Request::None);
  CHECK(typePin(m2, g, r, "1332", 66000) == s51::Menu::Request::Unlocked);

  if (failures) {
    fprintf(stderr, "%d Prüfungen fehlgeschlagen\n", failures);
    return 1;
  }
  printf("Menüs: alle Prüfungen bestanden\n");
  return 0;
}
