"""Mitgelieferte Layouts. Dienen als Startpunkt im Designer und als
eingebautes Standard-Layout der Firmware."""

import math

from . import images as I
from .layout_format import Layout, Screen, Widget

TEXT = "#F1EFE8"
DIM = "#888780"
LINE = "#2C2C2A"
GREEN = "#1D9E75"
AMBER = "#EF9F27"
RED = "#E24B4A"
BLUE = "#378ADD"
CREAM = "#E8E2D0"


def _w(type_key, x, y, w, h, **props):
    wd = Widget.new(type_key, x, y)
    wd.w, wd.h = w, h
    wd.props.update(props)
    return wd


def _logo(img_id=0, size=128, ring=(29, 158, 117)):
    w, h, rgba = I.make_logo(size, ring=ring)
    return I.from_rgba(img_id, "Logo", w, h, rgba)


def _startup(sid, logo, title="S51", subtitle="Digitaltacho", color=TEXT, sub_color=DIM, bg="#000000"):
    """Startbild-Seite: Logo mittig, darunter zwei Textzeilen."""
    x = (480 - logo.width) // 2
    return Screen(sid, "Startbild", role="startup", bg=bg, widgets=[
        _w("image", x, 40, logo.width, logo.height, image=logo.id),
        _w("text", 40, 40 + logo.height + 16, 400, 40, text=title, size=34, font="sans_bold", color=color),
        _w("text", 40, 40 + logo.height + 56, 400, 24, text=subtitle, size=16, color=sub_color),
    ])


