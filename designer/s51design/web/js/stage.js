// Die Bühne: Display mit Rahmen, Auswahl, Ziehen, Größe ändern, Hilfslinien

import { model } from "./model.js";
import { demoValues, drawScreen } from "./render.js";

const HANDLE = 5;           // halbe Größe der Anfasser in Bildschirmpixeln
const SNAP_PX = 5;          // Fangbereich der Hilfslinien in Bildschirmpixeln
const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
const CURSOR = { nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize", n: "ns-resize",
  s: "ns-resize", e: "ew-resize", w: "ew-resize" };

export const view = {
  zoomMode: "fit",          // "fit" oder Zahl
  zoom: 1.5,
  grid: true,
  preview: false,
  demo: false,
  onZoom: null,
};

let screenCv, overlayCv, scroll, stageEl, coordsEl;
let drag = null;            // laufende Mausaktion
let guides = [];            // sichtbare Hilfslinien beim Ziehen
let hover = null;
let animTimer = null;

export function initStage() {
  screenCv = document.getElementById("screen");
  overlayCv = document.getElementById("overlay");
  scroll = document.getElementById("stage-scroll");
  stageEl = document.getElementById("stage");
  coordsEl = document.getElementById("coords");
  overlayCv.addEventListener("pointerdown", onDown);
  overlayCv.addEventListener("pointermove", onMove);
  overlayCv.addEventListener("pointerup", onUp);
  overlayCv.addEventListener("pointercancel", onUp);
  overlayCv.addEventListener("pointerleave", () => { hover = null; coordsEl.textContent = ""; drawOverlay(); });
  overlayCv.addEventListener("dblclick", (e) => {
    const w = model.widget;
    if (w && w.type === "text") document.dispatchEvent(new CustomEvent("s51-edit-text"));
  });
  // Elemente aus dem Dock auf das Display ziehen
  overlayCv.addEventListener("dragover", (e) => {
    if (e.dataTransfer.types.includes("text/s51-type")) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }
  });
  overlayCv.addEventListener("drop", (e) => {
    const type = e.dataTransfer.getData("text/s51-type");
    if (!type) return;
    e.preventDefault();
    const p = toDisplay(e);
    document.dispatchEvent(new CustomEvent("s51-add", { detail: { type, x: p.x, y: p.y } }));
  });
  scroll.addEventListener("wheel", (e) => {
    if (!e.ctrlKey) return;
    e.preventDefault();
    const steps = [0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4];
    let i = steps.findIndex((z) => z >= view.zoom - 0.01);
    if (i < 0) i = steps.length - 1;
    i = Math.max(0, Math.min(steps.length - 1, i + (e.deltaY < 0 ? 1 : -1)));
    setZoom(steps[i]);
  }, { passive: false });
  new ResizeObserver(() => { if (view.zoomMode === "fit") layoutStage(); }).observe(scroll);
}

// -- Größe und Zoom -----------------------------------------------------------

function fitZoom() {
  const L = model.layout;
  const w = scroll.clientWidth - 80 - 36, h = scroll.clientHeight - 150 - 36;
  return Math.max(0.5, Math.min(4, Math.min(w / L.width, h / L.height)));
}

export function setZoom(z) {
  view.zoomMode = z;
  layoutStage();
}

export function layoutStage() {
  if (!model.layout) return;
  view.zoom = view.zoomMode === "fit" ? Math.floor(fitZoom() * 20) / 20 : view.zoomMode;
  const L = model.layout, z = view.zoom, dpr = window.devicePixelRatio || 1;
  for (const cv of [screenCv, overlayCv]) {
    cv.style.width = `${L.width * z}px`;
    cv.style.height = `${L.height * z}px`;
    cv.width = Math.round(L.width * z * dpr);
    cv.height = Math.round(L.height * z * dpr);
  }
  if (view.onZoom) view.onZoom();
  render();
}

// -- Zeichnen -------------------------------------------------------------------

export function render() {
  if (!model.layout) return;
  const dpr = window.devicePixelRatio || 1;
  const t = performance.now() / 1000;
  const ctx = screenCv.getContext("2d");
  drawScreen(ctx, model.layout, model.screen, {
    scale: view.zoom * dpr,
    vals: demoValues(t, view.demo),
    t: view.demo ? t : 0.1,
    showHidden: !view.preview,
    grid: view.grid && !view.preview ? 16 : 0,
  });
  drawOverlay();
}

