// Zeichnet Seiten eines Layouts auf eine Canvas, nach denselben Regeln wie die
// Firmware (firmware/lib/s51render) und designer/s51design/values.py.
// Schriften: DejaVu wie am Tacho, dadurch stimmen Breiten und Zeilen.

import { S, get } from "./schema.js";

// ------------------------------------------------------------------ Werte

export function demoValues(t = performance.now() / 1000, animate = true, now = new Date()) {
  const v = {};
  const phase = animate ? (t % 20) / 20 : 0.55;
  for (const s of S.info.sources) {
    if (s.kind !== "number") continue;
    const [lo, hi] = s.demo;
    v[s.key] = lo === hi ? lo : lo + (hi - lo) * (0.5 - 0.5 * Math.cos(phase * 2 * Math.PI));
  }
  const speed = v.speed;
  const gear = speed < 1 ? 0 : speed < 15 ? 1 : speed < 30 ? 2 : speed < 45 ? 3 : 4;
  v.gear = gear;
  v.rpm = gear === 0 ? 1500 : 3000 + ((speed % 15) / 15) * 4500;
  v.lean = animate ? 30 * Math.sin(t * 0.7) : 12;
  v.time = { h: now.getHours(), m: now.getMinutes(), s: now.getSeconds() };
  v.song_title = "Schwalbenflug";
  v.song_artist = "Testband";
  v.song_album = "Mopedtour";
  v.song_position = "1:23";
  v.song_length = "3:41";
  v.phone_name = "iPhone";
  const blink = animate ? Math.floor(t * 2) % 2 === 0 : true;
  Object.assign(v, {
    blinker_left: blink, blinker_right: false, high_beam: true, neutral: gear === 0, light: true,
    alarm_armed: false, gps_fix: true, bt_connected: true, shift_light: v.rpm > 6500, warning: v.head_temp > 200,
    music_playing: true,
  });
  return v;
}

export function formatNumber(value, decimals) {
  const s = Number(value).toFixed(Math.max(0, Math.min(6, decimals | 0)));
  const neg = s.startsWith("-");
  const [ip, fp] = (neg ? s.slice(1) : s).split(".");
  const grouped = ip.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (neg ? "-" : "") + grouped + (fp ? "," + fp : "");
}

function formatTime(tm, fmt) {
  const two = (n) => String(n).padStart(2, "0");
  if (!tm) return fmt.replaceAll("HH", "--").replaceAll("MM", "--").replaceAll("SS", "--");
  return fmt.replaceAll("HH", two(tm.h)).replaceAll("MM", two(tm.m)).replaceAll("SS", two(tm.s));
}

export function displayText(w, vals) {
  if (w.type === "text") return get(w, "text");
  const src = S.sources.get(get(w, "source"));
  if (!src || src.key === "none") return "–";
  const raw = vals[src.key];
  if (src.kind === "time") return formatTime(raw, get(w, "format") || "HH:MM");
  if (src.kind === "text") return String(raw || "");
  if (src.kind === "bool") return raw ? "an" : "aus";
  if (raw === undefined || raw === null) return "–";
  return formatNumber(raw, get(w, "decimals")) + get(w, "unit");
}

function numberOf(w, vals) {
  const src = S.sources.get(get(w, "source"));
  if (!src || src.kind !== "number") return null;
  const v = vals[src.key];
  return typeof v === "number" ? v : null;
}

export function thresholdColor(w, value, normal) {
  if (typeof value !== "number") return normal;
  const crit = get(w, "crit_above"), warn = get(w, "warn_above");
  if (crit && value >= crit) return get(w, "crit_color");
  if (warn && value >= warn) return get(w, "warn_color");
  return normal;
}

export function fraction(w, value) {
  const lo = get(w, "min"), hi = get(w, "max");
  if (typeof value !== "number" || hi === lo) return 0;
  return Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
}

export function fillRange(w, value) {
  const f = fraction(w, value);
  if (!get(w, "from_zero")) return [0, f];
  if (typeof value !== "number") return [0, 0];
  const f0 = fraction(w, 0);
  return [Math.min(f0, f), Math.max(f0, f)];
}

export function fillValue(w, value) {
  return get(w, "from_zero") && typeof value === "number" ? Math.abs(value) : value;
}

