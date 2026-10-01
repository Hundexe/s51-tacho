"""Schema für Layout-Dateien (.s51) und Konfiguration (tacho.cfg).

Diese Datei ist die einzige Quelle für alle Nummern im Dateiformat:
Element-Typen, Datenquellen, Eigenschaften, Symbole und Konfigurationsschlüssel.
Der C++-Header für die Firmware wird daraus erzeugt
(tools/gen_cpp_header.py). Wer hier etwas ändert, erzeugt den Header neu
und passt docs/dateiformat-layout.md bzw. docs/konfiguration.md an.

Regeln, damit alte Dateien lesbar bleiben:
- Vorhandene Nummern nie umbelegen oder wiederverwenden.
- Neues nur mit neuen Nummern hinzufügen.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Layout-Format
# ---------------------------------------------------------------------------

MAGIC = b"S51L"
VERSION_MAJOR = 1
VERSION_MINOR = 1
HEADER_SIZE = 16
DISPLAY_WIDTH = 480
DISPLAY_HEIGHT = 320

MAX_FILE_SIZE = 1048576       # 1 MiB, Bilder brauchen Platz
MAX_SCREENS = 16
MAX_WIDGETS_PER_SCREEN = 96
MAX_STRING_BYTES = 255
MAX_IMAGES = 32
MAX_IMAGE_SIDE = 480

CHUNK_META = b"META"
CHUNK_SCREEN = b"SCRN"
CHUNK_IMAGE = b"IMAG"

# Rollen einer Seite
ROLE_PAGE = 0
ROLE_NIGHT = 1
ROLE_STARTUP = 2      # wird beim Einschalten kurz gezeigt
NO_PAGE = 0xFF
NO_IMAGE = 0xFF

# Bilder
IMAGE_FORMAT_RAW = 1    # Pixel unkomprimiert
IMAGE_FORMAT_RLE = 2    # Pixel lauflängenkodiert
IMAGE_FLAG_ALPHA = 0x01 # jedes Pixel hat ein Alpha-Byte

# Bits im Flag-Byte eines Elements
WFLAG_HIDDEN = 0x01   # wird nicht angezeigt
WFLAG_LOCKED = 0x02   # nur im Designer: nicht verschiebbar

# Meta-Schlüssel (TLV im META-Chunk)
META_NAME = 1
META_AUTHOR = 2
META_CREATED = 3      # u32, Unix-Zeit
META_TOOL = 4         # Programm und Version, das die Datei geschrieben hat


@dataclass(frozen=True)
class Source:
    code: int
    key: str
    label: str
    unit: str = ""
    kind: str = "number"   # number | bool | text | time
    demo_min: float = 0
    demo_max: float = 0


# Datenquellen: woher ein Element seinen Wert bekommt.
# 1–63 Zahlen und Texte, 64–127 Ja/Nein-Zustände.
SOURCES = [
    Source(0, "none", "Keine"),
    Source(1, "speed", "Geschwindigkeit", "km/h", demo_min=0, demo_max=65),
    Source(2, "rpm", "Drehzahl", "U/min", demo_min=1200, demo_max=7500),
    Source(3, "gear", "Gang", "", demo_min=0, demo_max=4),
    Source(4, "odometer", "Gesamtkilometer", "km", demo_min=12345, demo_max=12346),
    Source(5, "trip_a", "Tageskilometer A", "km", demo_min=0, demo_max=150),
    Source(6, "trip_b", "Tageskilometer B", "km", demo_min=0, demo_max=999),
    Source(7, "head_temp", "Zylinderkopftemperatur", "°C", demo_min=60, demo_max=240),
    Source(8, "voltage", "Bordspannung", "V", demo_min=11.5, demo_max=14.4),
    Source(9, "outside_temp", "Außentemperatur", "°C", demo_min=2, demo_max=28),
    Source(10, "housing_temp", "Temperatur in der Lampe", "°C", demo_min=15, demo_max=55),
    Source(11, "lean", "Schräglage", "°", demo_min=-35, demo_max=35),
    Source(12, "lean_max", "Schräglage maximal", "°", demo_min=38, demo_max=38),
    Source(13, "time", "Uhrzeit", "", kind="time"),
    Source(14, "speed_max", "Höchstgeschwindigkeit", "km/h", demo_min=62, demo_max=62),
    Source(15, "speed_avg", "Durchschnitt", "km/h", demo_min=34, demo_max=34),
    Source(16, "ride_time", "Fahrzeit", "min", demo_min=0, demo_max=90),
    Source(17, "tank_km", "Kilometer seit Tanken", "km", demo_min=0, demo_max=180),
    Source(18, "song_title", "Songtitel", kind="text"),
    Source(19, "song_artist", "Interpret", kind="text"),
    Source(20, "service_km", "Kilometer bis Wartung", "km", demo_min=0, demo_max=800),
    Source(64, "blinker_left", "Blinker links", kind="bool"),
    Source(65, "blinker_right", "Blinker rechts", kind="bool"),
    Source(66, "high_beam", "Fernlicht", kind="bool"),
    Source(67, "neutral", "Leerlauf", kind="bool"),
    Source(68, "light", "Licht an", kind="bool"),
    Source(69, "alarm_armed", "Alarm scharf", kind="bool"),
    Source(70, "gps_fix", "GPS-Empfang", kind="bool"),
    Source(71, "bt_connected", "iPhone verbunden", kind="bool"),
    Source(72, "shift_light", "Schaltblitz", kind="bool"),
    Source(73, "warning", "Eine Warnung aktiv", kind="bool"),
]

# Symbole für Kontrollleuchten
ICONS = [
    (0, "none", "Kein Symbol"),
    (1, "arrow_left", "Pfeil links"),
    (2, "arrow_right", "Pfeil rechts"),
    (3, "high_beam", "Fernlicht"),
    (4, "neutral", "Leerlauf (N)"),
    (5, "light", "Licht"),
    (6, "battery", "Batterie"),
    (7, "temp", "Thermometer"),
    (8, "gps", "GPS"),
    (9, "bluetooth", "Bluetooth"),
    (10, "lock", "Schloss"),
    (11, "warning", "Warndreieck"),
    (12, "music", "Musik"),
]

FONTS = [(0, "sans", "Normal"), (1, "sans_bold", "Fett"), (2, "segment", "7-Segment")]
ALIGNS = [(0, "left", "Links"), (1, "center", "Mitte"), (2, "right", "Rechts")]
ORIENTATIONS = [(0, "horizontal", "Waagerecht"), (1, "vertical", "Senkrecht")]


@dataclass(frozen=True)
class Prop:
    code: int
    key: str
    label: str
    type: str          # color | u8 | i16 | f32 | str | bool | enum:<name>
    default: object


# Eigenschaften. Jede hat eine feste Nummer und einen festen Datentyp.
PROPS = [
    Prop(1, "source", "Datenquelle", "enum:source", "none"),
    Prop(2, "color", "Farbe", "color", "#F1EFE8"),
    Prop(3, "bg_color", "Hintergrund", "color", "#000000"),
    Prop(4, "font", "Schrift", "enum:font", "sans"),
    Prop(5, "size", "Schriftgröße (px)", "u8", 24),
    Prop(6, "align", "Ausrichtung", "enum:align", "center"),
    Prop(7, "text", "Text", "str", ""),
    Prop(8, "decimals", "Nachkommastellen", "u8", 0),
    Prop(9, "unit", "Einheit", "str", ""),
    Prop(10, "min", "Minimum", "f32", 0.0),
    Prop(11, "max", "Maximum", "f32", 100.0),
    Prop(12, "warn_above", "Warnung ab", "f32", 0.0),
    Prop(13, "warn_color", "Warnfarbe", "color", "#EF9F27"),
    Prop(14, "crit_above", "Kritisch ab", "f32", 0.0),
    Prop(15, "crit_color", "Kritisch-Farbe", "color", "#E24B4A"),
    Prop(16, "segments", "Segmente (0 = durchgehend)", "u8", 0),
    Prop(17, "orientation", "Richtung", "enum:orientation", "horizontal"),
    Prop(18, "start_angle", "Startwinkel (°)", "i16", 135),
    Prop(19, "end_angle", "Endwinkel (°)", "i16", 405),
    Prop(20, "thickness", "Dicke (px)", "u8", 12),
    Prop(21, "radius", "Eckenradius (px)", "u8", 0),
    Prop(22, "icon", "Symbol", "enum:icon", "none"),
    Prop(23, "on_color", "Farbe an", "color", "#639922"),
    Prop(24, "off_color", "Farbe aus", "color", "#2C2C2A"),
    Prop(25, "blink", "Blinken, wenn an", "bool", False),
    Prop(26, "format", "Format", "str", "HH:MM"),
    Prop(27, "border_color", "Rahmenfarbe", "color", "#000000"),
    Prop(28, "border_width", "Rahmenbreite (px)", "u8", 0),
    Prop(29, "image", "Bild", "u8", 0xFF),
]


@dataclass(frozen=True)
class WidgetType:
    code: int
    key: str
    label: str
    props: tuple       # Schlüssel der erlaubten Eigenschaften
    default_size: tuple = (120, 40)
    overrides: dict = field(default_factory=dict)   # abweichende Standardwerte


THRESHOLDS = ("warn_above", "warn_color", "crit_above", "crit_color")

WIDGET_TYPES = [
    WidgetType(1, "text", "Text",
               ("text", "color", "font", "size", "align"),
               (120, 32), {"text": "Text"}),
    WidgetType(2, "value", "Wert",
               ("source", "color", "font", "size", "align", "decimals", "unit", "format") + THRESHOLDS,
               (160, 80), {"source": "speed", "size": 64, "font": "segment"}),
    WidgetType(3, "bar", "Balken",
               ("source", "min", "max", "segments", "orientation", "color", "bg_color", "radius") + THRESHOLDS,
               (440, 20), {"source": "rpm", "max": 8000.0, "segments": 24,
                           "color": "#1D9E75", "bg_color": "#2C2C2A",
                           "warn_above": 5500.0, "crit_above": 7000.0}),
    WidgetType(4, "gauge", "Rundinstrument",
               ("source", "min", "max", "start_angle", "end_angle", "thickness", "color", "bg_color") + THRESHOLDS,
               (200, 200), {"source": "speed", "max": 80.0, "color": "#1D9E75", "bg_color": "#2C2C2A"}),
    WidgetType(5, "indicator", "Kontrollleuchte",
               ("source", "icon", "on_color", "off_color", "blink"),
               (32, 32), {"source": "neutral", "icon": "neutral"}),
    WidgetType(6, "rect", "Fläche / Linie",
               ("color", "radius", "border_color", "border_width"),
               (100, 2), {"color": "#2C2C2A"}),
    WidgetType(7, "image", "Bild",
               ("image",),
               (64, 64), {}),
]

# Nachschlagetabellen
SOURCE_BY_KEY = {s.key: s for s in SOURCES}
SOURCE_BY_CODE = {s.code: s for s in SOURCES}
PROP_BY_KEY = {p.key: p for p in PROPS}
PROP_BY_CODE = {p.code: p for p in PROPS}
WTYPE_BY_KEY = {t.key: t for t in WIDGET_TYPES}
WTYPE_BY_CODE = {t.code: t for t in WIDGET_TYPES}

ENUMS = {
    "source": [(s.code, s.key, s.label) for s in SOURCES],
    "icon": ICONS,
    "font": FONTS,
    "align": ALIGNS,
    "orientation": ORIENTATIONS,
}


def enum_code(enum_name, key):
    for code, k, _ in ENUMS[enum_name]:
        if k == key:
            return code
    raise ValueError(f"Unbekannter Wert '{key}' für {enum_name}")


def enum_key(enum_name, code):
    for c, k, _ in ENUMS[enum_name]:
        if c == code:
            return k
    return None


def prop_default(wtype, prop_key):
    if prop_key in wtype.overrides:
        return wtype.overrides[prop_key]
    return PROP_BY_KEY[prop_key].default


# ---------------------------------------------------------------------------
# Konfiguration (tacho.cfg)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CfgKey:
    section: str
    key: str
    type: str            # int | float | bool | str | enum
    default: object
    description: str
    min: float = None
    max: float = None
    choices: tuple = ()


CONFIG = [
    # Fahrzeug
    CfgKey("fahrzeug", "radumfang_mm", "int", 1720,
           "Abrollumfang des Vorderrads in mm. Wird mit GPS automatisch nachgelernt, wenn radumfang_lernen = ja.",
           1000, 2500),
    CfgKey("fahrzeug", "radumfang_lernen", "bool", True,
           "Radumfang bei gutem GPS-Empfang selbst nachlernen."),
    CfgKey("fahrzeug", "hall_sensor", "bool", False,
           "Hall-Sensor am Vorderrad verbaut. Bei nein kommt die Geschwindigkeit nur vom GPS."),
    CfgKey("fahrzeug", "magnete", "int", 2, "Anzahl Magnete am Rad für den Hall-Sensor.", 1, 8),
    CfgKey("fahrzeug", "impulse_pro_umdrehung", "int", 1,
           "Zündimpulse pro Kurbelwellenumdrehung. Zweitakter mit einem Zylinder: 1.", 1, 4),
    CfgKey("fahrzeug", "gaenge", "int", 4, "Anzahl Gänge (3 oder 4 bei der S51).", 3, 6),
    CfgKey("fahrzeug", "tankreichweite_km", "int", 150,
           "Ab dieser Strecke seit dem letzten Tanken erscheint die Reserve-Warnung. 0 = aus.", 0, 1000),
    # Anzeige
    CfgKey("anzeige", "layout_datei", "str", "design.s51",
           "Name der Layout-Datei im Ordner s51 auf der SD-Karte."),
    CfgKey("anzeige", "startseite", "int", 0, "Nummer (id) der Tagseite, die nach dem Start gezeigt wird.", 0, 15),
    CfgKey("anzeige", "startbild_dauer_s", "int", 2,
           "Wie lange die Startbild-Seite des Layouts beim Einschalten gezeigt wird, in Sekunden. 0 = aus.", 0, 10),
    CfgKey("anzeige", "startbild_text", "str", "S51",
           "Text beim Einschalten, falls das Layout keine Startbild-Seite hat. Leer = nichts anzeigen."),
    CfgKey("anzeige", "helligkeit_tag", "int", 100, "Helligkeit am Tag in Prozent.", 5, 100),
    CfgKey("anzeige", "helligkeit_nacht", "int", 30, "Helligkeit nachts in Prozent.", 5, 100),
    CfgKey("anzeige", "helligkeit_auto", "bool", True, "Helligkeit über den Lichtsensor regeln."),
    CfgKey("anzeige", "nachtmodus", "enum", "auto",
           "auto = mit dem Licht bzw. Lichtsensor, an = immer, aus = nie.",
           choices=("auto", "an", "aus")),
    # Warnungen
    CfgKey("warnungen", "kopftemp_warnung", "int", 200, "Zylinderkopf: gelbe Warnung ab °C.", 50, 400),
    CfgKey("warnungen", "kopftemp_kritisch", "int", 240, "Zylinderkopf: rote Warnung ab °C.", 50, 400),
    CfgKey("warnungen", "spannung_min", "float", 12.0, "Warnung unter dieser Bordspannung in V.", 9, 15),
    CfgKey("warnungen", "spannung_max", "float", 15.0, "Warnung über dieser Bordspannung in V.", 12, 18),
    CfgKey("warnungen", "glaette_unter", "float", 3.0, "Glättewarnung unter dieser Außentemperatur in °C.", -10, 10),
    CfgKey("warnungen", "schaltblitz_drehzahl", "int", 6500, "Schaltblitz ab dieser Drehzahl. 0 = aus.", 0, 15000),
    # Wartung
    CfgKey("wartung", "getriebeoel_km", "int", 0, "Erinnerung Getriebeöl alle x km. 0 = aus.", 0, 100000),
    CfgKey("wartung", "zuendkerze_km", "int", 0, "Erinnerung Zündkerze alle x km. 0 = aus.", 0, 100000),
    CfgKey("wartung", "kette_km", "int", 0, "Erinnerung Kette schmieren alle x km. 0 = aus.", 0, 100000),
    # Alarm
    CfgKey("alarm", "aktiv", "bool", True, "Bewegungsalarm einschalten."),
    CfgKey("alarm", "stufe", "int", 2,
           "1 = Zündschlüssel entschärft. 2 = nach Zündung an PIN oder NFC-Tag nötig.", 1, 2),
    CfgKey("alarm", "empfindlichkeit", "int", 3, "1 = unempfindlich bis 5 = sehr empfindlich.", 1, 5),
    CfgKey("alarm", "dauer_s", "int", 30, "Wie lange der Alarmton läuft, in Sekunden.", 5, 180),
    CfgKey("alarm", "entsperrzeit_s", "int", 30, "Zeit für PIN oder Tag nach Zündung an (Stufe 2).", 10, 120),
    # GPS
    CfgKey("gps", "messrate_hz", "int", 10, "Messungen pro Sekunde. NEO-6M: höchstens 5.", 1, 10),
    CfgKey("gps", "zeitzone", "str", "Europe/Berlin", "Zeitzone für die Uhrzeit (mit Sommerzeit)."),
    # Bluetooth
    CfgKey("bluetooth", "aktiv", "bool", True, "Bluetooth für Musik und Uhrzeit vom iPhone."),
    CfgKey("bluetooth", "name", "str", "S51-Tacho", "Name, unter dem der Tacho am Handy erscheint."),
    # WLAN
    CfgKey("wlan", "modus", "enum", "hotspot",
           "hotspot = Tacho öffnet eigenes WLAN. heimnetz = Tacho verbindet sich mit dem WLAN unten.",
           choices=("hotspot", "heimnetz")),
    CfgKey("wlan", "ssid", "str", "S51-Tacho", "Name des WLANs (Hotspot oder Heimnetz)."),
    CfgKey("wlan", "passwort", "str", "simson51", "WLAN-Passwort, mindestens 8 Zeichen."),
    CfgKey("wlan", "hostname", "str", "s51-tacho", "Name im Netzwerk, erreichbar als <hostname>.local."),
]

CONFIG_BY_ID = {(c.section, c.key): c for c in CONFIG}
CONFIG_SECTIONS = []
for _c in CONFIG:
    if _c.section not in CONFIG_SECTIONS:
        CONFIG_SECTIONS.append(_c.section)
