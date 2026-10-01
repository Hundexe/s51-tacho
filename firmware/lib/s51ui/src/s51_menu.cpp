#include "s51_menu.h"

#include <algorithm>
#include <cmath>

#include "s51_values.h"

namespace s51 {

namespace {
const Color kBg{14, 17, 16};
const Color kPanel{23, 28, 25};
const Color kPressed{40, 48, 44};
const Color kHi{31, 58, 49};
const Color kAccent{29, 158, 117};
const Color kText{241, 239, 232};
const Color kDim{136, 135, 128};
const Color kBorder{44, 48, 45};
const Color kInk{13, 36, 30};
const Color kRed{226, 75, 74};
const Color kRedDark{74, 22, 22};
const Color kAmber{239, 159, 39};

constexpr int kHeaderH = 48;
constexpr int kTop = 58;               // Oberkante des Inhalts
constexpr int kRowH = 56, kRowGap = 6;
constexpr int kAboutRowH = 30;

// Ziffernblock rechts
constexpr int kKeyX = 240, kKeyY = 60, kKeyW = 72, kKeyH = 58, kKeyGapX = 8, kKeyGapY = 6;

// Antipp-Ziele
enum : int {
  kHitBack = 1,
  kHitClose = 2,
  kHitHeaderAction = 3,
  kHitTile = 10,       // 10 … 15
  kHitRowArmed = 110,
  kHitRowPin = 112,
  kHitRowPinRemove = 113,
  kHitRowNfc = 114,
  kHitRowLog = 115,
  kHitRowGears = 120,
  kHitRowNotes = 121,
  kHitRowAbout = 122,
  kHitRowMaint = 130,  // 130 … 139
  kHitKey = 300,       // 300 … 309 Ziffern
  kHitKeyDel = 310,
  kHitKeyOk = 311,
  kHitMsgPrimary = 401,
  kHitMsgSecondary = 402,
  kHitTransferRetry = 410,
};

enum Tile : int { kTileDesign, kTileMaint, kTileAlarm, kTileTransfer, kTileSettings, kTileLock };

std::string km(float v) { return formatNumber(std::round(v), 0) + " km"; }

std::string plural(size_t n, const char* one, const char* many) {
  return std::to_string(n) + " " + (n == 1 ? one : many);
}

void chevron(LGFX_Sprite& g, int cx, int cy, bool left, uint16_t col) {
  int d = left ? -1 : 1;
  g.drawWideLine(cx - 4 * d, cy - 8, cx + 4 * d, cy, 1.6f, col);
  g.drawWideLine(cx + 4 * d, cy, cx - 4 * d, cy + 8, 1.6f, col);
}

void cross(LGFX_Sprite& g, int cx, int cy, uint16_t col) {
  g.drawWideLine(cx - 7, cy - 7, cx + 7, cy + 7, 1.6f, col);
  g.drawWideLine(cx + 7, cy - 7, cx - 7, cy + 7, 1.6f, col);
}
}  // namespace

// ---------------------------------------------------------------------------
// Seitenwechsel
// ---------------------------------------------------------------------------

void Menu::open() {
  if (isLocked()) return;
  close();
  push(Page::Main);
}

void Menu::close() {
  if (isLocked()) return;
  if (std::find(stack_.begin(), stack_.end(), Page::Transfer) != stack_.end()) host_.transferOpen(false);
  stack_.clear();
  scroll_ = 0;
}

void Menu::push(Page p) {
  stack_.push_back(p);
  scroll_ = 0;
  if (p == Page::Transfer) host_.transferOpen(true);
}

void Menu::pop() {
  if (stack_.empty() || page() == Page::Lock) return;
  if (page() == Page::Transfer) host_.transferOpen(false);
  stack_.pop_back();
  scroll_ = 0;
}

void Menu::showMessage(const std::string& title, const std::string& text, const std::string& primary,
                       const std::string& secondary, MsgAction action, int arg) {
  msgTitle_ = title;
  msgText_ = text;
  msgPrimary_ = primary;
  msgSecondary_ = secondary;
  msgAction_ = action;
  msgArg_ = arg;
  push(Page::Message);
}

void Menu::lock(uint32_t now, int timeoutS) {
  if (std::find(stack_.begin(), stack_.end(), Page::Transfer) != stack_.end()) host_.transferOpen(false);
  stack_.assign(1, Page::Lock);
  scroll_ = 0;
  now_ = now;
  digits_.clear();
  pinError_.clear();
  alarmActive_ = false;
  lockDeadline_ = timeoutS > 0 ? now + uint32_t(timeoutS) * 1000u : 0;
  if (lockDeadline_ == 0 && timeoutS > 0) lockDeadline_ = 1;
  // Nach einem Neustart mitten in einer Sperre wieder warten lassen
  if (host_.pinFailures() >= kMaxFailures) lockoutUntil_ = now + kLockoutMs;
}

void Menu::tick(uint32_t now) {
  now_ = now;
  if (lockoutUntil_ != 0 && now >= lockoutUntil_) {
    lockoutUntil_ = 0;
    pinError_.clear();
  }
  if (isLocked() && lockDeadline_ != 0 && !alarmActive_ && now >= lockDeadline_) {
    alarmActive_ = true;
    host_.alarm("Entsperrzeit abgelaufen");
  }
}

void Menu::pointer(int x, int y, bool down) {
  ptrX_ = x;
  ptrY_ = y;
  ptrDown_ = down;
}

void Menu::scroll(int dy) {
  int pitch = page() == Page::About ? kAboutRowH : kRowH + kRowGap;
  int steps = dy / pitch;
  if (steps == 0) steps = dy > 0 ? 1 : -1;
  scroll_ = std::max(0, std::min(scroll_ - steps, maxScroll_));
}

// ---------------------------------------------------------------------------
// Antippen
// ---------------------------------------------------------------------------

Menu::Request Menu::tap(int x, int y, uint32_t now) {
  now_ = now;
  int id = 0;
  for (auto it = hits_.rbegin(); it != hits_.rend(); ++it) {
    if (x >= it->x && x < it->x + it->w && y >= it->y && y < it->y + it->h) {
      id = it->id;
      break;
    }
  }
  if (id == 0) return Request::None;
  hits_.clear();   // bis zum nächsten Zeichnen keine weiteren Treffer auf der alten Seite

  if (id == kHitBack) {
    pop();
  } else if (id == kHitClose) {
    close();
  } else if (id >= kHitTile && id < kHitTile + 6) {
    switch (id - kHitTile) {
      case kTileDesign:
        close();
        return Request::OpenPicker;
      case kTileMaint: push(Page::Maintenance); break;
      case kTileAlarm: push(Page::Alarm); break;
      case kTileTransfer: push(Page::Transfer); break;
      case kTileSettings: push(Page::Settings); break;
      case kTileLock:
        if (host_.hasPin()) {
          lock(now, 0);
        } else {
          showMessage("Sperren", "Zum Sperren zuerst im Menü Alarm eine PIN festlegen.", "OK");
        }
        break;
    }
  } else if (id >= kHitKey && id <= kHitKeyOk) {
    return pinKey(id - kHitKey, now);
  } else if (id == kHitMsgPrimary) {
    if (msgAction_ == MsgAction::MaintenanceDone) host_.maintenanceDone(msgArg_);
    if (msgAction_ == MsgAction::ClearLog) host_.clearAlarmLog();
    msgAction_ = MsgAction::None;
    pop();
  } else if (id == kHitMsgSecondary) {
    pop();
  } else if (id == kHitHeaderAction) {
    showMessage("Protokoll leeren", "Alle Einträge im Alarm-Protokoll löschen?", "Leeren", "Abbrechen",
                MsgAction::ClearLog);
  } else if (id == kHitTransferRetry) {
    host_.transferOpen(true);
  } else {
    onRow(id);
  }
  return Request::None;
}

void Menu::onRow(int id) {
  if (id == kHitRowArmed) {
    host_.setAlarmArmed(!host_.alarmArmed());
  } else if (id == kHitRowPin) {
    startPin(host_.hasPin() ? PinFlow::Change : PinFlow::Set);
  } else if (id == kHitRowPinRemove) {
    startPin(PinFlow::Remove);
  } else if (id == kHitRowNfc) {
    showMessage("NFC-Tag anlernen",
                host_.nfcReader() ? "Der NFC-Leser ist angeschlossen. Das Anlernen von Tags folgt mit einer "
                                    "späteren Firmware."
                                  : "Am I²C-Bus ist kein NFC-Leser (PN532) angeschlossen. NFC ist optional, "
                                    "das Anlernen folgt mit einer späteren Firmware.",
                "OK");
  } else if (id == kHitRowLog) {
    push(Page::AlarmLog);
  } else if (id == kHitRowGears) {
    showMessage("Gänge anlernen",
                "Zum Anlernen braucht der Tacho Geschwindigkeit und Drehzahl. Das folgt mit einer späteren "
                "Firmware, sobald GPS und Drehzahl angeschlossen sind.",
                "OK");
  } else if (id == kHitRowNotes) {
    push(Page::ConfigNotes);
  } else if (id == kHitRowAbout) {
    push(Page::About);
  } else if (id >= kHitRowMaint && id < kHitRowMaint + 10) {
    int i = id - kHitRowMaint;
    auto items = host_.maintenance();
    if (i < int(items.size())) {
      showMessage(items[i].name + " erledigt?",
                  "Der Abstand von " + km(float(items[i].intervalKm)) + " zählt dann ab dem jetzigen "
                  "Kilometerstand " + km(host_.odometerKm()) + " neu.",
                  "Erledigt", "Abbrechen", MsgAction::MaintenanceDone, i);
    }
  }
}

// ---------------------------------------------------------------------------
// PIN
// ---------------------------------------------------------------------------

void Menu::startPin(PinFlow flow) {
  pinFlow_ = flow;
  pinStep_ = flow == PinFlow::Set ? PinStep::New : PinStep::Old;
  digits_.clear();
  newPin_.clear();
  pinError_.clear();
  push(Page::PinEntry);
}

void Menu::pinWrong(uint32_t now) {
  int n = host_.pinFailures() + 1;
  host_.setPinFailures(n);
  digits_.clear();
  if (n % kMaxFailures == 0) {
    lockoutUntil_ = now + kLockoutMs;
    pinError_.clear();
    if (isLocked()) alarmActive_ = true;
    host_.alarm(std::to_string(kMaxFailures) + " falsche PINs");
  } else {
    int left = kMaxFailures - n % kMaxFailures;
    pinError_ = "Falsche PIN. Noch " + plural(left, "Versuch", "Versuche") + ".";
  }
}

Menu::Request Menu::pinKey(int key, uint32_t now) {
  if (lockedOut(now)) return Request::None;
  if (key >= 0 && key <= 9) {
    if (int(digits_.size()) < kPinMax) digits_ += char('0' + key);
    pinError_.clear();
    return Request::None;
  }
  if (key == kHitKeyDel - kHitKey) {
    if (!digits_.empty()) digits_.pop_back();
    return Request::None;
  }
  // OK
  if (int(digits_.size()) < kPinMin) {
    pinError_ = "Mindestens " + std::to_string(kPinMin) + " Ziffern.";
    return Request::None;
  }
  if (page() == Page::Lock) {
    if (host_.checkPin(digits_)) {
      host_.setPinFailures(0);
      if (alarmActive_) host_.log("Alarm mit PIN beendet");
      alarmActive_ = false;
      lockDeadline_ = 0;
      digits_.clear();
      stack_.clear();
      return Request::Unlocked;
    }
    pinWrong(now);
    return Request::None;
  }

  auto finish = [&](const std::string& title, const std::string& text) {
    digits_.clear();
    newPin_.clear();
    msgTitle_ = title;
    msgText_ = text;
    msgPrimary_ = "Fertig";
    msgSecondary_.clear();
    msgAction_ = MsgAction::None;
    stack_.back() = Page::Message;   // PIN-Seite ersetzen, „zurück“ führt ins Menü Alarm
  };
  switch (pinStep_) {
    case PinStep::Old:
      if (!host_.checkPin(digits_)) {
        pinWrong(now);
        break;
      }
      host_.setPinFailures(0);
      if (pinFlow_ == PinFlow::Remove) {
        host_.setPin("");
        finish("PIN entfernt", host_.securityLevel() >= 2
                                   ? "Ohne PIN erscheint kein Sperrbildschirm, auch nicht bei Sicherheitsstufe 2."
                                   : "Ohne PIN erscheint kein Sperrbildschirm.");
        break;
      }
      pinStep_ = PinStep::New;
      digits_.clear();
      break;
    case PinStep::New:
      newPin_ = digits_;
      digits_.clear();
      pinStep_ = PinStep::Repeat;
      break;
    case PinStep::Repeat:
      if (digits_ == newPin_) {
        host_.setPin(newPin_);
        finish("PIN gespeichert",
               "Die PIN gilt ab sofort. Sie liegt nur im internen Speicher des Tachos, nicht auf der SD-Karte.");
      } else {
        pinError_ = "Die PINs stimmen nicht überein. Neue PIN bitte nochmal eingeben.";
        digits_.clear();
        newPin_.clear();
        pinStep_ = PinStep::New;
      }
      break;
  }
  return Request::None;
}

// ---------------------------------------------------------------------------
// Inhalt der Listen
// ---------------------------------------------------------------------------

std::vector<Menu::Row> Menu::rowsFor(Page p) {
  std::vector<Row> rows;
  auto add = [&](const std::string& label, const std::string& sub, int id, Row::Control c) -> Row& {
    Row r;
    r.label = label;
    r.sub = sub;
    r.id = id;
    r.control = c;
    rows.push_back(r);
    return rows.back();
  };
  auto plainRow = [&](const std::string& text) {
    Row& r = add(text, "", 0, Row::Control::None);
    r.plain = true;
  };

  if (p == Page::Maintenance) {
    float odo = host_.odometerKm();
    add("Kilometerstand", km(odo), 0, Row::Control::None);
    auto items = host_.maintenance();
    for (size_t i = 0; i < items.size(); i++) {
      const MaintenanceItem& m = items[i];
      if (m.intervalKm <= 0) {
        Row& r = add(m.name, "Aus. Abstand in der tacho.cfg unter [wartung]", 0, Row::Control::None);
        r.dim = true;
        continue;
      }
      float left = m.intervalKm - (odo - m.lastKm);
      Row& r = add(m.name, "", kHitRowMaint + int(i), Row::Control::Button);
      r.button = "Erledigt";
      if (left > 0) {
        r.sub = "Alle " + km(float(m.intervalKm)) + ", noch " + km(left);
      } else {
        r.sub = "Fällig seit " + km(-left);
        r.bad = true;
      }
    }
  } else if (p == Page::Alarm) {
    bool armed = host_.alarmArmed();
    Row& a = add("Bewegungsalarm", armed ? "Scharf, meldet Bewegung im Stand" : "Aus", kHitRowArmed,
                 Row::Control::Toggle);
    a.on = armed;
    int level = host_.securityLevel();
    add("Sicherheitsstufe",
        level >= 2 ? "Stufe 2, PIN nach Zündung an (tacho.cfg)" : "Stufe 1, Zündschlüssel genügt (tacho.cfg)", 0,
        Row::Control::None);
    if (host_.hasPin()) {
      add("PIN ändern", "PIN ist festgelegt", kHitRowPin, Row::Control::Chevron);
      add("PIN entfernen", "Ohne PIN kein Sperrbildschirm", kHitRowPinRemove, Row::Control::Chevron);
    } else {
      Row& r = add("PIN festlegen", level >= 2 ? "Fehlt, Stufe 2 braucht eine PIN" : "Noch keine PIN",
                   kHitRowPin, Row::Control::Chevron);
      r.warn = level >= 2;
    }
    add("NFC-Tag anlernen", host_.nfcReader() ? "NFC-Leser gefunden" : "Kein NFC-Leser angeschlossen", kHitRowNfc,
        Row::Control::Chevron);
    size_t n = host_.alarmLog().size();
    add("Protokoll", n == 0 ? "Keine Einträge" : plural(n, "Eintrag", "Einträge"), kHitRowLog,
        Row::Control::Chevron);
  } else if (p == Page::AlarmLog) {
    auto log = host_.alarmLog();
    if (log.empty()) plainRow("Noch keine Einträge.");
    for (const auto& e : log) plainRow(e);
  } else if (p == Page::Settings) {
    Row& g = add("Gänge anlernen", "Braucht GPS und Drehzahl", kHitRowGears, Row::Control::Chevron);
    g.dim = true;
    auto notes = host_.configNotes();
    Row& n = add("Hinweise zur tacho.cfg",
                 !host_.configFound() ? "Keine tacho.cfg, es gelten die Standardwerte"
                 : notes.empty()      ? "Keine Hinweise"
                                      : plural(notes.size(), "Hinweis", "Hinweise"),
                 kHitRowNotes, Row::Control::Chevron);
    n.warn = !notes.empty();
    add("Über diesen Tacho", "Firmware, Design, Speicher", kHitRowAbout, Row::Control::Chevron);
  } else if (p == Page::ConfigNotes) {
    auto notes = host_.configNotes();
    if (!host_.configFound()) {
      plainRow("Auf der SD-Karte liegt keine s51/tacho.cfg. Es gelten die Standardwerte.");
    } else if (notes.empty()) {
      plainRow("Die tacho.cfg wurde ohne Hinweise gelesen.");
    }
    for (const auto& t : notes) plainRow(t);
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Zeichnen
// ---------------------------------------------------------------------------

bool Menu::pressed(int x, int y, int w, int h) const {
  return ptrDown_ && ptrX_ >= x && ptrX_ < x + w && ptrY_ >= y && ptrY_ < y + h;
}

void Menu::drawHeader(LGFX_Sprite& g, Renderer& r, const std::string& title, bool back, bool closable) {
  const int W = g.width();
  if (back) {
    if (pressed(0, 0, 52, kHeaderH)) g.fillSmoothCircle(24, kHeaderH / 2, 18, kPressed.to565());
    chevron(g, 24, kHeaderH / 2, true, kText.to565());
    hit(0, 0, 52, kHeaderH, kHitBack);
  }
  r.drawLabel(g, title, back ? 52 : 16, 0, W - 120, kHeaderH, Font::SansBold, 20, kText, Align::Left);
  if (closable) {
    g.fillSmoothCircle(W - 26, kHeaderH / 2, 17, (pressed(W - 52, 0, 52, kHeaderH) ? kPressed : kPanel).to565());
    cross(g, W - 26, kHeaderH / 2, kText.to565());
    hit(W - 52, 0, 52, kHeaderH, kHitClose);
  }
  g.drawFastHLine(0, kHeaderH, W, kBorder.to565());
}

void Menu::drawButton(LGFX_Sprite& g, Renderer& r, int x, int y, int w, int h, const std::string& text,
                      bool primary, int id, bool enabled) {
  Color bg = primary && enabled ? kAccent : kPanel;
  if (enabled && pressed(x, y, w, h)) bg = primary ? kHi : kPressed;
  g.fillSmoothRoundRect(x, y, w, h, 10, bg.to565());
  if (!primary) g.drawRoundRect(x, y, w, h, 10, kBorder.to565());
  r.drawLabel(g, text, x, y, w, h, Font::SansBold, 16, !enabled ? kDim : primary ? kInk : kText);
  if (enabled) hit(x, y, w, h, id);
}

void Menu::drawMain(LGFX_Sprite& g, Renderer& r) {
  drawHeader(g, r, "Menü", false, true);
  auto items = host_.maintenance();
  float odo = host_.odometerKm();
  size_t due = 0, set = 0;
  for (const auto& m : items) {
    if (m.intervalKm <= 0) continue;
    set++;
    if (m.intervalKm - (odo - m.lastKm) <= 0) due++;
  }
  bool pinMissing = host_.securityLevel() >= 2 && !host_.hasPin();
  size_t notes = host_.configNotes().size();

  struct T {
    const char* title;
    std::string status;
    bool warn, dim;
  } tiles[6] = {
      {"Design", host_.designName(), false, false},
      {"Wartung", set == 0 ? "Keine Abstände eingestellt" : due ? plural(due, "Erinnerung", "Erinnerungen") + " fällig"
                                                               : "Nichts fällig",
       due > 0, false},
      {"Alarm", std::string(host_.alarmArmed() ? "Scharf" : "Aus") + (pinMissing ? ", PIN fehlt" : ""), pinMissing,
       false},
      {"Übertragung", "WLAN für den Designer", false, false},
      {"Einstellungen", notes ? plural(notes, "Hinweis", "Hinweise") + " zur tacho.cfg" : "Gänge, tacho.cfg, Info",
       notes > 0, false},
      {"Sperren", host_.hasPin() ? "Entsperren mit PIN" : "Erst PIN festlegen", false, !host_.hasPin()},
  };
  const int gap = 10, x0 = 12, y0 = kTop + 2;
  const int w = (g.width() - 2 * x0 - 2 * gap) / 3;
  const int h = (g.height() - y0 - 12 - gap) / 2;
  for (int i = 0; i < 6; i++) {
    int x = x0 + (i % 3) * (w + gap), y = y0 + (i / 3) * (h + gap);
    const T& t = tiles[i];
    g.fillSmoothRoundRect(x, y, w, h, 12, (pressed(x, y, w, h) ? kPressed : kPanel).to565());
    if (t.warn) g.fillSmoothRoundRect(x + 6, y + 16, 4, h - 32, 2, (i == kTileMaint ? kRed : kAmber).to565());
    r.drawLabel(g, t.title, x + 16, y + 12, w - 28, 28, Font::SansBold, 17, t.dim ? kDim : kText, Align::Left);
    r.drawLabel(g, t.status, x + 16, y + 42, w - 28, 40, Font::Sans, 14,
                t.warn ? (i == kTileMaint ? kRed : kAmber) : kDim, Align::Left);
    hit(x, y, w, h, kHitTile + i);
  }
}

void Menu::drawRows(LGFX_Sprite& g, Renderer& r, const std::vector<Row>& rows, int top) {
  const int pitch = kRowH + kRowGap;
  const int visible = std::max(1, (g.height() - top - 4 + kRowGap) / pitch);
  maxScroll_ = std::max(0, int(rows.size()) - visible);
  scroll_ = std::min(scroll_, maxScroll_);
  const bool bar = maxScroll_ > 0;
  const int x = 12, w = g.width() - 24 - (bar ? 10 : 0);
  for (int k = 0; k < visible; k++) {
    int i = scroll_ + k;
    if (i >= int(rows.size())) break;
    const Row& row = rows[i];
    int y = top + k * pitch;
    bool rowTap = row.id && (row.control == Row::Control::Chevron || row.control == Row::Control::Toggle);
    g.fillSmoothRoundRect(x, y, w, kRowH, 10, (rowTap && pressed(x, y, w, kRowH) ? kPressed : kPanel).to565());
    if (row.plain) {
      r.drawLabel(g, row.label, x + 16, y + 4, w - 32, kRowH - 8, Font::Sans, 14, kText, Align::Left);
      continue;
    }
    int ctrlW = row.control == Row::Control::Button ? 124 : row.control == Row::Control::Toggle ? 76
                : row.control == Row::Control::Chevron                                         ? 36
                                                                                               : 0;
    Color labelCol = row.dim ? kDim : kText;
    Color subCol = row.bad ? kRed : row.warn ? kAmber : kDim;
    if (row.sub.empty()) {
      r.drawLabel(g, row.label, x + 16, y, w - 32 - ctrlW, kRowH, Font::SansBold, 17, labelCol, Align::Left);
    } else {
      r.drawLabel(g, row.label, x + 16, y + 5, w - 32 - ctrlW, 24, Font::SansBold, 17, labelCol, Align::Left);
      r.drawLabel(g, row.sub, x + 16, y + 30, w - 32 - ctrlW, 20, Font::Sans, 13, subCol, Align::Left);
    }
    int cy = y + kRowH / 2;
    switch (row.control) {
      case Row::Control::Chevron:
        chevron(g, x + w - 22, cy, false, kDim.to565());
        break;
      case Row::Control::Toggle: {
        int tx = x + w - 68, tw = 52, th = 28;
        g.fillSmoothRoundRect(tx, cy - th / 2, tw, th, th / 2, (row.on ? kAccent : kBorder).to565());
        g.fillSmoothCircle(row.on ? tx + tw - th / 2 : tx + th / 2, cy, th / 2 - 4, kText.to565());
        break;
      }
      case Row::Control::Button:
        drawButton(g, r, x + w - 120, y + 9, 108, kRowH - 18, row.button, false, row.id);
        break;
      default:
        break;
    }
    if (rowTap) hit(x, y, w, kRowH, row.id);
  }
  if (bar) {
    int trackH = g.height() - top - 8;
    int barH = std::max(24, trackH * visible / int(rows.size()));
    int barY = top + (trackH - barH) * scroll_ / maxScroll_;
    g.fillSmoothRoundRect(g.width() - 14, barY, 4, barH, 2, kBorder.to565());
  }
}

void Menu::drawKeypad(LGFX_Sprite& g, Renderer& r, bool enabled, bool okEnabled) {
  static const char* labels[12] = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "\xE2\x86\x90", "0", "OK"};
  static const int ids[12] = {1, 2, 3, 4, 5, 6, 7, 8, 9, kHitKeyDel - kHitKey, 0, kHitKeyOk - kHitKey};
  for (int i = 0; i < 12; i++) {
    int x = kKeyX + (i % 3) * (kKeyW + kKeyGapX), y = kKeyY + (i / 3) * (kKeyH + kKeyGapY);
    bool ok = i == 11;
    bool on = enabled && (!ok || okEnabled);
    Color bg = ok && on ? kAccent : kPanel;
    if (on && pressed(x, y, kKeyW, kKeyH)) bg = ok ? kHi : kPressed;
    g.fillSmoothRoundRect(x, y, kKeyW, kKeyH, 10, bg.to565());
    Color fg = !on ? kBorder : ok ? kInk : kText;
    r.drawLabel(g, labels[i], x, y, kKeyW, kKeyH, Font::SansBold, ok ? 20 : 26, fg);
    if (enabled) hit(x, y, kKeyW, kKeyH, kHitKey + ids[i]);
  }
}

void Menu::drawPinDots(LGFX_Sprite& g, int x, int y, int n) {
  for (int i = 0; i < kPinMax; i++) {
    int cx = x + 10 + i * 32;
    if (i < n) {
      g.fillSmoothCircle(cx, y, 9, kText.to565());
    } else {
      g.fillSmoothCircle(cx, y, 9, (i < kPinMin ? kBorder : kPanel).to565());
      g.fillSmoothCircle(cx, y, 7, kBg.to565());
    }
  }
}

void Menu::drawPinEntry(LGFX_Sprite& g, Renderer& r) {
  const char* title = pinFlow_ == PinFlow::Set ? "PIN festlegen" : pinFlow_ == PinFlow::Change ? "PIN ändern"
                                                                                               : "PIN entfernen";
  drawHeader(g, r, title, true, false);
  const char* prompt = pinStep_ == PinStep::Old ? "Aktuelle PIN" : pinStep_ == PinStep::New ? "Neue PIN"
                                                                                            : "Neue PIN wiederholen";
  r.drawLabel(g, prompt, 16, 64, 210, 52, Font::SansBold, 20, kText, Align::Left);
  r.drawLabel(g, pinStep_ == PinStep::Old ? "Zur Bestätigung" : "4 bis 6 Ziffern, dann OK", 16, 116, 210, 20,
              Font::Sans, 13, kDim, Align::Left);
  drawPinDots(g, 16, 166, int(digits_.size()));
  bool out = lockedOut(now_);
  std::string err = out ? "Zu viele falsche Eingaben. Wieder möglich in " +
                              std::to_string((lockoutUntil_ - now_ + 999) / 1000) + " s."
                        : pinError_;
  if (!err.empty()) r.drawLabel(g, err, 16, 196, 210, 110, Font::Sans, 15, kRed, Align::Left);
  drawKeypad(g, r, !out, int(digits_.size()) >= kPinMin);
}

void Menu::drawLock(LGFX_Sprite& g, Renderer& r, uint32_t now) {
  bool out = lockedOut(now);
  if (alarmActive_) {
    g.fillSmoothRoundRect(8, 8, 220, 108, 12, kRedDark.to565());
    r.drawLabel(g, "Alarm", 24, 16, 196, 40, Font::SansBold, 26, kRed, Align::Left);
    r.drawLabel(g, "PIN eingeben, um den Alarm zu beenden", 24, 56, 196, 52, Font::Sans, 15, kText, Align::Left);
  } else {
    r.drawLabel(g, "Gesperrt", 16, 12, 210, 40, Font::SansBold, 26, kText, Align::Left);
    r.drawLabel(g, "PIN eingeben", 16, 56, 210, 24, Font::Sans, 16, kDim, Align::Left);
    if (lockDeadline_ != 0 && !out) {
      uint32_t left = now >= lockDeadline_ ? 0 : (lockDeadline_ - now + 999) / 1000;
      r.drawLabel(g, "Noch " + std::to_string(left) + " s, dann Alarm", 16, 84, 210, 24, Font::Sans, 15,
                  left <= 10 ? kRed : kAmber, Align::Left);
    }
  }
  drawPinDots(g, 16, 150, int(digits_.size()));
  std::string err = out ? "Zu viele falsche Eingaben. Wieder möglich in " +
                              std::to_string((lockoutUntil_ - now + 999) / 1000) + " s."
                        : pinError_;
  if (!err.empty()) r.drawLabel(g, err, 16, 180, 210, 120, Font::Sans, 15, kRed, Align::Left);
  drawKeypad(g, r, !out, int(digits_.size()) >= kPinMin);
}

void Menu::drawMessage(LGFX_Sprite& g, Renderer& r) {
  drawHeader(g, r, msgTitle_, true, false);
  r.drawLabel(g, msgText_, 24, kTop + 10, g.width() - 48, 120, Font::Sans, 18, kText, Align::Left);
  const int bw = 200, bh = 52, by = g.height() - bh - 16;
  if (!msgSecondary_.empty()) {
    drawButton(g, r, g.width() - 24 - 2 * bw - 12, by, bw, bh, msgSecondary_, false, kHitMsgSecondary);
  }
  drawButton(g, r, g.width() - 24 - bw, by, bw, bh, msgPrimary_, true, kHitMsgPrimary);
}

void Menu::drawTransfer(LGFX_Sprite& g, Renderer& r) {
  drawHeader(g, r, "Übertragung", true, true);
  TransferInfo t = host_.transfer();
  const int W = g.width();
  if (t.state != TransferInfo::State::Ready) {
    std::string head, text = t.message;
    Color col = kText;
    bool retry = false;
    switch (t.state) {
      case TransferInfo::State::Starting:
        head = t.hotspot ? "WLAN startet …" : "Verbinde mit „" + t.network + "“ …";
        break;
      case TransferInfo::State::Failed:
        head = "WLAN geht nicht";
        col = kRed;
        retry = true;
        break;
      default:
        head = "Übertragung beendet";
        retry = true;
        break;
    }
    r.drawLabel(g, head, 24, kTop + 10, W - 48, 40, Font::SansBold, 22, col, Align::Left);
    if (!text.empty()) r.drawLabel(g, text, 24, kTop + 56, W - 48, 120, Font::Sans, 16, kText, Align::Left);
    if (retry) drawButton(g, r, W - 224, g.height() - 68, 200, 52, "Nochmal starten", true, kHitTransferRetry);
    return;
  }

  // links: Verbindung
  r.drawLabel(g, t.hotspot ? "Mit diesem WLAN verbinden" : "Im Heimnetz", 16, kTop + 2, 216, 20, Font::Sans, 13,
              kDim, Align::Left);
  r.drawLabel(g, t.network, 16, kTop + 22, 216, 28, Font::SansBold, 20, kText, Align::Left);
  r.drawLabel(g, "Adresse im Designer", 16, kTop + 58, 216, 20, Font::Sans, 13, kDim, Align::Left);
  r.drawLabel(g, t.address, 16, kTop + 78, 216, 28, Font::SansBold, 18, kText, Align::Left);
  if (t.hotspot) {
    r.drawLabel(g, t.clients == 0 ? "Noch kein Gerät verbunden" : plural(t.clients, "Gerät", "Geräte") + " verbunden",
                16, kTop + 118, 216, 20, Font::Sans, 13, t.clients ? kAccent : kDim, Align::Left);
  }

  // rechts: Code
  g.fillSmoothRoundRect(244, kTop + 2, W - 256, 132, 12, kPanel.to565());
  r.drawLabel(g, "Code", 260, kTop + 10, W - 288, 20, Font::Sans, 14, kDim, Align::Left);
  std::string code = t.code.size() == 6 ? t.code.substr(0, 3) + " " + t.code.substr(3) : t.code;
  r.drawLabel(g, code, 244, kTop + 34, W - 256, 70, Font::SansBold, 46, kText);
  r.drawLabel(g, "Bei jedem Öffnen neu", 244, kTop + 104, W - 256, 22, Font::Sans, 12, kDim);

  int y = kTop + 150;
  if (t.defaultPassword) {
    g.fillSmoothRoundRect(12, y, W - 24, 46, 10, kPanel.to565());
    g.fillSmoothRoundRect(18, y + 10, 4, 26, 2, kAmber.to565());
    r.drawLabel(g, "Standard-Passwort aus der Doku. In der tacho.cfg unter [wlan] ändern.", 32, y, W - 56, 46,
                Font::Sans, 14, kAmber, Align::Left);
  }
  y = g.height() - 38;
  int left = std::max(0, t.secondsLeft);
  char buf[16];
  snprintf(buf, sizeof(buf), "%d:%02d", left / 60, left % 60);
  r.drawLabel(g, t.message.empty() ? "Bereit" : t.message, 16, y, W - 160, 30, Font::Sans, 14,
              t.message.empty() ? kDim : kAccent, Align::Left);
  r.drawLabel(g, std::string("schließt in ") + buf, W - 156, y, 140, 30, Font::Sans, 14, kDim, Align::Right);
}

void Menu::drawAbout(LGFX_Sprite& g, Renderer& r) {
  drawHeader(g, r, "Über diesen Tacho", true, true);
  auto rows = host_.about();
  const int visible = (g.height() - kTop - 4) / kAboutRowH;
  maxScroll_ = std::max(0, int(rows.size()) - visible);
  scroll_ = std::min(scroll_, maxScroll_);
  for (int k = 0; k < visible; k++) {
    int i = scroll_ + k;
    if (i >= int(rows.size())) break;
    int y = kTop + k * kAboutRowH;
    r.drawLabel(g, rows[i].first, 16, y, 170, kAboutRowH, Font::Sans, 14, kDim, Align::Left);
    r.drawLabel(g, rows[i].second, 190, y, g.width() - 210, kAboutRowH, Font::Sans, 14, kText, Align::Left);
  }
}

void Menu::draw(LGFX_Sprite& g, Renderer& r, uint32_t now) {
  now_ = now;
  hits_.clear();
  g.fillScreen(kBg.to565());
  switch (page()) {
    case Page::Closed:
      break;
    case Page::Main:
      drawMain(g, r);
      break;
    case Page::Maintenance:
      drawHeader(g, r, "Wartung", true, true);
      drawRows(g, r, rowsFor(Page::Maintenance), kTop);
      break;
    case Page::Alarm:
      drawHeader(g, r, "Alarm", true, true);
      drawRows(g, r, rowsFor(Page::Alarm), kTop);
      break;
    case Page::AlarmLog: {
      drawHeader(g, r, "Alarm-Protokoll", true, true);
      if (!host_.alarmLog().empty()) {
        int bx = g.width() - 60 - 96;
        drawButton(g, r, bx, 7, 92, 34, "Leeren", false, kHitHeaderAction);
      }
      drawRows(g, r, rowsFor(Page::AlarmLog), kTop);
      break;
    }
    case Page::Settings:
      drawHeader(g, r, "Einstellungen", true, true);
      drawRows(g, r, rowsFor(Page::Settings), kTop);
      break;
    case Page::ConfigNotes:
      drawHeader(g, r, "Hinweise zur tacho.cfg", true, true);
      drawRows(g, r, rowsFor(Page::ConfigNotes), kTop);
      break;
    case Page::About:
      drawAbout(g, r);
      break;
    case Page::Transfer:
      drawTransfer(g, r);
      break;
    case Page::PinEntry:
      drawPinEntry(g, r);
      break;
    case Page::Message:
      drawMessage(g, r);
      break;
    case Page::Lock:
      drawLock(g, r, now);
      break;
  }
}

}  // namespace s51
