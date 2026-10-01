// Öffnen und Speichern auf dem PC (File System Access in Edge und Chrome, sonst Download)

import { api } from "./api.js";
import { model } from "./model.js";
import { askSave, showError, toast } from "./ui.js";

const S51_TYPES = [{ description: "S51-Layout", accept: { "application/octet-stream": [".s51"] } }];
export const canPickFiles = "showOpenFilePicker" in window;
export const canPickFolder = "showDirectoryPicker" in window;

export function slugFileName(name) {
  let s = (name || "").trim().toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss");
  s = s.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  s = s.slice(0, 40).replace(/-+$/g, "");
  return `${s || "design"}.s51`;
}

// Wie sdcard.clean_file_name in Python
export function cleanFileName(name) {
  name = name.trim();
  if (!name.toLowerCase().endsWith(".s51")) name += ".s51";
  const stem = name.slice(0, -4);
  if (!stem || !/^[A-Za-z0-9_-]+$/.test(stem)) throw new Error("Dateiname nur aus Buchstaben (ohne Umlaute), Ziffern, - und _");
  if (stem.length > 40) throw new Error("Dateiname höchstens 40 Zeichen");
  return name;
}

export function download(bytes, name, type = "application/octet-stream") {
  const url = URL.createObjectURL(new Blob([bytes], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// Vor dem Verwerfen von Änderungen fragen. true = weitermachen
export async function confirmDiscard() {
  if (!model.dirty) return true;
  const ans = await askSave();
  if (ans === "cancel") return false;
  if (ans === "save") return save();
  return true;
}

export async function openFile() {
  if (!(await confirmDiscard())) return;
  try {
    if (canPickFiles) {
      let handle;
      try {
        [handle] = await window.showOpenFilePicker({ types: S51_TYPES, id: "s51-layouts" });
      } catch (e) {
        return;             // abgebrochen
      }
      const file = await handle.getFile();
      const layout = await api.decode(new Uint8Array(await file.arrayBuffer()));
      model.load(layout, { fileHandle: handle, fileName: file.name });
      toast(`„${file.name}“ geöffnet`);
    } else {
      const file = await pickWithInput(".s51");
      if (!file) return;
      const layout = await api.decode(new Uint8Array(await file.arrayBuffer()));
      model.load(layout, { fileName: file.name });
    }
  } catch (e) {
    showError(new Error(`Datei kann nicht geöffnet werden: ${e.message}`));
  }
}

export function pickWithInput(accept) {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.addEventListener("change", () => resolve(input.files[0] || null));
    input.addEventListener("cancel", () => resolve(null));
    input.click();
  });
}

export async function save() {
  if (!model.fileHandle) return saveAs();
  try {
    const bytes = await api.encode(model.layout);
    const w = await model.fileHandle.createWritable();
    await w.write(bytes);
    await w.close();
    model.dirty = false;
    model.emit("saved");
    toast(`Gespeichert: ${model.fileName}`);
    return true;
  } catch (e) {
    showError(new Error(`Speichern fehlgeschlagen: ${e.message}`));
    return false;
  }
}

export async function saveAs() {
  let bytes;
  try {
    bytes = await api.encode(model.layout);
  } catch (e) {
    showError(new Error(`Layout ist nicht gültig: ${e.message}`));
    return false;
  }
  const suggested = model.fileName || slugFileName(model.layout.name);
  if (!("showSaveFilePicker" in window)) {
    download(bytes, suggested);
    model.dirty = false;
    model.emit("saved");
    return true;
  }
  let handle;
  try {
    handle = await window.showSaveFilePicker({ suggestedName: suggested, types: S51_TYPES, id: "s51-layouts" });
  } catch (e) {
    return false;
  }
  try {
    const w = await handle.createWritable();
    await w.write(bytes);
    await w.close();
    model.fileHandle = handle;
    model.fileName = handle.name;
    model.dirty = false;
    model.emit("saved");
    toast(`Gespeichert: ${handle.name}`);
    return true;
  } catch (e) {
    showError(new Error(`Speichern fehlgeschlagen: ${e.message}`));
    return false;
  }
}