def klar():
    """Das Design „Klar“ aus dem Bauplan: große Geschwindigkeit, Drehzahlbalken, Infozeile."""
    dim = "#888780"
    line = "#2C2C2A"
    fahrt = Screen(0, "Fahrt", bg="#000000", widgets=[
        _w("indicator", 8, 6, 28, 28, source="blinker_left", icon="arrow_left"),
        _w("indicator", 444, 6, 28, 28, source="blinker_right", icon="arrow_right"),
        _w("indicator", 172, 6, 28, 28, source="high_beam", icon="high_beam", on_color="#378ADD"),
        _w("indicator", 206, 6, 28, 28, source="neutral", icon="neutral"),
        _w("value", 244, 6, 80, 28, source="time", font="sans", size=18, color=dim, align="left"),
        _w("bar", 14, 40, 452, 16, source="rpm", min=0.0, max=8000.0, segments=24),
        _w("text", 14, 58, 120, 14, text="x1000/min", size=11, color=dim, align="left"),
        _w("value", 14, 120, 90, 24, source="rpm", font="sans", size=18, color=dim, align="left"),
        _w("text", 14, 146, 90, 16, text="U/min", size=12, color=dim, align="left"),
        _w("value", 110, 80, 240, 130, source="speed", font="segment", size=120, align="center"),
        _w("text", 330, 186, 60, 22, text="km/h", size=18, color=dim, align="left"),
        _w("text", 400, 96, 60, 16, text="Gang", size=12, color=dim),
        _w("value", 400, 112, 60, 70, source="gear", font="segment", size=60, color="#EF9F27"),
        _w("rect", 0, 264, 480, 1, color=line),
        _w("text", 10, 270, 100, 14, text="Gesamt", size=11, color=dim, align="left"),
        _w("value", 10, 286, 110, 26, source="odometer", size=18, align="left", unit=" km"),
        _w("rect", 120, 264, 1, 56, color=line),
        _w("text", 130, 270, 100, 14, text="Trip", size=11, color=dim, align="left"),
        _w("value", 130, 286, 110, 26, source="trip_a", size=20, align="left", decimals=1, unit=" km"),
        _w("rect", 240, 264, 1, 56, color=line),
        _w("text", 250, 270, 100, 14, text="Kopf", size=11, color=dim, align="left"),
        _w("value", 250, 286, 110, 26, source="head_temp", size=20, align="left", unit=" °C",
           warn_above=200.0, crit_above=240.0),
        _w("rect", 360, 264, 1, 56, color=line),
        _w("text", 370, 270, 100, 14, text="Bordnetz", size=11, color=dim, align="left"),
        _w("value", 370, 286, 110, 26, source="voltage", size=20, align="left", decimals=1, unit=" V"),
    ])
    statistik = Screen(1, "Statistik", bg="#000000", widgets=[
        _w("text", 16, 12, 448, 30, text="Statistik", size=24, align="left", font="sans_bold"),
        _w("text", 16, 60, 200, 18, text="Höchstgeschwindigkeit", size=14, color=dim, align="left"),
        _w("value", 16, 80, 200, 40, source="speed_max", size=32, align="left", font="sans_bold", unit=" km/h"),
        _w("text", 250, 60, 200, 18, text="Durchschnitt", size=14, color=dim, align="left"),
        _w("value", 250, 80, 200, 40, source="speed_avg", size=32, align="left", font="sans_bold", unit=" km/h"),
        _w("text", 16, 140, 200, 18, text="Fahrzeit", size=14, color=dim, align="left"),
        _w("value", 16, 160, 200, 40, source="ride_time", size=32, align="left", font="sans_bold", unit=" min"),
        _w("text", 250, 140, 200, 18, text="Seit dem Tanken", size=14, color=dim, align="left"),
        _w("value", 250, 160, 200, 40, source="tank_km", size=32, align="left", font="sans_bold", unit=" km"),
        _w("text", 16, 220, 200, 18, text="Trip B", size=14, color=dim, align="left"),
        _w("value", 16, 240, 200, 40, source="trip_b", size=32, align="left", font="sans_bold", decimals=1, unit=" km"),
        _w("text", 250, 220, 200, 18, text="Schräglage max.", size=14, color=dim, align="left"),
        _w("value", 250, 240, 200, 40, source="lean_max", size=32, align="left", font="sans_bold", unit=" °"),
    ])
    nacht = Screen(2, "Fahrt (Nacht)", role="night", night_of=0, bg="#000000", widgets=[
        _w("value", 90, 70, 300, 150, source="speed", font="segment", size=130, color="#C0392B"),
        _w("text", 200, 222, 80, 20, text="km/h", size=16, color="#6B2A22"),
        _w("indicator", 8, 6, 28, 28, source="blinker_left", icon="arrow_left", on_color="#3B6D11"),
        _w("indicator", 444, 6, 28, 28, source="blinker_right", icon="arrow_right", on_color="#3B6D11"),
        _w("value", 20, 280, 120, 30, source="gear", size=24, color="#6B2A22", align="left"),
        _w("value", 340, 280, 120, 30, source="head_temp", size=24, color="#6B2A22", align="right",
           unit=" °C", warn_above=200.0, crit_above=240.0),
    ])
    logo = _logo()
    return Layout(name="Klar", author="S51-Tacho", images=[logo],
                  screens=[fahrt, statistik, nacht, _startup(3, logo)])



def _label(x, y, w, text, size=12, color=DIM, align="left", h=None):
    return _w("text", x, y, w, h or size + 6, text=text, size=size, color=color, align=align)


def _tile(x, y, w, h, fill="#151715", border="#2A2E2B"):
    return _w("rect", x, y, w, h, color=fill, radius=8, border_color=border, border_width=1)


