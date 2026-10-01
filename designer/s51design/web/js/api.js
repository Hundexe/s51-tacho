// Verbindung zum Python-Teil des Designers (s51design/webapp.py)

const token = new URLSearchParams(location.search).get("t") || sessionStorage.getItem("s51-token") || "";
if (token) sessionStorage.setItem("s51-token", token);

export class ApiError extends Error {}

async function call(path, { method = "GET", json, body, binary = false } = {}) {
  const headers = { "X-S51-Token": token };
  let data = body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    data = JSON.stringify(json);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/octet-stream";
  }
  let res;
  try {
    res = await fetch(`/api/${path}`, { method, headers, body: data });
  } catch (e) {
    throw new ApiError("Keine Verbindung zum Designer. Läuft das Programm noch?");
  }
  if (!res.ok) {
    let msg = `Fehler ${res.status}`;
    try { msg = (await res.json()).error || msg; } catch (e) { /* keine JSON-Antwort */ }
    throw new ApiError(msg);
  }
  if (binary) return new Uint8Array(await res.arrayBuffer());
  return res.json();
}

export const api = {
  info: () => call("info"),
  ping: () => call("ping", { method: "POST", json: {} }),
  preset: (name) => call(`preset?name=${encodeURIComponent(name)}`),
  decode: (bytes) => call("decode", { method: "POST", body: bytes }),
  encode: (layout) => call("encode", { method: "POST", json: layout, binary: true }),
  check: (layout) => call("check", { method: "POST", json: layout }),
  image: (payload) => call("image", { method: "POST", json: payload }),
  configDefaults: () => call("config/defaults"),
  configParse: (text) => call("config/parse", { method: "POST", json: { text } }),
  configDump: (values) => call("config/dump", { method: "POST", json: { values } }),
  configValidate: (values) => call("config/validate", { method: "POST", json: { values } }),
  wireless: (payload) => call("wireless", { method: "POST", json: payload }),
};

// Lebenszeichen, damit der Server weiß, dass das Fenster offen ist
export function startHeartbeat() {
  const beat = () => api.ping().catch(() => {});
  beat();
  setInterval(beat, 4000);
}
