"""S51 Designer: Oberfläche (Tkinter).

Start:  python -m s51design      (im Ordner designer/)
"""

import base64
from fractions import Fraction
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import __version__, config_format, icons, layout_format, presets, render, sdcard, theme, transfer
from . import images as I
from . import schema as S
from . import values as V
from .editor import Editor
from .theme import C, Tooltip

APP_NAME = "S51 Designer"
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".s51-designer.json")
FILETYPES = [("S51-Layout", "*.s51"), ("Alle Dateien", "*.*")]
CFG_FILETYPES = [("Tacho-Konfiguration", "*.cfg"), ("Alle Dateien", "*.*")]
IMAGE_FILETYPES = [("Bilder", "*.png *.jpg *.jpeg *.bmp *.gif"), ("PNG", "*.png"), ("Alle Dateien", "*.*")]
GRID_STEP = 16
STAGE_MARGIN = 28           # Rand um das Display auf der Zeichenfläche (Bildschirmpixel)
BEZEL = 14                  # Breite des Display-Rahmens (Bildschirmpixel)
SEL_COLOR = C["select"]

ROLE_LABELS = {"page": "Tagseite", "night": "Nachtversion", "startup": "Startbild"}
ZOOMS = (1.0, 1.5, 2.0, 3.0)

# Reihenfolge und Überschriften der Eigenschaften im rechten Bereich.
# Eigenschaften, die hier fehlen, landen unter „Weitere“.
PROP_GROUPS = [
    ("Daten", ("source", "decimals", "unit", "format", "min", "max")),
    ("Text", ("text", "font", "size", "align")),
    ("Form", ("icon", "segments", "orientation", "start_angle", "end_angle", "thickness", "radius",
              "border_width", "blink")),
    ("Farben", ("color", "bg_color", "on_color", "off_color", "border_color")),
    ("Warnschwellen", ("warn_above", "warn_color", "crit_above", "crit_color")),
]

HINTS = {
    "value": "Schwellen: 0 = aus. Ab „Warnung ab“ gilt die Warnfarbe, ab „Kritisch ab“ die Kritisch-Farbe.",
    "bar": "Mit Segmenten bekommt jedes Segment die Farbe seiner Stelle, z. B. der rote Bereich am Ende "
           "des Drehzahlbalkens.",
    "gauge": "Winkel: 0° = rechts, im Uhrzeigersinn. 135° bis 405° ergibt einen unten offenen Dreiviertelkreis.",
    "indicator": "Blinker-Eingänge pulsieren selbst. „Blinken“ ist für Zustände gedacht, die dauerhaft an sind.",
    "image": "Der Tacho zeichnet Bilder immer in Originalgröße ab der linken oberen Ecke. „Bild laden“ "
             "verkleinert ein Bild passend auf die Größe des Rahmens.",
}


def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def enum_labels(enum_name):
    return [label for _, _, label in S.ENUMS[enum_name]]


def enum_key_for_label(enum_name, label):
    for _, key, lbl in S.ENUMS[enum_name]:
        if lbl == label:
            return key
    return None


def enum_label_for_key(enum_name, key):
    for _, k, lbl in S.ENUMS[enum_name]:
        if k == key:
            return lbl
    return str(key)


def parse_prop_text(prop, text):
    """Text aus einem Eingabefeld -> Wert. Wirft ValueError mit verständlicher Meldung."""
    t = prop.type
    text = text.strip()
    if t == "u8":
        v = int(text)
        if not 0 <= v <= 255:
            raise ValueError("Wert muss zwischen 0 und 255 liegen")
        return v
    if t == "i16":
        v = int(text)
        if not -32768 <= v <= 32767:
            raise ValueError("Wert zu groß")
        return v
    if t == "f32":
        return float(text.replace(",", "."))
    return text


def human_size(n):
    if n < 1024:
        return f"{n} Bytes"
    return f"{n / 1024:.1f} KB".replace(".", ",")