def _gauge_label_pos(cx, cy, r, angle_deg):
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def retro():
    """Rundinstrument im Stil des alten Simson-Tachos."""
    bg_arc = "#2A2824"
    ws = [
        _w("gauge", 15, 20, 290, 290, source="speed", min=0.0, max=80.0, start_angle=135, end_angle=405,
           thickness=16, color=CREAM, bg_color=bg_arc, crit_above=65.0),
    ]
    cx, cy = 160, 165
    for v in range(0, 81, 10):
        x, y = _gauge_label_pos(cx, cy, 108, 135 + 270 * v / 80)
        big = v % 20 == 0
        ws.append(_w("text", int(x) - 15, int(y) - 10, 30, 20, text=str(v) if big else "·",
                     size=16 if big else 14, color=CREAM if big else DIM, font="sans_bold" if big else "sans"))
    ws += [
        _w("value", 95, 128, 130, 64, source="speed", font="segment", size=58, color=CREAM),
        _label(110, 192, 100, "km/h", 13, DIM, "center"),
        _w("rect", 100, 222, 120, 30, color="#1C1B18", radius=4, border_color="#4A4740", border_width=1),
        _w("value", 104, 224, 112, 26, source="odometer", font="segment", size=18, color=CREAM),
        _w("value", 145, 268, 30, 34, source="gear", font="segment", size=28, color=AMBER),
        _w("indicator", 322, 22, 30, 30, source="blinker_left", icon="arrow_left"),
        _w("indicator", 362, 22, 30, 30, source="high_beam", icon="high_beam", on_color=BLUE),
        _w("indicator", 402, 22, 30, 30, source="neutral", icon="neutral"),
        _w("indicator", 442, 22, 30, 30, source="blinker_right", icon="arrow_right"),
        _w("gauge", 325, 70, 140, 140, source="rpm", min=0.0, max=8000.0, thickness=10, color=CREAM,
           bg_color=bg_arc, warn_above=5500.0, crit_above=7000.0),
        _w("value", 345, 122, 100, 26, source="rpm", font="sans_bold", size=18, color=CREAM),
        _label(345, 148, 100, "U/min", 11, DIM, "center"),
        _label(325, 226, 70, "Kopf", 12, DIM),
        _w("value", 385, 222, 80, 22, source="head_temp", font="sans_bold", size=16, color=CREAM,
           align="right", unit=" °C", warn_above=200.0, crit_above=240.0),
        _w("bar", 325, 248, 140, 8, source="head_temp", min=40.0, max=260.0, segments=0, color=CREAM,
           bg_color=bg_arc, radius=4, warn_above=200.0, crit_above=240.0),
        _w("value", 325, 270, 140, 34, source="time", font="sans_bold", size=24, color=CREAM),
    ]
    return Layout(name="Retro", author="S51-Tacho",
                  screens=[Screen(0, "Rundinstrument", bg="#12110F", widgets=ws)])


def rennsport():
    """Drehzahl und Gang im Vordergrund, mit Schaltblitz und Schräglage."""
    seg_bg = "#1A1A18"
    fahrt = Screen(0, "Rennsport", bg="#000000", widgets=[
        _w("bar", 8, 8, 464, 40, source="rpm", min=0.0, max=8000.0, segments=32, color=GREEN,
           bg_color=seg_bg, warn_above=5500.0, crit_above=7000.0),
        *[_label(8 + int(464 * k / 8) - (14 if k == 8 else 0) - (0 if k == 0 else 6), 50, 20,
                 str(k), 12, DIM, "left") for k in range(0, 9, 2)],
        _w("indicator", 220, 72, 40, 40, source="shift_light", icon="warning", on_color=RED,
           off_color=seg_bg, blink=True),
        _w("value", 270, 70, 200, 30, source="rpm", font="sans_bold", size=22, color=TEXT,
           align="right", unit=" U/min"),
        _w("value", 10, 76, 170, 186, source="gear", font="segment", size=200, color=AMBER),
        _label(10, 262, 170, "Gang", 13, DIM, "center"),
        _w("value", 190, 112, 280, 110, source="speed", font="segment", size=110, color=TEXT, align="right"),
        _label(390, 222, 80, "km/h", 16, DIM, "right"),
        _w("rect", 190, 266, 282, 1, color=LINE),
        _label(196, 272, 80, "Kopf", 11),
        _w("value", 196, 286, 90, 26, source="head_temp", font="sans_bold", size=20, align="left",
           unit=" °C", warn_above=200.0, crit_above=240.0),
        _label(296, 272, 80, "Bordnetz", 11),
        _w("value", 296, 286, 90, 26, source="voltage", font="sans_bold", size=20, align="left",
           decimals=1, unit=" V"),
        _label(396, 272, 76, "Lage", 11),
        _w("value", 396, 286, 76, 26, source="lean", font="sans_bold", size=20, align="left", unit=" °"),
    ])
    lage = Screen(1, "Schräglage", bg="#000000", widgets=[
        _label(16, 12, 200, "Schräglage", 22, TEXT, h=30),
        _w("gauge", 90, 20, 300, 300, source="lean", min=-45.0, max=45.0, start_angle=180, end_angle=360,
           thickness=26, color=GREEN, bg_color=seg_bg, warn_above=30.0, crit_above=40.0),
        _label(62, 178, 56, "L 45°", 12, DIM, "center"),
        _label(362, 178, 56, "45° R", 12, DIM, "center"),
        _label(220, 2, 40, "0°", 12, DIM, "center"),
        _w("value", 165, 110, 150, 70, source="lean", font="segment", size=64, color=TEXT, unit="°"),
        _w("rect", 16, 236, 448, 1, color=LINE),
        _label(16, 246, 200, "Maximum dieser Fahrt", 13),
        _w("value", 16, 266, 200, 40, source="lean_max", font="sans_bold", size=30, align="left", unit=" °"),
        _label(264, 246, 200, "Geschwindigkeit", 13, DIM, "right"),
        _w("value", 264, 266, 200, 40, source="speed", font="sans_bold", size=30, align="right", unit=" km/h"),
    ])
    return Layout(name="Rennsport", author="S51-Tacho", screens=[fahrt, lage])


