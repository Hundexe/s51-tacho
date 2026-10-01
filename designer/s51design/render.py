"""Zeichnet ein Layout auf eine Tk-Canvas (Vorschau im Designer).

Die Vorschau ist eine Annäherung: Schriften am PC sehen anders aus als
die Schriften auf dem Tacho. Positionen, Größen, Farben und Werte stimmen.
"""

import math

from . import schema as S
from . import values as V

TAG = "layout"

FONT_FAMILY = {
    "sans": ("Arial", "normal"),
    "sans_bold": ("Arial", "bold"),
    "segment": ("Consolas", "bold"),
}


def tk_font(widget, z):
    family, weight = FONT_FAMILY.get(widget.get("font"), FONT_FAMILY["sans"])
    px = max(6, int(widget.get("size") * z))
    return (family, -px, weight)       # negative Größe = Pixel


def _r(c, x0, y0, x1, y1, z, **kw):
    return c.create_rectangle(x0 * z, y0 * z, x1 * z, y1 * z, tags=TAG, **kw)


def rounded_rect(c, x0, y0, x1, y1, r, z, **kw):
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    if r < 1:
        return _r(c, x0, y0, x1, y1, z, **kw)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon([p * z for p in pts], smooth=True, tags=TAG, **kw)


def draw_text(c, w, z, text, color, wrap=False):
    align = w.get("align")
    anchor = {"left": "w", "center": "center", "right": "e"}[align]
    x = {"left": w.x, "center": w.x + w.w / 2, "right": w.x + w.w}[align]
    extra = {"width": w.w * z, "justify": align} if wrap else {}
    c.create_text(x * z, (w.y + w.h / 2) * z, text=text, fill=color, font=tk_font(w, z),
                  anchor=anchor, tags=TAG, **extra)


def draw_bar(c, w, z, value):
    f = V.fraction(w, value)
    bg, normal = w.get("bg_color"), w.get("color")
    vertical = w.get("orientation") == "vertical"
    n = w.get("segments")
    lo, hi = w.get("min"), w.get("max")
    if n <= 0:
        rounded_rect(c, w.x, w.y, w.x + w.w, w.y + w.h, w.get("radius"), z, fill=bg, outline="")
        col = V.threshold_color(w, value, normal)
        if f > 0:
            if vertical:
                rounded_rect(c, w.x, w.y + w.h * (1 - f), w.x + w.w, w.y + w.h, w.get("radius"), z, fill=col, outline="")
            else:
                rounded_rect(c, w.x, w.y, w.x + w.w * f, w.y + w.h, w.get("radius"), z, fill=col, outline="")
        return
    gap = 2
    length = w.h if vertical else w.w
    seg = (length - gap * (n - 1)) / n
    lit = int(round(f * n))
    for i in range(n):
        seg_value = lo + (hi - lo) * (i + 1) / n
        col = V.threshold_color(w, seg_value, normal) if i < lit else bg
        a = i * (seg + gap)
        if vertical:
            _r(c, w.x, w.y + w.h - a - seg, w.x + w.w, w.y + w.h - a, z, fill=col, outline="")
        else:
            _r(c, w.x + a, w.y, w.x + a + seg, w.y + w.h, z, fill=col, outline="")


def draw_gauge(c, w, z, value):
    th = w.get("thickness")
    size = min(w.w, w.h)
    cx, cy = w.x + w.w / 2, w.y + w.h / 2
    r = size / 2 - th / 2
    a0, a1 = w.get("start_angle"), w.get("end_angle")
    box = ((cx - r) * z, (cy - r) * z, (cx + r) * z, (cy + r) * z)
    # Winkel im Format: 0° = rechts, im Uhrzeigersinn. Tk: gegen den Uhrzeigersinn.
    c.create_arc(*box, start=-a0, extent=-(a1 - a0), style="arc", width=th * z,
                 outline=w.get("bg_color"), tags=TAG)
    f = V.fraction(w, value)
    if f > 0:
        c.create_arc(*box, start=-a0, extent=-(a1 - a0) * f, style="arc", width=th * z,
                     outline=V.threshold_color(w, value, w.get("color")), tags=TAG)


