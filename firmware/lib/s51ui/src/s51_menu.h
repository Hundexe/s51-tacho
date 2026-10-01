// Fest eingebaute Menüs und der Sperrbildschirm mit PIN.
//
// Nur Zeichnen, Antippen und die Abläufe (PIN ändern, Wartung bestätigen …).
// Alles, was Speicher, WLAN oder Sensoren braucht, erledigt der Aufrufer über
// MenuHost (in der Firmware src/main.cpp, am PC firmware/hosttest/menu_main.cpp).
// Bedienung und Seiten: firmware/README.md, Abschnitt „Bedienung“.
#pragma once

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "s51_render.h"

namespace s51 {

// Zustand der WLAN-Übertragung für die Seite „Übertragung“
struct TransferInfo {
  enum class State : uint8_t { Off, Starting, Ready, Failed };
  State state = State::Off;
  bool hotspot = true;          // false: Heimnetz
  std::string network;          // Name des WLANs
  std::string address;          // Adresse für den Designer
  std::string code;             // 6 Ziffern
  std::string message;          // Fehler oder letzte Übertragung
  bool defaultPassword = false; // Passwort aus der Doku noch nicht geändert
  int clients = 0;              // verbundene Geräte (nur Hotspot)
  int secondsLeft = 0;          // bis zum automatischen Schließen
};

// Zustand von Bluetooth für die Seite „Bluetooth“
struct BluetoothInfo {
  bool enabled = false;         // bluetooth.aktiv
  std::string name;             // Name, unter dem der Tacho sichtbar ist
  bool connected = false;
  std::string device;           // Name des Handys
  bool mediaInfo = false;       // Titel und Uhrzeit vom iPhone
  std::string track;            // „Titel – Interpret“
  bool playing = false;
  int bonded = 0;               // gespeicherte Kopplungen
};

struct MaintenanceItem {
  std::string name;
  int intervalKm = 0;           // 0: aus
  float lastKm = 0;             // Kilometerstand beim letzten „Erledigt“
};

class MenuHost {
 public:
  virtual ~MenuHost() = default;

  virtual std::string designName() = 0;

  // Wartung
  virtual float odometerKm() = 0;
  virtual std::vector<MaintenanceItem> maintenance() = 0;
  virtual void maintenanceDone(int index) = 0;

  // Alarm und PIN
  virtual bool alarmArmed() = 0;
  virtual void setAlarmArmed(bool on) = 0;
  virtual int securityLevel() = 0;                         // 1 oder 2 (tacho.cfg)
  virtual bool hasPin() = 0;
  virtual bool checkPin(const std::string& pin) = 0;
  virtual void setPin(const std::string& pin) = 0;         // leer: PIN entfernen
  virtual int pinFailures() = 0;                           // falsche Eingaben seit der letzten richtigen
  virtual void setPinFailures(int n) = 0;
  virtual void alarm(const std::string& reason) = 0;       // Alarm auslösen und protokollieren
  virtual void log(const std::string& text) = 0;           // Eintrag ins Alarm-Protokoll
  virtual std::vector<std::string> alarmLog() = 0;         // neueste zuerst
  virtual void clearAlarmLog() = 0;
  virtual bool nfcReader() = 0;                            // PN532 am I²C-Bus gefunden

  // Einstellungen
  virtual bool configFound() = 0;
  virtual std::vector<std::string> configNotes() = 0;      // Hinweise beim Lesen der tacho.cfg
  virtual std::vector<std::pair<std::string, std::string>> about() = 0;

  // Bluetooth
  virtual BluetoothInfo bluetooth() = 0;
  virtual void mediaPlayPause() = 0;
  virtual void forgetBluetooth() = 0;

  // Übertragung
  virtual void transferOpen(bool open) = 0;
  virtual TransferInfo transfer() = 0;
};

class Menu {
 public:
  enum class Page : uint8_t {
    Closed, Main, Maintenance, Alarm, AlarmLog, Settings, ConfigNotes, About, Transfer, PinEntry, Message, Lock,
    Bluetooth
  };
  enum class Request : uint8_t { None, OpenPicker, Unlocked };

  static constexpr int kPinMin = 4;
  static constexpr int kPinMax = 6;
  static constexpr int kMaxFailures = 3;          // danach Sperre und Alarm
  static constexpr uint32_t kLockoutMs = 60000;

  explicit Menu(MenuHost& host) : host_(host) {}

