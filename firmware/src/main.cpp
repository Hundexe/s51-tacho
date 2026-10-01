// S51-Tacho – Phase 1: Display- und Touch-Test mit Demo-Daten
// Zeigt die Fahransicht "Klar" mit animierten Werten.
// Tippen auf das Display zeigt die Touch-Position an.
#include <Arduino.h>
#include "lgfx_sc01plus.h"
#include "version.h"

static LGFX_SC01Plus tft;
static LGFX_Sprite canvas(&tft);

constexpr int W = 480;
constexpr int H = 320;

// Farben (RGB565)
const uint16_t C_BG     = TFT_BLACK;
const uint16_t C_TEXT   = tft.color565(241, 239, 232);
const uint16_t C_DIM    = tft.color565(136, 135, 128);
const uint16_t C_LINE   = tft.color565(44, 44, 42);
const uint16_t C_GREEN  = tft.color565(29, 158, 117);
const uint16_t C_AMBER  = tft.color565(239, 159, 39);
const uint16_t C_RED    = tft.color565(226, 75, 74);
const uint16_t C_BLUE   = tft.color565(55, 138, 221);

struct Demo {
  float speed;   // km/h
  int   rpm;     // U/min
  int   gear;
  float trip;    // km
  float odo;     // km
  int   cht;     // °C Zylinderkopf
  float volt;    // V
} d{0, 1500, 1, 123.4f, 12345.0f, 120, 13.8f};

void drawScreen(int touchX, int touchY) {
  canvas.fillScreen(C_BG);

  // Kopfzeile: Blinker, Fernlicht, Leerlauf, Uhrzeit
  bool blink = (millis() / 500) % 2;
  canvas.setTextDatum(textdatum_t::middle_center);
  canvas.setFont(&fonts::FreeSansBold12pt7b);
  canvas.setTextColor(blink ? C_GREEN : C_LINE);
  canvas.drawString("<", 20, 18);
  canvas.setTextColor(C_LINE);
  canvas.drawString(">", W - 20, 18);
  canvas.setTextColor(C_BLUE);
  canvas.drawString("FL", 190, 18);
  canvas.fillRoundRect(214, 8, 26, 22, 4, d.gear == 0 ? C_GREEN : C_LINE);
  canvas.setTextColor(C_BG);
  canvas.drawString("N", 227, 19);
  canvas.setFont(&fonts::FreeSans12pt7b);
  canvas.setTextColor(C_DIM);
  canvas.drawString("14:32", 285, 18);

  // Drehzahlbalken: 24 Segmente bis 8.000 U/min
  const int segs = 24, x0 = 14, y0 = 38, segW = 17, gap = 2, segH = 16;
  int lit = d.rpm * segs / 8000;
  for (int i = 0; i < segs; i++) {
    uint16_t col = C_LINE;
    if (i < lit) col = (i < 14) ? C_GREEN : (i < 20 ? C_AMBER : C_RED);
    canvas.fillRect(x0 + i * (segW + gap), y0, segW, segH, col);
  }
  canvas.setFont(&fonts::Font2);
  canvas.setTextColor(C_DIM);
  canvas.setTextDatum(textdatum_t::top_left);
  for (int k = 0; k <= 8; k += 2) {
    int x = x0 + (k * segs / 8) * (segW + gap);
    canvas.drawString(String(k), x > W - 30 ? W - 30 : x, y0 + segH + 2);
  }
  canvas.drawString("x1000/min", W - 80, y0 + segH + 2);

  // Drehzahl links, Geschwindigkeit Mitte, Gang rechts
  canvas.setTextDatum(textdatum_t::middle_left);
  canvas.setFont(&fonts::FreeSans9pt7b);
  canvas.drawString(String(d.rpm), 20, 150);
  canvas.drawString("U/min", 20, 172);

  canvas.setTextDatum(textdatum_t::middle_center);
  canvas.setFont(&fonts::Font7);          // 7-Segment-Ziffern
  canvas.setTextSize(2);
  canvas.setTextColor(C_TEXT);
  canvas.drawString(String((int)d.speed), 230, 160);
  canvas.setTextSize(1);
  canvas.setFont(&fonts::FreeSans12pt7b);
  canvas.setTextColor(C_DIM);
  canvas.drawString("km/h", 350, 200);

  canvas.setFont(&fonts::FreeSans9pt7b);
  canvas.drawString("Gang", 430, 110);
  canvas.setFont(&fonts::Font7);
  canvas.setTextColor(C_AMBER);
  canvas.drawString(d.gear == 0 ? "-" : String(d.gear), 430, 155);

  // Infozeile
  canvas.drawFastHLine(0, H - 56, W, C_LINE);
  const char* labels[4] = {"Gesamt", "Trip", "Kopf", "Bordnetz"};
  String values[4] = {String(d.odo, 0) + " km", String(d.trip, 1) + " km",
                      String(d.cht) + " C", String(d.volt, 1) + " V"};
  for (int i = 0; i < 4; i++) {
    int x = i * (W / 4);
    if (i) canvas.drawFastVLine(x, H - 56, 56, C_LINE);
    canvas.setTextDatum(textdatum_t::top_left);
    canvas.setFont(&fonts::Font2);
    canvas.setTextColor(C_DIM);
    canvas.drawString(labels[i], x + 10, H - 50);
    canvas.setFont(&fonts::FreeSans12pt7b);
    uint16_t col = C_TEXT;
    if (i == 2 && d.cht > 200) col = C_RED;          // Warnfarben
    if (i == 3 && (d.volt < 12.0f || d.volt > 15.0f)) col = C_AMBER;
    canvas.setTextColor(col);
    canvas.drawString(values[i], x + 10, H - 32);
  }

  // Touch-Test
  if (touchX >= 0) {
    canvas.fillCircle(touchX, touchY, 10, C_RED);
    canvas.setFont(&fonts::Font2);
    canvas.setTextColor(C_TEXT);
    canvas.setTextDatum(textdatum_t::top_left);
    canvas.drawString("Touch " + String(touchX) + "," + String(touchY), 10, 90);
  }

  canvas.pushSprite(0, 0);
}

