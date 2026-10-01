#include "bluetooth.h"

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <NimBLEHIDDevice.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

namespace bt {

namespace {

// HID-Beschreibung: eine Fernbedienung mit 8 Medientasten (Consumer Control, Report 1).
// Jedes Bit ist eine Taste, gedrückt = 1.
uint8_t kReportMap[] = {
    0x05, 0x0C,        // Usage Page (Consumer)
    0x09, 0x01,        // Usage (Consumer Control)
    0xA1, 0x01,        // Collection (Application)
    0x85, 0x01,        //   Report ID 1
    0x15, 0x00,        //   Logical Minimum 0
    0x25, 0x01,        //   Logical Maximum 1
    0x75, 0x01,        //   Report Size 1
    0x95, 0x08,        //   Report Count 8
    0x09, 0xCD,        //   Bit 0: Play/Pause
    0x09, 0xB5,        //   Bit 1: Nächster Titel
    0x09, 0xB6,        //   Bit 2: Voriger Titel
    0x09, 0xE9,        //   Bit 3: Lauter
    0x09, 0xEA,        //   Bit 4: Leiser
    0x09, 0xE2,        //   Bit 5: Stumm
    0x09, 0xB7,        //   Bit 6: Stopp
    0x09, 0xB0,        //   Bit 7: Abspielen
    0x81, 0x02,        //   Input (Data, Variable, Absolute)
    0xC0,              // End Collection
};
constexpr uint16_t kAppearanceRemote = 0x0180;   // „Generic Remote Control“

SemaphoreHandle_t lock = nullptr;
QueueHandle_t commands = nullptr;
TaskHandle_t task = nullptr;
NimBLEServer* server = nullptr;
NimBLECharacteristic* input = nullptr;
NimBLERemoteCharacteristic* amsCommand = nullptr;
volatile uint16_t connHandle = BLE_HS_CONN_HANDLE_NONE;
volatile bool setupPending = false;
s51::MediaState st;
bool on = false;

// Benachrichtigungen kommen im Task von NimBLE an: nur kurz sperren und eintragen
void onAmsUpdate(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
  xSemaphoreTake(lock, portMAX_DELAY);
  s51::amsApplyUpdate(st, data, len, millis());
  xSemaphoreGive(lock);
}

void onTime(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
  xSemaphoreTake(lock, portMAX_DELAY);
  s51::ctsApply(st, data, len, millis());
  xSemaphoreGive(lock);
}

class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer*, NimBLEConnInfo& info) override {
    connHandle = info.getConnHandle();
    xSemaphoreTake(lock, portMAX_DELAY);
    st = s51::MediaState();
    st.connected = true;
    xSemaphoreGive(lock);
    // Verschlüsselung anstoßen. Apple Media Service und HID verlangen eine gekoppelte Verbindung.
    NimBLEDevice::startSecurity(info.getConnHandle());
    Serial.printf("Bluetooth: verbunden mit %s\n", info.getAddress().toString().c_str());
  }

  void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int reason) override {
    connHandle = BLE_HS_CONN_HANDLE_NONE;
    amsCommand = nullptr;
    xSemaphoreTake(lock, portMAX_DELAY);
    st = s51::MediaState();
    xSemaphoreGive(lock);
    Serial.printf("Bluetooth: getrennt (Grund %d)\n", reason);
  }

  void onAuthenticationComplete(NimBLEConnInfo& info) override {
    if (!info.isEncrypted()) {
      Serial.println("Bluetooth: Kopplung fehlgeschlagen");
      return;
    }
    setupPending = true;
    if (task) xTaskNotifyGive(task);
  }
} callbacks;

// Nach dem Koppeln: Name, Uhrzeit und Apple Media Service des Handys einrichten.
// Läuft im eigenen Task, weil die Abfragen blockieren.
void setupPeer() {
  uint16_t h = connHandle;
  if (h == BLE_HS_CONN_HANDLE_NONE || !server) return;
  NimBLEClient* client = server->getClient(h);
  if (!client) return;

  std::string name;
  if (NimBLERemoteService* gap = client->getService(NimBLEUUID(uint16_t(0x1800)))) {
    if (NimBLERemoteCharacteristic* c = gap->getCharacteristic(NimBLEUUID(uint16_t(0x2A00)))) {
      name = s51::fitCharset(std::string(c->readValue()));
    }
  }
  xSemaphoreTake(lock, portMAX_DELAY);
  st.phoneName = name;
  xSemaphoreGive(lock);

  if (NimBLERemoteService* cts = client->getService(NimBLEUUID(uint16_t(0x1805)))) {
    if (NimBLERemoteCharacteristic* c = cts->getCharacteristic(NimBLEUUID(uint16_t(0x2A2B)))) {
      NimBLEAttValue v = c->readValue();
      onTime(c, const_cast<uint8_t*>(v.data()), v.length(), false);
      if (c->canNotify()) c->subscribe(true, onTime);
      Serial.println("Bluetooth: Uhrzeit vom Handy");
    }
  }

  NimBLERemoteService* ams = client->getService(NimBLEUUID(s51::ams::kServiceUuid));
  if (!ams) {
    Serial.printf("Bluetooth: %s ohne Apple Media Service, nur Steuerung\n", name.c_str());
    return;
  }
  NimBLERemoteCharacteristic* update = ams->getCharacteristic(NimBLEUUID(s51::ams::kEntityUpdateUuid));
  NimBLERemoteCharacteristic* command = ams->getCharacteristic(NimBLEUUID(s51::ams::kRemoteCommandUuid));
  if (update && update->subscribe(true, onAmsUpdate)) {
    // Welche Angaben das iPhone schicken soll: Wiedergabe und Lautstärke, Titelangaben
    const uint8_t player[] = {s51::ams::kPlayer, s51::ams::kPlaybackInfo, s51::ams::kVolume};
    const uint8_t track[] = {s51::ams::kTrack, s51::ams::kArtist, s51::ams::kAlbum, s51::ams::kTitle,
                             s51::ams::kDuration};
    update->writeValue(player, sizeof(player), true);
    update->writeValue(track, sizeof(track), true);
    xSemaphoreTake(lock, portMAX_DELAY);
    st.mediaInfo = true;
    xSemaphoreGive(lock);
  }
  if (command) {
    command->subscribe(true, nullptr);   // meldet die gerade möglichen Befehle, wird nicht gebraucht
    amsCommand = command;
  }
  Serial.printf("Bluetooth: Apple Media Service von %s eingerichtet\n", name.c_str());
}