  void open();                                    // Hauptmenü
  void close();
  bool isOpen() const { return page() != Page::Closed; }
  bool isLocked() const { return !stack_.empty() && stack_[0] == Page::Lock; }
  Page page() const { return stack_.empty() ? Page::Closed : stack_.back(); }

  // Sperrbildschirm. timeoutS > 0: nach so vielen Sekunden ohne richtige PIN Alarm
  // (Stufe 2 nach „Zündung an“). 0: ohne Zeitlimit (von Hand gesperrt).
  void lock(uint32_t now, int timeoutS);
  bool alarmActive() const { return alarmActive_; }

  Request tap(int x, int y, uint32_t now);
  void scroll(int dy);                            // Wischen, dy in Pixel (nach unten positiv)
  void pointer(int x, int y, bool down);          // Finger auf dem Display, für die Druck-Anzeige
  void tick(uint32_t now);                        // Zeitlimits prüfen, in jeder Runde aufrufen
  void draw(LGFX_Sprite& g, Renderer& r, uint32_t now);

 private:
  enum class PinFlow : uint8_t { Set, Change, Remove };
  enum class PinStep : uint8_t { Old, New, Repeat };
  enum class MsgAction : uint8_t { None, MaintenanceDone, ClearLog, ForgetBluetooth };

  struct Hit {
    int x, y, w, h, id;
  };
  struct Row {
    std::string label, sub;
    int id = 0;                 // 0: nicht antippbar
    enum class Control : uint8_t { None, Chevron, Toggle, Button } control = Control::None;
    bool on = false;            // Schalter
    std::string button;         // Text des Knopfs
    bool warn = false, bad = false, dim = false;
    bool plain = false;         // nur Text über die ganze Zeile (Hinweise, Protokoll)
  };

  void push(Page p);
  void pop();
  void showMessage(const std::string& title, const std::string& text, const std::string& primary,
                   const std::string& secondary = "", MsgAction action = MsgAction::None, int arg = 0);
  void startPin(PinFlow flow);
  Request pinKey(int key, uint32_t now);
  void pinWrong(uint32_t now);
  bool lockedOut(uint32_t now) const { return lockoutUntil_ != 0 && now < lockoutUntil_; }

  std::vector<Row> rowsFor(Page p);
  void onRow(int id);

  // Zeichnen
  void hit(int x, int y, int w, int h, int id) { hits_.push_back({x, y, w, h, id}); }
  bool pressed(int x, int y, int w, int h) const;
  void drawHeader(LGFX_Sprite& g, Renderer& r, const std::string& title, bool back, bool closable);
  void drawMain(LGFX_Sprite& g, Renderer& r);
  void drawRows(LGFX_Sprite& g, Renderer& r, const std::vector<Row>& rows, int top);
  void drawKeypad(LGFX_Sprite& g, Renderer& r, bool enabled, bool okEnabled);
  void drawPinDots(LGFX_Sprite& g, int x, int y, int n);
  void drawPinEntry(LGFX_Sprite& g, Renderer& r);
  void drawLock(LGFX_Sprite& g, Renderer& r, uint32_t now);
  void drawMessage(LGFX_Sprite& g, Renderer& r);
  void drawTransfer(LGFX_Sprite& g, Renderer& r);
  void drawAbout(LGFX_Sprite& g, Renderer& r);
  void drawButton(LGFX_Sprite& g, Renderer& r, int x, int y, int w, int h, const std::string& text, bool primary,
                  int id, bool enabled = true);

  MenuHost& host_;
  std::vector<Page> stack_;
  std::vector<Hit> hits_;
  int scroll_ = 0;               // erste sichtbare Zeile
  int maxScroll_ = 0;
  int ptrX_ = -1, ptrY_ = -1;
  bool ptrDown_ = false;
  uint32_t now_ = 0;

  // Meldung
  std::string msgTitle_, msgText_, msgPrimary_, msgSecondary_;
  MsgAction msgAction_ = MsgAction::None;
  int msgArg_ = 0;

  // PIN-Eingabe und Sperre
  PinFlow pinFlow_ = PinFlow::Set;
  PinStep pinStep_ = PinStep::New;
  std::string digits_, newPin_, pinError_;
  uint32_t lockDeadline_ = 0;    // 0: kein Zeitlimit
  uint32_t lockoutUntil_ = 0;    // gesperrt nach zu vielen falschen PINs
  bool alarmActive_ = false;
};

}  // namespace s51
