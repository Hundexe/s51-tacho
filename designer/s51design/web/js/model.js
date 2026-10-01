// Das geöffnete Layout, Auswahl und Rückgängig-Verlauf (wie designer/s51design/editor.py)

import { S, get, newWidget } from "./schema.js";

const GRID = 4;
const MAX_UNDO = 200;

class Model {
  constructor() {
    this.layout = null;
    this.screenIndex = 0;
    this.selected = null;       // Index des gewählten Elements auf der Seite
    this.dirty = false;
    this.fileHandle = null;     // Datei auf dem PC (File System Access)
    this.fileName = null;
    this.snap = true;
    this.undoStack = [];
    this.redoStack = [];
    this.listeners = new Set();
    this.clipboard = null;
  }

  // -- Benachrichtigung ------------------------------------------------------

  on(fn) { this.listeners.add(fn); }
  emit(kind = "all") { for (const fn of this.listeners) fn(kind); }

  // -- Laden -----------------------------------------------------------------

  load(layout, { fileHandle = null, fileName = null } = {}) {
    this.layout = layout;
    this.screenIndex = 0;
    this.selected = null;
    this.dirty = false;
    this.fileHandle = fileHandle;
    this.fileName = fileName;
    this.undoStack = [];
    this.redoStack = [];
    this.emit("load");
  }

  get screen() { return this.layout.screens[this.screenIndex]; }
  get widget() { return this.selected === null ? null : this.screen.widgets[this.selected] || null; }

  // -- Verlauf ---------------------------------------------------------------

  snapshot() {
    return JSON.stringify({ l: this.layout, s: this.screenIndex, w: this.selected });
  }

