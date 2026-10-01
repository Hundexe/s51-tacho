"""Bearbeitungslogik des Designers, unabhängig von der Oberfläche.

Hält das geöffnete Layout, die aktuelle Seite, die Auswahl und den
Rückgängig-Verlauf. Die Oberfläche (app.py) ruft nur diese Methoden auf,
dadurch lässt sich alles ohne Fenster testen.
"""

import copy

from . import layout_format, presets
from . import schema as S
from .layout_format import Layout, Screen, Widget

HANDLE = 8          # Größe des Ziehpunkts unten rechts in Display-Pixeln
MIN_SIZE = 1


class Editor:
    def __init__(self, layout=None):
        self.layout = layout or presets.klar()
        self.screen_index = 0
        self.selected = None          # Index des gewählten Elements auf der aktuellen Seite
        self.grid = 4
        self.snap = True
        self.path = None
        self.dirty = False
        self._undo = []
        self._redo = []
        self._drag = None

    # -- Seiten -------------------------------------------------------------

    @property
    def screen(self):
        return self.layout.screens[self.screen_index]

    def select_screen(self, index):
        if 0 <= index < len(self.layout.screens):
            self.screen_index = index
            self.selected = None

    def _free_screen_id(self):
        used = {s.id for s in self.layout.screens}
        for i in range(S.MAX_SCREENS):
            if i not in used:
                return i
        raise ValueError(f"Höchstens {S.MAX_SCREENS} Seiten möglich")

    def add_screen(self, name=None):
        self.checkpoint()
        sid = self._free_screen_id()
        self.layout.screens.append(Screen(sid, name or f"Seite {sid + 1}"))
        self.select_screen(len(self.layout.screens) - 1)

    def duplicate_screen(self):
        self.checkpoint()
        src = self.screen
        new = copy.deepcopy(src)
        new.id = self._free_screen_id()
        new.name = src.name + " (Kopie)"
        self.layout.screens.insert(self.screen_index + 1, new)
        self.select_screen(self.screen_index + 1)

    def delete_screen(self):
        if len(self.layout.screens) <= 1:
            raise ValueError("Die letzte Seite kann nicht gelöscht werden")
        self.checkpoint()
        removed = self.layout.screens.pop(self.screen_index)
        for s in self.layout.screens:          # verwaiste Nachtversionen zurücksetzen
            if s.role == "night" and s.night_of == removed.id:
                s.role, s.night_of = "page", S.NO_PAGE
        self.select_screen(max(0, self.screen_index - 1))

    def move_screen(self, delta):
        i, j = self.screen_index, self.screen_index + delta
        if 0 <= j < len(self.layout.screens):
            self.checkpoint()
            sc = self.layout.screens
            sc[i], sc[j] = sc[j], sc[i]
            self.screen_index = j

    def set_screen(self, **changes):
        self.checkpoint()
        for k, v in changes.items():
            setattr(self.screen, k, v)

    def day_pages(self):
        return [s for s in self.layout.screens if s.role == "page"]

    # -- Elemente -----------------------------------------------------------

    @property
    def widget(self):
        if self.selected is None:
            return None
        return self.screen.widgets[self.selected]

    def add_widget(self, type_key, x=None, y=None):
        if len(self.screen.widgets) >= S.MAX_WIDGETS_PER_SCREEN:
            raise ValueError(f"Höchstens {S.MAX_WIDGETS_PER_SCREEN} Elemente pro Seite")
        self.checkpoint()
        w = Widget.new(type_key)
        w.x = self._snap(x if x is not None else (self.layout.width - w.w) // 2)
        w.y = self._snap(y if y is not None else (self.layout.height - w.h) // 2)
        self.screen.widgets.append(w)
        self.selected = len(self.screen.widgets) - 1
        return w

    def delete_widget(self):
        if self.selected is None:
            return
        self.checkpoint()
        self.screen.widgets.pop(self.selected)
        self.selected = None

    def duplicate_widget(self):
        if self.widget is None:
            return
        if len(self.screen.widgets) >= S.MAX_WIDGETS_PER_SCREEN:
            raise ValueError(f"Höchstens {S.MAX_WIDGETS_PER_SCREEN} Elemente pro Seite")
        self.checkpoint()
        w = copy.deepcopy(self.widget)
        w.x += self.grid * 2
        w.y += self.grid * 2
        self.screen.widgets.append(w)
        self.selected = len(self.screen.widgets) - 1

    def raise_widget(self, to_top=False):
        self._reorder(len(self.screen.widgets) - 1 if to_top else (self.selected or 0) + 1)

    def lower_widget(self, to_bottom=False):
        self._reorder(0 if to_bottom else (self.selected or 0) - 1)

    def _reorder(self, target):
        if self.selected is None:
            return
        ws = self.screen.widgets
        target = max(0, min(len(ws) - 1, target))
        if target == self.selected:
            return
        self.checkpoint()
        w = ws.pop(self.selected)
        ws.insert(target, w)
        self.selected = target

    def set_geometry(self, x=None, y=None, w=None, h=None):
        wd = self.widget
        if wd is None:
            return
        self.checkpoint()
        if x is not None:
            wd.x = int(x)
        if y is not None:
            wd.y = int(y)
        if w is not None:
            wd.w = max(MIN_SIZE, int(w))
        if h is not None:
            wd.h = max(MIN_SIZE, int(h))

    def set_prop(self, key, value):
        wd = self.widget
        if wd is None:
            return
        prop = S.PROP_BY_KEY[key]
        layout_format.encode_prop(prop, value)       # prüft den Wert, wirft LayoutError
        self.checkpoint()
        wd.props[key] = value

    def set_flag(self, hidden=None, locked=None):
        wd = self.widget
        if wd is None:
            return
        self.checkpoint()
        if hidden is not None:
            wd.hidden = bool(hidden)
        if locked is not None:
            wd.locked = bool(locked)

    def nudge(self, dx, dy):
        wd = self.widget
        if wd is None or wd.locked:
            return
        self.checkpoint()
        wd.x += dx
        wd.y += dy

    # -- Maus ---------------------------------------------------------------

    def hit_test(self, x, y):
        """Oberstes Element an der Stelle (Display-Pixel) oder None."""
        ws = self.screen.widgets
        for i in range(len(ws) - 1, -1, -1):
            w = ws[i]
            pad = 3 if (w.w < 6 or w.h < 6) else 0     # dünne Linien greifbar machen
            if w.x - pad <= x <= w.x + w.w + pad and w.y - pad <= y <= w.y + w.h + pad:
                return i
        return None

    def on_handle(self, x, y):
        w = self.widget
        if w is None:
            return False
        hx, hy = w.x + w.w, w.y + w.h
        return abs(x - hx) <= HANDLE and abs(y - hy) <= HANDLE

    def press(self, x, y):
        """Maustaste gedrückt. Gibt zurück, ob sich die Auswahl geändert hat."""
        before = self.selected
        if self.widget is not None and self.on_handle(x, y) and not self.widget.locked:
            self._drag = ("resize", x, y, self.widget.w, self.widget.h, False)
            return False
        hit = self.hit_test(x, y)
        self.selected = hit
        if hit is not None and not self.widget.locked:
            self._drag = ("move", x, y, self.widget.x, self.widget.y, False)
        else:
            self._drag = None
        return before != hit

    def drag(self, x, y):
        if self._drag is None:
            return False
        mode, sx, sy, a, b, started = self._drag
        if not started:
            if abs(x - sx) < 2 and abs(y - sy) < 2:
                return False
            self.checkpoint()
            self._drag = (mode, sx, sy, a, b, True)
        w = self.widget
        if mode == "move":
            w.x = self._snap(a + (x - sx))
            w.y = self._snap(b + (y - sy))
        else:
            w.w = max(MIN_SIZE, self._snap(a + (x - sx)))
            w.h = max(MIN_SIZE, self._snap(b + (y - sy)))
        return True

    def release(self):
        self._drag = None

    def _snap(self, v):
        v = int(round(v))
        if self.snap and self.grid > 1:
            return int(round(v / self.grid) * self.grid)
        return v

    # -- Verlauf ------------------------------------------------------------

    def checkpoint(self):
        self._undo.append(self._state())
        if len(self._undo) > 200:
            self._undo.pop(0)
        self._redo.clear()
        self.dirty = True

    def _state(self):
        return (copy.deepcopy(self.layout), self.screen_index, self.selected)

    def _restore(self, st):
        self.layout, self.screen_index, self.selected = copy.deepcopy(st[0]), st[1], st[2]
        if self.screen_index >= len(self.layout.screens):
            self.screen_index = 0
        if self.selected is not None and self.selected >= len(self.screen.widgets):
            self.selected = None
        self.dirty = True

    def undo(self):
        if self._undo:
            self._redo.append(self._state())
            self._restore(self._undo.pop())
            return True
        return False

    def redo(self):
        if self._redo:
            self._undo.append(self._state())
            self._restore(self._redo.pop())
            return True
        return False

    # -- Dateien ------------------------------------------------------------

    def new(self, preset=None):
        self.layout = presets.PRESETS[preset]() if preset else Layout(screens=[Screen(0, "Fahrt")])
        self.screen_index, self.selected, self.path, self.dirty = 0, None, None, False
        self._undo.clear()
        self._redo.clear()

    def open(self, path):
        self.layout = layout_format.load(path)
        self.screen_index, self.selected, self.path, self.dirty = 0, None, path, False
        self._undo.clear()
        self._redo.clear()

    def save(self, path=None):
        path = path or self.path
        n = layout_format.save(self.layout, path)
        self.path, self.dirty = path, False
        return n

    def encoded(self):
        return layout_format.encode(self.layout)
