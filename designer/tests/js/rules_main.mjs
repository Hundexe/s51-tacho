// Gibt für jedes Element aus, was die Oberfläche anzeigen würde (Text, Farbe,
// gefüllter Bereich, Segmente, Kontrollleuchte). Gleiches Format wie
// firmware/hosttest/values_main.cpp. Aufruf: node rules_main.mjs <info.json> <layout.json>
import fs from "node:fs";
import { initSchema, get } from "../../s51design/web/js/schema.js";
import { buttonBoxes, demoValues, displayText, fillRange, fillValue, indicatorOn, resolveIcon, segmentLit, thresholdColor } from "../../s51design/web/js/render.js";

const info = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const layout = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
initSchema(info);
const now = new Date(2026, 0, 1, 14, 27, 0);
const vals = demoValues(0, false, now);
const out = [];
for (const s of layout.screens) {
  s.widgets.forEach((w, i) => {
    let text = "-", col = "-", fr = [0, 0], on = 0;
    const src = ["value", "bar", "gauge", "indicator"].includes(w.type) ? info.sources.find((x) => x.key === get(w, "source")) : null;
    const num = src && src.kind === "number" && typeof vals[src.key] === "number" ? vals[src.key] : null;
    if (w.type === "text" || w.type === "value") {
      text = displayText(w, vals);
      col = w.type === "value" ? thresholdColor(w, num, get(w, "color")) : get(w, "color");
    } else if (w.type === "bar" || w.type === "gauge") {
      fr = fillRange(w, num);
      col = thresholdColor(w, fillValue(w, num), get(w, "color"));
      if (w.type === "bar" && get(w, "segments") > 0) {
        let marks = "";
        for (let k = 0; k < get(w, "segments"); k++) {
          const [lit, sv] = segmentLit(w, num, k, get(w, "segments"));
          marks += lit ? (thresholdColor(w, sv, get(w, "color")) === get(w, "color") ? "n" : "w") : ".";
        }
        text = "-" + marks;
      }
    } else if (w.type === "indicator") {
      on = indicatorOn(w, vals, 0.1) ? 1 : 0;
    } else if (w.type === "button") {
      const [ib, tb] = buttonBoxes(w);
      const code = info.enums.icon.find((e) => e[1] === resolveIcon(get(w, "icon"), vals))[0];
      const f = (x) => x.toFixed(1);
      text = `${code}:${ib ? f(ib[0]) : "-1.0"},${ib ? f(ib[1]) : "-1.0"},${ib ? f(ib[2]) : "-1.0"}:` +
        `${tb ? f(tb[0]) : "-1.0"},${tb ? f(tb[2]) : "-1.0"}`;
    }
    out.push(`${s.id}|${i}|${text}|${col === "-" ? col : col.toUpperCase()}|${fr[0].toFixed(3)}-${fr[1].toFixed(3)}|${on}`);
  });
}
console.log(out.join("\n"));
