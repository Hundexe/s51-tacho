// LovyanGFX-Konfiguration für das WT32-SC01 Plus
// ST7796 über 8-Bit-Parallelbus, Touch FT6336U (kompatibel zum FT5x06-Treiber)
#pragma once
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include "pins.h"

class LGFX_SC01Plus : public lgfx::LGFX_Device {
  lgfx::Panel_ST7796  _panel;
  lgfx::Bus_Parallel8 _bus;
  lgfx::Light_PWM     _light;
  lgfx::Touch_FT5x06  _touch;

 public:
  LGFX_SC01Plus() {
    {
      auto cfg = _bus.config();
      cfg.freq_write = 40000000;
      cfg.pin_wr = PIN_LCD_WR;
      cfg.pin_rd = -1;
      cfg.pin_rs = PIN_LCD_RS;
      cfg.pin_d0 = PIN_LCD_D0;
      cfg.pin_d1 = PIN_LCD_D1;
      cfg.pin_d2 = PIN_LCD_D2;
      cfg.pin_d3 = PIN_LCD_D3;
      cfg.pin_d4 = PIN_LCD_D4;
      cfg.pin_d5 = PIN_LCD_D5;
      cfg.pin_d6 = PIN_LCD_D6;
      cfg.pin_d7 = PIN_LCD_D7;
      _bus.config(cfg);
      _panel.setBus(&_bus);
    }
    {
      auto cfg = _panel.config();
      cfg.pin_cs = -1;
      cfg.pin_rst = PIN_LCD_RST;
      cfg.pin_busy = -1;
      cfg.panel_width = 320;
      cfg.panel_height = 480;
      cfg.offset_x = 0;
      cfg.offset_y = 0;
      cfg.offset_rotation = 0;
      cfg.readable = false;
      // Falls Farben falsch aussehen: invert oder rgb_order umstellen
      cfg.invert = true;
      cfg.rgb_order = false;
      cfg.dlen_16bit = false;
      cfg.bus_shared = false;
      _panel.config(cfg);
    }
    {
      auto cfg = _light.config();
      cfg.pin_bl = PIN_LCD_BL;
      cfg.invert = false;
      cfg.freq = 44100;
      cfg.pwm_channel = 7;
      _light.config(cfg);
      _panel.setLight(&_light);
    }
    {
      auto cfg = _touch.config();
      cfg.i2c_port = 1;          // Port 0 bleibt für den externen Modul-Bus
      cfg.i2c_addr = 0x38;
      cfg.pin_sda = PIN_TP_SDA;
      cfg.pin_scl = PIN_TP_SCL;
      cfg.pin_int = PIN_TP_INT;
      cfg.pin_rst = -1;          // Reset läuft über den LCD-Reset (GPIO 4)
      cfg.freq = 400000;
      cfg.x_min = 0;
      cfg.x_max = 319;
      cfg.y_min = 0;
      cfg.y_max = 479;
      cfg.bus_shared = false;
      cfg.offset_rotation = 0;
      _touch.config(cfg);
      _panel.setTouch(&_touch);
    }
    setPanel(&_panel);
  }
};
