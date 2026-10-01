// Drahtlose Übertragung: WLAN (Hotspot oder Heimnetz) und HTTP-Gegenstelle für
// den S51 Designer. Protokoll: docs/uebertragung.md.
//
// Die Anfragen kommen im Programmteil des HTTP-Servers an. Gelesen, geprüft und
// gespeichert wird aber nur in loop(): transfer::poll() übergibt jede Anfrage an
// eine Funktion des Hauptprogramms und schickt danach die Antwort zurück. So
// greifen Anzeige und Übertragung nie gleichzeitig auf SD-Karte und Layout zu.
#pragma once

#include <cstdint>
#include <string>

#include "s51_menu.h"

namespace transfer {

struct Request {
  enum class Kind : uint8_t { Info, GetLayout, PutLayout, GetConfig, PutConfig };
  Kind kind = Kind::Info;
  std::string body;                                     // Nutzdaten bei PUT
  int status = 200;                                     // Antwort
  std::string type = "application/json; charset=utf-8";
  std::string answer;
};

using Handler = void (*)(Request&);

struct Settings {
  bool hotspot = true;
  std::string ssid, password, hostname;
};

constexpr uint32_t kOpenMs = 10u * 60u * 1000u;         // schließt spätestens nach 10 Minuten
constexpr uint32_t kConnectMs = 30000;                  // Heimnetz: so lange auf Verbindung warten
constexpr int kMaxWrongCodes = 5;                       // danach neuer Code
constexpr size_t kMaxBody = 1048576;                    // 1 MiB

void open(const Settings& s);
void close();
bool isOpen();
void poll(Handler h);                                   // in jeder Runde von loop() aufrufen
void setMessage(const std::string& text);               // letzte Übertragung, für die Anzeige
s51::TransferInfo info();

// Text sicher in JSON einsetzen (mit Anführungszeichen)
std::string jsonString(const std::string& s);

}  // namespace transfer
