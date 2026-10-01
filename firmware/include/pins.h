// Pinbelegung S51-Tacho auf dem WT32-SC01 Plus (ZX3D50CE08S-USRC-4832)
// Quelle Board-Pins: Datenblatt ZX3D50CE08S-USRC-4832, Links in docs/datenblaetter.md
#pragma once
#include <cstdint>

// ---------------------------------------------------------------
// Fest auf dem Board belegt (nicht anders verwenden)
// ---------------------------------------------------------------
// Display ST7796, 8-Bit-Parallel (i80)
constexpr int PIN_LCD_WR  = 47;
constexpr int PIN_LCD_RS  = 0;   // Command/Data, zugleich BOOT-Pin
constexpr int PIN_LCD_RST = 4;   // teilt sich den Reset mit dem Touch
constexpr int PIN_LCD_TE  = 48;
constexpr int PIN_LCD_D0  = 9;
constexpr int PIN_LCD_D1  = 46;
constexpr int PIN_LCD_D2  = 3;
constexpr int PIN_LCD_D3  = 8;
constexpr int PIN_LCD_D4  = 18;
constexpr int PIN_LCD_D5  = 17;
constexpr int PIN_LCD_D6  = 16;
constexpr int PIN_LCD_D7  = 15;
constexpr int PIN_LCD_BL  = 45;  // Hintergrundbeleuchtung, aktiv high

// Touch FT6336U (I2C, eigener Bus)
constexpr int PIN_TP_SDA = 6;
constexpr int PIN_TP_SCL = 5;
constexpr int PIN_TP_INT = 7;

// SD-Karte (SPI)
constexpr int PIN_SD_CS   = 41;
constexpr int PIN_SD_MOSI = 40;
constexpr int PIN_SD_CLK  = 39;
constexpr int PIN_SD_MISO = 38;

// Audio-Verstärker NS4168 (I2S) -> Alarmton und Warntöne
constexpr int PIN_I2S_LRCK = 35;
constexpr int PIN_I2S_BCLK = 36;
constexpr int PIN_I2S_DOUT = 37;

// RS485 (Reserve)
constexpr int PIN_RS485_RX  = 1;
constexpr int PIN_RS485_RTS = 2;
constexpr int PIN_RS485_TX  = 42;

// ---------------------------------------------------------------
// Erweiterungsstecker (die 6 freien GPIOs) - Projektbelegung
// ---------------------------------------------------------------
constexpr int PIN_POWER_HOLD = 10;  // Ausgang: hält die Versorgung an
constexpr int PIN_SPEED_HALL = 11;  // Eingang: Hall-Sensor Vorderrad (optional), über Optokoppler
constexpr int PIN_RPM        = 12;  // Eingang: Drehzahl vom Zündkabel
constexpr int PIN_I2C_SDA    = 13;  // externer I2C-Bus (Module)
constexpr int PIN_I2C_SCL    = 14;
constexpr int PIN_GPS_RX     = 21;  // UART-Eingang vom GPS-Modul

// ---------------------------------------------------------------
// Externer I2C-Bus: Adressen
// ---------------------------------------------------------------
constexpr uint8_t I2C_ADDR_MCP23017 = 0x20;  // Ein-/Ausgänge
constexpr uint8_t I2C_ADDR_BH1750   = 0x23;  // Umgebungslicht
constexpr uint8_t I2C_ADDR_PN532    = 0x24;  // NFC (optional, Entschärfen)
constexpr uint8_t I2C_ADDR_ADS1115  = 0x48;  // Bordspannung
constexpr uint8_t I2C_ADDR_MCP9600  = 0x60;  // Zylinderkopftemperatur
constexpr uint8_t I2C_ADDR_DS3231   = 0x68;  // Uhr
constexpr uint8_t I2C_ADDR_LSM6DS3  = 0x6A;  // Lage / Alarm-Bestätigung
constexpr uint8_t I2C_ADDR_BME280   = 0x76;  // Außentemperatur

// MCP23017: Belegung der Ports (A = Eingänge, B = Taster/Ausgänge)
enum Mcp23017Pin : uint8_t {
  MCP_IN_BLINKER_L = 0,   // GPA0
  MCP_IN_BLINKER_R = 1,   // GPA1
  MCP_IN_FERNLICHT = 2,   // GPA2
  MCP_IN_LEERLAUF  = 3,   // GPA3
  MCP_IN_ZUENDUNG  = 4,   // GPA4  Kl. 15
  MCP_IN_LICHT     = 5,   // GPA5  Licht an (Nachtmodus)
  MCP_IN_TASTER_1  = 8,   // GPB0  Seite / Trip
  MCP_IN_TASTER_2  = 9,   // GPB1  später Play/Pause
  MCP_IN_TASTER_3  = 10,  // GPB2  später Weiter
};
