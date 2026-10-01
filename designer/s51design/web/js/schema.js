// Nummern und Standardwerte aus designer/s51design/schema.py (geladen über /api/info)

export const S = {
  info: null,
  props: new Map(),
  types: new Map(),
  sources: new Map(),
  enums: {},
};

export function initSchema(info) {
  S.info = info;
  for (const p of info.props) S.props.set(p.key, p);
  for (const t of info.widget_types) S.types.set(t.key, t);
  for (const s of info.sources) S.sources.set(s.key, s);
  S.enums = info.enums;
}

export function propDefault(typeKey, key) {
  const t = S.types.get(typeKey);
  if (t && key in t.overrides) return t.overrides[key];
  const p = S.props.get(key);
  return p ? p.default : undefined;
}

// Wert einer Eigenschaft eines Elements (mit Standardwert, wenn nicht gesetzt)
export function get(w, key) {
  return key in w.props ? w.props[key] : propDefault(w.type, key);
}

export function enumLabel(name, key) {
  const e = (S.enums[name] || []).find((x) => x[1] === key);
  return e ? e[2] : key;
}

export function typeLabel(key) {
  const t = S.types.get(key);
  return t ? t.label : key;
}

export function newWidget(typeKey, x, y) {
  const t = S.types.get(typeKey);
  const props = {};
  for (const k of t.props) props[k] = propDefault(typeKey, k);
  return { type: typeKey, x, y, w: t.size[0], h: t.size[1], hidden: false, locked: false, props };
}