def draw_icon(c, w, z, color):
    icon = w.get("icon")
    x0, y0, x1, y1 = w.x, w.y, w.x + w.w, w.y + w.h
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = min(w.w, w.h)
    P = lambda pts: [p * z for p in pts]  # noqa: E731
    if icon == "arrow_left":
        c.create_polygon(P([x0, cy, cx, y0 + s * 0.1, cx, cy - s * 0.18, x1, cy - s * 0.18,
                            x1, cy + s * 0.18, cx, cy + s * 0.18, cx, y1 - s * 0.1]), fill=color, tags=TAG)
    elif icon == "arrow_right":
        c.create_polygon(P([x1, cy, cx, y0 + s * 0.1, cx, cy - s * 0.18, x0, cy - s * 0.18,
                            x0, cy + s * 0.18, cx, cy + s * 0.18, cx, y1 - s * 0.1]), fill=color, tags=TAG)
    elif icon == "high_beam":
        c.create_arc(*P([cx - s * 0.1, y0 + s * 0.15, cx + s * 0.5, y1 - s * 0.15]), start=90, extent=180,
                     style="chord", fill=color, outline=color, tags=TAG)
        for k in range(4):
            yy = y0 + s * (0.25 + 0.17 * k)
            c.create_line(*P([x0 + s * 0.05, yy, cx - s * 0.15, yy]), fill=color, width=max(1, 2 * z), tags=TAG)
    elif icon == "neutral":
        rounded_rect(c, x0 + 1, y0 + 1, x1 - 1, y1 - 1, s * 0.2, z, fill=color, outline="")
        c.create_text(cx * z, cy * z, text="N", fill="#000000", font=("Arial", -int(s * 0.7 * z), "bold"), tags=TAG)
    elif icon == "light":
        c.create_oval(*P([cx - s * 0.22, cy - s * 0.22, cx + s * 0.22, cy + s * 0.22]), fill=color, outline="", tags=TAG)
        for k in range(8):
            a = k * math.pi / 4
            c.create_line(*P([cx + math.cos(a) * s * 0.3, cy + math.sin(a) * s * 0.3,
                              cx + math.cos(a) * s * 0.45, cy + math.sin(a) * s * 0.45]),
                          fill=color, width=max(1, 2 * z), tags=TAG)
    elif icon == "battery":
        _r(c, x0 + s * 0.1, cy - s * 0.25, x1 - s * 0.1, cy + s * 0.3, z, outline=color, width=max(1, 2 * z))
        _r(c, x0 + s * 0.25, cy - s * 0.35, x0 + s * 0.35, cy - s * 0.25, z, fill=color, outline="")
        _r(c, x1 - s * 0.35, cy - s * 0.35, x1 - s * 0.25, cy - s * 0.25, z, fill=color, outline="")
    elif icon == "temp":
        c.create_line(*P([cx, y0 + s * 0.1, cx, y1 - s * 0.35]), fill=color, width=max(1, s * 0.15 * z), tags=TAG)
        c.create_oval(*P([cx - s * 0.17, y1 - s * 0.4, cx + s * 0.17, y1 - s * 0.06]), fill=color, outline="", tags=TAG)
    elif icon == "lock":
        _r(c, x0 + s * 0.2, cy - s * 0.05, x1 - s * 0.2, y1 - s * 0.1, z, fill=color, outline="")
        c.create_arc(*P([cx - s * 0.2, y0 + s * 0.1, cx + s * 0.2, cy + s * 0.15]), start=0, extent=180,
                     style="arc", outline=color, width=max(1, 2 * z), tags=TAG)
    elif icon == "warning":
        c.create_polygon(P([cx, y0 + s * 0.08, x1 - s * 0.05, y1 - s * 0.1, x0 + s * 0.05, y1 - s * 0.1]),
                         fill=color, tags=TAG)
        c.create_text(cx * z, (cy + s * 0.12) * z, text="!", fill="#000000",
                      font=("Arial", -int(s * 0.5 * z), "bold"), tags=TAG)
    else:
        label = {"gps": "GPS", "bluetooth": "BT", "music": "♪"}.get(icon, "●")
        c.create_text(cx * z, cy * z, text=label, fill=color,
                      font=("Arial", -int(s * (0.4 if len(label) > 1 else 0.7) * z), "bold"), tags=TAG)


def draw_widget(c, w, z, vals, t=None):
    if w.type == "text":
        draw_text(c, w, z, w.get("text"), w.get("color"), wrap=True)
    elif w.type == "value":
        src = S.SOURCE_BY_KEY.get(w.get("source"))
        raw = vals.get(src.key) if src else None
        draw_text(c, w, z, V.display_text(w, vals), V.threshold_color(w, raw, w.get("color")))
    elif w.type == "bar":
        draw_bar(c, w, z, vals.get(w.get("source")))
    elif w.type == "gauge":
        draw_gauge(c, w, z, vals.get(w.get("source")))
    elif w.type == "indicator":
        on = V.indicator_on(w, vals, t)
        draw_icon(c, w, z, w.get("on_color") if on else w.get("off_color"))
    elif w.type == "rect":
        bw = w.get("border_width")
        rounded_rect(c, w.x, w.y, w.x + w.w, w.y + w.h, w.get("radius"), z, fill=w.get("color"),
                     outline=w.get("border_color") if bw else "", width=bw * z if bw else 0)
    else:
        _r(c, w.x, w.y, w.x + w.w, w.y + w.h, z, outline="#E24B4A", dash=(4, 2))
        c.create_text((w.x + 2) * z, (w.y + 2) * z, text=f"unbekannt {w.type}", anchor="nw",
                      fill="#E24B4A", font=("Arial", -10), tags=TAG)


def draw_screen(c, screen, z, vals, size=(480, 320), show_hidden=True, t=None):
    c.delete(TAG)
    bg_item = _r(c, 0, 0, size[0], size[1], z, fill=screen.bg, outline="")
    for w in screen.widgets:
        if w.hidden and not show_hidden:
            continue
        draw_widget(c, w, z, vals, t)
        if w.hidden:
            _r(c, w.x, w.y, w.x + w.w, w.y + w.h, z, outline="#888780", dash=(2, 3))
    return bg_item
