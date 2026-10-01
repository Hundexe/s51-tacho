"""Designs auf die SD-Karte des Tachos schreiben.

Auf der Karte liegen im Ordner s51 beliebig viele Designs (.s51) und die
tacho.cfg. Welches Design beim Start gilt, steht in der tacho.cfg unter
anzeige.layout_datei (Standard-Design). Am Tacho lässt sich durch langes
Drücken ein anderes wählen, siehe firmware/README.md.
"""

import os
import re
import unicodedata

from . import config_format

DIR_NAME = "s51"
CFG_NAME = "tacho.cfg"
MAX_NAME = 40


def target_dir(chosen):
    """Ordner s51 auf der Karte. Wurde er selbst gewählt, wird er direkt benutzt."""
    return chosen if os.path.basename(os.path.normpath(chosen)).lower() == DIR_NAME else os.path.join(chosen, DIR_NAME)


def file_name_for(layout_name):
    """Dateiname aus dem Namen des Layouts: klein, ohne Umlaute und Sonderzeichen."""
    s = layout_name.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:MAX_NAME].strip("-")
    return (s or "design") + ".s51"


def clean_file_name(name):
    """Prüft einen eingegebenen Dateinamen. Gibt den Namen mit .s51 zurück oder wirft ValueError."""
    name = name.strip()
    if not name.lower().endswith(".s51"):
        name += ".s51"
    stem = name[:-4]
    if not stem or not re.fullmatch(r"[A-Za-z0-9_\-]+", stem):
        raise ValueError("Dateiname nur aus Buchstaben (ohne Umlaute), Ziffern, - und _")
    if len(stem) > MAX_NAME:
        raise ValueError(f"Dateiname höchstens {MAX_NAME} Zeichen")
    return name


def list_designs(directory):
    """Alle .s51-Dateien im Ordner, alphabetisch (wie der Tacho sie anzeigt)."""
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return sorted(n for n in names if n.lower().endswith(".s51") and not n.startswith(".")
                  and os.path.isfile(os.path.join(directory, n)))


def card_config(directory):
    """Standard-Design laut tacho.cfg auf der Karte, oder None."""
    path = os.path.join(directory, CFG_NAME)
    if not os.path.exists(path):
        return None
    try:
        values, _ = config_format.load(path)
    except (OSError, UnicodeDecodeError):
        return None
    return values


def export(directory, data, file_name, default_name, cfg=None):
    """Schreibt ein Design und legt das Standard-Design fest.

    cfg: Einstellungen aus dem Designer. None heißt: Einstellungen auf der Karte
    behalten (oder Standardwerte, wenn es dort keine gibt) und nur das
    Standard-Design ändern. Gibt die geschriebene tacho.cfg als Werte zurück.
    """
    file_name = clean_file_name(file_name)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, file_name), "wb") as f:
        f.write(data)
    values = dict(cfg) if cfg is not None else (card_config(directory) or config_format.defaults())
    values[("anzeige", "layout_datei")] = clean_file_name(default_name)
    config_format.save(values, os.path.join(directory, CFG_NAME))
    return values
