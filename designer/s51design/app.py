"""S51 Designer: Oberfläche (Tkinter).

Start:  python -m s51design      (im Ordner designer/)
"""

import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import __version__, config_format, layout_format, render, transfer
from . import schema as S
from . import values as V
from .editor import Editor

APP_NAME = "S51 Designer"
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".s51-designer.json")
FILETYPES = [("S51-Layout", "*.s51"), ("Alle Dateien", "*.*")]
CFG_FILETYPES = [("Tacho-Konfiguration", "*.cfg"), ("Alle Dateien", "*.*")]
GRID_STEP = 16
SEL_COLOR = "#378ADD"


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


class App:
    def __init__(self, root):
        self.root = root
        self.ed = Editor()
        self.cfg = config_format.defaults()
        self.cfg_loaded = False        # aus Datei geladen oder im Dialog bearbeitet
        self.settings = load_settings()
        self.zoom = tk.IntVar(value=self.settings.get("zoom", 2))
        self.show_grid = tk.BooleanVar(value=True)
        self.snap = tk.BooleanVar(value=True)
        self.preview = tk.BooleanVar(value=False)
        self.animate = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="")
        self._prop_vars = {}
        self._bg_item = None
        self.ui_queue = queue.Queue()      # Aufgaben aus Hintergrund-Threads für die Oberfläche

        root.title(APP_NAME)
        root.geometry("1400x820")
        root.minsize(1000, 600)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._build_menu()
        self._build_ui()
        self._bind_keys()
        self.refresh_all()
        self._tick()

    # ------------------------------------------------------------------ Aufbau

    def _build_menu(self):
        m = tk.Menu(self.root)
        f = tk.Menu(m, tearoff=False)
        f.add_command(label="Neu (leer)", command=lambda: self.new(None))
        f.add_command(label="Neu aus Vorlage „Klar“", command=lambda: self.new("Klar"))
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
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # Links: Seiten und Elemente
        left = ttk.Frame(root, padding=8)
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="Seiten", font=("Arial", 11, "bold")).pack(anchor="w")
        self.screen_list = tk.Listbox(left, height=10, exportselection=False, width=26)
        self.screen_list.pack(fill="x", pady=(4, 4))
        self.screen_list.bind("<<ListboxSelect>>", self._on_screen_select)
        row = ttk.Frame(left)
        row.pack(fill="x")
        for text, cmd in (("Neu", self.ed_add_screen), ("Kopie", self.ed_dup_screen),
                          ("Löschen", self.ed_del_screen)):
            ttk.Button(row, text=text, width=7, command=cmd).pack(side="left", padx=1)
        row = ttk.Frame(left)
        row.pack(fill="x", pady=(2, 12))
        ttk.Button(row, text="↑", width=3, command=lambda: self._act(lambda: self.ed.move_screen(-1), True)).pack(side="left", padx=1)
        ttk.Button(row, text="↓", width=3, command=lambda: self._act(lambda: self.ed.move_screen(1), True)).pack(side="left", padx=1)

        ttk.Label(left, text="Element hinzufügen", font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 4))
        for wt in S.WIDGET_TYPES:
            ttk.Button(left, text=wt.label, command=lambda k=wt.key: self.add_widget(k)).pack(fill="x", pady=1)

        ttk.Label(left, text="Elemente auf der Seite", font=("Arial", 11, "bold")).pack(anchor="w", pady=(12, 4))
        self.widget_list = tk.Listbox(left, height=12, exportselection=False, width=26)
        self.widget_list.pack(fill="both", expand=True)
        self.widget_list.bind("<<ListboxSelect>>", self._on_widget_list_select)

        # Mitte: Zeichenfläche
        mid = ttk.Frame(root, padding=(0, 8))
        mid.grid(row=0, column=1, sticky="nsew")
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)
        cf = ttk.Frame(mid)
        cf.grid(row=0, column=0, sticky="nsew")
        cf.rowconfigure(0, weight=1)
        cf.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(cf, background="#3a3a38", highlightthickness=0, cursor="arrow")
        xs = ttk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview)
        ys = ttk.Scrollbar(cf, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        opts = ttk.Frame(mid, padding=(0, 6))
        opts.grid(row=1, column=0, sticky="ew")
        ttk.Label(opts, text="Zoom").pack(side="left")
        zoom = ttk.Combobox(opts, width=4, state="readonly", values=("1", "2", "3"))
        zoom.set(str(self.zoom.get()))
        zoom.bind("<<ComboboxSelected>>", lambda e: (self.zoom.set(int(zoom.get())), self.redraw()))
        zoom.pack(side="left", padx=(4, 16))
        ttk.Checkbutton(opts, text="Raster", variable=self.show_grid, command=self.redraw).pack(side="left")
        ttk.Checkbutton(opts, text="Am Raster ausrichten", variable=self.snap,
                        command=lambda: setattr(self.ed, "snap", self.snap.get())).pack(side="left", padx=8)
        ttk.Checkbutton(opts, text="Vorschau wie am Tacho", variable=self.preview, command=self.redraw).pack(side="left", padx=8)
        ttk.Checkbutton(opts, text="Demo-Werte bewegen", variable=self.animate).pack(side="left", padx=8)
        self.pos_label = ttk.Label(opts, text="")
        self.pos_label.pack(side="right")
        self.canvas.bind("<Motion>", self._on_motion)

        # Rechts: Eigenschaften
        right = ttk.Frame(root, padding=8, width=330)
        right.grid(row=0, column=2, sticky="ns")
        right.grid_propagate(False)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Eigenschaften", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w")
        pc = tk.Canvas(right, highlightthickness=0, width=300)
        psb = ttk.Scrollbar(right, orient="vertical", command=pc.yview)
        pc.configure(yscrollcommand=psb.set)
        pc.grid(row=1, column=0, sticky="nsew")
        psb.grid(row=1, column=1, sticky="ns")
        self.props_frame = ttk.Frame(pc)
        pc.create_window((0, 0), window=self.props_frame, anchor="nw")
        self.props_frame.bind("<Configure>", lambda e: pc.configure(scrollregion=pc.bbox("all")))
        self.props_canvas = pc

        bar = ttk.Frame(root, padding=(8, 2))
        bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        ttk.Label(bar, textvariable=self.status).pack(side="left")

    def _bind_keys(self):
        r = self.root
        r.bind_all("<Control-z>", lambda e: self.undo())
        r.bind_all("<Control-y>", lambda e: self.redo())
        r.bind_all("<Control-s>", lambda e: self.save())
        r.bind_all("<Control-o>", lambda e: self.open())
        r.bind_all("<Control-d>", lambda e: self.duplicate())
        c = self.canvas
        c.bind("<Delete>", lambda e: self.delete())
        c.bind("<BackSpace>", lambda e: self.delete())
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            c.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy))
            c.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx * 10, dy * 10))

    # ------------------------------------------------------------------ Zeichnen

    def z(self):
        return self.zoom.get()

    def redraw(self):
        c, z, L = self.canvas, self.z(), self.ed.layout
        c.configure(scrollregion=(0, 0, L.width * z, L.height * z))
        vals = V.demo_values(animate=self.animate.get())
        self._bg_item = render.draw_screen(c, self.ed.screen, z, vals, (L.width, L.height),
                                           show_hidden=not self.preview.get())
        c.delete("grid")
        if self.show_grid.get() and not self.preview.get():
            for x in range(GRID_STEP, L.width, GRID_STEP):
                c.create_line(x * z, 0, x * z, L.height * z, fill="#1f2421", tags="grid")
            for y in range(GRID_STEP, L.height, GRID_STEP):
                c.create_line(0, y * z, L.width * z, y * z, fill="#1f2421", tags="grid")
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
                           outline=SEL_COLOR, dash=(4, 3), width=1, tags="sel")
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
                suffix = f"  (Nacht von {day.name})" if day else "  (Nacht)"
            sl.insert("end", f"{s.id}: {s.name}{suffix}")
        sl.selection_clear(0, "end")
        sl.selection_set(self.ed.screen_index)
        wl = self.widget_list
        wl.delete(0, "end")
        for w in self.ed.screen.widgets:
            wl.insert("end", self._widget_title(w))
        if self.ed.selected is not None:
            wl.selection_set(self.ed.selected)
            wl.see(self.ed.selected)

    def _widget_title(self, w):
        wt = S.WTYPE_BY_KEY.get(w.type)
        label = wt.label if wt else w.type
        detail = ""
        if w.type == "text":
            detail = w.get("text")
        elif "source" in w.props:
            src = S.SOURCE_BY_KEY.get(w.get("source"))
            detail = src.label if src else ""
        hidden = " (versteckt)" if w.hidden else ""
        return f"{label}: {detail}{hidden}" if detail else label + hidden

    def refresh_all(self):
        self.refresh_lists()
        self.redraw()
        self.build_props()
        self.update_title()

    def update_title(self):
        name = os.path.basename(self.ed.path) if self.ed.path else "Unbenannt"
        self.root.title(f"{'● ' if self.ed.dirty else ''}{name} – {APP_NAME}")
        n = len(self.ed.screen.widgets)
        self.status.set(f"Layout „{self.ed.layout.name}“ · Seite {self.ed.screen.name} · {n} von "
                        f"{S.MAX_WIDGETS_PER_SCREEN} Elementen")

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
        f.columnconfigure(1, weight=1)
        w = self.ed.widget
        if w is None:
            self._build_screen_props(f)
        else:
            self._build_widget_props(f, w)
        self.props_canvas.yview_moveto(0)

    def _row_label(self, f, r, text):
        ttk.Label(f, text=text).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=3)

    def _entry(self, f, r, value, on_commit, width=18):
        var = tk.StringVar(value=str(value))
        e = ttk.Entry(f, textvariable=var, width=width)
        e.grid(row=r, column=1, sticky="ew", pady=3)

        def commit(_event=None):
            on_commit(var.get(), var, e)
        e.bind("<Return>", commit)
        e.bind("<FocusOut>", commit)
        return var

    def _color_button(self, f, r, color, on_pick):
        b = tk.Button(f, text=color, bg=color, fg=self._contrast(color), relief="groove", width=12)

        def pick():
            res = colorchooser.askcolor(color=b.cget("bg"), parent=self.root, title="Farbe wählen")
            if res and res[1]:
                new = res[1].upper()
                b.configure(bg=new, text=new, fg=self._contrast(new))
                on_pick(new)
        b.configure(command=pick)
        b.grid(row=r, column=1, sticky="w", pady=3)
        return b

    @staticmethod
    def _contrast(color):
        try:
            r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            return "black"
        return "black" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "white"

    def _build_screen_props(self, f):
        s = self.ed.screen
        r = 0
        ttk.Label(f, text="Seite", font=("Arial", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w")
        r += 1
        self._row_label(f, r, "Name")
        self._entry(f, r, s.name, lambda v, var, e: self._set_screen(name=v.strip() or s.name))
        r += 1
        self._row_label(f, r, "Hintergrund")
        self._color_button(f, r, s.bg, lambda c: self._set_screen(bg=c))
        r += 1
        self._row_label(f, r, "Art")
        role = ttk.Combobox(f, state="readonly", values=("Tagseite", "Nachtversion einer Seite"))
        role.set("Nachtversion einer Seite" if s.role == "night" else "Tagseite")
        role.grid(row=r, column=1, sticky="ew", pady=3)
        r += 1
        days = [d for d in self.ed.layout.screens if d.role == "page" and d is not s]
        self._row_label(f, r, "Nacht für")
        night = ttk.Combobox(f, state="readonly", values=[f"{d.id}: {d.name}" for d in days])
        current = next((d for d in days if d.id == s.night_of), None)
        if current:
            night.set(f"{current.id}: {current.name}")
        night.grid(row=r, column=1, sticky="ew", pady=3)
        night.configure(state="readonly" if s.role == "night" else "disabled")

        def on_role(_e=None):
            if role.get() == "Tagseite":
                self._set_screen(role="page", night_of=S.NO_PAGE)
            elif days:
                target = current or days[0]
                self._set_screen(role="night", night_of=target.id)
            else:
                role.set("Tagseite")
                messagebox.showinfo(APP_NAME, "Zuerst eine Tagseite anlegen, zu der diese Nachtversion gehört.")
            self.build_props()

        def on_night(_e=None):
            self._set_screen(night_of=int(night.get().split(":")[0]))
        role.bind("<<ComboboxSelected>>", on_role)
        night.bind("<<ComboboxSelected>>", on_night)
        r += 1
        ttk.Label(f, text=("Nachtversionen ersetzen ihre Tagseite automatisch, wenn der Nachtmodus "
                           "an ist.\n\nElement anklicken, um es zu bearbeiten. Ziehen verschiebt, "
                           "der Punkt unten rechts ändert die Größe. Pfeiltasten verschieben um 1 Pixel, "
                           "mit Umschalt um 10."),
                  wraplength=290, foreground="#5b6660").grid(row=r, column=0, columnspan=2, sticky="w", pady=(12, 0))
        r += 1
        ttk.Separator(f).grid(row=r, column=0, columnspan=2, sticky="ew", pady=10)
        r += 1
        ttk.Label(f, text="Layout", font=("Arial", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w")
        r += 1
        self._row_label(f, r, "Name")
        self._entry(f, r, self.ed.layout.name, lambda v, var, e: self._set_layout(name=v.strip()))
        r += 1
        self._row_label(f, r, "Autor")
        self._entry(f, r, self.ed.layout.author, lambda v, var, e: self._set_layout(author=v.strip()))

    def _build_widget_props(self, f, w):
        wt = S.WTYPE_BY_KEY.get(w.type)
        r = 0
        ttk.Label(f, text=wt.label if wt else f"Unbekannter Typ {w.type}",
                  font=("Arial", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w")
        r += 1
        for key, label in (("x", "X"), ("y", "Y"), ("w", "Breite"), ("h", "Höhe")):
            self._row_label(f, r, label)
            self._prop_vars[key] = self._entry(f, r, getattr(w, key),
                                               lambda v, var, e, k=key: self._commit_geometry(k, v, var))
            r += 1
        hidden = tk.BooleanVar(value=w.hidden)
        ttk.Checkbutton(f, text="Versteckt", variable=hidden,
                        command=lambda: self._act(lambda: self.ed.set_flag(hidden=hidden.get()))).grid(
            row=r, column=0, columnspan=2, sticky="w")
        r += 1
        locked = tk.BooleanVar(value=w.locked)
        ttk.Checkbutton(f, text="Gesperrt (nicht verschiebbar)", variable=locked,
                        command=lambda: self._act(lambda: self.ed.set_flag(locked=locked.get()))).grid(
            row=r, column=0, columnspan=2, sticky="w")
        r += 1
        ttk.Separator(f).grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)
        r += 1
        if wt is None:
            return
        for key in wt.props:
            prop = S.PROP_BY_KEY[key]
            value = w.get(key)
            self._row_label(f, r, prop.label)
            t = prop.type
            if t == "color":
                self._color_button(f, r, value, lambda c, k=key: self._commit_prop(k, c))
            elif t == "bool":
                var = tk.BooleanVar(value=bool(value))
                ttk.Checkbutton(f, variable=var, command=lambda k=key, v=var: self._commit_prop(k, v.get())).grid(
                    row=r, column=1, sticky="w")
            elif t.startswith("enum:"):
                enum = t[5:]
                labels = enum_labels(enum)
                if enum == "source":
                    labels = self._source_labels(w.type)
                cb = ttk.Combobox(f, state="readonly", values=labels)
                cb.set(enum_label_for_key(enum, value))
                cb.grid(row=r, column=1, sticky="ew", pady=3)
                cb.bind("<<ComboboxSelected>>",
                        lambda e, k=key, en=enum, c=cb: self._commit_prop(k, enum_key_for_label(en, c.get())))
            else:
                self._entry(f, r, self._fmt(prop, value),
                            lambda v, var, e, p=prop: self._commit_text_prop(p, v, var))
            r += 1
        hint = {
            "value": "Schwellen: 0 = aus. Ab „Warnung ab“ wird die Warnfarbe benutzt, ab „Kritisch ab“ die Kritisch-Farbe.",
            "bar": "Mit Segmenten bekommt jedes Segment die Farbe seiner Stelle (z. B. roter Bereich am Ende des Drehzahlbalkens).",
            "gauge": "Winkel: 0° = rechts, im Uhrzeigersinn. 135° bis 405° ist ein unten offener Dreiviertelkreis.",
            "indicator": "Blinker-Eingänge pulsieren selbst. „Blinken“ ist für Zustände gedacht, die dauerhaft an sind.",
        }.get(w.type)
        if hint:
            ttk.Label(f, text=hint, wraplength=290, foreground="#5b6660").grid(
                row=r, column=0, columnspan=2, sticky="w", pady=(10, 0))

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

    def _set_layout(self, **changes):
        if all(getattr(self.ed.layout, k) == v for k, v in changes.items()):
            return
        self.ed.checkpoint()
        for k, v in changes.items():
            setattr(self.ed.layout, k, v)
        self.update_title()

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
        if sel and sel[0] != self.ed.selected:
            self.ed.selected = sel[0]
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
        self.pos_label.configure(text=f"x {int(x)}  y {int(y)}")

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

    def new(self, preset):
        if self._confirm_discard():
            self.ed.new(preset)
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
        self.status.set(f"Gespeichert: {self.ed.path} ({n} Bytes)")
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
        try:
            data = self.ed.encoded()
        except layout_format.LayoutError as e:
            messagebox.showerror(APP_NAME, f"Layout ist nicht gültig:\n{e}")
            return
        root_dir = filedialog.askdirectory(parent=self.root, title="SD-Karte (Laufwerk) auswählen",
                                           initialdir=self.settings.get("last_sd"))
        if not root_dir:
            return
        target = root_dir if os.path.basename(os.path.normpath(root_dir)).lower() == "s51" else os.path.join(root_dir, "s51")
        layout_name = self.cfg[("anzeige", "layout_datei")] or "design.s51"
        cfg_path = os.path.join(target, "tacho.cfg")
        write_cfg = True
        if os.path.exists(cfg_path) and not self.cfg_loaded:
            ans = messagebox.askyesnocancel(
                APP_NAME, "Auf der Karte liegt schon eine tacho.cfg.\n\n"
                          "Ja: mit den Einstellungen aus dem Designer überschreiben\n"
                          "Nein: vorhandene Einstellungen auf der Karte behalten")
            if ans is None:
                return
            write_cfg = ans
        try:
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, layout_name), "wb") as f:
                f.write(data)
            if write_cfg:
                config_format.save(self.cfg, cfg_path)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Schreiben auf die Karte fehlgeschlagen:\n{e}")
            return
        self.settings["last_sd"] = root_dir
        save_settings(self.settings)
        done = f"{layout_name} ({len(data)} Bytes)" + (" und tacho.cfg" if write_cfg else "")
        messagebox.showinfo(APP_NAME, f"Auf die Karte geschrieben: {done}\nOrdner: {target}\n\n"
                                      "Karte sicher auswerfen, in den Tacho stecken und den Tacho neu starten.")

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
        ConfigDialog(self)

    def open_wireless(self):
        WirelessDialog(self)


class ConfigDialog:
    """Bearbeitet die Werte der tacho.cfg."""

    def __init__(self, app):
        self.app = app
        self.top = tk.Toplevel(app.root)
        self.top.title("Tacho-Konfiguration")
        self.top.transient(app.root)
        self.top.geometry("620x560")
        self.vars = {}
        nb = ttk.Notebook(self.top)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        titles = {"fahrzeug": "Fahrzeug", "anzeige": "Anzeige", "warnungen": "Warnungen", "wartung": "Wartung",
                  "alarm": "Alarm", "gps": "GPS", "bluetooth": "Bluetooth", "wlan": "WLAN"}
        for section in S.CONFIG_SECTIONS:
            frame = ttk.Frame(nb, padding=10)
            frame.columnconfigure(1, weight=1)
            nb.add(frame, text=titles.get(section, section))
            r = 0
            for c in [c for c in S.CONFIG if c.section == section]:
                value = app.cfg[(c.section, c.key)]
                ttk.Label(frame, text=c.key, font=("Arial", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(6, 0))
                if c.type == "bool":
                    var = tk.BooleanVar(value=bool(value))
                    ttk.Checkbutton(frame, variable=var).grid(row=r, column=1, sticky="w", pady=(6, 0))
                elif c.type == "enum":
                    var = tk.StringVar(value=value)
                    ttk.Combobox(frame, textvariable=var, values=c.choices, state="readonly", width=16).grid(
                        row=r, column=1, sticky="w", pady=(6, 0))
                else:
                    var = tk.StringVar(value=config_format.format_value(c, value).strip('"')
                                       if c.type != "str" else str(value))
                    ttk.Entry(frame, textvariable=var, width=28).grid(row=r, column=1, sticky="w", pady=(6, 0))
                self.vars[(c.section, c.key)] = var
                r += 1
                info = c.description
                if c.type in ("int", "float") and c.min is not None:
                    info += f" ({c.min:g} bis {c.max:g})"
                ttk.Label(frame, text=info, wraplength=560, foreground="#5b6660").grid(
                    row=r, column=0, columnspan=2, sticky="w")
                r += 1
        btns = ttk.Frame(self.top, padding=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Standardwerte", command=self.reset).pack(side="left")
        ttk.Button(btns, text="Abbrechen", command=self.top.destroy).pack(side="right")
        ttk.Button(btns, text="Übernehmen", command=self.apply).pack(side="right", padx=6)

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
        f = ttk.Frame(self.top, padding=12)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        steps = ("1. Am Tacho im Stand das Menü „Übertragung“ öffnen. Das Display zeigt einen 6-stelligen Code.\n"
                 "2. PC mit dem WLAN des Tachos verbinden (Hotspot) oder mit demselben Heimnetz.\n"
                 "3. Adresse und Code eingeben und senden.")
        ttk.Label(f, text=steps, wraplength=460, justify="left").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Adresse").grid(row=1, column=0, sticky="w", pady=(12, 3))
        self.host = tk.StringVar(value=app.settings.get("host", default_host))
        ttk.Entry(f, textvariable=self.host, width=30).grid(row=1, column=1, sticky="w", pady=(12, 3))
        ttk.Label(f, text="Code vom Display").grid(row=2, column=0, sticky="w", pady=3)
        self.code = tk.StringVar()
        ttk.Entry(f, textvariable=self.code, width=10).grid(row=2, column=1, sticky="w", pady=3)
        btns = ttk.Frame(f)
        btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 6))
        self.buttons = [
            ttk.Button(btns, text="Verbindung prüfen", command=self.check),
            ttk.Button(btns, text="Layout senden", command=self.send_layout),
            ttk.Button(btns, text="Konfiguration senden", command=self.send_config),
            ttk.Button(btns, text="Layout vom Tacho laden", command=self.fetch_layout),
        ]
        for b in self.buttons:
            b.pack(side="left", padx=(0, 6))
        self.msg = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.msg, wraplength=460, justify="left").grid(row=4, column=0, columnspan=2, sticky="w")

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
            lay = f"Layout {layout['groesse']} Bytes" if layout else "kein Layout"
            offen = "Übertragung freigegeben" if info.get("uebertragung_offen") else "Übertragung am Tacho noch nicht freigegeben"
            return f"Verbunden: {info.get('geraet')} (Firmware {info.get('firmware')}, Format {info.get('format')}), {lay}. {offen}."
        self._run("Verbinde", lambda h, c: transfer.info(h), done)

    def send_layout(self):
        try:
            data = self.app.ed.encoded()
        except layout_format.LayoutError as e:
            self.msg.set(f"Layout ist nicht gültig: {e}")
            return
        self._run("Sende Layout", lambda h, c: transfer.send_layout(h, c, data),
                  lambda r: f"Layout übertragen ({len(data)} Bytes). Der Tacho zeigt es sofort an.")

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
            self.app.refresh_all()
            return f"Layout „{layout.name}“ vom Tacho geladen."
        self._run("Lade Layout", get, done)


def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
