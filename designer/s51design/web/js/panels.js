// Linke Spalte: Seiten mit Miniaturbild und Ebenen der aktuellen Seite

import { icon, TYPE_ICON } from "./icons.js";
import { model } from "./model.js";
import { demoValues, renderThumb } from "./render.js";
import { S, get, typeLabel } from "./schema.js";
import { dropdown, h, showError } from "./ui.js";

const ROLE_TEXT = { page: "Tagseite", night: "Nachtversion", startup: "Startbild" };

export function widgetTitle(w) {
  let detail = "";
  if (w.type === "text") detail = String(get(w, "text")).replace(/\n/g, " ");
  else if (w.type === "image") {
    const img = model.imageById(get(w, "image"));
    detail = img ? img.name : "kein Bild";
  } else if ("source" in w.props || w.type === "value") {
    const src = S.sources.get(get(w, "source"));
    detail = src && src.key !== "none" ? src.label : "";
  } else if (w.type === "rect") {
    detail = w.w <= 2 || w.h <= 2 ? "Linie" : "";
  }
  return detail ? `${typeLabel(w.type)}: ${detail}` : typeLabel(w.type);
}

function roleText(s) {
  if (s.role === "night") {
    const day = model.layout.screens.find((d) => d.id === s.night_of && d.role === "page");
    return day ? `Nacht für „${day.name}“` : "Nachtversion";
  }
  return ROLE_TEXT[s.role] || s.role;
}

// -- Seiten ------------------------------------------------------------------------

let dragFrom = null;

export function renderPages() {
  const list = document.getElementById("page-list");
  const vals = demoValues(0, false);
  const items = model.layout.screens.map((s, i) => {
    const cv = h("canvas", { width: 108, height: 72 });
    const more = h("button", { class: "icon-btn small", "data-tip": "Mehr", html: icon("more") });
    const card = h("div", {
      class: `page ${i === model.screenIndex ? "current" : ""}`, draggable: "true", tabindex: "0",
      onclick: (e) => { if (!e.target.closest(".page-more")) model.selectScreen(i); },
      onkeydown: (e) => { if (e.key === "Enter") model.selectScreen(i); },
      ondragstart: (e) => { dragFrom = i; e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", ""); },
      ondragover: (e) => { if (dragFrom !== null) e.preventDefault(); },
      ondrop: (e) => { e.preventDefault(); if (dragFrom !== null) model.moveScreen(dragFrom, i); dragFrom = null; },
      ondragend: () => { dragFrom = null; },
    },
    cv,
    h("div", { class: "page-text" },
      h("div", { class: "page-name" }, s.name || "Ohne Namen"),
      h("div", { class: `page-role role-${s.role}` }, roleText(s))),
    h("div", { class: "page-more" }, dropdown(more, () => [
      { label: "Seite kopieren", icon: icon("duplicate"), run: () => wrap(() => { model.selectScreen(i); model.duplicateScreen(); }) },
      { label: "Nach oben", icon: icon("up"), disabled: i === 0, run: () => model.moveScreen(i, i - 1) },
      { label: "Nach unten", icon: icon("down"), disabled: i === model.layout.screens.length - 1, run: () => model.moveScreen(i, i + 1) },
      "-",
      { label: "Seite löschen", icon: icon("trash"), disabled: model.layout.screens.length <= 1,
        run: () => wrap(() => { model.selectScreen(i); model.deleteScreen(); }) },
    ])));
    requestAnimationFrame(() => renderThumb(cv, model.layout, s, vals));
    return card;
  });
  list.replaceChildren(...items);
}

// Nur das Bild der aktuellen Seite neu zeichnen (nach Änderungen)
let thumbPending = false;
export function refreshCurrentThumb() {
  if (thumbPending) return;
  thumbPending = true;
  requestAnimationFrame(() => {
    thumbPending = false;
    const card = document.querySelectorAll("#page-list > .page")[model.screenIndex];
    if (card) renderThumb(card.querySelector("canvas"), model.layout, model.screen, demoValues(0, false));
  });
}

function wrap(fn) {
  try { fn(); } catch (e) { showError(e); }
}

export function initPageTools() {
  const tools = document.getElementById("page-tools");
  tools.append(
    h("button", { class: "icon-btn small", "data-tip": "Neue Seite", html: icon("plus"), onclick: () => wrap(() => model.addScreen()) }),
  );
}

// -- Ebenen --------------------------------------------------------------------------

export function renderLayers() {
  const list = document.getElementById("layer-list");
  const ws = model.screen.widgets;
  if (!ws.length) {
    list.replaceChildren(h("div", { class: "empty" }, "Die Seite ist leer. Ein Element aus der Leiste unten antippen oder auf das Display ziehen."));
    return;
  }
  const rows = [];
  for (let i = ws.length - 1; i >= 0; i--) {
    const w = ws[i];
    rows.push(h("div", {
      class: `layer ${i === model.selected ? "selected" : ""} ${w.hidden ? "hidden-el" : ""}`,
      onclick: (e) => { if (!e.target.closest("button")) model.select(i); },
    },
    h("span", { html: icon(TYPE_ICON[w.type] || "page", "type") }),
    h("span", { class: "layer-name" }, widgetTitle(w)),
    h("span", { class: "layer-flags" },
      h("button", { class: `icon-btn small ${w.hidden ? "on" : ""}`, "data-tip": w.hidden ? "Einblenden" : "Am Tacho ausblenden",
        html: icon(w.hidden ? "eyeoff" : "eye"), onclick: () => model.setFlag("hidden", !w.hidden, i) }),
      h("button", { class: `icon-btn small ${w.locked ? "on" : ""}`, "data-tip": w.locked ? "Entsperren" : "Sperren",
        html: icon(w.locked ? "lock" : "unlock"), onclick: () => model.setFlag("locked", !w.locked, i) }))));
  }
  list.replaceChildren(...rows);
  const sel = list.querySelector(".layer.selected");
  if (sel) sel.scrollIntoView({ block: "nearest" });
}