// Wie Pythons round(): .5 zur geraden Zahl
function roundHalfEven(x) {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

export function segmentLit(w, value, i, n) {
  const lo = get(w, "min"), hi = get(w, "max");
  if (!get(w, "from_zero")) {
    return [i < roundHalfEven(fraction(w, value) * n), lo + ((hi - lo) * (i + 1)) / n];
  }
  const [a, b] = fillRange(w, value);
  const c = (i + 0.5) / n;
  const f0 = fraction(w, 0);
  const end = c >= f0 ? (i + 1) / n : i / n;
  return [b > a && a <= c && c <= b, Math.abs(lo + (hi - lo) * end)];
}

// play_pause wird zu pause, solange Musik läuft, sonst play
export function resolveIcon(icon, vals) {
  if (icon === "play_pause") return vals.music_playing ? "pause" : "play";
  return icon;
}

// Rahmen für Symbol und Text einer Taste: [symbol, text], je [x, y, w, h] oder null
export function buttonBoxes(w) {
  const hasIcon = get(w, "icon") !== "none", hasText = get(w, "text") !== "";
  const m = Math.min(w.w, w.h), s = 0.55 * m;
  if (hasIcon && !hasText) return [[w.x + w.w / 2 - s / 2, w.y + w.h / 2 - s / 2, s, s], null];
  if (hasText && !hasIcon) return [null, [w.x, w.y, w.w, w.h]];
  if (!hasIcon) return [null, null];
  const a = (m - s) / 2;
  return [[w.x + a, w.y + w.h / 2 - s / 2, s, s], [w.x + s + 2 * a, w.y, w.w - s - 3 * a, w.h]];
}

export function indicatorOn(w, vals, t) {
  const src = S.sources.get(get(w, "source"));
  let on = src ? Boolean(vals[src.key]) : false;
  if (on && get(w, "blink")) on = Math.floor(t * 2) % 2 === 0;
  return on;
}

// ------------------------------------------------------------------ Schrift

const FAMILY = { sans: ['400', '"S51 Sans"'], sans_bold: ['700', '"S51 Sans"'], segment: ['700', '"S51 Mono"'] };
const metricsCache = new Map();

function setFont(ctx, font, size) {
  const [weight, family] = FAMILY[font] || FAMILY.sans;
  const css = `${weight} ${size}px ${family}`;
  ctx.font = css;
  let m = metricsCache.get(css);
  if (!m) {
    const mt = ctx.measureText("Hg");
    m = { ascent: mt.fontBoundingBoxAscent ?? size * 0.93, descent: mt.fontBoundingBoxDescent ?? size * 0.24 };
    if (document.fonts && document.fonts.check(css)) metricsCache.set(css, m);
  }
  return m;
}

function wrapLines(ctx, text, width, wrap) {
  const lines = [];
  for (const para of String(text).split("\n")) {
    if (!wrap) { lines.push(para); continue; }
    let line = "";
    for (const word of para.split(" ")) {
      const trial = line === "" ? word : line + " " + word;
      if (line !== "" && ctx.measureText(trial).width > width) {
        lines.push(line);
        line = word;
      } else {
        line = trial;
      }
    }
    lines.push(line);
  }
  return lines;
}

// Text im Rahmen: waagerecht nach align, senkrecht mittig, am Rahmen abgeschnitten
export function drawTextBox(ctx, text, x, y, w, h, font, size, color, align, wrap, clip = true) {
  if (text === "" || text === undefined || size < 1) return;
  ctx.save();
  if (clip) {
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
  }
  const m = setFont(ctx, font, size);
  ctx.fillStyle = color;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  const lines = wrapLines(ctx, text, w, wrap);
  const lineH = lines.length > 1 ? 1.2 * size : m.ascent + m.descent;
  const total = lineH * (lines.length - 1) + m.ascent + m.descent;
  const top = y + h / 2 - total / 2;
  lines.forEach((line, k) => {
    const tw = ctx.measureText(line).width;
    const tx = align === "left" ? x : align === "right" ? x + w - tw : x + w / 2 - tw / 2;
    ctx.fillText(line, Math.round(tx), Math.round(top + k * lineH + m.ascent));
  });
  ctx.restore();
}

// ------------------------------------------------------------------ Formen

function roundRect(ctx, x0, y0, x1, y1, r, color) {
  r = Math.max(0, Math.min(r, (x1 - x0) / 2, (y1 - y0) / 2));
  if (x1 <= x0 || y1 <= y0) return;
  ctx.fillStyle = color;
  ctx.beginPath();
  if (r < 1) ctx.rect(x0, y0, x1 - x0, y1 - y0);
  else ctx.roundRect(x0, y0, x1 - x0, y1 - y0, r);
  ctx.fill();
}

function rectF(ctx, x0, y0, x1, y1, color) {
  const a = Math.round(x0), b = Math.round(y0), c = Math.round(x1), d = Math.round(y1);
  if (c > a && d > b) {
    ctx.fillStyle = color;
    ctx.fillRect(a, b, c - a, d - b);
  }
}

function drawBar(ctx, w, vals) {
  const value = numberOf(w, vals);
  const [a, b] = fillRange(w, value);
  const bg = get(w, "bg_color"), normal = get(w, "color");
  const vertical = get(w, "orientation") === "vertical";
  const n = get(w, "segments");
  if (n <= 0) {
    roundRect(ctx, w.x, w.y, w.x + w.w, w.y + w.h, get(w, "radius"), bg);
    const col = thresholdColor(w, fillValue(w, value), normal);
    if (b > a) {
      if (vertical) roundRect(ctx, w.x, w.y + w.h * (1 - b), w.x + w.w, w.y + w.h * (1 - a), get(w, "radius"), col);
      else roundRect(ctx, w.x + w.w * a, w.y, w.x + w.w * b, w.y + w.h, get(w, "radius"), col);
    }
    return;
  }
  const gap = 2;
  const length = vertical ? w.h : w.w;
  const seg = (length - gap * (n - 1)) / n;
  for (let i = 0; i < n; i++) {
    const [lit, segValue] = segmentLit(w, value, i, n);
    const col = lit ? thresholdColor(w, segValue, normal) : bg;
    const p = i * (seg + gap);
    if (vertical) rectF(ctx, w.x, w.y + w.h - p - seg, w.x + w.w, w.y + w.h - p, col);
    else rectF(ctx, w.x + p, w.y, w.x + p + seg, w.y + w.h, col);
  }
}

function arc(ctx, cx, cy, r, th, a0, a1, color) {
  if (a1 - a0 <= 0.01) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = th;
  ctx.lineCap = "butt";
  ctx.arc(cx, cy, r, (a0 * Math.PI) / 180, (Math.min(a1, a0 + 360) * Math.PI) / 180);
  ctx.stroke();
}

function drawGauge(ctx, w, vals) {
  const th = get(w, "thickness");
  const size = Math.min(w.w, w.h);
  const cx = w.x + w.w / 2, cy = w.y + w.h / 2;
  const r = size / 2 - th / 2;
  let a0 = get(w, "start_angle"), a1 = get(w, "end_angle");
  if (a1 < a0) [a0, a1] = [a1, a0];
  arc(ctx, cx, cy, r, th, a0, a1, get(w, "bg_color"));
  const value = numberOf(w, vals);
  const [fa, fb] = fillRange(w, value);
  if (fb > fa) {
    arc(ctx, cx, cy, r, th, a0 + (a1 - a0) * fa, a0 + (a1 - a0) * fb,
      thresholdColor(w, fillValue(w, value), get(w, "color")));
  }
}

function poly(ctx, pts, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(pts[0], pts[1]);
  for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
  ctx.closePath();
  ctx.fill();
}

function line(ctx, x0, y0, x1, y1, width, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "butt";
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
}

// Symbol im Rahmen x, y, bw × bh
function drawIcon(ctx, icon, bx, by, bw, bh, color) {
  const x0 = bx, y0 = by, x1 = bx + bw, y1 = by + bh;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, s = Math.min(bw, bh);
  const label = (text, size, col) => drawTextBox(ctx, text, x0, y0, bw, bh, "sans_bold", size, col, "center", false, false);
  const R = (a, b, c, d) => rectF(ctx, a, b, c, d, color);
  switch (icon) {
    case "play":
      poly(ctx, [cx - s * 0.22, cy - s * 0.32, cx - s * 0.22, cy + s * 0.32, cx + s * 0.32, cy], color);
      break;
    case "pause":
      R(cx - s * 0.28, cy - s * 0.3, cx - s * 0.08, cy + s * 0.3);
      R(cx + s * 0.08, cy - s * 0.3, cx + s * 0.28, cy + s * 0.3);
      break;
    case "next":
    case "previous": {
      const d = icon === "next" ? 1 : -1, hh = s * 0.28;
      poly(ctx, [cx - d * s * 0.38, cy - hh, cx - d * s * 0.38, cy + hh, cx - d * s * 0.02, cy], color);
      poly(ctx, [cx - d * s * 0.02, cy - hh, cx - d * s * 0.02, cy + hh, cx + d * s * 0.32, cy], color);
      const xa = Math.min(cx + d * s * 0.32, cx + d * s * 0.42), xb = Math.max(cx + d * s * 0.32, cx + d * s * 0.42);
      R(xa, cy - hh, xb, cy + hh);
      break;
    }
    case "volume_up":
    case "volume_down":
      R(cx - s * 0.4, cy - s * 0.12, cx - s * 0.25, cy + s * 0.12);
      poly(ctx, [cx - s * 0.25, cy - s * 0.12, cx - s * 0.05, cy - s * 0.3, cx - s * 0.05, cy + s * 0.3, cx - s * 0.25, cy + s * 0.12], color);
      R(cx + s * 0.08, cy - s * 0.04, cx + s * 0.4, cy + s * 0.04);
      if (icon === "volume_up") R(cx + s * 0.2, cy - s * 0.16, cx + s * 0.28, cy + s * 0.16);
      break;
    case "menu":
      for (const k of [-1, 0, 1]) R(cx - s * 0.32, cy + k * s * 0.2 - s * 0.05, cx + s * 0.32, cy + k * s * 0.2 + s * 0.05);
      break;
    case "arrow_left":
      poly(ctx, [x0, cy, cx, y0 + s * 0.1, cx, cy - s * 0.18, x1, cy - s * 0.18, x1, cy + s * 0.18, cx, cy + s * 0.18,
        cx, y1 - s * 0.1], color);
      break;
    case "arrow_right":
      poly(ctx, [x1, cy, cx, y0 + s * 0.1, cx, cy - s * 0.18, x0, cy - s * 0.18, x0, cy + s * 0.18, cx, cy + s * 0.18,
        cx, y1 - s * 0.1], color);
      break;
    case "high_beam": {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.ellipse(cx + s * 0.2, cy, s * 0.3, (y1 - y0 - s * 0.3) / 2, 0, Math.PI / 2, (3 * Math.PI) / 2);
      ctx.closePath();
      ctx.fill();
      for (let k = 0; k < 4; k++) {
        const yy = y0 + s * (0.25 + 0.17 * k);
        rectF(ctx, x0 + s * 0.05, yy - 1, cx - s * 0.15, yy + 1, color);
      }
      break;
    }
    case "neutral":
      roundRect(ctx, x0 + 1, y0 + 1, x1 - 1, y1 - 1, s * 0.2, color);
      label("N", s * 0.7, "#000000");
      break;
    case "light":
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, cy, s * 0.22, 0, Math.PI * 2);
      ctx.fill();
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        line(ctx, cx + Math.cos(a) * s * 0.3, cy + Math.sin(a) * s * 0.3, cx + Math.cos(a) * s * 0.45,
          cy + Math.sin(a) * s * 0.45, 2, color);
      }
      break;
    case "battery": {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      const a = Math.round(x0 + s * 0.1), b = Math.round(cy - s * 0.25), c = Math.round(x1 - s * 0.1), d = Math.round(cy + s * 0.3);
      ctx.strokeRect(a + 1, b + 1, c - a - 2, d - b - 2);
      rectF(ctx, x0 + s * 0.25, cy - s * 0.35, x0 + s * 0.35, cy - s * 0.25, color);
      rectF(ctx, x1 - s * 0.35, cy - s * 0.35, x1 - s * 0.25, cy - s * 0.25, color);
      break;
    }
    case "temp":
      line(ctx, cx, y0 + s * 0.1, cx, y1 - s * 0.35, s * 0.15, color);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, y1 - s * 0.23, s * 0.17, 0, Math.PI * 2);
      ctx.fill();
      break;
    case "lock": {
      rectF(ctx, x0 + s * 0.2, cy - s * 0.05, x1 - s * 0.2, y1 - s * 0.1, color);
      const top = y0 + s * 0.1, bottom = cy + s * 0.15;
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(cx, (top + bottom) / 2, s * 0.2 - 1, (bottom - top) / 2 - 1, 0, Math.PI, 2 * Math.PI);
      ctx.stroke();
      break;
    }
    case "warning":
      poly(ctx, [cx, y0 + s * 0.08, x1 - s * 0.05, y1 - s * 0.1, x0 + s * 0.05, y1 - s * 0.1], color);
      drawTextBox(ctx, "!", cx - s / 2, cy + s * 0.12 - s / 2, s, s, "sans_bold", s * 0.5, "#000000", "center", false, false);
      break;
    case "gps": label("GPS", s * 0.4, color); break;
    case "bluetooth": label("BT", s * 0.4, color); break;
    case "music": label("♪", s * 0.7, color); break;
    default:
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, cy, s * 0.2, 0, Math.PI * 2);
      ctx.fill();
  }
}

