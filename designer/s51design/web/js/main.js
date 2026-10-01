// Start und Verdrahtung der Oberfläche

import { api, startHeartbeat } from "./api.js";
import { blankLayout, cfg, configDialog, exportDialog, importImage, initConfig, templateDialog, wirelessDialog } from "./dialogs.js";
import { confirmDiscard, openFile, save, saveAs } from "./files.js";
import { icon, TYPE_ICON } from "./icons.js";
import { renderInspector, syncGeometry } from "./inspector.js";
import { model } from "./model.js";
import { initPageTools, refreshCurrentThumb, renderLayers, renderPages } from "./panels.js";
import { S, initSchema } from "./schema.js";
import { initStage, layoutStage, render, setDemo, setPreview, setZoom, view } from "./stage.js";
import { dropdown, h, initTooltips, showError, toast } from "./ui.js";

const $ = (id) => document.getElementById(id);
const DOCK_LABEL = { text: "Text", value: "Wert", bar: "Balken", gauge: "Instrument", indicator: "Leuchte", rect: "Fläche", image: "Bild",
  button: "Taste" };

function wrap(fn) {
  return (...a) => { try { const r = fn(...a); if (r && r.catch) r.catch(showError); } catch (e) { showError(e); } };
}

// -- Kopfleiste ------------------------------------------------------------------------

function buildTopbar() {
  const fileBtn = h("button", { class: "btn ghost" }, "Datei");
  $("file-menu").append(dropdown(fileBtn, () => [
    { label: "Neues Design…", icon: icon("new"), key: "Strg+N", run: wrap(templateDialog) },
    { label: "Öffnen…", icon: icon("open"), key: "Strg+O", run: wrap(openFile) },
    { label: "Speichern", icon: icon("save"), key: "Strg+S", run: wrap(save) },
    { label: "Speichern unter…", icon: icon("save"), key: "Strg+Umschalt+S", run: wrap(saveAs) },
    "-",
    { label: "Auf SD-Karte schreiben…", icon: icon("sd"), run: wrap(exportDialog) },
    { label: "Drahtlos übertragen…", icon: icon("wireless"), run: wrap(wirelessDialog) },
    "-",
    { label: "Tacho-Einstellungen…", icon: icon("settings"), run: wrap(configDialog) },
    { label: `Über den S51 Designer ${S.info.version}`, icon: icon("flag"),
      run: () => toast(`S51 Designer ${S.info.version}, Layout-Format ${S.info.format}. Doku und Quellen: github.com/Hundexe/s51-tacho`, "ok", 7000) },
  ]));

  const tb = $("toolbar");
  const undoBtn = h("button", { class: "icon-btn", "data-tip": "Rückgängig (Strg+Z)", html: icon("undo"), onclick: () => model.undo() });
  const redoBtn = h("button", { class: "icon-btn", "data-tip": "Wiederholen (Strg+Y)", html: icon("redo"), onclick: () => model.redo() });
  tb.append(undoBtn, redoBtn,
    h("button", { class: "icon-btn", "data-tip": "Bild laden", html: icon("image"), onclick: wrap(importImage) }),
    h("button", { class: "icon-btn", "data-tip": "Tacho-Einstellungen", html: icon("settings"), onclick: wrap(configDialog) }));
  model.on(() => {
    undoBtn.disabled = !model.undoStack.length;
    redoBtn.disabled = !model.redoStack.length;
  });

  $("actions").append(
    h("button", { class: "btn", "data-tip": "Layout und Einstellungen per WLAN zum Tacho schicken", onclick: wrap(wirelessDialog),
      html: `${icon("wireless")}<span>Drahtlos</span>` }),
    h("button", { class: "btn primary", "data-tip": "Design und Einstellungen auf die SD-Karte des Tachos schreiben", onclick: wrap(exportDialog),
      html: `${icon("sd")}<span>Auf SD-Karte</span>` }));

  const nameInput = $("doc-name");
  nameInput.addEventListener("change", () => model.setLayoutField("name", nameInput.value.trim() || "Ohne Namen"));
  nameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") nameInput.blur(); });
}