def cockpit():
    """Viele Werte auf einen Blick in Kacheln, dazu eine Musikseite."""
    def tile_value(x, y, w, h, label, **vp):
        vp.setdefault("font", "sans_bold")
        vp.setdefault("size", 24)
        vp.setdefault("align", "left")
        return [_tile(x, y, w, h), _label(x + 10, y + 6, w - 20, label, 12),
                _w("value", x + 10, y + 24, w - 20, h - 30, **vp)]

    ws = [
        _tile(8, 8, 228, 150),
        _label(18, 14, 200, "Geschwindigkeit", 12),
        _w("value", 18, 34, 208, 96, source="speed", font="segment", size=86, color=TEXT),
        _label(18, 130, 208, "km/h", 13, DIM, "center"),
        _tile(244, 8, 228, 150),
        _label(254, 14, 200, "Drehzahl", 12),
        _w("gauge", 288, 26, 140, 140, source="rpm", min=0.0, max=8000.0, thickness=12, color=GREEN,
           bg_color="#262A27", warn_above=5500.0, crit_above=7000.0),
        _w("value", 298, 78, 120, 30, source="rpm", font="sans_bold", size=20, color=TEXT),
        _w("value", 298, 104, 120, 20, source="gear", font="sans", size=14, color=AMBER, unit=". Gang"),
    ]
    ws += tile_value(8, 166, 149, 70, "Zylinderkopf", source="head_temp", unit=" °C",
                     warn_above=200.0, crit_above=240.0)
    ws.append(_w("bar", 18, 226, 129, 4, source="head_temp", min=40.0, max=260.0, segments=0, color=GREEN,
                 bg_color="#262A27", radius=2, warn_above=200.0, crit_above=240.0))
    ws += tile_value(165, 166, 150, 70, "Bordnetz", source="voltage", decimals=1, unit=" V")
    ws += tile_value(323, 166, 149, 70, "Außen", source="outside_temp", decimals=1, unit=" °C")
    ws += tile_value(8, 244, 149, 68, "Trip A", source="trip_a", decimals=1, unit=" km")
    ws += tile_value(165, 244, 150, 68, "Seit dem Tanken", source="tank_km", unit=" km")
    ws += tile_value(323, 244, 149, 68, "Uhrzeit", source="time")
    musik = Screen(1, "Musik", bg="#0B0C0B", widgets=[
        _w("indicator", 20, 20, 56, 56, source="bt_connected", icon="music", on_color=GREEN),
        _label(92, 22, 360, "Läuft gerade", 13),
        _w("value", 92, 40, 370, 34, source="song_title", font="sans_bold", size=26, color=TEXT, align="left"),
        _w("value", 92, 76, 370, 24, source="song_artist", font="sans", size=18, color=DIM, align="left"),
        _tile(20, 120, 440, 110),
        _w("value", 30, 130, 420, 90, source="time", font="segment", size=80, color=TEXT),
        _w("indicator", 20, 260, 30, 30, source="bt_connected", icon="bluetooth", on_color=BLUE),
        _label(56, 266, 200, "iPhone verbunden", 14, DIM),
        _w("value", 300, 252, 160, 46, source="speed", font="sans_bold", size=34, color=TEXT,
           align="right", unit=" km/h"),
    ])
    return Layout(name="Cockpit", author="S51-Tacho",
                  screens=[Screen(0, "Übersicht", bg="#0B0C0B", widgets=ws), musik])