// Fläche mit Eckenradius, der Rahmen liegt innerhalb (Fläche und Taste)
function drawPlate(ctx, w, color) {
  const bw = get(w, "border_width"), r = get(w, "radius");
  if (bw > 0) {
    roundRect(ctx, w.x, w.y, w.x + w.w, w.y + w.h, r, get(w, "border_color"));
    if (w.w > 2 * bw && w.h > 2 * bw) roundRect(ctx, w.x + bw, w.y + bw, w.x + w.w - bw, w.y + w.h - bw, Math.max(0, r - bw), color);
  } else {
    roundRect(ctx, w.x, w.y, w.x + w.w, w.y + w.h, r, color);
  }
}

function drawRect(ctx, w) {
  drawPlate(ctx, w, get(w, "color"));
}

function drawButton(ctx, w, vals) {
  drawPlate(ctx, w, get(w, "bg_color"));
  const [ib, tb] = buttonBoxes(w);
  if (ib) drawIcon(ctx, resolveIcon(get(w, "icon"), vals), ib[0], ib[1], ib[2], ib[3], get(w, "color"));
  if (tb && tb[2] > 0) {
    drawTextBox(ctx, get(w, "text"), tb[0], tb[1], tb[2], tb[3], get(w, "font"), get(w, "size"), get(w, "color"), "center", true);
  }
}

