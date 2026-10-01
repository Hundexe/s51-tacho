"""Rauchtest der Oberfläche ohne echtes Fenster.

Ersetzt tkinter durch einfache Attrappen, damit die Logik der Oberfläche
(Klicks, Ziehen, Eigenschaften, Export, Konfiguration, Übertragung) auch
auf Rechnern ohne Bildschirm geprüft werden kann. Wie das Programm wirklich
aussieht, prüft dieser Test nicht.
"""

import importlib
import itertools
import os
import sys
import tempfile
import threading
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

_ids = itertools.count(1)


class _Var:
    def __init__(self, master=None, value=None):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class _Widget:
    def __init__(self, *args, **kw):
        self.kw = dict(kw)
        self.children = []
        self.bindings = {}
        self.items = []
        self.selection = []
        self.value = ""
        self.states = set()
        if args and isinstance(args[0], _Widget):
            args[0].children.append(self)

    def __getattr__(self, name):
        def noop(*a, **k):
            return None
        return noop

    # gemeinsame Methoden
    def bind(self, seq, fn=None, add=None):
        self.bindings[seq] = fn

    def configure(self, *a, **kw):
        self.kw.update(kw)

    config = configure

    def cget(self, key):
        return self.kw.get(key, "#000000")

    def winfo_children(self):
        return list(self.children)

    def destroy(self):
        self.children = []

    # Listbox
    def delete(self, *a):
        if self.__class__.__name__ == "Canvas":
            return
        self.items = []

    def insert(self, idx, text):
        self.items.append(text)

    def selection_set(self, i):
        self.selection = [i]

    def selection_clear(self, *a):
        self.selection = []

    def curselection(self):
        return tuple(self.selection)

    # Combobox
    def set(self, v):
        self.value = v

    def get(self):
        return self.value

    def state(self, s):
        self.states = set(s)


class Canvas(_Widget):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.created = []

    def _create(self, kind, *a, **kw):
        i = next(_ids)
        self.created.append((kind, a, kw))
        return i

    def create_rectangle(self, *a, **kw): return self._create("rect", *a, **kw)
    def create_text(self, *a, **kw): return self._create("text", *a, **kw)
    def create_line(self, *a, **kw): return self._create("line", *a, **kw)
    def create_arc(self, *a, **kw): return self._create("arc", *a, **kw)
    def create_polygon(self, *a, **kw): return self._create("poly", *a, **kw)
    def create_oval(self, *a, **kw): return self._create("oval", *a, **kw)
    def create_window(self, *a, **kw): return self._create("window", *a, **kw)
    def create_image(self, *a, **kw): return self._create("image", *a, **kw)
    def canvasx(self, x): return x
    def canvasy(self, y): return y


class PhotoImage:
    def __init__(self, *a, data=None, **kw):
        self.data = data
        self.factor = 1

    def zoom(self, x, y=None):
        p = PhotoImage(data=self.data)
        p.factor = self.factor * x
        return p


class Tk(_Widget):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.after_calls = []
        self.destroyed = False

    def after(self, ms, fn=None):
        self.after_calls.append(fn)

    def destroy(self):
        self.destroyed = True


def install_fake_tk():
    tk = types.ModuleType("tkinter")
    tk.Tk = Tk
    tk.Toplevel = _Widget
    tk.Canvas = Canvas
    tk.Listbox = _Widget
    tk.Menu = _Widget
    tk.Button = _Widget
    tk.Label = _Widget
    tk.PhotoImage = PhotoImage
    tk.StringVar = tk.IntVar = tk.BooleanVar = _Var
    tk.TclError = RuntimeError
    ttk = types.ModuleType("tkinter.ttk")
    for name in ("Frame", "Label", "Button", "Entry", "Combobox", "Checkbutton", "Radiobutton", "Scrollbar",
                 "Notebook", "Separator", "Style"):
        setattr(ttk, name, type(name, (_Widget,), {}))
    mb = types.ModuleType("tkinter.messagebox")
    mb.answer = True
    mb.shown = []
    for fn in ("showinfo", "showwarning", "showerror"):
        setattr(mb, fn, lambda *a, _fn=fn, **k: mb.shown.append((_fn, a)))
    mb.askyesno = lambda *a, **k: mb.answer
    mb.askyesnocancel = lambda *a, **k: mb.answer
    fd = types.ModuleType("tkinter.filedialog")
    fd.next_path = None
    fd.askdirectory = lambda *a, **k: fd.next_path
    fd.askopenfilename = lambda *a, **k: fd.next_path
    fd.asksaveasfilename = lambda *a, **k: fd.next_path
    cc = types.ModuleType("tkinter.colorchooser")
    cc.askcolor = lambda *a, **k: ((1, 2, 3), "#010203")
    font = types.ModuleType("tkinter.font")
    font.families = lambda *a, **k: ("DejaVu Sans", "DejaVu Sans Mono")
    font.nametofont = lambda *a, **k: _Widget()
    tk.ttk, tk.messagebox, tk.filedialog, tk.colorchooser, tk.font = ttk, mb, fd, cc, font
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": mb,
                        "tkinter.filedialog": fd, "tkinter.colorchooser": cc, "tkinter.font": font})
    return tk, mb, fd