function drawOverlay() {
  const dpr = window.devicePixelRatio || 1, z = view.zoom;
  const ctx = overlayCv.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, overlayCv.width, overlayCv.height);
  if (view.preview || !model.layout) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const sel = model.widget;
  if (hover !== null && hover !== model.selected && !drag) {
    const w = model.screen.widgets[hover];
    if (w) {
      ctx.strokeStyle = "rgba(240, 160, 48, 0.55)";
      ctx.lineWidth = 1;
      ctx.strokeRect(w.x * z + 0.5, w.y * z + 0.5, w.w * z - 1, w.h * z - 1);
    }
  }
  if (guides.length) {
    ctx.strokeStyle = "#e2604f";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    for (const g of guides) {
      if (g.axis === "x") { ctx.moveTo(g.v * z + 0.5, 0); ctx.lineTo(g.v * z + 0.5, model.layout.height * z); }
      else { ctx.moveTo(0, g.v * z + 0.5); ctx.lineTo(model.layout.width * z, g.v * z + 0.5); }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }
  if (!sel) return;
  ctx.strokeStyle = "#f0a030";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(sel.x * z - 0.75, sel.y * z - 0.75, sel.w * z + 1.5, sel.h * z + 1.5);
  if (sel.locked) return;
  for (const h of HANDLES) {
    const [hx, hy] = handlePos(sel, h, z);
    ctx.fillStyle = "#ece5d3";
    ctx.strokeStyle = "#f0a030";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.rect(hx - HANDLE + 0.5, hy - HANDLE + 0.5, HANDLE * 2 - 1, HANDLE * 2 - 1);
    ctx.fill();
    ctx.stroke();
  }
  if (drag && drag.started) {
    const label = drag.mode === "move" ? `${sel.x}, ${sel.y}` : `${sel.w} × ${sel.h}`;
    ctx.font = '700 11px "UI"';
    const tw = ctx.measureText(label).width + 12;
    let lx = sel.x * z + (sel.w * z) / 2 - tw / 2, ly = (sel.y + sel.h) * z + 10;
    if (ly + 20 > model.layout.height * z) ly = sel.y * z - 30;
    ctx.fillStyle = "#f0a030";
    ctx.beginPath();
    ctx.roundRect(lx, ly, tw, 20, 5);
    ctx.fill();
    ctx.fillStyle = "#2b1a02";
    ctx.fillText(label, lx + 6, ly + 14);
  }
}

function handlePos(w, h, z) {
  const x0 = w.x * z, y0 = w.y * z, x1 = (w.x + w.w) * z, y1 = (w.y + w.h) * z;
  const xm = (x0 + x1) / 2, ym = (y0 + y1) / 2;
  return { nw: [x0, y0], n: [xm, y0], ne: [x1, y0], e: [x1, ym], se: [x1, y1], s: [xm, y1], sw: [x0, y1], w: [x0, ym] }[h];
}

// -- Maus -----------------------------------------------------------------------

function toDisplay(e) {
  const r = overlayCv.getBoundingClientRect();
  return { x: (e.clientX - r.left) / view.zoom, y: (e.clientY - r.top) / view.zoom, sx: e.clientX - r.left, sy: e.clientY - r.top };
}

function hitTest(x, y) {
  const ws = model.screen.widgets;
  for (let i = ws.length - 1; i >= 0; i--) {
    const w = ws[i];
    const pad = w.w < 6 || w.h < 6 ? 3 : 0;
    if (x >= w.x - pad && x <= w.x + w.w + pad && y >= w.y - pad && y <= w.y + w.h + pad) return i;
  }
  return null;
}

function handleAt(p) {
  const w = model.widget;
  if (!w || w.locked) return null;
  for (const h of HANDLES) {
    const [hx, hy] = handlePos(w, h, view.zoom);
    if (Math.abs(p.sx - hx) <= HANDLE + 2 && Math.abs(p.sy - hy) <= HANDLE + 2) return h;
  }
  return null;
}

function onDown(e) {
  if (view.preview || e.button !== 0) return;
  overlayCv.setPointerCapture(e.pointerId);
  overlayCv.focus();
  const p = toDisplay(e);
  const h = handleAt(p);
  if (h) {
    const w = model.widget;
    drag = { mode: "resize", handle: h, p0: p, start: { x: w.x, y: w.y, w: w.w, h: w.h }, started: false };
    return;
  }
  const hit = hitTest(p.x, p.y);
  model.select(hit);
  const w = model.widget;
  drag = w && !w.locked ? { mode: "move", p0: p, start: { x: w.x, y: w.y, w: w.w, h: w.h }, started: false } : null;
  drawOverlay();
}