// ------------------------------------------------------------------ Bilder

const imageCache = new Map();

// Bild aus den Rohdaten (RGB565 Little Endian, optional ein Alpha-Byte je Pixel)
export function imageCanvas(img) {
  const key = `${img.id}:${img.width}x${img.height}:${img.raw.length}:${img.raw.slice(0, 64)}:${img.raw.slice(-64)}`;
  let c = imageCache.get(key);
  if (c) return c;
  const bin = atob(img.raw);
  const step = img.alpha ? 3 : 2;
  c = document.createElement("canvas");
  c.width = img.width;
  c.height = img.height;
  const cx = c.getContext("2d");
  const data = cx.createImageData(img.width, img.height);
  for (let i = 0, p = 0; p < img.width * img.height; p++, i += step) {
    const v = bin.charCodeAt(i) | (bin.charCodeAt(i + 1) << 8);
    const r = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31;
    data.data[p * 4] = (r << 3) | (r >> 2);
    data.data[p * 4 + 1] = (g << 2) | (g >> 4);
    data.data[p * 4 + 2] = (b << 3) | (b >> 2);
    data.data[p * 4 + 3] = img.alpha ? bin.charCodeAt(i + 2) : 255;
  }
  cx.putImageData(data, 0, 0);
  if (imageCache.size > 120) imageCache.clear();
  imageCache.set(key, c);
  return c;
}

