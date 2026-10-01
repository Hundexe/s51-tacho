// Kleine Bausteine der Oberfläche: Elemente bauen, Hinweise, Meldungen, Dialoge, Menüs

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// -- Hinweise beim Darüberfahren ----------------------------------------------

let tipEl = null, tipTimer = null;
export function initTooltips() {
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-tip]");
    clearTimeout(tipTimer);
    if (tipEl) { tipEl.remove(); tipEl = null; }
    if (!t) return;
    tipTimer = setTimeout(() => {
      const r = t.getBoundingClientRect();
      tipEl = h("div", { class: "tip" }, t.dataset.tip);
      document.body.append(tipEl);
      const tw = tipEl.offsetWidth;
      let x = r.left + r.width / 2 - tw / 2;
      x = Math.max(8, Math.min(window.innerWidth - tw - 8, x));
      let y = r.bottom + 8;
      if (y + 30 > window.innerHeight) y = r.top - 34;
      tipEl.style.left = `${x}px`;
      tipEl.style.top = `${y}px`;
    }, 450);
  });
  document.addEventListener("pointerdown", () => {
    clearTimeout(tipTimer);
    if (tipEl) { tipEl.remove(); tipEl = null; }
  });
}

// -- Meldungen ------------------------------------------------------------------

export function toast(text, kind = "ok", ms = 3800) {
  const el = h("div", { class: `toast ${kind === "error" ? "error" : ""}` }, text);
  document.getElementById("toast-root").append(el);
  setTimeout(() => el.remove(), ms);
}

export function showError(e) {
  toast(e && e.message ? e.message : String(e), "error", 6000);
}

// -- Dialoge --------------------------------------------------------------------

export function modal({ title, body, actions = [], wide = false, onClose }) {
  const root = document.getElementById("modal-root");
  const msg = h("span", { class: "msg" });
  const close = () => { back.remove(); document.removeEventListener("keydown", onKey, true); if (onClose) onClose(); };
  const foot = h("div", { class: "modal-foot" }, msg,
    actions.map((a) => h("button", {
      class: `btn ${a.primary ? "primary" : ""} ${a.ghost ? "ghost" : ""}`,
      onclick: async (ev) => {
        const btn = ev.currentTarget;
        btn.disabled = true;
        try {
          const r = a.run ? await a.run({ close, setMessage }) : undefined;
          if (r !== false && a.close !== false) close();
        } catch (e) {
          setMessage(e.message || String(e));
        } finally {
          btn.disabled = false;
        }
      },
    }, a.label)));
  const dlg = h("div", { class: `modal ${wide ? "wide" : ""}`, role: "dialog", "aria-modal": "true", "aria-label": title },
    h("div", { class: "modal-head" }, h("h2", {}, title),
      h("button", { class: "icon-btn", "data-tip": "Schließen", onclick: close,
        html: '<svg class="i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>' })),
    h("div", { class: "modal-body" }, body), foot);
  const back = h("div", { class: "modal-back", onmousedown: (e) => { if (e.target === back) close(); } }, dlg);
  function setMessage(text, ok = false) {
    msg.textContent = text || "";
    msg.classList.toggle("ok", ok);
  }
  function onKey(e) {
    if (e.key === "Escape") { e.stopPropagation(); close(); }
  }
  document.addEventListener("keydown", onKey, true);
  root.append(back);
  const first = dlg.querySelector("input, select, textarea, .card, button.btn");
  if (first) setTimeout(() => first.focus(), 30);
  return { close, setMessage, el: dlg };
}

export function confirmDialog(title, text, okLabel = "OK", danger = false) {
  return new Promise((resolve) => {
    let result = false;
    modal({
      title, body: h("p", { class: "note", style: { fontSize: "13px", color: "var(--ivory)" } }, text),
      actions: [
        { label: "Abbrechen", ghost: true },
        { label: okLabel, primary: !danger, run: () => { result = true; } },
      ],
      onClose: () => resolve(result),
    });
  });
}

// Fragt nach Speichern / Verwerfen / Abbrechen
export function askSave() {
  return new Promise((resolve) => {
    let result = "cancel";
    modal({
      title: "Änderungen speichern?",
      body: h("p", { class: "note", style: { fontSize: "13px", color: "var(--ivory)" } },
        "Das Layout hat ungespeicherte Änderungen."),
      actions: [
        { label: "Abbrechen", ghost: true },
        { label: "Nicht speichern", run: () => { result = "discard"; } },
        { label: "Speichern", primary: true, run: () => { result = "save"; } },
      ],
      onClose: () => resolve(result),
    });
  });
}

// -- Ausklappmenü --------------------------------------------------------------

export function dropdown(button, items) {
  const menu = h("div", { class: "dropdown-menu", hidden: true, role: "menu" });
  const wrap = h("div", { class: "dropdown" }, button, menu);
  const build = () => {
    menu.replaceChildren(...items().map((it) => it === "-" ? h("div", { class: "menu-sep" }) :
      h("button", { class: "menu-item", role: "menuitem", disabled: it.disabled,
        onclick: () => { menu.hidden = true; it.run(); } },
      it.icon ? h("span", { html: it.icon }) : null, it.label, it.key ? h("span", { class: "key" }, it.key) : null)));
  };
  button.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = menu.hidden;
    document.querySelectorAll(".dropdown-menu").forEach((m) => { m.hidden = true; });
    if (open) { build(); menu.hidden = false; }
  });
  document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) menu.hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") menu.hidden = true; });
  return wrap;
}