def minimal():
    """Nur das Nötigste, mit eigener Nachtversion."""
    def page(sid, name, color, small, role="page", night_of=255):
        return Screen(sid, name, role=role, night_of=night_of, bg="#000000", widgets=[
            _w("value", 190, 10, 100, 24, source="time", font="sans", size=18, color=small),
            _w("value", 40, 50, 400, 190, source="speed", font="segment", size=190, color=color),
            _label(190, 240, 100, "km/h", 18, small, "center", h=24),
            _w("indicator", 16, 276, 30, 30, source="blinker_left", icon="arrow_left",
               on_color=GREEN if role == "page" else "#2F5A14", off_color="#000000"),
            _w("indicator", 434, 276, 30, 30, source="blinker_right", icon="arrow_right",
               on_color=GREEN if role == "page" else "#2F5A14", off_color="#000000"),
            _w("indicator", 225, 280, 30, 26, source="warning", icon="warning", on_color=AMBER,
               off_color="#000000", blink=True),
        ])
    return Layout(name="Minimal", author="S51-Tacho", screens=[
        page(0, "Minimal", TEXT, DIM),
        page(1, "Minimal (Nacht)", "#B03A2E", "#5C221C", role="night", night_of=0),
    ])


def alle_elemente():
    """Zeigt alle Element-Typen und ihre Einstellungen, eine Seite je Thema."""
    hdr = lambda t: _label(12, 8, 456, t, 20, TEXT, h=28)  # noqa: E731
    texte = Screen(0, "Texte", widgets=[
        hdr("Texte und Werte"),
        _tile(12, 44, 146, 70), _label(20, 48, 130, "Schrift: Normal", 11),
        _w("text", 20, 66, 130, 40, text="S51", font="sans", size=30, color=TEXT),
        _tile(167, 44, 146, 70), _label(175, 48, 130, "Schrift: Fett", 11),
        _w("text", 175, 66, 130, 40, text="S51", font="sans_bold", size=30, color=TEXT),
        _tile(322, 44, 146, 70), _label(330, 48, 130, "Schrift: 7-Segment", 11),
        _w("value", 330, 66, 130, 40, source="time", font="segment", size=30, color=TEXT, format="HH:MM:SS"),
        _w("rect", 12, 124, 456, 30, color="#151715", radius=4),
        _w("text", 20, 124, 440, 30, text="Ausrichtung links", align="left", size=16, color=TEXT),
        _w("rect", 12, 160, 456, 30, color="#151715", radius=4),
        _w("text", 20, 160, 440, 30, text="Ausrichtung Mitte", align="center", size=16, color=TEXT),
        _w("rect", 12, 196, 456, 30, color="#151715", radius=4),
        _w("text", 20, 196, 440, 30, text="Ausrichtung rechts", align="right", size=16, color=TEXT),
        _label(12, 236, 456, "Wert mit 0, 1 und 2 Nachkommastellen, Einheit und Warnfarben:", 12),
        _w("value", 12, 256, 146, 50, source="voltage", font="sans_bold", size=28, decimals=0, unit=" V"),
        _w("value", 167, 256, 146, 50, source="voltage", font="sans_bold", size=28, decimals=1, unit=" V"),
        _w("value", 322, 256, 146, 50, source="head_temp", font="sans_bold", size=28, decimals=2,
           unit=" °", warn_above=150.0, crit_above=200.0),
    ])
    balken = Screen(1, "Balken", widgets=[
        hdr("Balken"),
        _label(12, 40, 300, "Mit Segmenten und Warnbereich (Drehzahl)", 12),
        _w("bar", 12, 58, 456, 26, source="rpm", min=0.0, max=8000.0, segments=24, color=GREEN,
           bg_color=LINE, warn_above=5500.0, crit_above=7000.0),
        _label(12, 92, 300, "Durchgehend mit runden Ecken (Kopftemperatur)", 12),
        _w("bar", 12, 110, 456, 18, source="head_temp", min=40.0, max=260.0, segments=0, radius=9,
           color=GREEN, bg_color=LINE, warn_above=200.0, crit_above=240.0),
        _label(12, 138, 300, "Senkrecht, füllt von unten", 12),
        _w("bar", 30, 160, 40, 120, source="voltage", min=11.0, max=15.0, orientation="vertical",
           segments=10, color=BLUE, bg_color=LINE),
        _label(14, 284, 72, "Spannung", 11, DIM, "center"),
        _w("bar", 110, 160, 40, 120, source="outside_temp", min=-10.0, max=35.0, orientation="vertical",
           segments=0, radius=6, color=AMBER, bg_color=LINE),
        _label(94, 284, 72, "Außen", 11, DIM, "center"),
        _w("bar", 190, 160, 40, 120, source="tank_km", min=0.0, max=180.0, orientation="vertical",
           segments=6, color=GREEN, bg_color=LINE, warn_above=120.0, crit_above=150.0),
        _label(174, 284, 72, "Tank-km", 11, DIM, "center"),
        _tile(260, 160, 208, 120),
        _w("text", 270, 166, 190, 108, text="Farbe je Segment", size=14, color=TEXT),
        _label(270, 236, 190, "grün → gelb → rot", 12, DIM, "center"),
    ])
    rund = Screen(2, "Rundinstrumente", widgets=[
        hdr("Rundinstrumente"),
        _w("gauge", 12, 44, 140, 140, source="speed", min=0.0, max=80.0, thickness=14, color=GREEN,
           bg_color=LINE, crit_above=65.0),
        _w("value", 32, 96, 100, 36, source="speed", font="sans_bold", size=26),
        _label(12, 188, 140, "135° bis 405°", 12, DIM, "center"),
        _w("gauge", 170, 44, 140, 140, source="lean", min=-45.0, max=45.0, start_angle=180,
           end_angle=360, thickness=20, color=BLUE, bg_color=LINE),
        _w("value", 190, 90, 100, 30, source="lean", font="sans_bold", size=22, unit="°"),
        _label(170, 188, 140, "180° bis 360° (Halbkreis)", 12, DIM, "center"),
        _w("gauge", 328, 44, 140, 140, source="rpm", min=0.0, max=8000.0, start_angle=-90,
           end_angle=270, thickness=6, color=AMBER, bg_color=LINE, warn_above=5500.0, crit_above=7000.0),
        _w("value", 348, 96, 100, 36, source="rpm", font="sans_bold", size=20),
        _label(328, 188, 140, "-90° bis 270° (Vollkreis)", 12, DIM, "center"),
        _w("rect", 12, 214, 456, 1, color=LINE),
        _w("text", 12, 222, 456, 86,
           text="0° = rechts, Winkel im Uhrzeigersinn. Dicke, Farben und Warnschwellen frei wählbar.",
           size=13, color=DIM, align="left"),
    ])
    icons = ["arrow_left", "arrow_right", "high_beam", "neutral", "light", "battery",
             "temp", "gps", "bluetooth", "lock", "warning", "music"]
    names = ["Pfeil links", "Pfeil rechts", "Fernlicht", "Leerlauf", "Licht", "Batterie",
             "Thermometer", "GPS", "Bluetooth", "Schloss", "Warnung", "Musik"]
    colors = [GREEN, GREEN, BLUE, GREEN, GREEN, AMBER, RED, GREEN, BLUE, AMBER, RED, GREEN]
    lw = [hdr("Kontrollleuchten")]
    for i, (ic, nm, col) in enumerate(zip(icons, names, colors)):
        col_i, row_i = i % 6, i // 6
        x, y = 12 + col_i * 77, 50 + row_i * 100
        lw.append(_w("indicator", x + 18, y, 40, 40, source="gps_fix", icon=ic, on_color=col))
        lw.append(_label(x, y + 46, 76, nm, 11, DIM, "center"))
    lw += [
        _w("rect", 12, 252, 456, 1, color=LINE),
        _w("indicator", 12, 264, 36, 36, source="alarm_armed", icon="lock", on_color=AMBER),
        _label(54, 272, 150, "aus = Farbe aus", 12),
        _w("indicator", 240, 264, 36, 36, source="gps_fix", icon="warning", on_color=RED, blink=True),
        _label(282, 272, 180, "blinkt, solange an", 12),
    ]
    leuchten = Screen(3, "Kontrollleuchten", widgets=lw)
    flaechen = Screen(4, "Flächen", widgets=[
        hdr("Flächen, Linien, Versteckt, Gesperrt"),
        _w("rect", 12, 48, 100, 70, color=BLUE),
        _label(12, 122, 100, "eckig", 11, DIM, "center"),
        _w("rect", 128, 48, 100, 70, color=GREEN, radius=12),
        _label(128, 122, 100, "Radius 12", 11, DIM, "center"),
        _w("rect", 244, 48, 100, 70, color="#151715", radius=20, border_color=AMBER, border_width=3),
        _label(244, 122, 100, "Rahmen 3 px", 11, DIM, "center"),
        _w("rect", 360, 48, 108, 70, color=RED, radius=35),
        _label(360, 122, 108, "Pille", 11, DIM, "center"),
        _w("rect", 12, 150, 456, 1, color=TEXT),
        _w("rect", 12, 156, 456, 3, color=DIM),
        _w("rect", 240, 166, 1, 60, color=TEXT),
        _label(12, 170, 220, "Linien sind Flächen mit 1 px", 12),
        _w("text", 250, 166, 218, 60, text="Hier liegt ein verstecktes Element. Am Tacho unsichtbar.",
           size=12, color=DIM, align="left"),
        _w("text", 250, 190, 218, 30, text="Ich bin versteckt", size=16, color=RED, hidden=True),
        _w("rect", 12, 240, 456, 66, color="#151715", radius=8, border_color=LINE, border_width=1),
        _w("text", 24, 246, 432, 54, text="Dieser Kasten ist gesperrt und lässt sich nicht verschieben.",
           size=13, color=TEXT, align="left"),
    ])
    for w in flaechen.widgets:
        if w.type == "text" and w.get("text") == "Ich bin versteckt":
            w.hidden = True
            w.props.pop("hidden", None)
    flaechen.widgets[-2].locked = True
    flaechen.widgets[-1].locked = True
    nacht = Screen(5, "Texte (Nacht)", role="night", night_of=0, widgets=[
        _label(12, 8, 456, "Nachtversion der Seite „Texte“", 20, "#B03A2E", h=28),
        _w("text", 12, 60, 456, 120,
           text="Im Nachtmodus ersetzt diese Seite automatisch ihre Tagseite.",
           size=16, color="#8A2E24"),
        _w("value", 140, 190, 200, 80, source="speed", font="segment", size=72, color="#B03A2E"),
    ])
    gross, klein, amber = _logo(0, 128), _logo(1, 64), _logo(2, 64, ring=(239, 159, 39))
    bilder = Screen(6, "Bilder", widgets=[
        _label(12, 8, 456, "Bilder", 20, TEXT, h=28),
        _w("image", 24, 56, 128, 128, image=0),
        _w("image", 184, 88, 64, 64, image=1),
        _w("image", 272, 88, 64, 64, image=2),
        _label(24, 190, 128, "128 × 128", 11, DIM, "center"),
        _label(184, 190, 64, "64 × 64", 11, DIM, "center"),
        _label(272, 190, 64, "andere Farbe", 11, DIM, "center"),
        _w("rect", 352, 56, 112, 128, color="#1D9E75", radius=10),
        _w("image", 376, 88, 64, 64, image=1),
        _label(352, 190, 112, "mit Transparenz", 11, DIM, "center"),
        _w("text", 12, 222, 456, 90,
           text="Bilder werden als PNG, JPG oder BMP geladen und beim Laden auf die Größe des Rahmens "
                "gebracht. Durchsichtige Stellen bleiben durchsichtig. Ein Bild kann auf vielen Seiten "
                "benutzt werden und steht nur einmal in der Datei.",
           size=13, color=DIM, align="left"),
    ])
    return Layout(name="Alle Elemente", author="S51-Tacho", images=[gross, klein, amber],
                  screens=[texte, balken, rund, leuchten, flaechen, nacht, bilder,
                           _startup(7, gross, "Alle Elemente", "Startbild-Seite mit Logo und Text")])


PRESETS = {
    "Klar": klar,
    "Retro": retro,
    "Rennsport": rennsport,
    "Cockpit": cockpit,
    "Minimal": minimal,
    "Alle Elemente": alle_elemente,
}