// Kanten und Mitten der anderen Elemente und des Displays für die Hilfslinien
function snapTargets() {
  const L = model.layout, xs = [0, L.width / 2, L.width], ys = [0, L.height / 2, L.height];
  model.screen.widgets.forEach((w, i) => {
    if (i === model.selected || w.hidden) return;
    xs.push(w.x, w.x + w.w / 2, w.x + w.w);
    ys.push(w.y, w.y + w.h / 2, w.y + w.h);
  });
  return { xs, ys };
}

function snapAxis(candidates, targets, axis) {
  // candidates: Werte des gezogenen Elements (z. B. links, Mitte, rechts) mit Versatz
  const tol = SNAP_PX / view.zoom;
  let best = null;
  for (const c of candidates) {
    for (const t of targets) {
      const d = t - c.v;
      if (Math.abs(d) <= tol && (!best || Math.abs(d) < Math.abs(best.d))) best = { d, v: t, axis };
    }
  }
  return best;
}

function onMove(e) {
  const p = toDisplay(e);
  if (!drag) {
    const L = model.layout;
    coordsEl.textContent = p.x >= 0 && p.y >= 0 && p.x < L.width && p.y < L.height ? `x ${Math.floor(p.x)}   y ${Math.floor(p.y)}` : "";
    if (view.preview) return;
    const h = handleAt(p);
    const hit = h ? model.selected : hitTest(p.x, p.y);
    overlayCv.style.cursor = h ? CURSOR[h] : hit !== null && !model.screen.widgets[hit].locked ? "move" : "default";
    if (hit !== hover) { hover = hit; drawOverlay(); }
    return;
  }
  const dx = p.x - drag.p0.x, dy = p.y - drag.p0.y;
  if (!drag.started) {
    if (Math.abs(dx) * view.zoom < 3 && Math.abs(dy) * view.zoom < 3) return;
    model.checkpoint();
    drag.started = true;
  }
  const s = drag.start, w = model.widget;
  const free = e.altKey;      // Alt: ohne Einrasten
  guides = [];
  const { xs, ys } = snapTargets();
  if (drag.mode === "move") {
    let nx = s.x + dx, ny = s.y + dy;
    if (!free) {
      const gx = snapAxis([{ v: nx }, { v: nx + s.w / 2 }, { v: nx + s.w }], xs, "x");
      const gy = snapAxis([{ v: ny }, { v: ny + s.h / 2 }, { v: ny + s.h }], ys, "y");
      if (gx) { nx += gx.d; guides.push(gx); } else nx = model.snapValue(nx);
      if (gy) { ny += gy.d; guides.push(gy); } else ny = model.snapValue(ny);
    }
    if (e.shiftKey) { if (Math.abs(dx) > Math.abs(dy)) ny = s.y; else nx = s.x; }
    model.setGeometry({ x: nx, y: ny }, { record: false });
  } else {
    let x0 = s.x, y0 = s.y, x1 = s.x + s.w, y1 = s.y + s.h;
    const hnd = drag.handle;
    const adjust = (v, axis) => {
      if (free) return Math.round(v);
      const g = snapAxis([{ v }], axis === "x" ? xs : ys, axis);
      if (g) { guides.push(g); return g.v; }
      return model.snapValue(v);
    };
    if (hnd.includes("w")) x0 = Math.min(adjust(s.x + dx, "x"), x1 - 1);
    if (hnd.includes("e")) x1 = Math.max(adjust(s.x + s.w + dx, "x"), x0 + 1);
    if (hnd.includes("n")) y0 = Math.min(adjust(s.y + dy, "y"), y1 - 1);
    if (hnd.includes("s")) y1 = Math.max(adjust(s.y + s.h + dy, "y"), y0 + 1);
    if (e.shiftKey && hnd.length === 2 && s.w > 0 && s.h > 0) {
      // Seitenverhältnis halten
      const ratio = s.w / s.h;
      const nw = x1 - x0, nh = y1 - y0;
      if (nw / nh > ratio) { const h2 = nw / ratio; if (hnd.includes("n")) y0 = y1 - h2; else y1 = y0 + h2; }
      else { const w2 = nh * ratio; if (hnd.includes("w")) x0 = x1 - w2; else x1 = x0 + w2; }
    }
    model.setGeometry({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, { record: false });
  }
  void w;
}

function onUp(e) {
  if (drag && drag.started) model.emit("geometry-done");
  drag = null;
  guides = [];
  drawOverlay();
}

// -- Vorschau-Animation -------------------------------------------------------

export function setDemo(on) {
  view.demo = on;
  clearInterval(animTimer);
  if (on) animTimer = setInterval(render, 50);
  render();
}

export function setPreview(on) {
  view.preview = on;
  stageEl.classList.toggle("preview", on);
  render();
}