function updateDocState() {
  const nameInput = $("doc-name");
  if (document.activeElement !== nameInput) nameInput.value = model.layout.name;
  const file = model.fileName ? model.fileName : "nicht gespeichert";
  $("doc-state").textContent = model.dirty ? `${file}, geändert` : file;
  document.title = `${model.dirty ? "● " : ""}${model.layout.name} – S51 Designer`;
}

// -- Dock ----------------------------------------------------------------------------

function buildDock() {
  const dock = $("dock");
  for (const t of S.info.widget_types) {
    const tile = h("button", {
      class: "tile", draggable: "true", "data-tip": t.key === "image" ? "Bild-Element. Das Bild kommt über „Bild laden“." : `${t.label} hinzufügen oder auf das Display ziehen`,
      onclick: wrap(() => model.addWidget(t.key)),
      ondragstart: (e) => { e.dataTransfer.setData("text/s51-type", t.key); e.dataTransfer.effectAllowed = "copy"; },
      html: `${icon(TYPE_ICON[t.key] || "page")}<span>${DOCK_LABEL[t.key] || t.label}</span>`,
    });
    dock.append(tile);
  }
  dock.append(h("div", { class: "sep" }));
  const zoomBox = h("div", { class: "seg", role: "group", "aria-label": "Zoom" });
  const zooms = [["fit", "Einpassen"], [1, "1×"], [2, "2×"], [3, "3×"]];
  const refreshZoom = () => {
    zoomBox.replaceChildren(...zooms.map(([z, l]) => h("button", {
      class: view.zoomMode === z ? "on" : "", "data-tip": z === "fit" ? `Einpassen (jetzt ${String(view.zoom).replace(".", ",")}×)` : `Zoom ${l}`,
      onclick: () => setZoom(z),
    }, z === "fit" ? h("span", { html: icon("fit") }) : l)));
  };
  view.onZoom = refreshZoom;
  refreshZoom();
  const toggle = (name, tip, get, set) => {
    const b = h("button", { class: `toggle ${get() ? "on" : ""}`, "data-tip": tip, html: icon(name),
      onclick: () => { set(!get()); b.classList.toggle("on", get()); } });
    return b;
  };
  dock.append(zoomBox, h("div", { class: "sep" }),
    toggle("grid", "Raster (16 px)", () => view.grid, (v) => { view.grid = v; render(); }),
    toggle("magnet", "Einrasten auf 4 px und an anderen Elementen", () => model.snap, (v) => { model.snap = v; }),
    toggle("eye", "Vorschau wie am Tacho", () => view.preview, (v) => setPreview(v)),
    toggle("play", "Demo-Werte laufen lassen", () => view.demo, (v) => setDemo(v)));
}

// -- Statuszeile und Dateigröße ------------------------------------------------------------

let checkTimer = null;
function scheduleCheck() {
  clearTimeout(checkTimer);
  checkTimer = setTimeout(async () => {
    const el = $("filesize");
    try {
      const r = await api.check(model.layout);
      el.classList.remove("bad", "warn");
      if (!r.ok) { el.textContent = `So nicht speicherbar: ${r.error}`; el.classList.add("bad"); return; }
      const kb = (n) => (n / 1024).toFixed(1).replace(".", ",");
      el.textContent = `Dateigröße ${kb(r.size)} KB von ${kb(S.info.limits.file)} KB`;
      if (r.size > S.info.limits.file * 0.8) el.classList.add("warn");
    } catch (e) {
      el.textContent = e.message;
      el.classList.add("bad");
    }
  }, 400);
}

function updateStatus() {
  const n = model.screen.widgets.length;
  $("status").textContent = `Seite „${model.screen.name}“: ${n} von ${S.info.limits.widgets} Elementen. ${model.layout.images.length === 1 ? "1 Bild" : `${model.layout.images.length} Bilder`} im Layout.`;
}

// -- Änderungen verteilen --------------------------------------------------------------------