function drawImage(ctx, w, layout, editor) {
  const img = layout.images.find((i) => i.id === get(w, "image"));
  if (!img) {
    if (editor) {
      ctx.save();
      ctx.strokeStyle = "#888780";
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1;
      ctx.strokeRect(w.x + 0.5, w.y + 0.5, w.w - 1, w.h - 1);
      ctx.restore();
      drawTextBox(ctx, "Kein Bild", w.x, w.y, w.w, w.h, "sans", 11, "#888780", "center", false);
    }
    return;
  }
  ctx.save();
  ctx.beginPath();
  ctx.rect(w.x, w.y, w.w, w.h);
  ctx.clip();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(imageCanvas(img), w.x, w.y);
  ctx.restore();
}

// ------------------------------------------------------------------ Seite

export function drawWidget(ctx, w, vals, t, layout, editor) {
  switch (w.type) {
    case "text":
      drawTextBox(ctx, get(w, "text"), w.x, w.y, w.w, w.h, get(w, "font"), get(w, "size"), get(w, "color"), get(w, "align"), true);
      break;
    case "value":
      drawTextBox(ctx, displayText(w, vals), w.x, w.y, w.w, w.h, get(w, "font"), get(w, "size"),
        thresholdColor(w, numberOf(w, vals), get(w, "color")), get(w, "align"), false);
      break;
    case "bar": drawBar(ctx, w, vals); break;
    case "gauge": drawGauge(ctx, w, vals); break;
    case "indicator":
      drawIcon(ctx, resolveIcon(get(w, "icon"), vals), w.x, w.y, w.w, w.h,
        indicatorOn(w, vals, t) ? get(w, "on_color") : get(w, "off_color"));
      break;
    case "button": drawButton(ctx, w, vals); break;
    case "rect": drawRect(ctx, w); break;
    case "image": drawImage(ctx, w, layout, editor); break;
    default:
      if (editor) {
        ctx.save();
        ctx.strokeStyle = "#E24B4A";
        ctx.setLineDash([4, 2]);
        ctx.strokeRect(w.x + 0.5, w.y + 0.5, w.w - 1, w.h - 1);
        ctx.restore();
      }
  }
}

