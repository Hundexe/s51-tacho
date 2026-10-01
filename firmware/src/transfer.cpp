#include "transfer.h"

#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include <esp_http_server.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

namespace transfer {

namespace {

struct Job {
  Request* req = nullptr;
  SemaphoreHandle_t done = nullptr;
  bool started = false;
};

SemaphoreHandle_t lock = nullptr;      // schützt pending, code, wrongCodes
Job* pending = nullptr;
std::string code;
int wrongCodes = 0;

httpd_handle_t server = nullptr;
bool openFlag = false;
bool mdnsOn = false;
Settings settings;
s51::TransferInfo::State state = s51::TransferInfo::State::Off;
std::string message, address;
uint32_t openedAt = 0;

constexpr const char* kDefaultPassword = "simson51";   // Standard aus docs/konfiguration.md

std::string newCode() {
  char buf[8];
  snprintf(buf, sizeof(buf), "%06u", unsigned(esp_random() % 1000000u));
  return buf;
}

const char* statusLine(int status) {
  switch (status) {
    case 200: return "200 OK";
    case 400: return "400 Bad Request";
    case 401: return "401 Unauthorized";
    case 403: return "403 Forbidden";
    case 404: return "404 Not Found";
    case 413: return "413 Payload Too Large";
    case 503: return "503 Service Unavailable";
    default: return "500 Internal Server Error";
  }
}

esp_err_t send(httpd_req_t* req, int status, const std::string& type, const std::string& body) {
  httpd_resp_set_status(req, statusLine(status));
  httpd_resp_set_type(req, type.c_str());
  return httpd_resp_send(req, body.data(), body.size());
}

esp_err_t sendError(httpd_req_t* req, int status, const std::string& text) {
  return send(req, status, "application/json; charset=utf-8",
              "{\"ok\": false, \"fehler\": " + jsonString(text) + "}");
}

// Übergibt die Anfrage an loop() und wartet, bis sie bearbeitet ist
bool runInLoop(Request& r) {
  Job job;
  job.req = &r;
  job.done = xSemaphoreCreateBinary();
  if (!job.done) return false;
  xSemaphoreTake(lock, portMAX_DELAY);
  if (pending) {
    xSemaphoreGive(lock);
    vSemaphoreDelete(job.done);
    return false;
  }
  pending = &job;
  xSemaphoreGive(lock);
  if (xSemaphoreTake(job.done, pdMS_TO_TICKS(20000)) != pdTRUE) {
    xSemaphoreTake(lock, portMAX_DELAY);
    bool started = job.started;
    if (!started) pending = nullptr;
    xSemaphoreGive(lock);
    if (!started) {
      vSemaphoreDelete(job.done);
      return false;
    }
    xSemaphoreTake(job.done, portMAX_DELAY);   // läuft schon, zu Ende warten
  }
  vSemaphoreDelete(job.done);
  return true;
}

esp_err_t handle(httpd_req_t* req) {
  Request r;
  r.kind = static_cast<Request::Kind>(reinterpret_cast<intptr_t>(req->user_ctx));

  if (r.kind != Request::Kind::Info) {
    if (!openFlag) return sendError(req, 403, "Übertragungsmodus ist aus");
    char given[16] = {0};
    if (httpd_req_get_hdr_value_str(req, "X-S51-Code", given, sizeof(given)) != ESP_OK) given[0] = 0;
    std::string g(given);
    while (!g.empty() && g.back() == ' ') g.pop_back();
    while (!g.empty() && g.front() == ' ') g.erase(0, 1);
    xSemaphoreTake(lock, portMAX_DELAY);
    bool ok = !code.empty() && g == code;
    if (!ok && ++wrongCodes >= kMaxWrongCodes) {
      code = newCode();
      wrongCodes = 0;
      message = "Neuer Code nach " + std::to_string(kMaxWrongCodes) + " falschen Versuchen";
    }
    xSemaphoreGive(lock);
    if (!ok) return sendError(req, 401, "Falscher Code");
  }

  if (r.kind == Request::Kind::PutLayout || r.kind == Request::Kind::PutConfig) {
    if (req->content_len > kMaxBody) {
      return sendError(req, 413, "Datei größer als " + std::to_string(kMaxBody) + " Bytes");
    }
    r.body.resize(req->content_len);
    size_t got = 0;
    while (got < r.body.size()) {
      int n = httpd_req_recv(req, &r.body[got], r.body.size() - got);
      if (n == HTTPD_SOCK_ERR_TIMEOUT) continue;
      if (n <= 0) return ESP_FAIL;
      got += size_t(n);
    }
  }

  if (!runInLoop(r)) return sendError(req, 503, "Tacho ist beschäftigt, bitte gleich nochmal");
  return send(req, r.status, r.type, r.answer);
}

esp_err_t notFound(httpd_req_t* req, httpd_err_code_t) { return sendError(req, 404, "Unbekannter Pfad"); }

void startServer() {
  if (server) return;
  httpd_config_t conf = HTTPD_DEFAULT_CONFIG();
  conf.stack_size = 8192;
  conf.max_uri_handlers = 8;
  conf.lru_purge_enable = true;
  if (httpd_start(&server, &conf) != ESP_OK) {
    server = nullptr;
    state = s51::TransferInfo::State::Failed;
    message = "Der Webserver ließ sich nicht starten.";
    return;
  }
  struct Route {
    const char* uri;
    httpd_method_t method;
    Request::Kind kind;
  };
  static const Route routes[] = {
      {"/api/v1/info", HTTP_GET, Request::Kind::Info},
      {"/api/v1/layout", HTTP_GET, Request::Kind::GetLayout},
      {"/api/v1/layout", HTTP_PUT, Request::Kind::PutLayout},
      {"/api/v1/config", HTTP_GET, Request::Kind::GetConfig},
      {"/api/v1/config", HTTP_PUT, Request::Kind::PutConfig},
  };
  for (const Route& rt : routes) {
    httpd_uri_t u = {};
    u.uri = rt.uri;
    u.method = rt.method;
    u.handler = handle;
    u.user_ctx = reinterpret_cast<void*>(static_cast<intptr_t>(rt.kind));
    httpd_register_uri_handler(server, &u);
  }
  httpd_register_err_handler(server, HTTPD_404_NOT_FOUND, notFound);
}

// Offene Anfrage beantworten, ohne loop() (beim Schließen)
void failPending() {
  xSemaphoreTake(lock, portMAX_DELAY);
  Job* j = pending;
  if (j && !j->started) {
    j->req->status = 503;
    j->req->answer = "{\"ok\": false, \"fehler\": \"Übertragung wurde am Tacho beendet\"}";
    pending = nullptr;
    xSemaphoreGive(j->done);
  }
  xSemaphoreGive(lock);
}

}  // namespace

std::string jsonString(const std::string& s) {
  std::string out = "\"";
  for (unsigned char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char buf[8];
          snprintf(buf, sizeof(buf), "\\u%04x", c);
          out += buf;
        } else {
          out += char(c);
        }
    }
  }
  return out + "\"";
}

