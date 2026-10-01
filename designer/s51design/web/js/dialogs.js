// Dialoge: Vorlagen, Bild laden, SD-Karte, Tacho-Einstellungen, Drahtlos

import { api } from "./api.js";
import { canPickFolder, cleanFileName, confirmDiscard, download, pickWithInput, slugFileName } from "./files.js";
import { icon } from "./icons.js";
import { model } from "./model.js";
import { demoValues, renderThumb } from "./render.js";
import { S } from "./schema.js";
import { h, modal, showError, toast } from "./ui.js";

// Einstellungen des Tachos (tacho.cfg), wie im Designer zuletzt geladen oder bearbeitet
export const cfg = { values: null, loaded: false };

export async function initConfig() {
  cfg.values = (await api.configDefaults()).values;
}

// -- Vorlagen --------------------------------------------------------------------

const presetCache = new Map();
async function presetLayout(name) {
  if (!presetCache.has(name)) presetCache.set(name, await api.preset(name));
  return structuredClone(presetCache.get(name));
}

export function blankLayout() {
  const [w, hgt] = S.info.display;
  return { width: w, height: hgt, name: "Neues Design", author: "", created: 0, tool: "",
    screens: [{ id: 0, name: "Fahrt", role: "page", night_of: null, bg: "#000000", widgets: [] }], images: [], unknown_chunks: [] };
}

export async function templateDialog() {
  if (!(await confirmDiscard())) return;
  const vals = demoValues(0, false);
  const DESCR = {
    "Klar": "Standard des Tachos mit Statistik, Nachtversion und Startbild",
    "Retro": "Rundinstrument wie der alte Simson-Tacho",
    "Rennsport": "Große Ganganzeige, Schaltblitz, Schräglage",
    "Cockpit": "Werte in Kacheln, Musikseite",
    "Minimal": "Nur das Nötigste, mit Nachtversion",
    "Alle Elemente": "Zeigt jede Funktion des Designers",
  };
  let dlg;
  const cards = [];
  const pick = async (name) => {
    try {
      const layout = name ? await presetLayout(name) : blankLayout();
      model.load(layout);
      dlg.close();
    } catch (e) { showError(e); }
  };
  const blank = h("button", { class: "card", onclick: () => pick(null) },
    h("canvas", {}), h("div", { class: "card-name" }, "Leer"), h("div", { class: "card-sub" }, "Eine leere Seite"));
  cards.push(blank);
  for (const name of S.info.presets) {
    const cv = h("canvas", {});
    cards.push(h("button", { class: "card", onclick: () => pick(name) }, cv,
      h("div", { class: "card-name" }, name), h("div", { class: "card-sub" }, DESCR[name] || "")));
    presetLayout(name).then((L) => {
      const first = L.screens.find((s) => s.role === "page") || L.screens[0];
      requestAnimationFrame(() => renderThumb(cv, L, first, vals));
    }).catch(() => {});
  }
  dlg = modal({ title: "Neues Design", wide: true, body: h("div", { class: "gallery" }, cards), actions: [] });
  requestAnimationFrame(() => {
    const cv = blank.querySelector("canvas");
    renderThumb(cv, blankLayout(), blankLayout().screens[0], vals);
  });
}

// -- Bild laden ---------------------------------------------------------------------

async function scaled(bitmap, w, h2) {
  // In Halbschritten verkleinern, dann auf die Zielgröße: sauberer als ein großer Schritt
  let src = bitmap, sw = bitmap.width, sh = bitmap.height;
  while (sw / 2 >= w && sh / 2 >= h2) {
    const c = new OffscreenCanvas(Math.round(sw / 2), Math.round(sh / 2));
    const cx = c.getContext("2d");
    cx.imageSmoothingQuality = "high";
    cx.drawImage(src, 0, 0, c.width, c.height);
    src = c; sw = c.width; sh = c.height;
  }
  const out = new OffscreenCanvas(w, h2);
  const ox = out.getContext("2d");
  ox.imageSmoothingQuality = "high";
  ox.drawImage(src, 0, 0, w, h2);
  return ox.getImageData(0, 0, w, h2).data;
}

function toBase64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

