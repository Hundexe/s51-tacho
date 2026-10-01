"""Werte für die Vorschau und die Regeln, wie Werte angezeigt werden.

Die Regeln (Zahlenformat, Warnfarben, Balken- und Zeigerberechnung) gelten
genauso für die Firmware, siehe docs/dateiformat-layout.md, Abschnitt
„Darstellung“.
"""

import math
import time

from . import schema as S


def demo_values(t=None, animate=True):
    """Werte aller Datenquellen für die Vorschau. t in Sekunden."""
    if t is None:
        t = time.monotonic()
    v = {}
    phase = (t % 20.0) / 20.0 if animate else 0.55
    for s in S.SOURCES:
        if s.kind == "number":
            if s.demo_min == s.demo_max:
                v[s.key] = s.demo_min
            else:
                v[s.key] = s.demo_min + (s.demo_max - s.demo_min) * (0.5 - 0.5 * math.cos(phase * 2 * math.pi))
    speed = v["speed"]
    gear = 0 if speed < 1 else 1 if speed < 15 else 2 if speed < 30 else 3 if speed < 45 else 4
    in_gear = (speed % 15) / 15
    v["gear"] = gear
    v["rpm"] = 1500 if gear == 0 else 3000 + in_gear * 4500
    v["lean"] = 30 * math.sin(t * 0.7) if animate else 12
    v["time"] = time.localtime()
    v["song_title"] = "Schwalbenflug"
    v["song_artist"] = "Testband"
    blink = int(t * 2) % 2 == 0 if animate else True
    v.update({
        "blinker_left": blink, "blinker_right": False, "high_beam": True, "neutral": gear == 0,
        "light": True, "alarm_armed": False, "gps_fix": True, "bt_connected": True,
        "shift_light": v["rpm"] > 6500, "warning": v["head_temp"] > 200,
    })
    return v


def format_number(value, decimals):
    """Zahl mit Tausenderpunkt und Dezimalkomma, z. B. 12.345 oder 13,8."""
    s = f"{float(value):,.{int(decimals)}f}"
    return s.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")


def format_time(tm, fmt):
    if tm is None:
        return fmt.replace("HH", "--").replace("MM", "--").replace("SS", "--")
    return (fmt.replace("HH", f"{tm.tm_hour:02d}")
               .replace("MM", f"{tm.tm_min:02d}")
               .replace("SS", f"{tm.tm_sec:02d}"))


def display_text(widget, values):
    """Text, den ein Element vom Typ text oder value zeigt."""
    if widget.type == "text":
        return widget.get("text")
    src = S.SOURCE_BY_KEY.get(widget.get("source"))
    if src is None or src.key == "none":
        return "–"
    raw = values.get(src.key)
    if src.kind == "time":
        return format_time(raw, widget.get("format") or "HH:MM")
    if src.kind == "text":
        return str(raw or "")
    if src.kind == "bool":
        return "an" if raw else "aus"
    if raw is None:
        return "–"
    return format_number(raw, widget.get("decimals")) + widget.get("unit")


def threshold_color(widget, value, normal):
    """Farbe abhängig von Warn- und Kritisch-Schwelle. 0 heißt: Schwelle aus."""
    if value is None or not isinstance(value, (int, float)):
        return normal
    crit, warn = widget.get("crit_above"), widget.get("warn_above")
    if crit and value >= crit:
        return widget.get("crit_color")
    if warn and value >= warn:
        return widget.get("warn_color")
    return normal


def fraction(widget, value):
    """Anteil 0..1 für Balken und Rundinstrument."""
    lo, hi = widget.get("min"), widget.get("max")
    if value is None or hi == lo or not isinstance(value, (int, float)):
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def indicator_on(widget, values, t=None):
    src = S.SOURCE_BY_KEY.get(widget.get("source"))
    on = bool(values.get(src.key)) if src else False
    if on and widget.get("blink"):
        t = time.monotonic() if t is None else t
        on = int(t * 2) % 2 == 0
    return on