  checkpoint() {
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > MAX_UNDO) this.undoStack.shift();
    this.redoStack = [];
    this.dirty = true;
  }

  restore(snap) {
    const d = JSON.parse(snap);
    this.layout = d.l;
    this.screenIndex = Math.min(d.s, this.layout.screens.length - 1);
    this.selected = d.w !== null && d.w < this.screen.widgets.length ? d.w : null;
    this.dirty = true;
  }

  undo() {
    if (!this.undoStack.length) return false;
    this.redoStack.push(this.snapshot());
    this.restore(this.undoStack.pop());
    this.emit("all");
    return true;
  }

  redo() {
    if (!this.redoStack.length) return false;
    this.undoStack.push(this.snapshot());
    this.restore(this.redoStack.pop());
    this.emit("all");
    return true;
  }

  // Änderung mit einem Rückgängig-Schritt
  change(fn, kind = "all") {
    this.checkpoint();
    fn();
    this.emit(kind);
  }

  // -- Seiten ----------------------------------------------------------------

  selectScreen(i) {
    if (i < 0 || i >= this.layout.screens.length || i === this.screenIndex) return;
    this.screenIndex = i;
    this.selected = null;
    this.emit("screen");
  }

  freeScreenId() {
    const used = new Set(this.layout.screens.map((s) => s.id));
    for (let i = 0; i < S.info.limits.screens; i++) if (!used.has(i)) return i;
    throw new Error(`Höchstens ${S.info.limits.screens} Seiten möglich`);
  }

  addScreen() {
    const id = this.freeScreenId();
    this.change(() => {
      this.layout.screens.splice(this.screenIndex + 1, 0,
        { id, name: `Seite ${id + 1}`, role: "page", night_of: null, bg: "#000000", widgets: [] });
      this.screenIndex += 1;
      this.selected = null;
    });
  }

  duplicateScreen() {
    const id = this.freeScreenId();
    this.change(() => {
      const copy = structuredClone(this.screen);
      copy.id = id;
      copy.name = `${copy.name} (Kopie)`;
      if (copy.role === "startup") copy.role = "page";
      this.layout.screens.splice(this.screenIndex + 1, 0, copy);
      this.screenIndex += 1;
      this.selected = null;
    });
  }

  deleteScreen() {
    if (this.layout.screens.length <= 1) throw new Error("Die letzte Seite kann nicht gelöscht werden");
    this.change(() => {
      const [removed] = this.layout.screens.splice(this.screenIndex, 1);
      for (const s of this.layout.screens) {
        if (s.role === "night" && s.night_of === removed.id) { s.role = "page"; s.night_of = null; }
      }
      this.screenIndex = Math.max(0, this.screenIndex - 1);
      this.selected = null;
    });
  }

  moveScreen(from, to) {
    const n = this.layout.screens.length;
    if (to < 0 || to >= n || from === to) return;
    this.change(() => {
      const [s] = this.layout.screens.splice(from, 1);
      this.layout.screens.splice(to, 0, s);
      this.screenIndex = to;
    });
  }

  setScreen(changes) {
    if (changes.role === "startup" && this.layout.screens.some((s) => s !== this.screen && s.role === "startup")) {
      throw new Error("Es gibt schon eine Startbild-Seite. Ein Layout kann nur eine haben.");
    }
    if (Object.entries(changes).every(([k, v]) => this.screen[k] === v)) return;
    this.change(() => Object.assign(this.screen, changes), "screen-props");
  }

  setLayoutField(key, value) {
    if (this.layout[key] === value) return;
    this.change(() => { this.layout[key] = value; }, "meta");
  }

  // -- Elemente --------------------------------------------------------------

  snapValue(v) {
    v = Math.round(v);
    return this.snap ? Math.round(v / GRID) * GRID : v;
  }

  select(i) {
    if (i === this.selected) return;
    this.selected = i;
    this.emit("selection");
  }

  addWidget(type, x, y) {
    if (this.screen.widgets.length >= S.info.limits.widgets) {
      throw new Error(`Höchstens ${S.info.limits.widgets} Elemente pro Seite`);
    }
    const w = newWidget(type, 0, 0);
    w.x = this.snapValue(x === undefined ? (this.layout.width - w.w) / 2 : x - w.w / 2);
    w.y = this.snapValue(y === undefined ? (this.layout.height - w.h) / 2 : y - w.h / 2);
    this.change(() => {
      this.screen.widgets.push(w);
      this.selected = this.screen.widgets.length - 1;
    });
    return w;
  }

  deleteWidget() {
    if (this.selected === null) return;
    this.change(() => {
      this.screen.widgets.splice(this.selected, 1);
      this.selected = null;
    });
  }

  duplicateWidget() {
    if (!this.widget) return;
    this.pasteWidget(structuredClone(this.widget), GRID * 2);
  }

  copyWidget() {
    if (this.widget) this.clipboard = structuredClone(this.widget);
  }

  pasteWidget(w = this.clipboard && structuredClone(this.clipboard), offset = GRID * 2) {
    if (!w) return;
    if (this.screen.widgets.length >= S.info.limits.widgets) {
      throw new Error(`Höchstens ${S.info.limits.widgets} Elemente pro Seite`);
    }
    w.x += offset;
    w.y += offset;
    w.locked = false;
    this.change(() => {
      this.screen.widgets.push(w);
      this.selected = this.screen.widgets.length - 1;
    });
  }

  reorder(target) {
    if (this.selected === null) return;
    const ws = this.screen.widgets;
    target = Math.max(0, Math.min(ws.length - 1, target));
    if (target === this.selected) return;
    this.change(() => {
      const [w] = ws.splice(this.selected, 1);
      ws.splice(target, 0, w);
      this.selected = target;
    });
  }

  toFront() { this.reorder(this.screen.widgets.length - 1); }
  toBack() { this.reorder(0); }
  forward() { if (this.selected !== null) this.reorder(this.selected + 1); }
  backward() { if (this.selected !== null) this.reorder(this.selected - 1); }

  setGeometry(changes, { record = true } = {}) {
    const w = this.widget;
    if (!w) return;
    const apply = () => {
      for (const [k, v] of Object.entries(changes)) {
        w[k] = k === "w" || k === "h" ? Math.max(1, Math.round(v)) : Math.round(v);
      }
    };
    if (record) this.change(apply, "geometry");
    else { apply(); this.emit("geometry"); }
  }

  setProp(key, value) {
    const w = this.widget;
    if (!w || get(w, key) === value) return;
    this.change(() => { w.props[key] = value; }, "props");
  }

  // Mehrere Eigenschaften in einem Schritt (ein Mal Rückgängig)
  setProps(values) {
    const w = this.widget;
    if (!w || Object.entries(values).every(([k, v]) => get(w, k) === v)) return;
    this.change(() => { Object.assign(w.props, values); }, "props");
  }

  setFlag(key, value, index = this.selected) {
    const w = this.screen.widgets[index];
    if (!w || w[key] === value) return;
    this.change(() => { w[key] = value; }, "flags");
  }

  nudge(dx, dy) {
    const w = this.widget;
    if (!w || w.locked) return;
    this.change(() => { w.x += dx; w.y += dy; }, "geometry");
  }

  // -- Bilder ----------------------------------------------------------------

  imageById(id) { return this.layout.images.find((i) => i.id === id) || null; }

  freeImageId() {
    const used = new Set(this.layout.images.map((i) => i.id));
    for (let i = 0; i < S.info.limits.images; i++) if (!used.has(i)) return i;
    throw new Error(`Höchstens ${S.info.limits.images} Bilder pro Layout`);
  }

  // Neues Bild: in das gewählte Bild-Element einsetzen oder als neues Element in die Mitte
  addImage(img) {
    if (this.layout.images.length >= S.info.limits.images) throw new Error(`Höchstens ${S.info.limits.images} Bilder pro Layout`);
    this.change(() => {
      this.layout.images.push(img);
      let w = this.widget;
      if (!w || w.type !== "image") {
        w = newWidget("image", 0, 0);
        w.x = Math.round((this.layout.width - img.width) / 2);
        w.y = Math.round((this.layout.height - img.height) / 2);
        this.screen.widgets.push(w);
        this.selected = this.screen.widgets.length - 1;
      }
      w.props.image = img.id;
      w.w = img.width;
      w.h = img.height;
    });
  }

  removeImage(id) {
    this.change(() => {
      this.layout.images = this.layout.images.filter((i) => i.id !== id);
      for (const s of this.layout.screens) {
        for (const w of s.widgets) if (w.type === "image" && get(w, "image") === id) w.props.image = S.info.no_image;
      }
    });
  }

  imageUsage(id) {
    let n = 0;
    for (const s of this.layout.screens) for (const w of s.widgets) if (w.type === "image" && get(w, "image") === id) n++;
    return n;
  }
}

export const model = new Model();