export async function importImage() {
  const file = await pickWithInput("image/*,.bmp");
  if (!file) return;
  try {
    const bmp = await createImageBitmap(file);
    const max = S.info.limits.image_side;
    const w = model.widget;
    const intoFrame = w && w.type === "image";
    let boxW = intoFrame ? w.w : Math.min(bmp.width, model.layout.width);
    let boxH = intoFrame ? w.h : Math.min(bmp.height, model.layout.height);
    boxW = Math.max(1, Math.min(boxW, max));
    boxH = Math.max(1, Math.min(boxH, max));
    const k = Math.min(boxW / bmp.width, boxH / bmp.height);
    const nw = Math.max(1, Math.round(bmp.width * k)), nh = Math.max(1, Math.round(bmp.height * k));
    const rgba = await scaled(bmp, nw, nh);
    const name = file.name.replace(/\.[^.]+$/, "").slice(0, 60) || "Bild";
    const img = await api.image({ id: model.freeImageId(), name, width: nw, height: nh, rgba: toBase64(new Uint8Array(rgba.buffer)) });
    model.addImage(img);
    const change = nw !== bmp.width ? ` (${nw < bmp.width ? "verkleinert" : "vergrößert"} von ${bmp.width} × ${bmp.height})` : "";
    toast(`Bild „${name}“ geladen, ${nw} × ${nh} Pixel${change}`);
  } catch (e) {
    showError(new Error(`Bild kann nicht geladen werden: ${e.message}`));
  }
}

// -- SD-Karte -----------------------------------------------------------------------

async function readText(dir, name) {
  try {
    const f = await (await dir.getFileHandle(name)).getFile();
    return await f.text();
  } catch (e) {
    return null;
  }
}

async function writeFile(dir, name, data) {
  const fh = await dir.getFileHandle(name, { create: true });
  const w = await fh.createWritable();
  await w.write(data);
  await w.close();
}

export async function exportDialog() {
  let bytes;
  try {
    bytes = await api.encode(model.layout);
  } catch (e) {
    showError(new Error(`Layout ist nicht gültig: ${e.message}`));
    return;
  }
  if (!canPickFolder) {
    download(bytes, slugFileName(model.layout.name));
    const text = (await api.configDump(cfg.values)).text;
    download(new TextEncoder().encode(text), "tacho.cfg", "text/plain");
    toast("Dateien heruntergeladen. Beide in den Ordner s51 der SD-Karte kopieren.");
    return;
  }
  let root;
  try {
    root = await window.showDirectoryPicker({ id: "s51-sd", mode: "readwrite" });
  } catch (e) {
    return;
  }
  try {
    const dir = root.name.toLowerCase() === "s51" ? root : await root.getDirectoryHandle("s51", { create: true });
    const existing = [];
    for await (const [name, handle] of dir.entries()) {
      if (handle.kind === "file" && name.toLowerCase().endsWith(".s51") && !name.startsWith(".")) existing.push(name);
    }
    existing.sort();
    const cfgText = await readText(dir, "tacho.cfg");
    const cardValues = cfgText !== null ? (await api.configParse(cfgText)).values : null;
    showExportForm(dir, bytes, existing, cardValues);
  } catch (e) {
    showError(new Error(`Karte kann nicht gelesen werden: ${e.message}`));
  }
}

function showExportForm(dir, bytes, existing, cardValues) {
  const currentDefault = (cardValues || cfg.values)["anzeige.layout_datei"];
  const nameInput = h("input", { class: "field", value: slugFileName(model.layout.name), spellcheck: "false" });
  const writeLayout = h("input", { type: "checkbox", role: "switch" });
  writeLayout.checked = true;
  const hint = h("div", { class: "cfg-desc" });
  const choices = h("div", { class: "choice-list" });
  let chosen = existing.includes(currentDefault) ? currentDefault : null;

  const options = () => {
    const names = [...existing];
    if (writeLayout.checked) {
      try {
        const n = cleanFileName(nameInput.value);
        if (!names.includes(n)) names.push(n);
      } catch (e) { /* ungültiger Name, Hinweis steht schon da */ }
    }
    return names.sort();
  };
  const refresh = () => {
    try {
      const n = cleanFileName(nameInput.value);
      hint.textContent = existing.includes(n) ? "Eine Datei mit diesem Namen liegt schon auf der Karte und wird ersetzt." : "Neue Datei auf der Karte.";
      nameInput.classList.remove("invalid");
      if (!chosen) chosen = n;
    } catch (e) {
      hint.textContent = e.message;
      nameInput.classList.add("invalid");
    }
    const opts = options();
    if (!opts.includes(chosen)) chosen = opts[0] || null;
    choices.replaceChildren(...(opts.length ? opts.map((n) => {
      const radio = h("input", { type: "radio", name: "s51-default", value: n });
      radio.checked = n === chosen;
      radio.addEventListener("change", () => { chosen = n; });
      return h("label", { class: "choice" }, radio, n,
        h("span", { class: "tag" }, n === currentDefault ? "bisher Standard" : existing.includes(n) ? "" : "neu"));
    }) : [h("p", { class: "note" }, "Noch keine Designs auf der Karte.")]));
  };
  nameInput.addEventListener("input", refresh);
  writeLayout.addEventListener("change", () => { nameInput.disabled = !writeLayout.checked; refresh(); });
  refresh();

  const body = h("div", {},
    h("div", { class: "cfg-item" },
      h("label", { class: "check" }, writeLayout, `Design „${model.layout.name}“ speichern als`),
      h("div", { style: { marginTop: "8px" } }, nameInput), hint),
    h("div", { class: "cfg-item" },
      h("div", { class: "cfg-key", style: { marginBottom: "8px" } }, "Standard-Design beim Start"),
      choices,
      h("div", { class: "cfg-desc" }, "Am Tacho lässt sich durch langes Drücken jederzeit ein anderes Design wählen. Ein hier neu festgelegter Standard gilt beim nächsten Start.")),
    h("p", { class: "note" }, cfg.loaded
      ? "Die Tacho-Einstellungen aus dem Designer werden mit auf die Karte geschrieben."
      : cardValues ? "Die Einstellungen in der tacho.cfg auf der Karte bleiben erhalten, nur das Standard-Design wird eingetragen."
        : "Auf der Karte liegt noch keine tacho.cfg. Sie wird mit Standardwerten angelegt."));

  modal({
    title: "Auf SD-Karte schreiben", body,
    actions: [
      { label: "Abbrechen", ghost: true },
      { label: "Auf die Karte schreiben", primary: true, run: async ({ setMessage }) => {
        if (!chosen) { setMessage("Bitte ein Standard-Design wählen."); return false; }
        let fileName = null;
        if (writeLayout.checked) fileName = cleanFileName(nameInput.value);
        const values = { ...(cfg.loaded ? cfg.values : cardValues || cfg.values), "anzeige.layout_datei": chosen };
        if (fileName) await writeFile(dir, fileName, bytes);
        const text = (await api.configDump(values)).text;
        await writeFile(dir, "tacho.cfg", text);
        if (cfg.loaded) cfg.values["anzeige.layout_datei"] = chosen;
        toast(fileName ? `${fileName} und tacho.cfg geschrieben. Standard: ${chosen}` : `Standard-Design auf ${chosen} gesetzt`);
        return true;
      } },
    ],
  });
}