void open(const Settings& s) {
  if (!lock) lock = xSemaphoreCreateMutex();
  close();
  settings = s;
  xSemaphoreTake(lock, portMAX_DELAY);
  code = newCode();
  wrongCodes = 0;
  xSemaphoreGive(lock);
  message.clear();
  address.clear();
  openedAt = millis();
  openFlag = true;

  if (settings.hotspot) {
    WiFi.mode(WIFI_AP);
    if (!WiFi.softAP(settings.ssid.c_str(), settings.password.c_str())) {
      state = s51::TransferInfo::State::Failed;
      message = "Der Hotspot ließ sich nicht starten. Das WLAN-Passwort in der tacho.cfg muss mindestens 8 "
                "Zeichen haben.";
      return;
    }
    address = WiFi.softAPIP().toString().c_str();
    state = s51::TransferInfo::State::Ready;
    startServer();
  } else {
    WiFi.setHostname(settings.hostname.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.begin(settings.ssid.c_str(), settings.password.c_str());
    state = s51::TransferInfo::State::Starting;
  }
  Serial.printf("Übertragung offen (%s „%s“), Code %s\n", settings.hotspot ? "Hotspot" : "Heimnetz",
                settings.ssid.c_str(), code.c_str());
}

void close() {
  if (!lock) return;
  if (!openFlag && !server) return;
  failPending();
  if (server) {
    httpd_stop(server);
    server = nullptr;
  }
  if (mdnsOn) {
    MDNS.end();
    mdnsOn = false;
  }
  WiFi.softAPdisconnect(true);
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  openFlag = false;
  state = s51::TransferInfo::State::Off;
  Serial.println("Übertragung geschlossen, WLAN aus");
}

bool isOpen() { return openFlag; }

void poll(Handler h) {
  if (!openFlag) return;
  uint32_t now = millis();
  if (now - openedAt >= kOpenMs) {
    close();
    message = "Nach 10 Minuten automatisch beendet.";
    return;
  }
  if (state == s51::TransferInfo::State::Starting) {
    if (WiFi.status() == WL_CONNECTED) {
      address = WiFi.localIP().toString().c_str();
      if (MDNS.begin(settings.hostname.c_str())) {
        MDNS.addService("http", "tcp", 80);
        mdnsOn = true;
        message = "Auch erreichbar als " + settings.hostname + ".local";
      }
      state = s51::TransferInfo::State::Ready;
      startServer();
    } else if (now - openedAt > kConnectMs) {
      WiFi.disconnect(true);
      WiFi.mode(WIFI_OFF);
      state = s51::TransferInfo::State::Failed;
      message = "Keine Verbindung zu „" + settings.ssid + "“. Name und Passwort unter [wlan] in der tacho.cfg prüfen.";
    }
  }

  xSemaphoreTake(lock, portMAX_DELAY);
  Job* j = pending;
  if (j) j->started = true;
  xSemaphoreGive(lock);
  if (!j) return;
  h(*j->req);
  xSemaphoreTake(lock, portMAX_DELAY);
  pending = nullptr;
  xSemaphoreGive(lock);
  xSemaphoreGive(j->done);
}

void setMessage(const std::string& text) { message = text; }

s51::TransferInfo info() {
  s51::TransferInfo t;
  t.state = state;
  t.hotspot = settings.hotspot;
  t.network = settings.ssid;
  t.address = address;
  if (lock) {
    xSemaphoreTake(lock, portMAX_DELAY);
    t.code = code;
    xSemaphoreGive(lock);
  }
  t.message = message;
  t.defaultPassword = settings.password == kDefaultPassword;
  t.clients = settings.hotspot && openFlag ? WiFi.softAPgetStationNum() : 0;
  uint32_t elapsed = millis() - openedAt;
  t.secondsLeft = openFlag && elapsed < kOpenMs ? int((kOpenMs - elapsed) / 1000) : 0;
  return t;
}

}  // namespace transfer
