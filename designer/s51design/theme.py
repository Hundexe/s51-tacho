"""Aussehen des Designers: dunkles Design passend zum Tacho."""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

C = {
    "bg": "#141917",        # Fensterhintergrund
    "panel": "#1a201d",     # Seitenleisten
    "panel2": "#232b27",    # Knöpfe, Kacheln
    "hover": "#2c3631",
    "field": "#0f1311",     # Eingabefelder
    "border": "#2f3934",
    "stage": "#0c0f0e",     # Fläche um das Display
    "text": "#e3e9e5",
    "muted": "#93a19a",
    "dim": "#64706a",
    "accent": "#5fb39b",
    "accent_hi": "#78c8b0",
    "accent_ink": "#0d241e",
    "select": "#378ADD",
    "danger": "#e2765f",
}

FONT_CANDIDATES = ("Segoe UI", "Inter", "Helvetica Neue", "Ubuntu", "Cantarell", "DejaVu Sans", "Arial")
MONO_CANDIDATES = ("Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Courier New")


def _pick(families, candidates, fallback):
    lower = {f.lower(): f for f in families}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return fallback


def fonts(root):
    try:
        fams = tkfont.families(root)
    except Exception:          # noqa: BLE001 – ohne Bildschirm (Tests)
        fams = ()
    base = _pick(fams, FONT_CANDIDATES, "TkDefaultFont")
    mono = _pick(fams, MONO_CANDIDATES, "TkFixedFont")
    return {
        "base": (base, 10),
        "small": (base, 9),
        "bold": (base, 10, "bold"),
        "head": (base, 8, "bold"),
        "title": (base, 12, "bold"),
        "brand": (base, 11, "bold"),
        "mono": (mono, 9),
    }