// -- Tacho-Einstellungen ------------------------------------------------------------------

const SECTION_TITLES = { fahrzeug: "Fahrzeug", anzeige: "Anzeige", warnungen: "Warnungen", wartung: "Wartung",
  alarm: "Alarm", gps: "GPS", bluetooth: "Bluetooth", taster: "Lenkertaster", wlan: "WLAN" };

export function configDialog() {
  const draft = { ...cfg.values };
  const errors = {};
  const tabs = h("div", { class: "tabs", role: "tablist" });
  const pane = h("div", {});
  let current = S.info.config_sections[0];

  const field = (c) => {
    const name = `${c.section}.${c.key}`;
    const v = draft[name];
    if (c.type === "bool") {
      const input = h("input", { type: "checkbox", role: "switch" });
      input.checked = Boolean(v);
      input.addEventListener("change", () => { draft[name] = input.checked; });
      return h("label", { class: "check" }, input, input.checked ? "" : "");
    }
    if (c.type === "enum") {
      const sel = h("select", { class: "field" }, c.choices.map((ch, i) => h("option", { value: ch }, (c.choice_labels || [])[i] || ch)));
      sel.value = v;
      sel.addEventListener("change", () => { draft[name] = sel.value; });
      return sel;
    }
    const input = h("input", { class: `field ${errors[name] ? "invalid" : ""}`, value: c.type === "float" ? String(v).replace(".", ",") : String(v) });
    input.addEventListener("change", () => { draft[name] = input.value; });
    return input;
  };
  const show = () => {
    tabs.replaceChildren(...S.info.config_sections.map((sec) => h("button", {
      class: sec === current ? "on" : "", role: "tab",
      onclick: () => { current = sec; show(); },
    }, SECTION_TITLES[sec] || sec, Object.keys(errors).some((k) => k.startsWith(sec + ".")) ? " •" : "")));
    pane.replaceChildren(...S.info.config.filter((c) => c.section === current).map((c) => {
      const name = `${c.section}.${c.key}`;
      const range = (c.type === "int" || c.type === "float") && c.min !== null ? ` (${c.min} bis ${c.max})` : "";
      return h("div", { class: "cfg-item" },
        h("div", { class: "cfg-line" }, h("div", { class: "cfg-key" }, c.key), field(c)),
        h("div", { class: "cfg-desc" }, c.description + range),
        errors[name] ? h("div", { class: "cfg-err" }, errors[name]) : null);
    }));
  };
  show();
  modal({
    title: "Tacho-Einstellungen (tacho.cfg)", wide: true, body: h("div", {}, tabs, pane),
    actions: [
      { label: "Datei laden…", ghost: true, close: false, run: async ({ setMessage }) => {
        const f = await pickWithInput(".cfg,.txt");
        if (!f) return;
        const res = await api.configParse(await f.text());
        Object.assign(draft, res.values);
        show();
        setMessage(res.warnings.length ? `Geladen, ${res.warnings.length} Hinweise: ${res.warnings.slice(0, 3).join("; ")}` : `${f.name} geladen`, !res.warnings.length);
      } },
      { label: "Standardwerte", ghost: true, close: false, run: async () => {
        Object.assign(draft, (await api.configDefaults()).values);
        for (const k of Object.keys(errors)) delete errors[k];
        show();
      } },
      { label: "Als Datei speichern…", ghost: true, close: false, run: async ({ setMessage }) => {
        const res = await api.configValidate(draft);
        if (Object.keys(res.errors).length) { Object.assign(errors, res.errors); show(); setMessage("Bitte die markierten Werte korrigieren."); return; }
        download(new TextEncoder().encode((await api.configDump(res.values)).text), "tacho.cfg", "text/plain");
      } },
      { label: "Übernehmen", primary: true, run: async ({ setMessage }) => {
        const res = await api.configValidate(draft);
        for (const k of Object.keys(errors)) delete errors[k];
        if (Object.keys(res.errors).length) {
          Object.assign(errors, res.errors);
          current = Object.keys(res.errors)[0].split(".")[0];
          show();
          setMessage("Bitte die markierten Werte korrigieren.");
          return false;
        }
        cfg.values = res.values;
        cfg.loaded = true;
        toast("Einstellungen übernommen. Mit „Auf SD-Karte“ oder „Drahtlos“ zum Tacho schicken.");
        return true;
      } },
    ],
  });
}