void updateDemo() {
  // Langsame Beschleunigung bis 60 km/h, dann Neustart
  static uint32_t t0 = millis();
  float t = (millis() - t0) / 1000.0f;
  if (t > 20) { t0 = millis(); t = 0; }
  d.speed = min(60.0f, t * 3.5f);
  d.gear = d.speed < 1 ? 0 : (d.speed < 15 ? 1 : d.speed < 30 ? 2 : d.speed < 45 ? 3 : 4);
  float inGear = fmodf(d.speed, 15.0f) / 15.0f;
  d.rpm = d.gear == 0 ? 1500 : 3000 + (int)(inGear * 4000);
  d.trip += d.speed / 3600.0f * 0.033f;
  d.odo  += d.speed / 3600.0f * 0.033f;
  d.cht = 120 + (int)(d.speed * 1.5f);
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);          // Querformat 480 x 320
  tft.setBrightness(200);
  canvas.setColorDepth(16);
  canvas.setPsram(true);       // 480x320x2 Byte = 300 KB, passt ins PSRAM
  if (!canvas.createSprite(W, H)) {
    Serial.println("Sprite konnte nicht angelegt werden (PSRAM aktiv?)");
  }

  // Kurzer Startbildschirm: zeigt, dass Flashen und Display funktionieren
  tft.fillScreen(C_BG);
  tft.setTextDatum(textdatum_t::middle_center);
  tft.setFont(&fonts::FreeSansBold24pt7b);
  tft.setTextColor(C_GREEN);
  tft.drawString("S51", W / 2, H / 2 - 30);
  tft.setFont(&fonts::FreeSans12pt7b);
  tft.setTextColor(C_DIM);
  tft.drawString("Firmware " FW_VERSION " - Display-Test", W / 2, H / 2 + 25);
  delay(1500);

  Serial.println("S51-Tacho Firmware " FW_VERSION " (Phase 1) gestartet");
}

void loop() {
  int32_t tx = -1, ty = -1;
  lgfx::touch_point_t tp;
  if (tft.getTouch(&tp)) { tx = tp.x; ty = tp.y; }
  updateDemo();
  drawScreen(tx, ty);
  delay(33);                   // ca. 30 fps
}
