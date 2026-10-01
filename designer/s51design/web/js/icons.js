// Eigene Symbole (24 × 24, Linien), gezeichnet für den S51 Designer.

const P = {
  new: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M12 11v6M9 14h6"/>',
  open: '<path d="M3 8V6a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v1"/><path d="M3 8h18l-2 10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  save: '<path d="M5 4a1 1 0 0 1 1-1h10l4 4v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z"/><path d="M8 3v5h7V3M8 21v-6h8v6"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
  duplicate: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>',
  front: '<rect x="9" y="9" width="11" height="11" rx="2" fill="currentColor" stroke="none"/><path d="M15 5V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1"/>',
  back: '<rect x="4" y="4" width="11" height="11" rx="2" fill="currentColor" stroke="none"/><path d="M19 9a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1"/>',
  forward: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  backward: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="15.5" cy="9" r="1.8"/><path d="m3 17 5.5-5.5 4 4L15 13l6 5"/>',
  settings: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  wireless: '<path d="M4.5 10a11 11 0 0 1 15 0M7.5 13.3a6.5 6.5 0 0 1 9 0"/><circle cx="12" cy="17.5" r="1.4" fill="currentColor" stroke="none"/>',
  sd: '<path d="M8 3h8l3 3v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6z"/><path d="M9 6.5v3M12 6.5v3M15 6.5v3"/>',
  play: '<path d="M7 5v14l11-7z"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M10 5.7A9.6 9.6 0 0 1 12 5.5C18 5.5 21.5 12 21.5 12a17 17 0 0 1-2.6 3.4M6.5 7.3A17 17 0 0 0 2.5 12S6 18.5 12 18.5a9.4 9.4 0 0 0 4.6-1.2M4 4l16 16"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  unlock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.6-1.7"/>',
  grid: '<path d="M4 9h16M4 15h16M9 4v16M15 4v16"/>',
  magnet: '<path d="M6 4v8a6 6 0 0 0 12 0V4"/><path d="M6 8h4M14 8h4"/><path d="M10 4v8a2 2 0 0 0 4 0V4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  up: '<path d="m6 15 6-6 6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  more: '<circle cx="5.5" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="18.5" cy="12" r="1.3" fill="currentColor" stroke="none"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 4 2.8 19.5h18.4z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  download: '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
  upload: '<path d="M12 16V5M7 9.5l5-5 5 5M5 20h14"/>',
  fit: '<path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/>',
  moon: '<path d="M19 14.5A7.5 7.5 0 1 1 9.5 5a6 6 0 0 0 9.5 9.5z"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  page: '<rect x="3" y="5" width="18" height="14" rx="2"/>',
  pulse: '<path d="M3 12h4l2.5-6 5 12L17 12h4"/>',
  // Element-Typen
  text: '<path d="M5 7V5h14v2M12 5v14M9 19h6"/>',
  value: '<path d="M5.5 8.5 8.5 6v12M13 9.2a3 3 0 0 1 6 .3c0 3.5-6 4.5-6 8.5h6"/>',
  bar: '<rect x="3" y="9" width="3.6" height="6" rx=".6"/><rect x="8.1" y="9" width="3.6" height="6" rx=".6"/><rect x="13.2" y="9" width="3.6" height="6" rx=".6" opacity=".55"/><rect x="18.3" y="9" width="2.7" height="6" rx=".6" opacity=".3"/>',
  gauge: '<path d="M5.6 18.4a9 9 0 1 1 12.8 0"/><path d="m12 14 4-5"/><circle cx="12" cy="14" r="1.4" fill="currentColor" stroke="none"/>',
  indicator: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
  rect: '<rect x="4" y="6" width="16" height="12" rx="2.5"/>',
};

export function icon(name, cls = "") {
  return `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[name] || P.page}</svg>`;
}

export const TYPE_ICON = { text: "text", value: "value", bar: "bar", gauge: "gauge", indicator: "indicator", rect: "rect",
  image: "image" };