class App:
    def __init__(self, root):
        self.root = root
        self.F = theme.apply(root)
        self.ed = Editor()
        self.cfg = config_format.defaults()
        self.cfg_loaded = False        # aus Datei geladen oder im Dialog bearbeitet
        self.settings = load_settings()
        zoom = self.settings.get("zoom", 1.5)
        self.zoom = tk.DoubleVar(value=float(zoom) if zoom in ZOOMS else 1.5)   # float, passend zu den Zoom-Knöpfen
        self.show_grid = tk.BooleanVar(value=True)
        self.snap = tk.BooleanVar(value=True)
        self.preview = tk.BooleanVar(value=False)
        self.animate = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="")
        self.size_info = tk.StringVar(value="")
        self.inspector_title = tk.StringVar(value="")
        self.inspector_sub = tk.StringVar(value="")
        self._prop_vars = {}
        self._bg_item = None
        self._icons = {}
        self._photos = {}              # (Bild-Objekt, Zoom) -> tk.PhotoImage
        self._origin = (0, 0)          # Lage des Displays auf der Zeichenfläche
        self.ui_queue = queue.Queue()  # Aufgaben aus Hintergrund-Threads für die Oberfläche

        root.title(APP_NAME)
        root.geometry("1440x860")
        root.minsize(1100, 640)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._build_menu()
        self._build_ui()
        self._bind_keys()
        self.refresh_all()
        self._tick()

    # ------------------------------------------------------------------ Hilfen

    def icon(self, name, kind="tool"):
        key = (kind, name)
        if key not in self._icons:
            table = {"tool": icons.TOOL, "accent": icons.TOOL_ACCENT, "element": icons.ELEMENTS}[kind]
            self._icons[key] = tk.PhotoImage(data=table[name])
        return self._icons[key]

    def tool_button(self, parent, icon_name, tip, command):
        b = ttk.Button(parent, image=self.icon(icon_name), style="Tool.TButton", command=command, takefocus=False)
        Tooltip(b, tip)
        return b

    @staticmethod
    def heading(parent, text, row, pady=(16, 6)):
        ttk.Label(parent, text=text.upper(), style="Head.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=pady)

    @staticmethod
    def note(parent, text, row, pady=(8, 0)):
        ttk.Label(parent, text=text, style="Muted.TLabel", wraplength=290, justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=pady)

    # ------------------------------------------------------------------ Aufbau

    def _build_menu(self):
        m = tk.Menu(self.root)
        f = tk.Menu(m, tearoff=False)
        f.add_command(label="Neu (leer)", command=lambda: self.new(None))
        vorlagen = tk.Menu(f, tearoff=False)
        for name in presets.PRESETS:
            vorlagen.add_command(label=name, command=lambda n=name: self.new(n))
        f.add_cascade(label="Neu aus Vorlage", menu=vorlagen)
        f.add_command(label="Öffnen…", accelerator="Strg+O", command=self.open)
        f.add_command(label="Speichern", accelerator="Strg+S", command=self.save)
        f.add_command(label="Speichern unter…", command=self.save_as)
        f.add_separator()
        f.add_command(label="Auf SD-Karte exportieren…", command=self.export_sd)
        f.add_command(label="Drahtlos übertragen…", command=self.open_wireless)
        f.add_separator()
        f.add_command(label="Beenden", command=self.quit)
        m.add_cascade(label="Datei", menu=f)

        e = tk.Menu(m, tearoff=False)
        e.add_command(label="Rückgängig", accelerator="Strg+Z", command=self.undo)
        e.add_command(label="Wiederholen", accelerator="Strg+Y", command=self.redo)
        e.add_separator()
        e.add_command(label="Bild laden…", command=self.import_image)
        e.add_command(label="Element duplizieren", accelerator="Strg+D", command=self.duplicate)
        e.add_command(label="Element löschen", accelerator="Entf", command=self.delete)
        e.add_separator()
        e.add_command(label="Ganz nach vorn", command=lambda: self._act(lambda: self.ed.raise_widget(True)))
        e.add_command(label="Eine Ebene nach vorn", command=lambda: self._act(self.ed.raise_widget))
        e.add_command(label="Eine Ebene nach hinten", command=lambda: self._act(self.ed.lower_widget))
        e.add_command(label="Ganz nach hinten", command=lambda: self._act(lambda: self.ed.lower_widget(True)))
        m.add_cascade(label="Bearbeiten", menu=e)

        c = tk.Menu(m, tearoff=False)
        c.add_command(label="Tacho-Konfiguration bearbeiten…", command=self.open_config)
        c.add_command(label="Konfiguration laden…", command=self.load_config)
        c.add_command(label="Konfiguration speichern unter…", command=self.save_config_as)
        m.add_cascade(label="Einstellungen", menu=c)

        h = tk.Menu(m, tearoff=False)
        h.add_command(label="Über", command=lambda: messagebox.showinfo(
            APP_NAME, f"{APP_NAME} {__version__}\nLayouts und Einstellungen für den S51-Tacho.\n"
                      f"Dateiformat S51L {S.VERSION_MAJOR}.{S.VERSION_MINOR}"))
        m.add_cascade(label="Hilfe", menu=h)
        self.root.config(menu=m)

    def _build_ui(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self._build_toolbar()
        body = ttk.Frame(root, style="Bg.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_stage(body)
        self._build_inspector(body)
        bar = ttk.Frame(root, style="Bg.TFrame", padding=(12, 3))
        bar.grid(row=2, column=0, sticky="ew")
        ttk.Label(bar, textvariable=self.status, style="Status.TLabel").pack(side="left")
        ttk.Label(bar, textvariable=self.size_info, style="Status.TLabel").pack(side="right")

    def _build_toolbar(self):
        tb = ttk.Frame(self.root, style="Bar.TFrame", padding=(10, 6))
        tb.grid(row=0, column=0, sticky="ew")
        ttk.Label(tb, text="S51 Designer", style="Brand.TLabel").pack(side="left", padx=(4, 16))
        groups = [
            [("new", "Neues leeres Layout", lambda: self.new(None)),
             ("open", "Öffnen (Strg+O)", self.open),
             ("save", "Speichern (Strg+S)", self.save)],
            [("undo", "Rückgängig (Strg+Z)", self.undo),
             ("redo", "Wiederholen (Strg+Y)", self.redo)],
            [("duplicate", "Element duplizieren (Strg+D)", self.duplicate),
             ("delete", "Element löschen (Entf)", self.delete),
             ("front", "Ganz nach vorn", lambda: self._act(lambda: self.ed.raise_widget(True))),
             ("back", "Ganz nach hinten", lambda: self._act(lambda: self.ed.lower_widget(True)))],
            [("image_load", "Bild laden (PNG, JPG, BMP)", self.import_image),
             ("settings", "Tacho-Konfiguration", self.open_config)],
        ]
        for gi, group in enumerate(groups):
            if gi:
                ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=8, pady=4)
            for name, tip, cmd in group:
                self.tool_button(tb, name, tip, cmd).pack(side="left", padx=1)
        send = ttk.Button(tb, text="Drahtlos senden", style="Accent.TButton", command=self.open_wireless,
                          takefocus=False)
        send.pack(side="right", padx=(6, 2))
        Tooltip(send, "Layout und Einstellungen per WLAN zum Tacho schicken")
        sd = ttk.Button(tb, text="Auf SD-Karte", image=self.icon("sd"), compound="left",
                        command=self.export_sd, takefocus=False)
        sd.pack(side="right", padx=4)
        Tooltip(sd, "Layout und Einstellungen in den Ordner s51 einer SD-Karte schreiben")

    def _build_left(self, parent):
        left = ttk.Frame(parent, padding=(14, 4, 14, 12), width=272)
        left.grid(row=0, column=0, sticky="ns")
        left.pack_propagate(False)

        ttk.Label(left, text="ELEMENTE", style="Head.TLabel").pack(anchor="w", pady=(10, 8))
        tiles = ttk.Frame(left)
        tiles.pack(fill="x")
        tiles.columnconfigure((0, 1), weight=1, uniform="tiles")
        for i, wt in enumerate(S.WIDGET_TYPES):
            b = ttk.Button(tiles, text=wt.label, image=self.icon(wt.key, "element"), compound="top",
                           style="Tile.TButton", command=lambda k=wt.key: self.add_widget(k), takefocus=False)
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            Tooltip(b, "Bild-Element hinzufügen. Das Bild selbst kommt über „Bild laden“."
                    if wt.key == "image" else f"{wt.label} hinzufügen")

        head = ttk.Frame(left)
        head.pack(fill="x", pady=(16, 6))
        ttk.Label(head, text="SEITEN", style="Head.TLabel").pack(side="left")
        for name, tip, cmd in (("down", "Seite nach unten", lambda: self._act(lambda: self.ed.move_screen(1))),
                               ("up", "Seite nach oben", lambda: self._act(lambda: self.ed.move_screen(-1))),
                               ("delete", "Seite löschen", self.ed_del_screen),
                               ("duplicate", "Seite kopieren", self.ed_dup_screen),
                               ("plus", "Neue Seite", self.ed_add_screen)):
            self.tool_button(head, name, tip, cmd).pack(side="right")
        self.screen_list = tk.Listbox(left, height=7, exportselection=False, font=self.F["base"])
        self.screen_list.pack(fill="x")
        self.screen_list.bind("<<ListboxSelect>>", self._on_screen_select)

        ttk.Label(left, text="EBENEN  ·  OBEN LIEGT VORN", style="Head.TLabel").pack(anchor="w", pady=(16, 6))
        self.widget_list = tk.Listbox(left, exportselection=False, font=self.F["small"])
        self.widget_list.pack(fill="both", expand=True)
        self.widget_list.bind("<<ListboxSelect>>", self._on_widget_list_select)

    def _build_stage(self, parent):
        mid = ttk.Frame(parent, style="Stage.TFrame")
        mid.grid(row=0, column=1, sticky="nsew")
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(mid, background=C["stage"], highlightthickness=0, cursor="arrow")
        xs = ttk.Scrollbar(mid, orient="horizontal", command=self.canvas.xview, style="Stage.Horizontal.TScrollbar")
        ys = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview, style="Stage.Vertical.TScrollbar")
        self.canvas.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Configure>", lambda e: self._update_scrollregion())

        opts = ttk.Frame(mid, style="Stage.TFrame", padding=(14, 8))
        opts.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(opts, text="Zoom", style="Stage.TLabel").pack(side="left", padx=(0, 6))
        for z in ZOOMS:
            ttk.Radiobutton(opts, text=f"{z:g}×".replace(".", ","), value=z, variable=self.zoom, style="Seg.Toolbutton",
                            command=self._zoom_changed, takefocus=False).pack(side="left")
        ttk.Frame(opts, style="Stage.TFrame", width=18).pack(side="left")
        for text, var, cmd, tip in (
                ("Raster", self.show_grid, self.redraw, "Hilfslinien alle 16 Pixel"),
                ("Einrasten", self.snap, lambda: setattr(self.ed, "snap", self.snap.get()),
                 "Position und Größe rasten auf 4 Pixel ein"),
                ("Vorschau", self.preview, self.redraw,
                 "Seite wie am Tacho zeigen, ohne Auswahl, Raster und versteckte Elemente"),
                ("Demo-Werte", self.animate, self.redraw, "Geschwindigkeit, Drehzahl, Blinker usw. laufen lassen")):
            cb = ttk.Checkbutton(opts, text=text, variable=var, command=cmd, style="Chip.Toolbutton",
                                 takefocus=False)
            cb.pack(side="left", padx=2)
            Tooltip(cb, tip)
        self.pos_label = ttk.Label(opts, text="", style="Stage.TLabel")
        self.pos_label.pack(side="right")

    def _build_inspector(self, parent):
        right = ttk.Frame(parent, padding=(16, 12, 6, 10), width=345)
        right.grid(row=0, column=2, sticky="ns")
        right.grid_propagate(False)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        head = ttk.Frame(right)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        ttk.Label(head, textvariable=self.inspector_title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(head, textvariable=self.inspector_sub, style="Muted.TLabel").pack(anchor="w")
        pc = tk.Canvas(right, highlightthickness=0, background=C["panel"], width=310)
        psb = ttk.Scrollbar(right, orient="vertical", command=pc.yview)
        pc.configure(yscrollcommand=psb.set)
        pc.grid(row=1, column=0, sticky="nsew")
        psb.grid(row=1, column=1, sticky="ns")
        self.props_frame = ttk.Frame(pc)
        pc.create_window((0, 0), window=self.props_frame, anchor="nw", width=302)
        self.props_frame.bind("<Configure>", lambda e: pc.configure(scrollregion=pc.bbox("all")))
        self.props_canvas = pc

    def _bind_keys(self):
        r = self.root
        r.bind_all("<Control-z>", lambda e: self.undo())
        r.bind_all("<Control-y>", lambda e: self.redo())
        r.bind_all("<Control-s>", lambda e: self.save())
        r.bind_all("<Control-o>", lambda e: self.open())
        r.bind_all("<Control-d>", lambda e: self.duplicate())
        r.bind_all("<MouseWheel>", self._on_wheel)
        c = self.canvas
        c.bind("<Delete>", lambda e: self.delete())
        c.bind("<BackSpace>", lambda e: self.delete())
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            c.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy))
            c.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx * 10, dy * 10))

    def _on_wheel(self, event):
        """Mausrad scrollt die Eigenschaften, wenn der Mauszeiger darüber steht."""
        try:
            w = self.root.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError):
            return
        while w is not None:
            if w is self.props_canvas:
                self.props_canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")
                return
            w = getattr(w, "master", None)

    # ------------------------------------------------------------------ Zeichnen

    def z(self):
        return self.zoom.get()

    def _zoom_changed(self):
        self.settings["zoom"] = self.z()
        self._update_scrollregion()
        self.redraw()

    def _update_scrollregion(self):
        """Display mittig in der Fläche, mit Rand für den Rahmen. Das Display beginnt immer bei (0, 0)."""
        c, z, L = self.canvas, self.z(), self.ed.layout
        w, h = int(L.width * z) + 2 * STAGE_MARGIN, int(L.height * z) + 2 * STAGE_MARGIN
        try:
            cw, ch = int(c.winfo_width()), int(c.winfo_height())
        except (tk.TclError, TypeError, ValueError):
            cw, ch = 0, 0
        left = -STAGE_MARGIN - max(0, (cw - w) // 2)
        top = -STAGE_MARGIN - max(0, (ch - h) // 2)
        c.configure(scrollregion=(left, top, left + max(cw, w), top + max(ch, h)))
        c.xview_moveto(0)
        c.yview_moveto(0)

    def photo_for(self, img_id, z):
        """Tk-Bild für ein Bild des Layouts in der passenden Vergrößerung (zwischengespeichert)."""
        img = self.ed.image_by_id(img_id)
        if img is None:
            return None
        key = (id(img), z)
        entry = self._photos.get(key)
        if entry is None or entry[0] is not img:
            data = base64.b64encode(I.png_encode(img.width, img.height, I.to_rgba(img))).decode("ascii")
            photo = tk.PhotoImage(data=data)
            f = Fraction(z).limit_denominator(4)        # 1,5 = 3/2: erst verdreifachen, dann halbieren
            if f.numerator > 1:
                photo = photo.zoom(f.numerator, f.numerator)
            if f.denominator > 1:
                photo = photo.subsample(f.denominator, f.denominator)
            entry = (img, photo)
            self._photos[key] = entry
        return entry[1]

    def redraw(self):
        c, z, L = self.canvas, self.z(), self.ed.layout
        c.delete("bezel")
        W, H, b = L.width * z, L.height * z, BEZEL
        r = 16
        pts = [-b + r, -b, W + b - r, -b, W + b, -b, W + b, -b + r, W + b, H + b - r, W + b, H + b,
               W + b - r, H + b, -b + r, H + b, -b, H + b, -b, H + b - r, -b, -b + r, -b, -b]
        c.create_polygon(pts, smooth=True, fill="#050605", outline=C["border"], tags="bezel")
        vals = V.demo_values(animate=self.animate.get())
        self._bg_item = render.draw_screen(c, self.ed.screen, z, vals, (L.width, L.height),
                                           show_hidden=not self.preview.get(), image_for=self.photo_for)
        c.tag_lower("bezel")
        c.delete("grid")
        if self.show_grid.get() and not self.preview.get():
            for x in range(GRID_STEP, L.width, GRID_STEP):
                c.create_line(x * z, 0, x * z, L.height * z, fill="#1c2320", tags="grid")
            for y in range(GRID_STEP, L.height, GRID_STEP):
                c.create_line(0, y * z, L.width * z, y * z, fill="#1c2320", tags="grid")
            if self._bg_item is not None:
                c.tag_raise("grid", self._bg_item)
        self._draw_selection()

    def _draw_selection(self):
        c, z = self.canvas, self.z()
        c.delete("sel")
        w = self.ed.widget
        if w is None or self.preview.get():
            return
        c.create_rectangle(w.x * z - 1, w.y * z - 1, (w.x + w.w) * z + 1, (w.y + w.h) * z + 1,
                           outline=SEL_COLOR, width=2 if z > 1 else 1, tags="sel")
        if not w.locked:
            hx, hy = (w.x + w.w) * z, (w.y + w.h) * z
            c.create_rectangle(hx - 5, hy - 5, hx + 5, hy + 5, fill=SEL_COLOR, outline="white", tags="sel")

    def refresh_lists(self):
        sl = self.screen_list
        sl.delete(0, "end")
        for s in self.ed.layout.screens:
            suffix = ""
            if s.role == "night":
                day = next((d for d in self.ed.layout.screens if d.id == s.night_of and d.role == "page"), None)
                suffix = f"  · Nacht von {day.name}" if day else "  · Nacht"
            elif s.role == "startup" and "startbild" not in s.name.lower():
                suffix = "  · Startbild"
            sl.insert("end", f"{s.name}{suffix}")
        sl.selection_clear(0, "end")
        sl.selection_set(self.ed.screen_index)
        wl = self.widget_list
        wl.delete(0, "end")
        ws = self.ed.screen.widgets
        for w in reversed(ws):                         # oberstes Element zuerst, wie in Grafikprogrammen
            wl.insert("end", self._widget_title(w))
        if self.ed.selected is not None:
            row = len(ws) - 1 - self.ed.selected
            wl.selection_set(row)
            wl.see(row)

    def _widget_title(self, w):
        wt = S.WTYPE_BY_KEY.get(w.type)
        label = wt.label if wt else w.type
        detail = ""
        if w.type == "text":
            detail = w.get("text").replace("\n", " ")
        elif w.type == "image":
            img = self.ed.image_by_id(w.get("image"))
            detail = img.name if img else "kein Bild"
        elif "source" in w.props:
            src = S.SOURCE_BY_KEY.get(w.get("source"))
            detail = src.label if src else ""
        text = f"{label}: {detail}" if detail else label
        if len(text) > 34:
            text = text[:33] + "…"
        return text + (" · versteckt" if w.hidden else "") + (" · gesperrt" if w.locked else "")

    def refresh_all(self):
        self._update_scrollregion()
        self.refresh_lists()
        self.redraw()
        self.build_props()
        self.update_title()

    def update_title(self):
        name = os.path.basename(self.ed.path) if self.ed.path else "Unbenannt"
        self.root.title(f"{'● ' if self.ed.dirty else ''}{name} – {APP_NAME}")
        n = len(self.ed.screen.widgets)
        self.status.set(f"„{self.ed.layout.name}“ · Seite „{self.ed.screen.name}“ · {n} von "
                        f"{S.MAX_WIDGETS_PER_SCREEN} Elementen")
        try:
            size = len(self.ed.encoded())
            self.size_info.set(f"Dateigröße {human_size(size)} von höchstens {human_size(S.MAX_FILE_SIZE)}")
        except layout_format.LayoutError as e:
            self.size_info.set(f"Layout so nicht speicherbar: {e}")

    def _tick(self):
        while True:
            try:
                job = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            job()
        if self.animate.get():
            self.redraw()
        self.root.after(100, self._tick)

    # ------------------------------------------------------------------ Eigenschaften

    def build_props(self):
        f = self.props_frame
        for child in f.winfo_children():
            child.destroy()
        self._prop_vars = {}
        f.columnconfigure(0, weight=0, minsize=118)
        f.columnconfigure(1, weight=1)
        w = self.ed.widget
        if w is None:
            self._build_screen_props(f)
        else:
            self._build_widget_props(f, w)
        self.props_canvas.yview_moveto(0)

    def _row_label(self, f, r, text):
        ttk.Label(f, text=text, style="Muted.TLabel").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=3)

    def _entry(self, f, r, value, on_commit, width=18, column=1, sticky="ew"):
        var = tk.StringVar(value=str(value))
        e = ttk.Entry(f, textvariable=var, width=width)
        e.grid(row=r, column=column, sticky=sticky, pady=3, padx=(0, 6) if column == 0 else 0)

        def commit(_event=None):
            on_commit(var.get(), var, e)
        e.bind("<Return>", commit)
        e.bind("<FocusOut>", commit)
        return var

    def _color_field(self, f, r, color, on_pick):
        """Farbfeld: Fläche zum Anklicken und Hex-Wert zum Eintippen."""
        box = ttk.Frame(f)
        box.grid(row=r, column=1, sticky="ew", pady=3)
        swatch = tk.Label(box, width=3, background=color, borderwidth=0, highlightthickness=1,
                          highlightbackground=C["border"], cursor="hand2")
        swatch.pack(side="left", padx=(0, 6), fill="y")
        var = tk.StringVar(value=color)
        entry = ttk.Entry(box, textvariable=var, width=9, font=self.F["mono"])
        entry.pack(side="left", fill="x", expand=True)

        def apply(new):
            new = new.strip().upper()
            if not new.startswith("#"):
                new = "#" + new
            old = str(swatch.cget("background")).upper()
            if len(new) != 7 or any(ch not in "0123456789ABCDEF" for ch in new[1:]):
                var.set(old)
                self.status.set("Farbe bitte als #RRGGBB eingeben, z. B. #1D9E75.")
                return
            var.set(new)
            if new != old:
                swatch.configure(background=new)
                on_pick(new)

        def pick(_e=None):
            res = colorchooser.askcolor(color=swatch.cget("background"), parent=self.root, title="Farbe wählen")
            if res and res[1]:
                apply(res[1])
        swatch.bind("<Button-1>", pick)
        entry.bind("<Return>", lambda e: apply(var.get()))
        entry.bind("<FocusOut>", lambda e: apply(var.get()))
        return var

    def _build_screen_props(self, f):
        s = self.ed.screen
        self.inspector_title.set(s.name)
        self.inspector_sub.set(f"{ROLE_LABELS.get(s.role, s.role)} · Seite {self.ed.screen_index + 1} von "
                               f"{len(self.ed.layout.screens)}")
        r = 0
        self.heading(f, "Seite", r, pady=(6, 6))
        r += 1
        self._row_label(f, r, "Name")
        self._entry(f, r, s.name, lambda v, var, e: self._set_screen(name=v.strip() or s.name))
        r += 1
        self._row_label(f, r, "Hintergrund")
        self._color_field(f, r, s.bg, lambda c: self._set_screen(bg=c))
        r += 1
        self._row_label(f, r, "Art")
        role = ttk.Combobox(f, state="readonly", values=list(ROLE_LABELS.values()))
        role.set(ROLE_LABELS.get(s.role, ROLE_LABELS["page"]))
        role.grid(row=r, column=1, sticky="ew", pady=3)
        r += 1
        days = [d for d in self.ed.layout.screens if d.role == "page" and d is not s]
        self._row_label(f, r, "Nacht für")
        night = ttk.Combobox(f, state="readonly", values=[d.name for d in days])
        current = next((d for d in days if d.id == s.night_of), None)
        if current:
            night.set(current.name)
        night.grid(row=r, column=1, sticky="ew", pady=3)
        night.configure(state="readonly" if s.role == "night" else "disabled")

        def on_role(_e=None):
            key = next((k for k, v in ROLE_LABELS.items() if v == role.get()), "page")
            try:
                if key in ("page", "startup"):
                    self._set_screen(role=key, night_of=S.NO_PAGE)
                elif days:
                    self._set_screen(role="night", night_of=(current or days[0]).id)
                else:
                    messagebox.showinfo(APP_NAME, "Zuerst eine Tagseite anlegen, zu der diese Nachtversion gehört.")
            except ValueError as e:
                messagebox.showwarning(APP_NAME, str(e))
            self.build_props()

        def on_night(_e=None):
            target = next((d for d in days if d.name == night.get()), None)
            if target:
                self._set_screen(night_of=target.id)
        role.bind("<<ComboboxSelected>>", on_role)
        night.bind("<<ComboboxSelected>>", on_night)
        r += 1
        if s.role == "startup":
            self.note(f, "Diese Seite zeigt der Tacho beim Einschalten, so lange wie in der Konfiguration unter "
                         "anzeige.startbild_dauer_s eingestellt. Im Fahrbetrieb taucht sie nicht auf.", r)
        else:
            self.note(f, "Nachtversionen ersetzen ihre Tagseite, wenn der Nachtmodus an ist. Eine Seite der Art "
                         "„Startbild“ zeigt der Tacho beim Einschalten.", r)
        r += 1

        self.heading(f, "Layout", r)
        r += 1
        self._row_label(f, r, "Name")
        self._entry(f, r, self.ed.layout.name, lambda v, var, e: self._set_layout(name=v.strip()))
        r += 1
        self._row_label(f, r, "Autor")
        self._entry(f, r, self.ed.layout.author, lambda v, var, e: self._set_layout(author=v.strip()))
        r += 1

        self.heading(f, f"Bilder im Layout  ·  {len(self.ed.layout.images)} von {S.MAX_IMAGES}", r)
        r += 1
        if not self.ed.layout.images:
            self.note(f, "Noch keine Bilder. „Bild laden“ setzt ein Bild als neues Element auf die Seite.", r,
                      pady=(0, 0))
            r += 1
        for img in self.ed.layout.images:
            row = ttk.Frame(f)
            row.grid(row=r, column=0, columnspan=2, sticky="ew", pady=1)
            thumb = self._thumbnail(img)
            if thumb is not None:
                tk.Label(row, image=thumb, background=C["field"], width=28, height=28, borderwidth=0).pack(
                    side="left", padx=(0, 8))
            txt = ttk.Frame(row)
            txt.pack(side="left", fill="x", expand=True)
            ttk.Label(txt, text=img.name[:26]).pack(anchor="w")
            used = self.ed.image_usage(img.id)
            ttk.Label(txt, text=f"{img.width}×{img.height} · {used}× benutzt", style="Muted.TLabel").pack(anchor="w")
            self.tool_button(row, "delete", "Bild aus dem Layout löschen",
                             lambda i=img: self.delete_image(i)).pack(side="right")
            r += 1
        ttk.Button(f, text="Bild laden…", image=self.icon("image_load"), compound="left",
                   command=self.import_image, takefocus=False).grid(row=r, column=0, columnspan=2,
                                                                     sticky="w", pady=(8, 0))
        r += 1
        self.heading(f, "Bedienung", r)
        r += 1
        self.note(f, "Element anklicken, um es zu bearbeiten. Ziehen verschiebt, der Punkt unten rechts ändert die "
                     "Größe. Pfeiltasten verschieben um 1 Pixel, mit Umschalt um 10.", r, pady=(0, 0))

    def _thumbnail(self, img):
        """Kleine Vorschau (höchstens 28 Pixel) für die Bilderliste."""
        key = ("thumb", id(img))
        entry = self._photos.get(key)
        if entry is not None and entry[0] is img:
            return entry[1]
        try:
            tw, th = I.fit_size(img.width, img.height, 28, 28)
            rgba = I.resize_rgba(img.width, img.height, I.to_rgba(img), tw, th)
            data = base64.b64encode(I.png_encode(tw, th, rgba)).decode("ascii")
            photo = tk.PhotoImage(data=data)
        except (tk.TclError, I.ImageError, ValueError):
            return None
        self._photos[key] = (img, photo)
        return photo

    def _build_widget_props(self, f, w):
        wt = S.WTYPE_BY_KEY.get(w.type)
        self.inspector_title.set(wt.label if wt else f"Unbekannter Typ {w.type}")
        self.inspector_sub.set(f"Ebene {self.ed.selected + 1} von {len(self.ed.screen.widgets)} · "
                               f"Seite „{self.ed.screen.name}“")
        r = 0
        self.heading(f, "Position und Größe", r, pady=(6, 4))
        r += 1
        geo = ttk.Frame(f)
        geo.grid(row=r, column=0, columnspan=2, sticky="ew")
        geo.columnconfigure((0, 1), weight=1, uniform="geo")
        for i, (key, label) in enumerate((("x", "X"), ("y", "Y"), ("w", "Breite"), ("h", "Höhe"))):
            gr, gc = (i // 2) * 2, i % 2
            ttk.Label(geo, text=label, style="Muted.TLabel").grid(row=gr, column=gc, sticky="w", pady=(2, 0))
            self._prop_vars[key] = self._entry(geo, gr + 1, getattr(w, key),
                                               lambda v, var, e, k=key: self._commit_geometry(k, v, var),
                                               width=8, column=gc)
        r += 1
        flags = ttk.Frame(f)
        flags.grid(row=r, column=0, columnspan=2, sticky="w", pady=(8, 0))
        hidden = tk.BooleanVar(value=w.hidden)
        locked = tk.BooleanVar(value=w.locked)
        hb = ttk.Checkbutton(flags, text="Versteckt", image=self.icon("hidden"), compound="left", variable=hidden,
                             style="Chip.Toolbutton", takefocus=False,
                             command=lambda: self._act(lambda: self.ed.set_flag(hidden=hidden.get())))
        hb.pack(side="left")
        Tooltip(hb, "Im Designer blass, am Tacho unsichtbar")
        lb = ttk.Checkbutton(flags, text="Gesperrt", image=self.icon("lock"), compound="left", variable=locked,
                             style="Chip.Toolbutton", takefocus=False,
                             command=lambda: self._act(lambda: self.ed.set_flag(locked=locked.get())))
        lb.pack(side="left", padx=4)
        Tooltip(lb, "Kann nicht aus Versehen verschoben werden")
        r += 1
        if wt is None:
            return
        if w.type == "image":
            r = self._build_image_props(f, w, r)
        grouped = set()
        for title, keys in PROP_GROUPS:
            keys = [k for k in keys if k in wt.props]
            grouped.update(keys)
            if not keys:
                continue
            self.heading(f, title, r)
            r += 1
            for key in keys:
                self._prop_row(f, r, w, key)
                r += 1
        rest = [k for k in wt.props if k not in grouped and k != "image"]
        if rest:
            self.heading(f, "Weitere", r)
            r += 1
            for key in rest:
                self._prop_row(f, r, w, key)
                r += 1
        hint = HINTS.get(w.type)
        if hint:
            self.note(f, hint, r, pady=(16, 0))

    def _prop_row(self, f, r, w, key):
        prop = S.PROP_BY_KEY[key]
        value = w.get(key)
        self._row_label(f, r, prop.label)
        t = prop.type
        if t == "color":
            self._color_field(f, r, value, lambda c, k=key: self._commit_prop(k, c))
        elif t == "bool":
            var = tk.BooleanVar(value=bool(value))
            ttk.Checkbutton(f, variable=var, command=lambda k=key, v=var: self._commit_prop(k, v.get())).grid(
                row=r, column=1, sticky="w")
        elif t.startswith("enum:"):
            enum = t[5:]
            labels = self._source_labels(w.type) if enum == "source" else enum_labels(enum)
            cb = ttk.Combobox(f, state="readonly", values=labels)
            cb.set(enum_label_for_key(enum, value))
            cb.grid(row=r, column=1, sticky="ew", pady=3)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, k=key, en=enum, c=cb: self._commit_prop(k, enum_key_for_label(en, c.get())))
        else:
            self._entry(f, r, self._fmt(prop, value), lambda v, var, e, p=prop: self._commit_text_prop(p, v, var))

    def _build_image_props(self, f, w, r):
        self.heading(f, "Bild", r)
        r += 1
        imgs = list(self.ed.layout.images)
        self._row_label(f, r, "Bild")
        names = ["Kein Bild"] + [f"{i.name} ({i.width}×{i.height})" for i in imgs]
        cb = ttk.Combobox(f, state="readonly", values=names)
        cur = self.ed.image_by_id(w.get("image"))
        cb.set(names[imgs.index(cur) + 1] if cur in imgs else names[0])
        cb.grid(row=r, column=1, sticky="ew", pady=3)

        def on_pick(_e=None):
            idx = names.index(cb.get()) if cb.get() in names else 0
            self._commit_prop("image", S.NO_IMAGE if idx == 0 else imgs[idx - 1].id)
            self.build_props()
        cb.bind("<<ComboboxSelected>>", on_pick)
        r += 1
        row = ttk.Frame(f)
        row.grid(row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))
        load = ttk.Button(row, text="Bild laden…", image=self.icon("image_load"), compound="left",
                          command=self.import_image, takefocus=False)
        load.pack(side="left")
        Tooltip(load, "Neues Bild laden und in diesen Rahmen einpassen")
        orig = ttk.Button(row, text="Originalgröße", style="Small.TButton", takefocus=False,
                          command=self.image_original_size)
        orig.pack(side="left", padx=6)
        Tooltip(orig, "Rahmen genau auf die Größe des Bildes setzen")
        if cur is not None and (cur.width, cur.height) != (w.w, w.h):
            r += 1
            self.note(f, f"Rahmen {w.w}×{w.h}, Bild {cur.width}×{cur.height}. Der Tacho zeichnet das Bild in "
                         "Originalgröße und schneidet am Rahmen ab.", r, pady=(6, 0))
        return r + 1

    def _source_labels(self, wtype):
        if wtype == "indicator":
            return [s.label for s in S.SOURCES if s.kind == "bool" or s.key == "none"]
        if wtype in ("bar", "gauge"):
            return [s.label for s in S.SOURCES if s.kind == "number" or s.key == "none"]
        return [s.label for s in S.SOURCES]

    @staticmethod
    def _fmt(prop, value):
        if prop.type == "f32":
            return f"{float(value):g}"
        return str(value)

    def _commit_geometry(self, key, text, var):
        w = self.ed.widget
        if w is None:
            return
        try:
            v = int(text.strip())
        except ValueError:
            var.set(str(getattr(w, key)))
            self.status.set("Bitte eine ganze Zahl eingeben.")
            return
        if v == getattr(w, key):
            return
        self.ed.set_geometry(**{key: v})
        var.set(str(getattr(w, key)))
        self.redraw()
        self.update_title()

    def _commit_text_prop(self, prop, text, var):
        w = self.ed.widget
        if w is None:
            return
        try:
            value = parse_prop_text(prop, text)
            if value == w.get(prop.key):
                return
            self.ed.set_prop(prop.key, value)
        except (ValueError, layout_format.LayoutError) as e:
            var.set(self._fmt(prop, w.get(prop.key)))
            self.status.set(f"{prop.label}: {e}")
            return
        self.redraw()
        self.refresh_lists()
        self.update_title()

    def _commit_prop(self, key, value):
        if value is None:
            return
        try:
            self.ed.set_prop(key, value)
        except layout_format.LayoutError as e:
            self.status.set(str(e))
            return
        self.redraw()
        self.refresh_lists()
        self.update_title()

    def _set_screen(self, **changes):
        if all(getattr(self.ed.screen, k) == v for k, v in changes.items()):
            return
        self.ed.set_screen(**changes)
        self.refresh_lists()
        self.redraw()
        self.update_title()
        if self.ed.widget is None:
            self.inspector_title.set(self.ed.screen.name)

    def _set_layout(self, **changes):
        if all(getattr(self.ed.layout, k) == v for k, v in changes.items()):
            return
        self.ed.checkpoint()
        for k, v in changes.items():
            setattr(self.ed.layout, k, v)
        self.update_title()

    # ------------------------------------------------------------------ Bilder

    def import_image(self, path=None):
        """Bild laden. Ist ein Bild-Element gewählt, wird das Bild in dessen Rahmen eingepasst,
        sonst als neues Element in die Mitte gesetzt."""
        if path is None:
            path = filedialog.askopenfilename(parent=self.root, filetypes=IMAGE_FILETYPES, title="Bild laden",
                                              initialdir=self.settings.get("last_img_dir"))
        if not path:
            return False
        try:
            width, height, rgba = I.load_rgba(path, max_side=S.MAX_IMAGE_SIDE)
        except Exception as e:  # noqa: BLE001 – Pillow und der PNG-Leser melden viele Fehlerarten
            messagebox.showerror(APP_NAME, f"Bild kann nicht gelesen werden:\n{e}")
            return False
        self.settings["last_img_dir"] = os.path.dirname(path)
        save_settings(self.settings)
        target = self.ed.widget
        into_frame = target is not None and target.type == "image"
        if into_frame:                       # in den Rahmen einpassen, auch vergrößern
            box_w, box_h = target.w, target.h
        else:                                # neues Element: nur verkleinern, falls zu groß
            box_w, box_h = min(width, self.ed.layout.width), min(height, self.ed.layout.height)
        box_w, box_h = max(1, min(box_w, S.MAX_IMAGE_SIDE)), max(1, min(box_h, S.MAX_IMAGE_SIDE))
        nw, nh = I.fit_size(width, height, box_w, box_h)
        if (nw, nh) != (width, height):
            rgba = I.resize_rgba(width, height, rgba, nw, nh)
        name = os.path.splitext(os.path.basename(path))[0][:60] or "Bild"
        try:
            img = I.from_rgba(self.ed.free_image_id(), name, nw, nh, rgba)
        except (ValueError, I.ImageError) as e:
            messagebox.showwarning(APP_NAME, str(e))
            return False
        self._act(lambda: self.ed.add_image(img))
        change = ""
        if (nw, nh) != (width, height):
            change = f" ({'verkleinert' if nw < width else 'vergrößert'} von {width}×{height})"
        self.status.set(f"Bild „{name}“ geladen, {nw}×{nh} Pixel{change}.")
        return True

    def image_original_size(self):
        w = self.ed.widget
        img = self.ed.image_by_id(w.get("image")) if w is not None and w.type == "image" else None
        if img is None:
            return
        self._act(lambda: self.ed.set_geometry(w=img.width, h=img.height))

    def delete_image(self, img):
        used = self.ed.image_usage(img.id)
        if used and not messagebox.askyesno(
                APP_NAME, f"Bild „{img.name}“ wird {used}× benutzt. Trotzdem löschen?\n"
                          "Die Bild-Elemente bleiben stehen und zeigen dann kein Bild."):
            return
        self._act(lambda: self.ed.remove_image(img.id))

    # ------------------------------------------------------------------ Aktionen

    def _act(self, fn, lists=True):
        try:
            fn()
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e))
            return
        if lists:
            self.refresh_lists()
        self.redraw()
        self.build_props()
        self.update_title()

    def add_widget(self, key):
        self._act(lambda: self.ed.add_widget(key))
        self.canvas.focus_set()

    def duplicate(self):
        self._act(self.ed.duplicate_widget)

    def delete(self):
        if self.ed.widget is not None:
            self._act(self.ed.delete_widget)

    def undo(self):
        if self.ed.undo():
            self.refresh_all()

    def redo(self):
        if self.ed.redo():
            self.refresh_all()

    def _nudge(self, dx, dy):
        if self.ed.widget is None:
            return
        self.ed.nudge(dx, dy)
        self.redraw()
        self._sync_geometry_fields()
        self.update_title()

    def ed_add_screen(self):
        self._act(self.ed.add_screen)

    def ed_dup_screen(self):
        self._act(self.ed.duplicate_screen)

    def ed_del_screen(self):
        if messagebox.askyesno(APP_NAME, f"Seite „{self.ed.screen.name}“ löschen?"):
            self._act(self.ed.delete_screen)

    def _on_screen_select(self, _e=None):
        sel = self.screen_list.curselection()
        if sel and sel[0] != self.ed.screen_index:
            self.ed.select_screen(sel[0])
            self.refresh_all()

    def _on_widget_list_select(self, _e=None):
        sel = self.widget_list.curselection()
        if not sel:
            return
        idx = len(self.ed.screen.widgets) - 1 - sel[0]
        if idx != self.ed.selected:
            self.ed.selected = idx
            self.redraw()
            self.build_props()

    def _sync_geometry_fields(self):
        w = self.ed.widget
        if w is None:
            return
        for key in ("x", "y", "w", "h"):
            var = self._prop_vars.get(key)
            if var is not None:
                var.set(str(getattr(w, key)))

    # ------------------------------------------------------------------ Maus

    def _display_pos(self, event):
        z = self.z()
        return self.canvas.canvasx(event.x) / z, self.canvas.canvasy(event.y) / z

    def _on_press(self, event):
        self.canvas.focus_set()
        x, y = self._display_pos(event)
        if self.preview.get():
            return
        changed = self.ed.press(x, y)
        self._draw_selection()
        if changed:
            self.build_props()
            self.refresh_lists()

    def _on_drag(self, event):
        x, y = self._display_pos(event)
        if self.ed.drag(x, y):
            self.redraw()
            self._sync_geometry_fields()

    def _on_release(self, _event):
        self.ed.release()
        self.update_title()

    def _on_motion(self, event):
        x, y = self._display_pos(event)
        L = self.ed.layout
        inside = 0 <= x < L.width and 0 <= y < L.height
        self.pos_label.configure(text=f"x {int(x)}   y {int(y)}" if inside else "")

    # ------------------------------------------------------------------ Dateien

    def _confirm_discard(self):
        if not self.ed.dirty:
            return True
        ans = messagebox.askyesnocancel(APP_NAME, "Änderungen am Layout speichern?")
        if ans is None:
            return False
        if ans:
            return self.save()
        return True

    def _reset_view(self):
        self._photos.clear()

    def new(self, preset):
        if self._confirm_discard():
            self.ed.new(preset)
            self._reset_view()
            self.refresh_all()

    def open(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(parent=self.root, filetypes=FILETYPES, title="Layout öffnen",
                                          initialdir=self.settings.get("last_dir"))
        if not path:
            return
        try:
            self.ed.open(path)
        except (OSError, layout_format.LayoutError) as e:
            messagebox.showerror(APP_NAME, f"Datei kann nicht geöffnet werden:\n{e}")
            return
        self._reset_view()
        self._remember_dir(path)
        self.refresh_all()

    def save(self):
        if not self.ed.path:
            return self.save_as()
        try:
            n = self.ed.save()
        except (OSError, layout_format.LayoutError) as e:
            messagebox.showerror(APP_NAME, f"Speichern fehlgeschlagen:\n{e}")
            return False
        self.status.set(f"Gespeichert: {self.ed.path} ({human_size(n)})")
        self.update_title()
        return True

    def save_as(self):
        path = filedialog.asksaveasfilename(parent=self.root, filetypes=FILETYPES, defaultextension=".s51",
                                            title="Layout speichern", initialdir=self.settings.get("last_dir"),
                                            initialfile=(self.ed.layout.name or "design") + ".s51")
        if not path:
            return False
        self.ed.path = path
        self._remember_dir(path)
        return self.save()

    def _remember_dir(self, path):
        self.settings["last_dir"] = os.path.dirname(path)
        save_settings(self.settings)

    def export_sd(self):
        """SD-Karte wählen und den Export-Dialog öffnen (Dateiname, Standard-Design)."""
        try:
            data = self.ed.encoded()
        except layout_format.LayoutError as e:
            messagebox.showerror(APP_NAME, f"Layout ist nicht gültig:\n{e}")
            return None
        root_dir = filedialog.askdirectory(parent=self.root, title="SD-Karte (Laufwerk) auswählen",
                                           initialdir=self.settings.get("last_sd"))
        if not root_dir:
            return None
        self.settings["last_sd"] = root_dir
        save_settings(self.settings)
        return ExportDialog(self, sdcard.target_dir(root_dir), data)

    def quit(self):
        if self._confirm_discard():
            self.settings["zoom"] = self.zoom.get()
            save_settings(self.settings)
            self.root.destroy()

    # ------------------------------------------------------------------ Konfiguration

    def load_config(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=CFG_FILETYPES,
                                          title="Konfiguration laden", initialdir=self.settings.get("last_sd"))
        if not path:
            return
        try:
            values, warnings = config_format.load(path)
        except (OSError, UnicodeDecodeError) as e:
            messagebox.showerror(APP_NAME, f"Datei kann nicht gelesen werden:\n{e}")
            return
        self.cfg, self.cfg_loaded = values, True
        if warnings:
            messagebox.showwarning(APP_NAME, "Geladen, mit Hinweisen:\n\n" + "\n".join(str(w) for w in warnings[:20]))
        else:
            self.status.set(f"Konfiguration geladen: {path}")

    def save_config_as(self):
        path = filedialog.asksaveasfilename(parent=self.root, filetypes=CFG_FILETYPES, defaultextension=".cfg",
                                            initialfile="tacho.cfg", title="Konfiguration speichern")
        if not path:
            return
        try:
            config_format.save(self.cfg, path)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Speichern fehlgeschlagen:\n{e}")
            return
        self.status.set(f"Konfiguration gespeichert: {path}")

    def open_config(self):
        return ConfigDialog(self)

    def open_wireless(self):
        return WirelessDialog(self)


class ExportDialog:
    """Design auf die SD-Karte schreiben und festlegen, welches Design der Tacho beim Start zeigt."""

    def __init__(self, app, directory, data):
        self.app, self.directory, self.data = app, directory, data
        self.existing = sdcard.list_designs(directory)
        card_cfg = sdcard.card_config(directory)
        current_default = (card_cfg or app.cfg)[("anzeige", "layout_datei")]
        self.filename = tk.StringVar(value=sdcard.file_name_for(app.ed.layout.name))
        self.write_layout = tk.BooleanVar(value=True)
        self.default = tk.StringVar(value=current_default if current_default in self.existing
                                    else self.filename.get())
        self.msg = tk.StringVar(value="")

        self.top = tk.Toplevel(app.root)
        self.top.title("Auf SD-Karte exportieren")
        self.top.transient(app.root)
        self.top.configure(background=C["bg"])
        f = ttk.Frame(self.top, padding=20)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        ttk.Label(f, text="Auf SD-Karte exportieren", style="Title.TLabel").grid(row=0, column=0, columnspan=2,
                                                                                 sticky="w")
        ttk.Label(f, text=f"Ordner: {directory}", style="Muted.TLabel").grid(row=1, column=0, columnspan=2,
                                                                            sticky="w", pady=(2, 12))
        ttk.Checkbutton(f, text=f"Design „{app.ed.layout.name}“ speichern als", variable=self.write_layout,
                        command=self.refresh).grid(row=2, column=0, sticky="w")
        e = ttk.Entry(f, textvariable=self.filename, width=28)
        e.grid(row=2, column=1, sticky="w", padx=(8, 0))
        e.bind("<KeyRelease>", lambda ev: self.refresh())
        self.hint = ttk.Label(f, text="", style="Muted.TLabel")
        self.hint.grid(row=3, column=1, sticky="w", padx=(8, 0))

        self.heading = ttk.Label(f, text="STANDARD-DESIGN BEIM START", style="Head.TLabel")
        self.heading.grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 4))
        self.choices = ttk.Frame(f)
        self.choices.grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text=("Am Tacho lässt sich durch langes Drücken auf das Display jederzeit ein anderes Design "
                           "wählen. Ein hier neu festgelegter Standard gilt beim nächsten Start, bis am Tacho "
                           "wieder etwas anderes gewählt wird."),
                  style="Muted.TLabel", wraplength=460, justify="left").grid(row=6, column=0, columnspan=2,
                                                                            sticky="w", pady=(10, 0))
        btns = ttk.Frame(f)
        btns.grid(row=7, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(btns, text="Abbrechen", command=self.top.destroy).pack(side="right")
        ttk.Button(btns, text="Auf die Karte schreiben", style="Accent.TButton",
                   command=self.do_export).pack(side="right", padx=6)
        ttk.Label(f, textvariable=self.msg, foreground=C["danger"]).grid(row=8, column=0, columnspan=2, sticky="w")
        self.refresh()

    def options(self):
        """Dateien, die als Standard wählbar sind: vorhandene und, falls gespeichert wird, die neue."""
        names = list(self.existing)
        if self.write_layout.get():
            try:
                new = sdcard.clean_file_name(self.filename.get())
            except ValueError:
                new = None
            if new and new not in names:
                names.append(new)
        return sorted(names)

    def refresh(self):
        try:
            name = sdcard.clean_file_name(self.filename.get())
            self.hint.configure(text="wird überschrieben" if name in self.existing else "neue Datei")
        except ValueError as e:
            self.hint.configure(text=str(e))
        for child in self.choices.winfo_children():
            child.destroy()
        opts = self.options()
        if self.default.get() not in opts and opts:
            self.default.set(opts[0])
        for n in opts:
            ttk.Radiobutton(self.choices, text=n, value=n, variable=self.default).pack(anchor="w", pady=1)
        if not opts:
            ttk.Label(self.choices, text="Noch keine Designs auf der Karte.", style="Muted.TLabel").pack(anchor="w")

    def do_export(self):
        app = self.app
        file_name = self.filename.get()
        default = self.default.get()
        try:
            if self.write_layout.get():
                file_name = sdcard.clean_file_name(file_name)
            else:
                file_name = None
            if not default:
                raise ValueError("Bitte ein Standard-Design wählen")
            if file_name is None:
                # nur das Standard-Design ändern
                values = dict(app.cfg) if app.cfg_loaded else (sdcard.card_config(self.directory)
                                                               or config_format.defaults())
                values[("anzeige", "layout_datei")] = sdcard.clean_file_name(default)
                os.makedirs(self.directory, exist_ok=True)
                config_format.save(values, os.path.join(self.directory, sdcard.CFG_NAME))
            else:
                values = sdcard.export(self.directory, self.data, file_name, default,
                                       app.cfg if app.cfg_loaded else None)
        except ValueError as e:
            self.msg.set(str(e))
            return False
        except OSError as e:
            self.msg.set(f"Schreiben auf die Karte fehlgeschlagen: {e}")
            return False
        if app.cfg_loaded:
            app.cfg[("anzeige", "layout_datei")] = values[("anzeige", "layout_datei")]
        written = f"{file_name} ({human_size(len(self.data))}) und tacho.cfg" if file_name else "tacho.cfg"
        self.top.destroy()
        messagebox.showinfo(APP_NAME, f"Auf die Karte geschrieben: {written}\nStandard-Design: {default}\n"
                                      f"Ordner: {self.directory}\n\n"
                                      "Karte sicher auswerfen, in den Tacho stecken und den Tacho neu starten.")
        return True


class ConfigDialog:
    """Bearbeitet die Werte der tacho.cfg."""

    TITLES = {"fahrzeug": "Fahrzeug", "anzeige": "Anzeige", "warnungen": "Warnungen", "wartung": "Wartung",
              "alarm": "Alarm", "gps": "GPS", "bluetooth": "Bluetooth", "wlan": "WLAN"}

    def __init__(self, app):
        self.app = app
        self.top = tk.Toplevel(app.root)
        self.top.title("Tacho-Konfiguration")
        self.top.transient(app.root)
        self.top.geometry("700x620")
        self.top.configure(background=C["bg"])
        self.vars = {}
        nb = ttk.Notebook(self.top)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        for section in S.CONFIG_SECTIONS:
            frame = ttk.Frame(nb, padding=16)
            frame.columnconfigure(1, weight=1)
            nb.add(frame, text=self.TITLES.get(section, section))
            r = 0
            for c in [c for c in S.CONFIG if c.section == section]:
                value = app.cfg[(c.section, c.key)]
                ttk.Label(frame, text=c.key, font=app.F["bold"]).grid(
                    row=r, column=0, sticky="w", pady=(10, 0), padx=(0, 16))
                if c.type == "bool":
                    var = tk.BooleanVar(value=bool(value))
                    ttk.Checkbutton(frame, text="ja", variable=var).grid(row=r, column=1, sticky="w", pady=(10, 0))
                elif c.type == "enum":
                    var = tk.StringVar(value=value)
                    ttk.Combobox(frame, textvariable=var, values=c.choices, state="readonly", width=16).grid(
                        row=r, column=1, sticky="w", pady=(10, 0))
                else:
                    var = tk.StringVar(value=config_format.format_value(c, value).strip('"')
                                       if c.type != "str" else str(value))
                    ttk.Entry(frame, textvariable=var, width=30).grid(row=r, column=1, sticky="w", pady=(10, 0))
                self.vars[(c.section, c.key)] = var
                r += 1
                info = c.description
                if c.type in ("int", "float") and c.min is not None:
                    info += f" ({c.min:g} bis {c.max:g})"
                ttk.Label(frame, text=info, style="Muted.TLabel", wraplength=620, justify="left").grid(
                    row=r, column=0, columnspan=2, sticky="w")
                r += 1
        btns = ttk.Frame(self.top, style="Bg.TFrame", padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="Standardwerte", command=self.reset).pack(side="left")
        ttk.Button(btns, text="Abbrechen", command=self.top.destroy).pack(side="right")
        ttk.Button(btns, text="Übernehmen", style="Accent.TButton", command=self.apply).pack(side="right", padx=6)

    def reset(self):
        for c in S.CONFIG:
            var = self.vars[(c.section, c.key)]
            var.set(c.default if c.type in ("bool", "enum", "str") else config_format.format_value(c, c.default))

    def apply(self):
        new, errors = {}, []
        for c in S.CONFIG:
            var = self.vars[(c.section, c.key)]
            raw = var.get()
            if c.type == "bool":
                new[(c.section, c.key)] = bool(raw)
                continue
            try:
                new[(c.section, c.key)] = config_format.parse_value(c, str(raw)) if c.type != "str" else str(raw)
            except ValueError as e:
                errors.append(f"{c.section}.{c.key}: {e}")
        if len(new.get(("wlan", "passwort"), "")) < 8:
            errors.append("wlan.passwort: mindestens 8 Zeichen")
        if errors:
            messagebox.showerror("Tacho-Konfiguration", "Bitte korrigieren:\n\n" + "\n".join(errors), parent=self.top)
            return
        self.app.cfg, self.app.cfg_loaded = new, True
        self.app.status.set("Konfiguration übernommen. Mit Export oder drahtloser Übertragung zum Tacho schicken.")
        self.top.destroy()


class WirelessDialog:
    """Überträgt Layout und Konfiguration per WLAN an den Tacho."""

    def __init__(self, app):
        self.app = app
        cfg = app.cfg
        default_host = (transfer.DEFAULT_HOST if cfg[("wlan", "modus")] == "hotspot"
                        else cfg[("wlan", "hostname")] + ".local")
        self.top = tk.Toplevel(app.root)
        self.top.title("Drahtlos übertragen")
        self.top.transient(app.root)
        self.top.configure(background=C["bg"])
        f = ttk.Frame(self.top, padding=20)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        ttk.Label(f, text="Drahtlos übertragen", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        steps = ("1. Am Tacho im Stand das Menü „Übertragung“ öffnen. Das Display zeigt einen 6-stelligen Code.\n"
                 "2. PC mit dem WLAN des Tachos verbinden (Hotspot) oder mit demselben Heimnetz.\n"
                 "3. Adresse und Code eingeben und senden.")
        ttk.Label(f, text=steps, style="Muted.TLabel", wraplength=500, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(f, text="Adresse").grid(row=2, column=0, sticky="w", pady=(16, 3), padx=(0, 12))
        self.host = tk.StringVar(value=app.settings.get("host", default_host))
        ttk.Entry(f, textvariable=self.host, width=30).grid(row=2, column=1, sticky="w", pady=(16, 3))
        ttk.Label(f, text="Code vom Display").grid(row=3, column=0, sticky="w", pady=3, padx=(0, 12))
        self.code = tk.StringVar()
        ttk.Entry(f, textvariable=self.code, width=10, font=app.F["mono"]).grid(row=3, column=1, sticky="w", pady=3)
        btns = ttk.Frame(f)
        btns.grid(row=4, column=0, columnspan=2, sticky="w", pady=(18, 8))
        self.buttons = [
            ttk.Button(btns, text="Layout senden", style="Accent.TButton", command=self.send_layout),
            ttk.Button(btns, text="Konfiguration senden", command=self.send_config),
            ttk.Button(btns, text="Verbindung prüfen", command=self.check),
            ttk.Button(btns, text="Layout vom Tacho laden", command=self.fetch_layout),
        ]
        for b in self.buttons:
            b.pack(side="left", padx=(0, 6))
        self.msg = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.msg, wraplength=500, justify="left").grid(
            row=5, column=0, columnspan=2, sticky="w")

    def _run(self, label, fn, on_done=None):
        host, code = self.host.get().strip(), self.code.get().strip()
        self.app.settings["host"] = host
        save_settings(self.app.settings)
        for b in self.buttons:
            b.state(["disabled"])
        self.msg.set(f"{label} …")

        def work():
            try:
                result, err = fn(host, code), None
            except (transfer.TransferError, layout_format.LayoutError, ValueError) as e:
                result, err = None, str(e)
            self.app.ui_queue.put(lambda: self._finish(result, err, on_done))
        threading.Thread(target=work, daemon=True).start()

    def _finish(self, result, err, on_done):
        try:
            for b in self.buttons:
                b.state(["!disabled"])
        except tk.TclError:
            return          # Fenster wurde inzwischen geschlossen
        if err:
            self.msg.set(err)
            return
        self.msg.set(on_done(result) if on_done else "Fertig.")

    def check(self):
        def done(info):
            layout = info.get("layout")
            lay = f"Layout {human_size(layout['groesse'])}" if layout else "kein Layout"
            offen = ("Übertragung freigegeben" if info.get("uebertragung_offen")
                     else "Übertragung am Tacho noch nicht freigegeben")
            return (f"Verbunden: {info.get('geraet')} (Firmware {info.get('firmware')}, "
                    f"Format {info.get('format')}), {lay}. {offen}.")
        self._run("Verbinde", lambda h, c: transfer.info(h), done)

    def send_layout(self):
        try:
            data = self.app.ed.encoded()
        except layout_format.LayoutError as e:
            self.msg.set(f"Layout ist nicht gültig: {e}")
            return
        self._run("Sende Layout", lambda h, c: transfer.send_layout(h, c, data),
                  lambda r: f"Layout übertragen ({human_size(len(data))}). Der Tacho zeigt es sofort an.")

    def send_config(self):
        text = config_format.dump(self.app.cfg)

        def done(r):
            warn = r.get("warnungen") or []
            return "Konfiguration übertragen." + (f" Hinweise: {'; '.join(warn)}" if warn else "")
        self._run("Sende Konfiguration", lambda h, c: transfer.send_config(h, c, text), done)

    def fetch_layout(self):
        if not self.app._confirm_discard():
            return

        def get(h, c):
            return layout_format.decode(transfer.fetch_layout(h, c))

        def done(layout):
            self.app.ed.new()
            self.app.ed.layout = layout
            self.app._reset_view()
            self.app.refresh_all()
            return f"Layout „{layout.name}“ vom Tacho geladen."
        self._run("Lade Layout", get, done)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
