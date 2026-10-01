// Rechte Spalte: Eigenschaften des gewählten Elements, sonst der Seite und des Layouts

import { importImage } from "./dialogs.js";
import { icon, TYPE_ICON } from "./icons.js";
import { model } from "./model.js";
import { S, get, typeLabel } from "./schema.js";
import { imageCanvas } from "./render.js";
import { confirmDialog, h, showError } from "./ui.js";
import { widgetTitle } from "./panels.js";

const GROUPS = [
  ["Bedienung", ["action"]],
  ["Daten", ["source", "decimals", "unit", "format", "min", "max", "from_zero"]],
  ["Text", ["text", "font", "size", "align"]],
  ["Form", ["icon", "segments", "orientation", "start_angle", "end_angle", "thickness", "radius", "border_width", "blink"]],
  ["Farben", ["color", "bg_color", "on_color", "off_color", "border_color"]],
  ["Warnschwellen", ["warn_above", "warn_color", "crit_above", "crit_color"]],
];
const SEGMENTED = new Set(["align", "orientation"]);

const HINTS = {
  value: "Schwellen auf 0 schalten sie aus. Ab „Warnung ab“ gilt die Warnfarbe, ab „Kritisch ab“ die Kritisch-Farbe.",
  bar: "Mit Segmenten bekommt jedes Segment die Farbe seiner Stelle, z. B. der rote Bereich am Ende des Drehzahlbalkens. „Ab 0 füllen“ lässt den Balken von der 0 aus wachsen.",
  gauge: "0° ist rechts, die Winkel laufen im Uhrzeigersinn. 135° bis 405° ergibt einen unten offenen Dreiviertelkreis. „Ab 0 füllen“ füllt von der 0 aus nach beiden Seiten, z. B. für die Schräglage.",
  indicator: "Blinker pulsieren von selbst. „Blinken, wenn an“ ist für Zustände gedacht, die dauerhaft an sind.",
  image: "Der Tacho zeichnet Bilder immer in Originalgröße ab der linken oberen Ecke und schneidet am Rahmen ab.",
  text: "Lange Texte brechen am Rahmen um. Doppelklick auf das Element bearbeitet den Text.",
  button: "Am Tacho löst Antippen die Aktion aus. Ohne Text steht das Symbol in der Mitte, mit Text links daneben. „Abspielen/Pause“ als Symbol wechselt von selbst, je nachdem ob Musik läuft. Die Lenkertaster belegt man unter Tacho-Einstellungen → Lenkertaster.",
};

// Passendes Symbol (oder kurzer Text) je Aktion, wird beim Wechsel der Aktion übernommen
const ACTION_LOOK = {
  none: ["none", ""], play_pause: ["play_pause", ""], next_track: ["next", ""], previous_track: ["previous", ""],
  volume_up: ["volume_up", ""], volume_down: ["volume_down", ""], page_next: ["arrow_right", ""],
  page_previous: ["arrow_left", ""], menu: ["menu", ""], night_mode: ["none", "Nacht"], lock: ["lock", ""],
  trip_reset: ["none", "Trip 0"],
};

const root = () => document.getElementById("inspector");
let geoInputs = {};

function wrap(fn) {
  try { fn(); } catch (e) { showError(e); }
}

// -- Felder ---------------------------------------------------------------------

function numberField(value, onCommit, { step = 1, float = false, prefix = null, min = null, max = null } = {}) {
  const input = h("input", { class: prefix ? "" : "field", type: "text", inputmode: "decimal", value: fmtNum(value, float) });
  const commit = () => {
    const raw = input.value.trim().replace(",", ".");
    const v = float ? Number.parseFloat(raw) : Number.parseInt(raw, 10);
    if (raw === "" || Number.isNaN(v) || (min !== null && v < min) || (max !== null && v > max)) {
      input.classList.add("invalid");
      return;
    }
    input.classList.remove("invalid");
    onCommit(v);
  };
  input.addEventListener("change", commit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { commit(); input.select(); }
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      const cur = Number.parseFloat(input.value.replace(",", ".")) || 0;
      const d = (e.key === "ArrowUp" ? 1 : -1) * step * (e.shiftKey ? 10 : 1);
      input.value = fmtNum(cur + d, float);
      commit();
    }
  });
  input.addEventListener("focus", () => input.select());
  if (!prefix) return input;
  return h("label", { class: "num" }, h("span", {}, prefix), input);
}

function fmtNum(v, float) {
  if (!float) return String(Math.round(v));
  return String(Math.round(v * 1000) / 1000).replace(".", ",");
}

function textField(value, onCommit, multiline = false) {
  const el = multiline ? h("textarea", { class: "field", rows: 2 }) : h("input", { class: "field", type: "text" });
  el.value = value;
  el.addEventListener("change", () => onCommit(el.value));
  if (!multiline) el.addEventListener("keydown", (e) => { if (e.key === "Enter") onCommit(el.value); });
  return el;
}