// opts: { scale, vals, t, showHidden, grid }
export function drawScreen(ctx, layout, screen, opts) {
  const scale = opts.scale || 1;
  ctx.save();
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.fillStyle = screen.bg;
  ctx.fillRect(0, 0, layout.width, layout.height);
  if (opts.grid) {
    // Hilfslinien über dem Hintergrund, unter den Elementen
    ctx.strokeStyle = "rgba(236, 229, 211, 0.07)";
    ctx.lineWidth = 1 / scale;
    ctx.beginPath();
    for (let x = opts.grid; x < layout.width; x += opts.grid) { ctx.moveTo(x, 0); ctx.lineTo(x, layout.height); }
    for (let y = opts.grid; y < layout.height; y += opts.grid) { ctx.moveTo(0, y); ctx.lineTo(layout.width, y); }
    ctx.stroke();
  }
  for (const w of screen.widgets) {
    if (w.hidden && !opts.showHidden) continue;
    ctx.save();
    if (w.hidden) ctx.globalAlpha = 0.35;
    drawWidget(ctx, w, opts.vals, opts.t || 0, layout, Boolean(opts.showHidden));
    ctx.restore();
    if (w.hidden) {
      ctx.save();
      ctx.strokeStyle = "#a9a394";
      ctx.lineWidth = 1 / scale;
      ctx.setLineDash([3 / scale, 3 / scale]);
      ctx.strokeRect(w.x, w.y, w.w, w.h);
      ctx.restore();
    }
  }
  ctx.restore();
}

// Kleines Vorschaubild einer Seite (für Seitenliste, Vorlagen, Auswahl)
export function renderThumb(canvas, layout, screen, vals) {
  const dpr = window.devicePixelRatio || 1;
  const cw = canvas.clientWidth || canvas.width, ch = canvas.clientHeight || canvas.height;
  canvas.width = Math.round(cw * dpr);
  canvas.height = Math.round(ch * dpr);
  const ctx = canvas.getContext("2d");
  drawScreen(ctx, layout, screen, { scale: (cw * dpr) / layout.width, vals, t: 0.1, showHidden: false });
}