class Ev:
    def __init__(self, x, y):
        self.x, self.y = x, y


class AppSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {k: sys.modules.get(k) for k in
                     ("tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog", "tkinter.colorchooser",
                      "tkinter.font")}
        cls.tk, cls.mb, cls.fd = install_fake_tk()
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["HOME"] = cls.tmp.name
        os.environ["USERPROFILE"] = cls.tmp.name
        import s51design.theme as theme_mod
        importlib.reload(theme_mod)
        import s51design.app as app_mod
        cls.app_mod = importlib.reload(app_mod)
        cls.app_mod.SETTINGS_PATH = os.path.join(cls.tmp.name, "settings.json")

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        cls.tmp.cleanup()

    def setUp(self):
        self.root = self.tk.Tk()
        self.app = self.app_mod.App(self.root)
        self.mb.shown.clear()

    def test_starts_with_preset(self):
        self.assertEqual(self.app.ed.layout.name, "Klar")
        self.assertTrue(len(self.app.canvas.created) > 20)
        self.assertEqual(len(self.app.screen_list.items), len(self.app.ed.layout.screens))
        self.assertTrue(any("Startbild" in item for item in self.app.screen_list.items))

    def test_add_select_drag_edit_undo(self):
        app, z = self.app, self.app.z()
        app.ed.new()
        app.refresh_all()
        for wt in self.app_mod.S.WIDGET_TYPES:
            app.add_widget(wt.key)
        n = len(self.app_mod.S.WIDGET_TYPES)
        self.assertEqual(len(app.ed.screen.widgets), n)
        app.ed.selected = 1                   # Wert nach ganz oben legen
        app.ed.raise_widget(True)
        w = app.ed.screen.widgets[-1]
        self.assertEqual(w.type, "value")
        app.ed.selected = None
        # anklicken und ziehen
        app._on_press(Ev((w.x + 5) * z, (w.y + 5) * z))
        self.assertIs(app.ed.widget, w)
        x0 = w.x
        app._on_drag(Ev((w.x + 45) * z, (w.y + 5) * z))
        app._on_release(Ev(0, 0))
        self.assertEqual(w.x, x0 + 40)
        # Eigenschaften
        prop = self.app_mod.S.PROP_BY_KEY["decimals"]
        var = self.tk.StringVar(value="2")
        app._commit_text_prop(prop, "2", var)
        self.assertEqual(w.props["decimals"], 2)
        app._commit_text_prop(prop, "999", var)                  # ungültig
        self.assertEqual(w.props["decimals"], 2)
        self.assertEqual(var.get(), "2")
        app._commit_prop("source", "rpm")
        self.assertEqual(w.props["source"], "rpm")
        app._commit_geometry("w", "77", self.tk.StringVar(value=""))
        self.assertEqual(w.w, 77)
        app._nudge(0, 10)
        self.assertEqual(w.y % 1, 0)
        app.undo()
        app.undo()
        self.assertNotEqual(app.ed.screen.widgets[1].w, 0)
        app.redo()
        # Element löschen und duplizieren
        app._on_press(Ev((w.x + 5) * z, (w.y + 5) * z))
        app.duplicate()
        self.assertEqual(len(app.ed.screen.widgets), n + 1)
        app.delete()
        self.assertEqual(len(app.ed.screen.widgets), n)
        # Eigenschaften-Panel für jeden Typ bauen
        for i in range(len(app.ed.screen.widgets)):
            app.ed.selected = i
            app.build_props()
        app.ed.selected = None
        app.build_props()

    def test_screens(self):
        app = self.app
        n = len(app.ed.layout.screens)
        app.ed_add_screen()
        self.assertEqual(len(app.ed.layout.screens), n + 1)
        app.ed_dup_screen()
        self.assertEqual(len(app.ed.layout.screens), n + 2)
        app._set_screen(name="Test")
        self.assertEqual(app.ed.screen.name, "Test")
        with self.assertRaises(ValueError):       # Klar hat schon eine Startbild-Seite
            app._set_screen(role="startup")
        app.ed_del_screen()
        self.assertEqual(len(app.ed.layout.screens), n + 1)
        self.screen_list_ok()
        for i in range(len(app.ed.layout.screens)):  # Eigenschaften jeder Seitenart bauen
            app.ed.select_screen(i)
            app.refresh_all()

    def test_images(self):
        from s51design import images as I
        app = self.app
        app.ed.new()
        app.refresh_all()
        w, h = 600, 300                      # größer als das Display: wird verkleinert
        rgba = bytes([200, 40, 40, 255]) * (w * h)
        path = os.path.join(self.tmp.name, "logo.png")
        with open(path, "wb") as f:
            f.write(I.png_encode(w, h, rgba))
        self.assertTrue(app.import_image(path))
        wd = app.ed.widget
        self.assertEqual(wd.type, "image")
        img = app.ed.image_by_id(wd.get("image"))
        self.assertEqual((img.width, img.height), (480, 240))
        self.assertEqual((wd.w, wd.h), (480, 240))
        self.assertTrue(any(kind == "image" for kind, _, _ in app.canvas.created))
        # zweites Bild in den gewählten Rahmen einpassen
        app._commit_geometry("w", "100", self.tk.StringVar(value=""))
        app._commit_geometry("h", "100", self.tk.StringVar(value=""))
        self.assertTrue(app.import_image(path))
        self.assertEqual(len(app.ed.layout.images), 2)
        img2 = app.ed.image_by_id(wd.get("image"))
        self.assertEqual((img2.width, img2.height), (100, 50))
        app.image_original_size()
        self.assertEqual((wd.w, wd.h), (100, 50))
        app.build_props()
        app.ed.selected = None
        app.build_props()                    # Bilderliste der Seite
        app.delete_image(img)
        self.assertEqual(len(app.ed.layout.images), 1)
        self.assertGreater(len(app.ed.encoded()), 0)
        app.undo()
        self.assertEqual(len(app.ed.layout.images), 2)
        # kaputte Datei
        bad = os.path.join(self.tmp.name, "kaputt.png")
        with open(bad, "wb") as f:
            f.write(b"kein Bild")
        self.assertFalse(app.import_image(bad))
        self.assertTrue(any(kind == "showerror" for kind, _ in self.mb.shown))

    def screen_list_ok(self):
        self.assertEqual(len(self.app.screen_list.items), len(self.app.ed.layout.screens))

    def test_save_open_export(self):
        app = self.app
        path = os.path.join(self.tmp.name, "mein.s51")
        self.fd.next_path = path
        self.assertTrue(app.save_as())
        self.assertFalse(app.ed.dirty)
        app.ed.new()
        self.fd.next_path = path
        app.open()
        self.assertEqual(app.ed.layout.name, "Klar")
        sd = os.path.join(self.tmp.name, "sd")
        os.makedirs(sd)
        self.fd.next_path = sd
        app.export_sd()
        from s51design import config_format, layout_format
        self.assertEqual(layout_format.load(os.path.join(sd, "s51", "design.s51")).name, "Klar")
        values, warnings = config_format.load(os.path.join(sd, "s51", "tacho.cfg"))
        self.assertEqual(warnings, [])
        # zweiter Export: vorhandene cfg behalten (Antwort Nein)
        with open(os.path.join(sd, "s51", "tacho.cfg"), "w", encoding="utf-8") as f:
            f.write("[fahrzeug]\nmagnete = 4\n")
        self.mb.answer = False
        app.export_sd()
        self.mb.answer = True
        with open(os.path.join(sd, "s51", "tacho.cfg"), encoding="utf-8") as f:
            self.assertIn("magnete = 4", f.read())

    def test_config_dialog(self):
        dlg = self.app_mod.ConfigDialog(self.app)
        dlg.vars[("fahrzeug", "magnete")].set("3")
        dlg.apply()
        self.assertEqual(self.app.cfg[("fahrzeug", "magnete")], 3)
        dlg = self.app_mod.ConfigDialog(self.app)
        dlg.vars[("fahrzeug", "magnete")].set("abc")
        dlg.apply()
        self.assertEqual(self.app.cfg[("fahrzeug", "magnete")], 3)
        self.assertTrue(any(kind == "showerror" for kind, _ in self.mb.shown))
        dlg.reset()
        dlg.apply()
        self.assertEqual(self.app.cfg[("fahrzeug", "magnete")], 2)

    def test_wireless(self):
        from s51design import mock_tacho
        httpd, _ = mock_tacho.serve(0, "111222", os.path.join(self.tmp.name, "w"), verbose=False)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            dlg = self.app_mod.WirelessDialog(self.app)
            dlg.host.set(f"localhost:{httpd.server_address[1]}")
            dlg.code.set("111222")
            for action in (dlg.check, dlg.send_layout, dlg.send_config):
                dlg.msg.set("")
                action()
                deadline = time.time() + 5
                while time.time() < deadline:
                    self.app._tick()
                    if dlg.msg.get() and not dlg.msg.get().endswith("…"):
                        break
                    time.sleep(0.02)
                self.assertNotIn("Fehler", dlg.msg.get())
                self.assertNotIn("nicht erreichbar", dlg.msg.get())
            self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "w", "design.s51")))
            dlg.code.set("000000")
            dlg.send_layout()
            deadline = time.time() + 5
            while time.time() < deadline and (not dlg.msg.get() or dlg.msg.get().endswith("…")):
                self.app._tick()
                time.sleep(0.02)
            self.assertIn("Code", dlg.msg.get())
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
