"""Lesen und Schreiben der Konfigurationsdatei tacho.cfg.

Aufbau: siehe docs/konfiguration.md. Kurz: Textdatei im INI-Stil,
UTF-8, Abschnitte in [eckigen Klammern], Zeilen "schluessel = wert",
Kommentare beginnen mit # oder ;.
"""

from . import schema as S

TRUE_WORDS = ("ja", "true", "1", "an", "yes")
FALSE_WORDS = ("nein", "false", "0", "aus", "no")


class ConfigWarning:
    def __init__(self, line, message):
        self.line = line
        self.message = message

    def __str__(self):
        return f"Zeile {self.line}: {self.message}" if self.line else self.message


def defaults():
    return {(c.section, c.key): c.default for c in S.CONFIG}


def parse_value(c, raw):
    """Wandelt den Text eines Werts in den passenden Typ. Wirft ValueError."""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        v = v[1:-1]
    if c.type == "bool":
        low = v.lower()
        if low in TRUE_WORDS:
            return True
        if low in FALSE_WORDS:
            return False
        raise ValueError(f"erwartet ja oder nein, steht da: {raw.strip()!r}")
    if c.type == "int":
        n = int(v)
        if (c.min is not None and n < c.min) or (c.max is not None and n > c.max):
            raise ValueError(f"{n} liegt außerhalb von {c.min:g}–{c.max:g}")
        return n
    if c.type == "float":
        n = float(v.replace(",", "."))
        if (c.min is not None and n < c.min) or (c.max is not None and n > c.max):
            raise ValueError(f"{n} liegt außerhalb von {c.min:g}–{c.max:g}")
        return n
    if c.type == "enum":
        if v.lower() not in c.choices:
            raise ValueError(f"erlaubt sind {', '.join(c.choices)}")
        return v.lower()
    return v


def format_value(c, value):
    if c.type == "bool":
        return "ja" if value else "nein"
    if c.type == "float":
        return f"{float(value):g}"
    if c.type == "str":
        s = str(value)
        if s != s.strip() or "#" in s or ";" in s or s == "":
            return f'"{s}"'
        return s
    return str(value)


def parse(text):
    """Text -> (Werte, Warnungen). Fehlende oder ungültige Werte bekommen den Standard."""
    values = defaults()
    warnings = []
    section = None
    for n, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if n == 1 and stripped.startswith("﻿"):
            stripped = stripped[1:]
        if not stripped or stripped[0] in "#;":
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip().lower()
            if section not in S.CONFIG_SECTIONS:
                warnings.append(ConfigWarning(n, f"Unbekannter Abschnitt [{section}], wird ignoriert"))
            continue
        if "=" not in stripped:
            warnings.append(ConfigWarning(n, "Zeile ohne '=', wird ignoriert"))
            continue
        key, raw = stripped.split("=", 1)
        key = key.strip().lower()
        # Kommentar hinter dem Wert abschneiden, außer innerhalb von Anführungszeichen
        raw = raw.strip()
        if not raw.startswith('"'):
            for mark in (" #", " ;"):
                if mark in raw:
                    raw = raw.split(mark, 1)[0]
        else:
            close = raw.find('"', 1)
            if close > 0:
                raw = raw[:close + 1]
        if section is None:
            warnings.append(ConfigWarning(n, f"{key} steht vor dem ersten Abschnitt, wird ignoriert"))
            continue
        c = S.CONFIG_BY_ID.get((section, key))
        if c is None:
            if section in S.CONFIG_SECTIONS:
                warnings.append(ConfigWarning(n, f"Unbekannter Schlüssel {key} in [{section}], wird ignoriert"))
            continue
        try:
            values[(section, key)] = parse_value(c, raw)
        except ValueError as e:
            warnings.append(ConfigWarning(n, f"{section}.{key}: {e}. Standard {format_value(c, c.default)} wird verwendet"))
    return values, warnings


def dump(values=None):
    """Werte -> vollständige Datei mit Erklärungen."""
    values = values or defaults()
    out = [
        "# S51-Tacho: Konfiguration",
        "# Diese Datei liegt auf der SD-Karte unter s51/tacho.cfg.",
        "# Erklärung aller Einträge: docs/konfiguration.md im Projekt.",
        "# Fehlende oder ungültige Werte ersetzt der Tacho durch den Standard.",
        "",
    ]
    for section in S.CONFIG_SECTIONS:
        out.append(f"[{section}]")
        for c in [c for c in S.CONFIG if c.section == section]:
            out.append(f"# {c.description}")
            extra = []
            if c.type == "enum":
                extra.append("Möglich: " + ", ".join(c.choices))
            elif c.min is not None:
                extra.append(f"Bereich: {c.min:g} bis {c.max:g}")
            extra.append(f"Standard: {format_value(c, c.default)}")
            out.append("# " + ". ".join(extra))
            out.append(f"{c.key} = {format_value(c, values.get((section, c.key), c.default))}")
            out.append("")
    return "\n".join(out)


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return parse(f.read())


def save(values, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(values))
