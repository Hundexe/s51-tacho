// Bluetooth LE zum Handy (Bauplan Abschnitt 3.5)
//
// - Der Tacho meldet sich als Medien-Fernbedienung an (HID, Consumer Control):
//   Abspielen/Pause, Titel vor und zurück, lauter, leiser. Geht mit iPhone und Android.
// - Ist ein iPhone verbunden, liest der Tacho über den Apple Media Service Titel,
//   Interpret, Album, Position, Länge und Lautstärke und schickt die Befehle direkt
//   dorthin. Über den Current Time Service kommt die Uhrzeit.
// - Gekoppelte Handys merkt sich NimBLE im internen Speicher (NVS) und verbindet sie
//   beim nächsten Start von selbst.
//
// Ausgewertet werden die Daten in lib/s51media (am PC getestet). Die Funktionen hier
// laufen in loop(); NimBLE und die Einrichtung nach dem Verbinden in eigenen Tasks.
#pragma once

#include <string>

#include "s51_media.h"
#include "s51_schema.h"

namespace bt {

void begin(const std::string& name);       // nur, wenn bluetooth.aktiv = ja
bool enabled();

// Medienbefehl schicken (Action::PlayPause … VolumeDown). false: kein Handy verbunden.
bool send(s51::Action action);

// Abzug des Zustands (Verbindung, Titel, Uhrzeit …)
s51::MediaState state();

int bondedCount();                         // gespeicherte Kopplungen
void forgetAll();                          // alle Kopplungen löschen und trennen

}  // namespace bt