function onModel(kind) {
  if (kind === "load") layoutStage();
  if (kind === "geometry") {           // während des Ziehens: nur zeichnen
    render();
    syncGeometry();
    return;
  }
  render();
  updateDocState();
  if (kind === "saved") return;
  updateStatus();
  if (kind === "selection") {
    renderLayers();
    renderInspector();
    return;
  }
  if (["load", "all", "screen"].includes(kind)) {
    renderPages();
  } else if (kind === "screen-props") {
    renderPages();
  } else {
    refreshCurrentThumb();
  }
  renderLayers();
  if (kind !== "props" && kind !== "meta") renderInspector();
  else if (kind === "props") syncGeometry();
  scheduleCheck();
}

// -- Tastatur --------------------------------------------------------------------------------

function onKey(e) {
  const t = e.target;
  const typing = t.closest && t.closest("input, textarea, select, [contenteditable]");
  if (document.querySelector(".modal-back")) return;
  const ctrl = e.ctrlKey || e.metaKey;
  const k = e.key.toLowerCase();
  if (ctrl && k === "s") { e.preventDefault(); wrap(e.shiftKey ? saveAs : save)(); return; }
  if (ctrl && k === "o") { e.preventDefault(); wrap(openFile)(); return; }
  if (ctrl && k === "n") { e.preventDefault(); wrap(templateDialog)(); return; }
  if (typing) return;
  if (ctrl && k === "z") { e.preventDefault(); if (e.shiftKey) model.redo(); else model.undo(); return; }
  if (ctrl && k === "y") { e.preventDefault(); model.redo(); return; }
  if (ctrl && k === "d") { e.preventDefault(); wrap(() => model.duplicateWidget())(); return; }
  if (ctrl && k === "c") { model.copyWidget(); if (model.widget) toast("Element kopiert", "ok", 1500); return; }
  if (ctrl && k === "v") { e.preventDefault(); wrap(() => model.pasteWidget())(); return; }
  if (ctrl && k === "0") { e.preventDefault(); setZoom("fit"); return; }
  if (k === "delete" || k === "backspace") { if (model.widget) { e.preventDefault(); model.deleteWidget(); } return; }
  if (k === "escape") { model.select(null); return; }
  const arrows = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] };
  if (arrows[k] && model.widget) {
    e.preventDefault();
    const step = e.shiftKey ? 10 : 1;
    model.nudge(arrows[k][0] * step, arrows[k][1] * step);
    return;
  }
  if (k === "pageup" || k === "pagedown") {
    e.preventDefault();
    model.selectScreen(model.screenIndex + (k === "pageup" ? -1 : 1));
  }
}

// -- Start -------------------------------------------------------------------------------------

async function boot() {
  initTooltips();
  try {
    initSchema(await api.info());
    await initConfig();
  } catch (e) {
    document.body.innerHTML = `<p style="padding:40px;font-size:15px">Der Designer ist nicht erreichbar: ${e.message}<br>Bitte das Programm neu starten.</p>`;
    return;
  }
  startHeartbeat();
  try { await document.fonts.load('700 20px "S51 Sans"'); await document.fonts.load('400 20px "S51 Sans"'); await document.fonts.load('700 20px "S51 Mono"'); } catch (e) { /* Schrift fehlt */ }
  buildTopbar();
  buildDock();
  initPageTools();
  initStage();
  model.on(onModel);
  document.addEventListener("keydown", onKey);
  document.addEventListener("s51-add", (e) => wrap(() => model.addWidget(e.detail.type, e.detail.x, e.detail.y))());
  document.addEventListener("s51-edit-text", () => {
    const ta = document.querySelector("#inspector textarea");
    if (ta) { ta.focus(); ta.select(); }
  });
  window.addEventListener("beforeunload", (e) => { if (model.dirty) { e.preventDefault(); e.returnValue = ""; } });
  const start = localStorage.getItem("s51-start") || "Klar";
  try {
    model.load(S.info.presets.includes(start) ? await api.preset(start) : blankLayout());
  } catch (e) {
    model.load(blankLayout());
  }
  void cfg;
  void confirmDiscard;
}

boot();
