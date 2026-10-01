"""Mitgelieferte Layouts. Dienen als Startpunkt im Designer und als
eingebautes Standard-Layout der Firmware."""

from .layout_format import Layout, Screen, Widget


def _w(type_key, x, y, w, h, **props):
    wd = Widget.new(type_key, x, y)
    wd.w, wd.h = w, h
    wd.props.update(props)
    return wd


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
        _w("value", 10, 286, 110, 26, source="odometer", size=20, align="left", unit=" km"),
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
        _w("value", 16, 80, 200, 40, source="speed_max", size=32, align="left", unit=" km/h"),
        _w("text", 250, 60, 200, 18, text="Durchschnitt", size=14, color=dim, align="left"),
        _w("value", 250, 80, 200, 40, source="speed_avg", size=32, align="left", unit=" km/h"),
        _w("text", 16, 140, 200, 18, text="Fahrzeit", size=14, color=dim, align="left"),
        _w("value", 16, 160, 200, 40, source="ride_time", size=32, align="left", unit=" min"),
        _w("text", 250, 140, 200, 18, text="Seit dem Tanken", size=14, color=dim, align="left"),
        _w("value", 250, 160, 200, 40, source="tank_km", size=32, align="left", unit=" km"),
        _w("text", 16, 220, 200, 18, text="Trip B", size=14, color=dim, align="left"),
        _w("value", 16, 240, 200, 40, source="trip_b", size=32, align="left", decimals=1, unit=" km"),
        _w("text", 250, 220, 200, 18, text="Schräglage max.", size=14, color=dim, align="left"),
        _w("value", 250, 240, 200, 40, source="lean_max", size=32, align="left", unit=" °"),
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
    return Layout(name="Klar", author="S51-Tacho", screens=[fahrt, statistik, nacht])


PRESETS = {"Klar": klar}
