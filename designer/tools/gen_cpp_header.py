"""Erzeugt den C++-Teil des Schemas für die Firmware aus s51design/schema.py.

Aufruf im Ordner designer/:  python tools/gen_cpp_header.py
Schreibt:
  firmware/lib/s51layout/src/s51_schema.h   Konstanten, Aufzählungen, Konfigurationstabelle
  firmware/lib/s51layout/src/s51_props.inc  Standardwerte und Decoder der Eigenschaften
Die Tests prüfen, dass die Dateien zum Schema passen.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from s51design import schema as S  # noqa: E402

OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "firmware", "lib", "s51layout", "src"))

BANNER = "// ERZEUGT von designer/tools/gen_cpp_header.py aus designer/s51design/schema.py.\n// Nicht von Hand ändern.\n"


def camel(key):
    return "".join(p[:1].upper() + p[1:] for p in key.split("_"))


def member(key):
    c = camel(key)
    return c[0].lower() + c[1:]


def c_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def color_expr(c):
    return f"Color{{0x{c[1:3]}, 0x{c[3:5]}, 0x{c[5:7]}}}"


def cpp_value(prop, value):
    t = prop.type
    if t == "color":
        return color_expr(value)
    if t.startswith("enum:"):
        enum_name = t[5:]
        return f"{camel(enum_name)}::{camel(value)}"
    if t == "bool":
        return "true" if value else "false"
    if t == "f32":
        return f"{float(value)!r}f"
    if t == "str":
        return c_str(value)
    return str(int(value))


def member_type(prop):
    t = prop.type
    return {
        "color": "Color", "u8": "uint8_t", "i16": "int16_t", "f32": "float",
        "str": "std::string", "bool": "bool",
    }.get(t) or camel(t[5:])


def gen_header():
    o = [BANNER, "#pragma once", "#include <cstddef>",
        "#include <cstdint>", "#include <string>", "", "namespace s51 {", ""]
    o += ["struct Color {", "  uint8_t r, g, b;",
          "  uint16_t to565() const { return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)); }",
          "  bool operator==(const Color& o) const { return r == o.r && g == o.g && b == o.b; }",
          "};", ""]
    o += [
        f'constexpr char kMagic[4] = {{\'S\', \'5\', \'1\', \'L\'}};',
        f"constexpr uint8_t kVersionMajor = {S.VERSION_MAJOR};",
        f"constexpr uint8_t kVersionMinor = {S.VERSION_MINOR};",
        f"constexpr uint16_t kHeaderSize = {S.HEADER_SIZE};",
        f"constexpr uint16_t kDisplayWidth = {S.DISPLAY_WIDTH};",
        f"constexpr uint16_t kDisplayHeight = {S.DISPLAY_HEIGHT};",
        f"constexpr uint32_t kMaxFileSize = {S.MAX_FILE_SIZE};",
        f"constexpr uint8_t kMaxScreens = {S.MAX_SCREENS};",
        f"constexpr uint16_t kMaxWidgetsPerScreen = {S.MAX_WIDGETS_PER_SCREEN};",
        f"constexpr uint8_t kRolePage = {S.ROLE_PAGE};",
        f"constexpr uint8_t kRoleNight = {S.ROLE_NIGHT};",
        f"constexpr uint8_t kRoleStartup = {S.ROLE_STARTUP};",
        f"constexpr uint8_t kNoPage = 0x{S.NO_PAGE:02X};",
        f"constexpr uint8_t kNoImage = 0x{S.NO_IMAGE:02X};",
        f"constexpr uint8_t kMaxImages = {S.MAX_IMAGES};",
        f"constexpr uint16_t kMaxImageSide = {S.MAX_IMAGE_SIDE};",
        f"constexpr uint8_t kImageFormatRaw = {S.IMAGE_FORMAT_RAW};",
        f"constexpr uint8_t kImageFormatRle = {S.IMAGE_FORMAT_RLE};",
        f"constexpr uint8_t kImageFlagAlpha = 0x{S.IMAGE_FLAG_ALPHA:02X};",
        f"constexpr uint8_t kFlagHidden = 0x{S.WFLAG_HIDDEN:02X};",
        f"constexpr uint8_t kFlagLocked = 0x{S.WFLAG_LOCKED:02X};",
        f"constexpr uint8_t kMetaName = {S.META_NAME};",
        f"constexpr uint8_t kMetaAuthor = {S.META_AUTHOR};",
        f"constexpr uint8_t kMetaCreated = {S.META_CREATED};",
        f"constexpr uint8_t kMetaTool = {S.META_TOOL};",
        "",
    ]
    o.append("enum class WidgetType : uint8_t {")
    o += [f"  {camel(t.key)} = {t.code},  // {t.label}" for t in S.WIDGET_TYPES]
    o += ["};", ""]
    o.append("constexpr bool isKnownWidgetType(uint8_t c) {")
    o.append("  return " + " || ".join(f"c == {t.code}" for t in S.WIDGET_TYPES) + ";")
    o += ["}", ""]
    o.append("enum class Source : uint8_t {")
    o += [f"  {camel(s.key)} = {s.code},  // {s.label}" for s in S.SOURCES]
    o += ["};", "", "constexpr bool isBoolSource(Source s) { return static_cast<uint8_t>(s) >= 64 && static_cast<uint8_t>(s) < 128; }", ""]
    o.append("enum class SourceKind : uint8_t { Number, Bool, Text, Time };")
    o.append("")
    o.append("// Art jeder Datenquelle und der Bereich der Demo-Werte (wie im Designer)")
    o.append("struct SourceDef {\n  Source source;\n  SourceKind kind;\n  float demoMin;\n  float demoMax;\n};")
    o.append("")
    o.append("constexpr SourceDef kSourceDefs[] = {")
    for s_ in S.SOURCES:
        o.append(f"  {{Source::{camel(s_.key)}, SourceKind::{camel(s_.kind)}, "
                 f"{float(s_.demo_min)!r}f, {float(s_.demo_max)!r}f}},")
    o += ["};", "", f"constexpr size_t kSourceCount = {len(S.SOURCES)};", ""]
    for name in ("icon", "font", "align", "orientation", "action"):
        o.append(f"enum class {camel(name)} : uint8_t {{")
        o += [f"  {camel(k)} = {c},  // {lbl}" for c, k, lbl in S.ENUMS[name]]
        o += ["};", ""]
    o.append("// Aktionen mit ihrem Namen in der tacho.cfg (Abschnitt [taster])")
    o.append("struct ActionDef {\n  Action action;\n  const char* cfgKey;\n};")
    o.append("")
    o.append("constexpr ActionDef kActionDefs[] = {")
    o += [f"  {{Action::{camel(a.key)}, {c_str(a.cfg)}}}," for a in S.ACTIONS]
    o += ["};", ""]
    o.append("enum class Prop : uint8_t {")
    o += [f"  {camel(p.key)} = {p.code},  // {p.label} ({p.type})" for p in S.PROPS]
    o += ["};", ""]

    # Konfiguration
    o.append("enum class CfgType : uint8_t { Int, Float, Bool, Str, Enum };")
    o.append("")
    o.append("enum class CfgKey : uint16_t {")
    o += [f"  {camel(c.section)}{camel(c.key)}," for c in S.CONFIG]
    o += ["  Count", "};", ""]
    o.append("struct CfgDef {\n  const char* section;\n  const char* key;\n  CfgType type;\n"
             "  const char* defaultValue;\n  float min;\n  float max;\n  const char* choices;  // durch | getrennt\n};")
    o.append("")
    o.append("// Felder eines Elements, eines je Eigenschaft (in WidgetData verwendet)")
    o.append("#define S51_WIDGET_FIELDS \\")
    o += [f"  {member_type(p)} {member(p.key)}; \\" for p in S.PROPS]
    o.append("  uint32_t propsSet[2];")
    o.append("")
    o.append("constexpr CfgDef kConfigDefs[] = {")
    for c in S.CONFIG:
        if c.type == "bool":
            d = "ja" if c.default else "nein"
        elif c.type == "float":
            d = f"{float(c.default):g}"
        else:
            d = str(c.default)
        mn = repr(float(c.min or 0))
        mx = repr(float(c.max or 0))
        o.append(f"  {{{c_str(c.section)}, {c_str(c.key)}, CfgType::{camel(c.type)}, {c_str(d)}, "
                 f"{mn}f, {mx}f, {c_str('|'.join(c.choices))}}},")
    o += ["};", "", "}  // namespace s51", ""]
    return "\n".join(o)


def gen_props_inc():
    o = [BANNER, "// Wird in s51_layout.cpp eingebunden.", ""]
    o.append("namespace s51 {")
    o.append("")
    o.append("static void applyDefaults(WidgetData& w) {")
    o += [f"  w.{member(p.key)} = {cpp_value(p, p.default)};" for p in S.PROPS]
    o.append("  switch (w.type) {")
    for t in S.WIDGET_TYPES:
        o.append(f"    case WidgetType::{camel(t.key)}:")
        for k, v in t.overrides.items():
            o.append(f"      w.{member(k)} = {cpp_value(S.PROP_BY_KEY[k], v)};")
        o.append("      break;")
    o += ["    default:", "      break;", "  }", "}", ""]

    o.append("// Gibt false zurück, wenn die Länge nicht zum Typ passt. Unbekannte Nummern werden übersprungen.")
    o.append("static bool decodeProp(uint8_t code, const uint8_t* p, uint8_t len, WidgetData& w) {")
    o.append("  switch (code) {")
    for prop in S.PROPS:
        m = member(prop.key)
        t = prop.type
        o.append(f"    case {prop.code}:  // {prop.key}")
        if t == "color":
            o.append(f"      if (len != 3) return false;\n      w.{m} = Color{{p[0], p[1], p[2]}};")
        elif t == "u8":
            o.append(f"      if (len != 1) return false;\n      w.{m} = p[0];")
        elif t == "bool":
            o.append(f"      if (len != 1) return false;\n      w.{m} = p[0] != 0;")
        elif t == "i16":
            o.append(f"      if (len != 2) return false;\n      w.{m} = static_cast<int16_t>(p[0] | (p[1] << 8));")
        elif t == "f32":
            o.append(f"      if (len != 4) return false;\n      w.{m} = readF32(p);")
        elif t == "str":
            o.append(f"      w.{m}.assign(reinterpret_cast<const char*>(p), len);")
        elif t.startswith("enum:"):
            o.append(f"      if (len != 1) return false;\n      w.{m} = static_cast<{camel(t[5:])}>(p[0]);")
        o.append(f"      w.propsSet[{prop.code // 32}] |= (1u << {prop.code % 32});")
        o.append("      return true;")
    o += ["    default:", "      return true;", "  }", "}", "", "}  // namespace s51", ""]
    return "\n".join(o)


def generated_files():
    return {"s51_schema.h": gen_header(), "s51_props.inc": gen_props_inc()}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, text in generated_files().items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("geschrieben:", os.path.relpath(path))


if __name__ == "__main__":
    main()