// -- Drahtlos ----------------------------------------------------------------------------

export function wirelessDialog() {
  const defHost = cfg.values["wlan.modus"] === "hotspot" ? S.info.default_host : `${cfg.values["wlan.hostname"]}.local`;
  const host = h("input", { class: "field", value: localStorage.getItem("s51-host") || defHost, spellcheck: "false" });
  const code = h("input", { class: "field", inputmode: "numeric", maxlength: 6, placeholder: "6 Ziffern",
    style: { fontFamily: '"S51 Mono", monospace', letterSpacing: ".15em", width: "140px" } });
  const status = h("p", { class: "note", style: { minHeight: "20px" } });
  const run = async (label, payload, done) => {
    localStorage.setItem("s51-host", host.value.trim());
    status.style.color = "";
    status.textContent = `${label} …`;
    try {
      const res = await api.wireless({ host: host.value, code: code.value, ...payload });
      status.style.color = "var(--green)";
      status.textContent = done(res);
    } catch (e) {
      status.style.color = "var(--red)";
      status.textContent = e.message;
    }
  };
  const body = h("div", {},
    h("ol", { class: "note", style: { paddingLeft: "18px", margin: "0 0 14px", fontSize: "13px" } },
      h("li", {}, "Am Tacho im Stand das Menü „Übertragung“ öffnen. Das Display zeigt einen 6-stelligen Code."),
      h("li", {}, "PC mit dem WLAN des Tachos verbinden (Hotspot) oder mit demselben Heimnetz."),
      h("li", {}, "Adresse und Code eingeben, dann senden.")),
    h("div", { class: "row" }, h("label", {}, "Adresse"), host),
    h("div", { class: "row" }, h("label", {}, "Code vom Display"), code),
    h("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap", margin: "12px 0 6px" } },
      h("button", { class: "btn primary", html: `${icon("upload")}<span>Layout senden</span>`,
        onclick: () => run("Sende Layout", { action: "send_layout", layout: model.layout }, (r) => `Layout übertragen (${Math.round(r.size / 1024)} KB)${r.datei ? `, gespeichert als ${r.datei}` : ""}. Der Tacho zeigt es sofort an.`) }),
      h("button", { class: "btn", onclick: () => run("Sende Einstellungen", { action: "send_config", values: cfg.values }, () => "Einstellungen übertragen.") }, "Einstellungen senden"),
      h("button", { class: "btn ghost", onclick: () => run("Verbinde", { action: "info" }, (i) => `Verbunden: ${i.geraet}, Firmware ${i.firmware}. ${i.uebertragung_offen ? "Übertragung freigegeben." : "Übertragung am Tacho noch nicht freigegeben."}`) }, "Verbindung prüfen"),
      h("button", { class: "btn ghost", onclick: async () => {
        if (!(await confirmDiscard())) return;
        run("Lade Layout", { action: "fetch_layout" }, (layout) => { model.load(layout); return `Layout „${layout.name}“ vom Tacho geladen.`; });
      } }, "Layout vom Tacho laden")),
    status);
  modal({ title: "Drahtlos übertragen", body, actions: [{ label: "Schließen", ghost: true }] });
}