// HID-Taste kurz drücken und loslassen
void pressHid(uint8_t bit) {
  if (!input) return;
  uint8_t v = uint8_t(1u << bit);
  input->setValue(&v, 1);
  input->notify();
  vTaskDelay(pdMS_TO_TICKS(30));
  v = 0;
  input->setValue(&v, 1);
  input->notify();
}

void runCommand(s51::Action a) {
  uint8_t amsId = 0xFF, hidBit = 0xFF;
  switch (a) {
    case s51::Action::PlayPause: amsId = s51::ams::kTogglePlayPause; hidBit = 0; break;
    case s51::Action::NextTrack: amsId = s51::ams::kNextTrack; hidBit = 1; break;
    case s51::Action::PreviousTrack: amsId = s51::ams::kPreviousTrack; hidBit = 2; break;
    case s51::Action::VolumeUp: amsId = s51::ams::kVolumeUp; hidBit = 3; break;
    case s51::Action::VolumeDown: amsId = s51::ams::kVolumeDown; hidBit = 4; break;
    default: return;
  }
  // iPhone mit Apple Media Service: Befehl direkt an die Musik-App. Sonst über HID.
  NimBLERemoteCharacteristic* c = amsCommand;
  if (c && c->writeValue(&amsId, 1, true)) return;
  pressHid(hidBit);
}

void taskMain(void*) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(50));
    if (setupPending) {
      setupPending = false;
      setupPeer();
    }
    uint8_t a;
    while (xQueueReceive(commands, &a, 0) == pdTRUE) runCommand(static_cast<s51::Action>(a));
  }
}

}  // namespace

void begin(const std::string& name) {
  if (on) return;
  lock = xSemaphoreCreateMutex();
  commands = xQueueCreate(8, 1);
  NimBLEDevice::init(name);
  NimBLEDevice::setSecurityAuth(true, false, true);              // koppeln und merken, ohne PIN
  NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT);
  NimBLEDevice::setMTU(185);                                      // längere Songtitel am Stück

  server = NimBLEDevice::createServer();
  server->setCallbacks(&callbacks);
  server->advertiseOnDisconnect(true);

  NimBLEHIDDevice* hid = new NimBLEHIDDevice(server);
  input = hid->getInputReport(1);
  hid->setManufacturer("S51-Tacho");
  hid->setPnp(0x02, 0x1209, 0x0001, 0x0100);   // USB-Herstellernummer von pid.codes (freie Projekte)
  hid->setHidInfo(0x00, 0x01);
  hid->setReportMap(kReportMap, sizeof(kReportMap));
  hid->setBatteryLevel(100);
  server->start();

  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->setAppearance(kAppearanceRemote);
  adv->addServiceUUID(hid->getHidService()->getUUID());
  adv->setName(name);
  adv->enableScanResponse(true);
  adv->start();

  xTaskCreatePinnedToCore(taskMain, "bt", 6144, nullptr, 1, &task, 0);
  on = true;
  Serial.printf("Bluetooth: sichtbar als „%s“, %d gekoppelte Geräte\n", name.c_str(), NimBLEDevice::getNumBonds());
}

bool enabled() { return on; }

bool send(s51::Action action) {
  if (!on || connHandle == BLE_HS_CONN_HANDLE_NONE) return false;
  uint8_t a = static_cast<uint8_t>(action);
  xQueueSend(commands, &a, 0);
  if (task) xTaskNotifyGive(task);
  return true;
}

s51::MediaState state() {
  if (!on) return s51::MediaState();
  xSemaphoreTake(lock, portMAX_DELAY);
  s51::MediaState copy = st;
  xSemaphoreGive(lock);
  return copy;
}

int bondedCount() { return on ? NimBLEDevice::getNumBonds() : 0; }

void forgetAll() {
  if (!on) return;
  uint16_t h = connHandle;
  if (h != BLE_HS_CONN_HANDLE_NONE) server->disconnect(h);
  NimBLEDevice::deleteAllBonds();
  Serial.println("Bluetooth: alle Kopplungen gelöscht");
}

}  // namespace bt
