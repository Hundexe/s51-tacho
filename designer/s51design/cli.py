"""Kommandozeile für Layout- und Konfigurationsdateien.

Beispiele:
  python -m s51design.cli decode design.s51            # Layout als JSON anzeigen
  python -m s51design.cli encode layout.json design.s51 # JSON -> .s51
  python -m s51design.cli check design.s51             # nur prüfen
  python -m s51design.cli preset Klar design.s51       # mitgeliefertes Layout schreiben
  python -m s51design.cli config-check tacho.cfg       # Konfiguration prüfen
  python -m s51design.cli config-new tacho.cfg         # Vorlage mit allen Einträgen schreiben
"""

import argparse
import json
import sys

from . import config_format, layout_format, presets


def main(argv=None):
    ap = argparse.ArgumentParser(prog="s51design", description="Werkzeuge für S51-Tacho-Dateien")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("decode", help="Layout-Datei als JSON ausgeben")
    p.add_argument("datei")
    p = sub.add_parser("encode", help="JSON in Layout-Datei umwandeln")
    p.add_argument("json")
    p.add_argument("datei")
    p = sub.add_parser("check", help="Layout-Datei prüfen")
    p.add_argument("datei")
    p = sub.add_parser("preset", help="Mitgeliefertes Layout als Datei schreiben")
    p.add_argument("name", choices=sorted(presets.PRESETS))
    p.add_argument("datei")
    p = sub.add_parser("config-check", help="Konfigurationsdatei prüfen")
    p.add_argument("datei")
    p = sub.add_parser("config-new", help="Konfigurationsvorlage schreiben")
    p.add_argument("datei")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "decode":
            layout = layout_format.load(args.datei)
            json.dump(layout_format.to_dict(layout), sys.stdout, ensure_ascii=False, indent=2)
            print()
        elif args.cmd == "encode":
            with open(args.json, encoding="utf-8") as f:
                layout = layout_format.from_dict(json.load(f))
            n = layout_format.save(layout, args.datei, tool="s51design cli")
            print(f"{args.datei}: {n} Bytes geschrieben")
        elif args.cmd == "check":
            layout = layout_format.load(args.datei)
            count = sum(len(s.widgets) for s in layout.screens)
            print(f"OK: „{layout.name}“, {len(layout.screens)} Seiten, {count} Elemente")
        elif args.cmd == "preset":
            n = layout_format.save(presets.PRESETS[args.name](), args.datei, tool="s51design cli")
            print(f"{args.datei}: {n} Bytes geschrieben")
        elif args.cmd == "config-check":
            _, warnings = config_format.load(args.datei)
            for w in warnings:
                print("Warnung:", w)
            print("OK" if not warnings else f"{len(warnings)} Warnungen")
            return 1 if warnings else 0
        elif args.cmd == "config-new":
            config_format.save(config_format.defaults(), args.datei)
            print(f"{args.datei} geschrieben")
    except layout_format.LayoutError as e:
        print("Fehler:", e, file=sys.stderr)
        return 2
    except OSError as e:
        print("Datei-Fehler:", e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
