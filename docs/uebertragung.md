# Drahtlose Übertragung (WLAN)

Layout und Konfiguration lassen sich ohne SD-Karte vom PC auf den Tacho schicken. Der Designer spricht dafür ein einfaches HTTP-Protokoll mit dem Tacho.

**Quellen im Code:**
- Programmteil im Designer: `designer/s51design/transfer.py`
- Simulierter Tacho zum Testen am PC: `designer/s51design/mock_tacho.py`
- Gegenstelle in der Firmware: **noch nicht umgesetzt** (folgt mit der WLAN-Phase). Sie muss sich genau so verhalten wie der Simulator.

---

## 1. Ablauf für Benutzer

1. Am Tacho im Stand (Geschwindigkeit 0) das Menü **Übertragung** öffnen. Der Tacho schaltet das WLAN ein und zeigt einen **6-stelligen Code**.
2. PC verbinden:
   - **Hotspot** (Standard): PC mit dem WLAN `S51-Tacho` verbinden. Adresse im Designer: `192.168.4.1`.
   - **Heimnetz:** Tacho und PC im selben WLAN. Adresse: `s51-tacho.local` (Name aus `hostname` in der Konfiguration).
3. Im Designer **Datei → Drahtlos übertragen**, Adresse und Code eingeben, **Layout senden** oder **Konfiguration senden**.
4. Der Tacho prüft die Datei, speichert sie auf der SD-Karte und intern und zeigt sie sofort an.
5. Menü verlassen oder losfahren beendet den Übertragungsmodus und schaltet das WLAN aus.

## 2. Sicherheit

- WLAN ist nur an, solange der Übertragungsmodus am Tacho offen ist. Er schließt sich beim Losfahren und spätestens nach 10 Minuten.
- Jede Anfrage, die etwas liest oder ändert, braucht den Code vom Display. Er wird bei jedem Öffnen des Modus neu gewürfelt.
- Nach 5 falschen Codes erzeugt der Tacho einen neuen Code.
- Das WLAN-Passwort aus der Konfiguration schützt den Hotspot. Das Standard-Passwort muss geändert werden.
- PIN und NFC-Tags lassen sich nicht übertragen und nicht auslesen.

## 3. Protokoll

HTTP/1.1 auf Port 80. Alle Pfade beginnen mit `/api/v1`. Antworten sind JSON (UTF-8), außer beim Herunterladen von Dateien.

Der Code wird im Kopf **`X-S51-Code`** mitgeschickt.

### GET /api/v1/info

Ohne Code. Für den Verbindungstest.

```json
{
  "geraet": "S51-Tacho",
  "firmware": "0.3.0",
  "format": "1.0",
  "layout": {"crc32": "1a2b3c4d", "groesse": 2412},
  "config": true,
  "uebertragung_offen": true
}
```

`layout` ist `null`, wenn kein Layout gespeichert ist. `format` ist die höchste Layout-Formatversion, die die Firmware lesen kann.

### PUT /api/v1/layout

Mit Code. Nutzdaten: die komplette `.s51`-Datei, `Content-Type: application/octet-stream`.

Der Tacho prüft die Datei mit dem Decoder, bevor er etwas überschreibt. Antwort bei Erfolg:

```json
{"ok": true, "crc32": "1a2b3c4d"}
```

### GET /api/v1/layout

Mit Code. Liefert die aktuell benutzte `.s51`-Datei.

### PUT /api/v1/config

Mit Code. Nutzdaten: Text der `tacho.cfg`, `Content-Type: text/plain; charset=utf-8`. Die Datei wird auch mit Hinweisen übernommen (siehe [konfiguration.md](konfiguration.md)). Antwort:

```json
{"ok": true, "warnungen": ["Zeile 4: fahrzeug.magnete: 99 liegt außerhalb von 1–8. Standard 2 wird verwendet"]}
```

### GET /api/v1/config

Mit Code. Liefert die aktuelle `tacho.cfg` als Text.

### Fehler

| Status | Bedeutung | Antwort |
|---|---|---|
| 400 | Datei ungültig (Decoder hat sie abgelehnt) oder kein UTF-8 | `{"ok": false, "fehler": "Prüfsumme falsch, Datei beschädigt"}` |
| 401 | Code fehlt oder ist falsch | `{"ok": false, "fehler": "Falscher Code"}` |
| 403 | Übertragungsmodus am Tacho ist aus | `{"ok": false, "fehler": "Übertragungsmodus ist aus"}` |
| 404 | Pfad unbekannt oder Datei nicht vorhanden | `{"ok": false, "fehler": "…"}` |
| 413 | Datei größer als 65 536 Bytes | `{"ok": false, "fehler": "…"}` |

## 4. Testen ohne Tacho

Der simulierte Tacho verhält sich wie oben beschrieben und legt empfangene Dateien in einem Ordner ab:

```
cd designer
python -m s51design.mock_tacho --port 8051 --code 123456 --ordner ./sd-simulator
```

Im Designer dann Adresse `localhost:8051` und Code `123456` eingeben.

Der Simulator bildet das Zeitlimit und den Code-Wechsel nach Fehlversuchen nicht nach.