function colorField(value, onCommit) {
  const picker = h("input", { type: "color", value: value.toLowerCase() });
  const text = h("input", { class: "field", type: "text", value: value.toUpperCase(), maxlength: 7, spellcheck: "false" });
  const swatch = h("label", { class: "swatch", style: { background: value } }, picker);
  const apply = (v) => {
    v = v.trim().toUpperCase();
    if (!v.startsWith("#")) v = `#${v}`;
    if (!/^#[0-9A-F]{6}$/.test(v)) { text.classList.add("invalid"); return; }
    text.classList.remove("invalid");
    text.value = v;
    swatch.style.background = v;
    picker.value = v.toLowerCase();
    onCommit(v);
  };
  picker.addEventListener("input", () => { swatch.style.background = picker.value; text.value = picker.value.toUpperCase(); });
  picker.addEventListener("change", () => apply(picker.value));
  text.addEventListener("change", () => apply(text.value));
  text.addEventListener("keydown", (e) => { if (e.key === "Enter") apply(text.value); });
  return h("div", { class: "color" }, swatch, text);
}

function switchField(value, onCommit, label = "") {
  const input = h("input", { type: "checkbox", role: "switch" });
  input.checked = Boolean(value);
  input.addEventListener("change", () => onCommit(input.checked));
  return h("label", { class: "check" }, input, label);
}

function segmented(options, value, onCommit) {
  const box = h("div", { class: "segctl", role: "radiogroup" });
  for (const [key, label] of options) {
    box.append(h("button", { class: key === value ? "on" : "", role: "radio", "aria-checked": String(key === value),
      onclick: () => onCommit(key) }, label));
  }
  return box;
}

function selectField(options, value, onCommit) {
  const sel = h("select", { class: "field" });
  for (const o of options) {
    if (o.group) {
      const g = h("optgroup", { label: o.group });
      for (const [k, l] of o.items) g.append(h("option", { value: k }, l));
      sel.append(g);
    } else {
      sel.append(h("option", { value: o[0] }, o[1]));
    }
  }
  sel.value = value;
  sel.addEventListener("change", () => onCommit(sel.value));
  return sel;
}

function row(label, field) {
  return h("div", { class: "row" }, h("label", {}, label), field);
}

function group(title, ...rows) {
  return h("section", { class: "group" }, title ? h("h3", {}, title) : null, ...rows);
}

// Datenquellen passend zum Element-Typ, gruppiert
function sourceOptions(type) {
  const kinds = type === "indicator" ? ["bool"] : type === "bar" || type === "gauge" ? ["number"] : ["number", "time", "text", "bool"];
  const groups = { number: "Zahlen", time: "Zeit", text: "Texte", bool: "Ja/Nein" };
  const out = [["none", "Keine"]];
  for (const k of kinds) {
    const items = S.info.sources.filter((s) => s.kind === k && s.key !== "none").map((s) => [s.key, s.unit ? `${s.label} (${s.unit})` : s.label]);
    if (items.length) out.push({ group: groups[k], items });
  }
  return out;
}

function propField(w, key) {
  const p = S.props.get(key);
  const value = get(w, key);
  const commit = (v) => {
    if (key === "action" && w.type === "button") {
      // Symbol und Text mitziehen, solange sie noch zur alten Aktion passen
      const [oldIcon, oldText] = ACTION_LOOK[get(w, "action")] || ["none", ""];
      const [newIcon, newText] = ACTION_LOOK[v] || ["none", ""];
      const next = { action: v };
      if (get(w, "icon") === oldIcon && get(w, "text") === oldText) Object.assign(next, { icon: newIcon, text: newText });
      wrap(() => model.setProps(next));
      renderInspector();
      return;
    }
    wrap(() => model.setProp(key, v));
    if (key === "source") renderInspector();
  };
  const t = p.type;
  if (t === "color") return colorField(value, commit);
  if (t === "bool") return switchField(value, commit);
  if (t.startsWith("enum:")) {
    const name = t.slice(5);
    if (name === "source") return selectField(sourceOptions(w.type), value, commit);
    const opts = S.enums[name].map((e) => [e[1], e[2]]);
    if (SEGMENTED.has(key)) return segmented(opts, value, commit);
    return selectField(opts, value, commit);
  }
  if (t === "u8") return numberField(value, commit, { min: 0, max: 255 });
  if (t === "i16") return numberField(value, commit, { step: 5, min: -32768, max: 32767 });
  if (t === "f32") return numberField(value, commit, { float: true, step: 1 });
  return textField(value, commit, key === "text" && w.type === "text");
}

// -- Aufbau ---------------------------------------------------------------------

export function renderInspector() {
  geoInputs = {};
  const w = model.widget;
  root().replaceChildren(...(w ? widgetPanel(w) : screenPanel()));
}

// Nur Position und Größe nachführen (beim Ziehen, ohne neu aufzubauen)
export function syncGeometry() {
  const w = model.widget;
  if (!w) return;
  for (const k of ["x", "y", "w", "h"]) {
    const input = geoInputs[k];
    if (input && document.activeElement !== input) input.value = String(w[k]);
  }
}

function widgetPanel(w) {
  const t = S.types.get(w.type);
  const n = model.screen.widgets.length;
  const head = h("div", { class: "insp-head" },
    h("div", { class: "insp-title", html: icon(TYPE_ICON[w.type] || "page") }, typeLabel(w.type)),
    h("div", { class: "insp-sub" }, `Ebene ${model.selected + 1} von ${n} auf „${model.screen.name}“`),
    h("div", { class: "insp-actions" },
      h("button", { class: "icon-btn", "data-tip": "Duplizieren (Strg+D)", html: icon("duplicate"), onclick: () => wrap(() => model.duplicateWidget()) }),
      h("button", { class: "icon-btn", "data-tip": "Ganz nach vorn", html: icon("front"), onclick: () => model.toFront() }),
      h("button", { class: "icon-btn", "data-tip": "Eine Ebene nach vorn", html: icon("forward"), onclick: () => model.forward() }),
      h("button", { class: "icon-btn", "data-tip": "Eine Ebene nach hinten", html: icon("backward"), onclick: () => model.backward() }),
      h("button", { class: "icon-btn", "data-tip": "Ganz nach hinten", html: icon("back"), onclick: () => model.toBack() }),
      h("span", { class: "spacer", style: { flex: "1" } }),
      h("button", { class: "icon-btn", "data-tip": "Löschen (Entf)", html: icon("trash"), onclick: () => model.deleteWidget() })));

  const geo = (key, prefix) => {
    const f = numberField(w[key], (v) => wrap(() => model.setGeometry({ [key]: v })), { prefix, min: key === "w" || key === "h" ? 1 : -2000 });
    geoInputs[key] = f.querySelector("input");
    return f;
  };
  const out = [head, group("Position und Größe",
    h("div", { class: "grid4" }, geo("x", "X"), geo("y", "Y"), geo("w", "B"), geo("h", "H")),
    h("div", { style: { display: "flex", gap: "18px", marginTop: "10px" } },
      switchField(w.hidden, (v) => model.setFlag("hidden", v), "Ausgeblendet"),
      switchField(w.locked, (v) => model.setFlag("locked", v), "Gesperrt")))];

  if (w.type === "image") out.push(imageGroup(w));
  if (!t) return out;
  // Nur zeigen, was zur Datenquelle passt (Format nur bei Uhrzeit, Zahlenformat und Schwellen nur bei Zahlen)
  const kind = (S.sources.get(get(w, "source")) || {}).kind;
  const irrelevant = new Set();
  if (w.type === "value") {
    if (kind !== "time") irrelevant.add("format");
    if (kind !== "number") ["decimals", "unit", "warn_above", "warn_color", "crit_above", "crit_color"].forEach((k) => irrelevant.add(k));
  }
  const used = new Set(irrelevant);
  for (const [title, keys] of GROUPS) {
    const ks = keys.filter((k) => t.props.includes(k) && !irrelevant.has(k));
    ks.forEach((k) => used.add(k));
    if (ks.length) out.push(group(title, ...ks.map((k) => row(S.props.get(k).label, propField(w, k)))));
  }
  const rest = t.props.filter((k) => !used.has(k) && k !== "image");
  if (rest.length) out.push(group("Weitere", ...rest.map((k) => row(S.props.get(k).label, propField(w, k)))));
  if (HINTS[w.type]) out.push(group(null, h("p", { class: "note" }, HINTS[w.type])));
  return out;
}

function imageGroup(w) {
  const imgs = model.layout.images;
  const cur = model.imageById(get(w, "image"));
  const sel = selectField([[String(S.info.no_image), "Kein Bild"], ...imgs.map((i) => [String(i.id), `${i.name} (${i.width} × ${i.height})`])],
    String(cur ? cur.id : S.info.no_image), (v) => { wrap(() => model.setProp("image", Number(v))); renderInspector(); });
  const rows = [row("Bild", sel),
    h("div", { style: { display: "flex", gap: "6px", marginTop: "4px" } },
      h("button", { class: "btn", "data-tip": "Neues Bild laden und in diesen Rahmen einpassen", onclick: () => importImage(),
        html: `${icon("upload")}<span>Bild laden</span>` }),
      h("button", { class: "btn ghost", disabled: !cur, "data-tip": "Rahmen genau auf die Größe des Bilds setzen",
        onclick: () => cur && wrap(() => model.setGeometry({ w: cur.width, h: cur.height })) }, "Originalgröße"))];
  if (cur && (cur.width !== w.w || cur.height !== w.h)) {
    rows.push(h("p", { class: "note" }, `Rahmen ${w.w} × ${w.h}, Bild ${cur.width} × ${cur.height}. Am Rahmen wird abgeschnitten.`));
  }
  return group("Bild", ...rows);
}

function screenPanel() {
  const s = model.screen;
  const days = model.layout.screens.filter((d) => d.role === "page" && d !== s);
  const head = h("div", { class: "insp-head" },
    h("div", { class: "insp-title", html: icon("page") }, s.name || "Seite"),
    h("div", { class: "insp-sub" }, `Seite ${model.screenIndex + 1} von ${model.layout.screens.length}. Element antippen, um es zu bearbeiten.`));

  const roleCtl = segmented([["page", "Tagseite"], ["night", "Nacht"], ["startup", "Startbild"]], s.role, (role) => wrap(() => {
    if (role === "night") {
      if (!days.length) throw new Error("Zuerst eine Tagseite anlegen, zu der diese Nachtversion gehört.");
      const target = days.find((d) => d.id === s.night_of) || days[0];
      model.setScreen({ role: "night", night_of: target.id });
    } else {
      model.setScreen({ role, night_of: null });
    }
    renderInspector();
  }));
  const pageRows = [
    row("Name", textField(s.name, (v) => wrap(() => model.setScreen({ name: v.trim() || s.name })))),
    row("Hintergrund", colorField(s.bg, (v) => wrap(() => model.setScreen({ bg: v })))),
    row("Art", roleCtl),
  ];
  if (s.role === "night") {
    pageRows.push(row("Nacht für", selectField(days.map((d) => [String(d.id), d.name]), String(s.night_of),
      (v) => wrap(() => model.setScreen({ night_of: Number(v) })))));
  }
  pageRows.push(h("p", { class: "note" }, s.role === "startup"
    ? "Diese Seite zeigt der Tacho beim Einschalten, so lange wie in den Tacho-Einstellungen unter „startbild_dauer_s“ steht."
    : s.role === "night"
      ? "Ist der Nachtmodus an, zeigt der Tacho diese Seite statt ihrer Tagseite."
      : "Tagseiten wechselt man am Tacho durch Wischen. Eine Seite „Startbild“ erscheint beim Einschalten."));

  const L = model.layout;
  const imgRows = L.images.length ? L.images.map((img) => {
    const cv = h("canvas", { width: 40, height: 40 });
    requestAnimationFrame(() => {
      const c = cv.getContext("2d"), src = imageCanvas(img);
      const k = Math.min(40 / img.width, 40 / img.height);
      c.clearRect(0, 0, 40, 40);
      c.drawImage(src, (40 - img.width * k) / 2, (40 - img.height * k) / 2, img.width * k, img.height * k);
    });
    const used = model.imageUsage(img.id);
    return h("div", { class: "img-item" }, cv,
      h("div", {}, h("div", {}, img.name), h("div", { class: "meta" }, `${img.width} × ${img.height}, ${used}× benutzt`)),
      h("button", { class: "icon-btn small", "data-tip": "Bild aus dem Layout löschen", html: icon("trash"),
        onclick: async () => {
          if (used && !(await confirmDialog("Bild löschen?", `„${img.name}“ wird ${used}× benutzt. Die Bild-Elemente bleiben stehen und zeigen dann kein Bild.`, "Löschen", true))) return;
          model.removeImage(img.id);
        } }));
  }) : [h("p", { class: "note" }, "Noch keine Bilder. „Bild laden“ setzt ein Bild als neues Element auf die Seite.")];

  return [head,
    group("Seite", ...pageRows),
    group("Layout",
      row("Name", textField(L.name, (v) => model.setLayoutField("name", v.trim()))),
      row("Autor", textField(L.author, (v) => model.setLayoutField("author", v.trim())))),
    group(`Bilder (${L.images.length} von ${S.info.limits.images})`, h("div", { class: "img-list" }, ...imgRows),
      h("button", { class: "btn", style: { marginTop: "10px" }, onclick: () => importImage(), html: `${icon("upload")}<span>Bild laden</span>` })),
    group("Bedienung", h("p", { class: "note" },
      "Ziehen verschiebt, die Punkte am Rand ändern die Größe. Umschalt hält beim Ziehen die Richtung oder das Seitenverhältnis, Alt schaltet das Einrasten ab. Pfeiltasten verschieben um 1 Pixel, mit Umschalt um 10. Strg+C und Strg+V kopieren Elemente, auch auf andere Seiten.")),
  ];
}

export { widgetTitle };