def apply(root):
    """Richtet Farben und Schriften für alle ttk- und tk-Elemente ein. Gibt die Schriften zurück."""
    F = fonts(root)
    root.configure(background=C["bg"])
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        try:
            tkfont.nametofont(name, root).configure(family=F["base"][0], size=F["base"][1])
        except Exception:      # noqa: BLE001
            pass

    # klassische tk-Elemente
    root.option_add("*Listbox.background", C["field"])
    root.option_add("*Listbox.foreground", C["text"])
    root.option_add("*Listbox.selectBackground", C["accent"])
    root.option_add("*Listbox.selectForeground", C["accent_ink"])
    root.option_add("*Listbox.borderWidth", 0)
    root.option_add("*Listbox.highlightThickness", 1)
    root.option_add("*Listbox.highlightColor", C["border"])
    root.option_add("*Listbox.highlightBackground", C["border"])
    root.option_add("*Listbox.activeStyle", "none")
    root.option_add("*TCombobox*Listbox.background", C["field"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["accent_ink"])
    root.option_add("*Toplevel.background", C["bg"])

    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure(".", background=C["panel"], foreground=C["text"], fieldbackground=C["field"],
                 bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                 troughcolor=C["panel"], focuscolor=C["accent"], selectbackground=C["accent"],
                 selectforeground=C["accent_ink"], insertcolor=C["text"], font=F["base"])
    st.map(".", foreground=[("disabled", C["dim"])])

    st.configure("TFrame", background=C["panel"])
    st.configure("Bg.TFrame", background=C["bg"])
    st.configure("Bar.TFrame", background=C["panel"])
    st.configure("Stage.TFrame", background=C["stage"])
    st.configure("Card.TFrame", background=C["panel2"])

    st.configure("TLabel", background=C["panel"], foreground=C["text"])
    st.configure("Muted.TLabel", foreground=C["muted"], font=F["small"])
    st.configure("Head.TLabel", foreground=C["muted"], font=F["head"])
    st.configure("Title.TLabel", font=F["title"])
    st.configure("Brand.TLabel", foreground=C["accent"], font=F["brand"])
    st.configure("Stage.TLabel", background=C["stage"], foreground=C["dim"], font=F["small"])
    st.configure("Card.TLabel", background=C["panel2"])
    st.configure("Status.TLabel", background=C["bg"], foreground=C["muted"], font=F["small"])

    btn = dict(background=C["panel2"], foreground=C["text"], bordercolor=C["border"],
               lightcolor=C["panel2"], darkcolor=C["panel2"], relief="flat", padding=(10, 5), focusthickness=0)
    st.configure("TButton", **btn)
    st.map("TButton",
           background=[("pressed", C["border"]), ("active", C["hover"]), ("disabled", C["panel"])],
           bordercolor=[("active", C["accent"])],
           lightcolor=[("active", C["hover"])], darkcolor=[("active", C["hover"])])
    st.configure("Accent.TButton", background=C["accent"], foreground=C["accent_ink"], bordercolor=C["accent"],
                 lightcolor=C["accent"], darkcolor=C["accent"], font=F["bold"])
    st.map("Accent.TButton", background=[("active", C["accent_hi"]), ("pressed", C["accent"])],
           lightcolor=[("active", C["accent_hi"])], darkcolor=[("active", C["accent_hi"])])
    st.configure("Tool.TButton", background=C["panel"], bordercolor=C["panel"], lightcolor=C["panel"],
                 darkcolor=C["panel"], padding=5)
    st.map("Tool.TButton", background=[("active", C["hover"]), ("pressed", C["border"])],
           bordercolor=[("active", C["hover"])], lightcolor=[("active", C["hover"])],
           darkcolor=[("active", C["hover"])])
    st.configure("Small.TButton", padding=(6, 3), background=C["panel2"])
    st.configure("Tile.TButton", background=C["panel2"], padding=(4, 8), font=F["small"], foreground=C["text"])

    for name in ("Chip.Toolbutton", "Seg.Toolbutton"):
        st.configure(name, background=C["panel2"], foreground=C["muted"], bordercolor=C["border"],
                     lightcolor=C["panel2"], darkcolor=C["panel2"], padding=(9, 4), font=F["small"],
                     relief="flat", anchor="center")
        st.map(name,
               background=[("selected", C["accent"]), ("active", C["hover"])],
               foreground=[("selected", C["accent_ink"]), ("active", C["text"])],
               lightcolor=[("selected", C["accent"])], darkcolor=[("selected", C["accent"])],
               bordercolor=[("selected", C["accent"])])

    st.configure("TCheckbutton", background=C["panel"], foreground=C["text"], indicatorbackground=C["field"],
                 indicatorforeground=C["accent"], indicatormargin=(0, 0, 6, 0))
    st.map("TCheckbutton", background=[("active", C["panel"])],
           indicatorbackground=[("selected", C["field"]), ("active", C["hover"])])

    field = dict(fieldbackground=C["field"], foreground=C["text"], bordercolor=C["border"],
                 lightcolor=C["field"], darkcolor=C["field"], insertcolor=C["text"], padding=(6, 4))
    st.configure("TEntry", **field)
    st.map("TEntry", bordercolor=[("focus", C["accent"])], lightcolor=[("focus", C["accent"])])
    st.configure("TCombobox", arrowcolor=C["muted"], background=C["panel2"], **field)
    st.map("TCombobox", fieldbackground=[("readonly", C["field"]), ("disabled", C["panel"])],
           foreground=[("readonly", C["text"]), ("disabled", C["dim"])],
           bordercolor=[("focus", C["accent"])], background=[("active", C["hover"])],
           arrowcolor=[("disabled", C["dim"])])

    st.configure("TScrollbar", background=C["panel2"], troughcolor=C["panel"], bordercolor=C["panel"],
                 arrowcolor=C["muted"], lightcolor=C["panel2"], darkcolor=C["panel2"], gripcount=0)
    st.map("TScrollbar", background=[("active", C["hover"])])
    st.configure("Stage.Vertical.TScrollbar", troughcolor=C["stage"], bordercolor=C["stage"])
    st.configure("Stage.Horizontal.TScrollbar", troughcolor=C["stage"], bordercolor=C["stage"])

    st.configure("TSeparator", background=C["border"])
    st.configure("TNotebook", background=C["bg"], bordercolor=C["border"], tabmargins=(8, 6, 8, 0))
    st.configure("TNotebook.Tab", background=C["panel"], foreground=C["muted"], padding=(12, 5),
                 bordercolor=C["border"], lightcolor=C["panel"], darkcolor=C["panel"])
    st.map("TNotebook.Tab", background=[("selected", C["panel2"])], foreground=[("selected", C["text"])],
           lightcolor=[("selected", C["panel2"])])
    return F


class Tooltip:
    """Kleiner Hinweis, der beim Darüberfahren erscheint."""

    def __init__(self, widget, text, delay=450):
        self.widget, self.text, self.delay = widget, text, delay
        self.tip, self.job = None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._cancel()
        self.job = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self.job:
            try:
                self.widget.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None

    def _show(self):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 4
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, background=C["panel2"], foreground=C["text"],
                 borderwidth=1, relief="solid", padx=8, pady=4, justify="left").pack()

    def _hide(self, _e=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None
