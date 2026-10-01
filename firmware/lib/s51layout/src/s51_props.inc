// ERZEUGT von designer/tools/gen_cpp_header.py aus designer/s51design/schema.py.
// Nicht von Hand ändern.

// Wird in s51_layout.cpp eingebunden.

namespace s51 {

static void applyDefaults(WidgetData& w) {
  w.source = Source::None;
  w.color = Color{0xF1, 0xEF, 0xE8};
  w.bgColor = Color{0x00, 0x00, 0x00};
  w.font = Font::Sans;
  w.size = 24;
  w.align = Align::Center;
  w.text = "";
  w.decimals = 0;
  w.unit = "";
  w.min = 0.0f;
  w.max = 100.0f;
  w.warnAbove = 0.0f;
  w.warnColor = Color{0xEF, 0x9F, 0x27};
  w.critAbove = 0.0f;
  w.critColor = Color{0xE2, 0x4B, 0x4A};
  w.segments = 0;
  w.orientation = Orientation::Horizontal;
  w.startAngle = 135;
  w.endAngle = 405;
  w.thickness = 12;
  w.radius = 0;
  w.icon = Icon::None;
  w.onColor = Color{0x63, 0x99, 0x22};
  w.offColor = Color{0x2C, 0x2C, 0x2A};
  w.blink = false;
  w.format = "HH:MM";
  w.borderColor = Color{0x00, 0x00, 0x00};
  w.borderWidth = 0;
  w.image = 255;
  w.fromZero = false;
  w.action = Action::None;
  switch (w.type) {
    case WidgetType::Text:
      w.text = "Text";
      break;
    case WidgetType::Value:
      w.source = Source::Speed;
      w.size = 64;
      w.font = Font::Segment;
      break;
    case WidgetType::Bar:
      w.source = Source::Rpm;
      w.max = 8000.0f;
      w.segments = 24;
      w.color = Color{0x1D, 0x9E, 0x75};
      w.bgColor = Color{0x2C, 0x2C, 0x2A};
      w.warnAbove = 5500.0f;
      w.critAbove = 7000.0f;
      break;
    case WidgetType::Gauge:
      w.source = Source::Speed;
      w.max = 80.0f;
      w.color = Color{0x1D, 0x9E, 0x75};
      w.bgColor = Color{0x2C, 0x2C, 0x2A};
      break;
    case WidgetType::Indicator:
      w.source = Source::Neutral;
      w.icon = Icon::Neutral;
      break;
    case WidgetType::Rect:
      w.color = Color{0x2C, 0x2C, 0x2A};
      break;
    case WidgetType::Image:
      break;
    case WidgetType::Button:
      w.action = Action::PlayPause;
      w.icon = Icon::PlayPause;
      w.bgColor = Color{0x2C, 0x2C, 0x2A};
      w.radius = 12;
      w.font = Font::SansBold;
      w.size = 16;
      break;
    default:
      break;
  }
}

// Gibt false zurück, wenn die Länge nicht zum Typ passt. Unbekannte Nummern werden übersprungen.
static bool decodeProp(uint8_t code, const uint8_t* p, uint8_t len, WidgetData& w) {
  switch (code) {
    case 1:  // source
      if (len != 1) return false;
      w.source = static_cast<Source>(p[0]);
      w.propsSet[0] |= (1u << 1);
      return true;
    case 2:  // color
      if (len != 3) return false;
      w.color = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 2);
      return true;
    case 3:  // bg_color
      if (len != 3) return false;
      w.bgColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 3);
      return true;
    case 4:  // font
      if (len != 1) return false;
      w.font = static_cast<Font>(p[0]);
      w.propsSet[0] |= (1u << 4);
      return true;
    case 5:  // size
      if (len != 1) return false;
      w.size = p[0];
      w.propsSet[0] |= (1u << 5);
      return true;
    case 6:  // align
      if (len != 1) return false;
      w.align = static_cast<Align>(p[0]);
      w.propsSet[0] |= (1u << 6);
      return true;
    case 7:  // text
      w.text.assign(reinterpret_cast<const char*>(p), len);
      w.propsSet[0] |= (1u << 7);
      return true;
    case 8:  // decimals
      if (len != 1) return false;
      w.decimals = p[0];
      w.propsSet[0] |= (1u << 8);
      return true;
    case 9:  // unit
      w.unit.assign(reinterpret_cast<const char*>(p), len);
      w.propsSet[0] |= (1u << 9);
      return true;
    case 10:  // min
      if (len != 4) return false;
      w.min = readF32(p);
      w.propsSet[0] |= (1u << 10);
      return true;
    case 11:  // max
      if (len != 4) return false;
      w.max = readF32(p);
      w.propsSet[0] |= (1u << 11);
      return true;
    case 12:  // warn_above
      if (len != 4) return false;
      w.warnAbove = readF32(p);
      w.propsSet[0] |= (1u << 12);
      return true;
    case 13:  // warn_color
      if (len != 3) return false;
      w.warnColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 13);
      return true;
    case 14:  // crit_above
      if (len != 4) return false;
      w.critAbove = readF32(p);
      w.propsSet[0] |= (1u << 14);
      return true;
    case 15:  // crit_color
      if (len != 3) return false;
      w.critColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 15);
      return true;
    case 16:  // segments
      if (len != 1) return false;
      w.segments = p[0];
      w.propsSet[0] |= (1u << 16);
      return true;
    case 17:  // orientation
      if (len != 1) return false;
      w.orientation = static_cast<Orientation>(p[0]);
      w.propsSet[0] |= (1u << 17);
      return true;
    case 18:  // start_angle
      if (len != 2) return false;
      w.startAngle = static_cast<int16_t>(p[0] | (p[1] << 8));
      w.propsSet[0] |= (1u << 18);
      return true;
    case 19:  // end_angle
      if (len != 2) return false;
      w.endAngle = static_cast<int16_t>(p[0] | (p[1] << 8));
      w.propsSet[0] |= (1u << 19);
      return true;
    case 20:  // thickness
      if (len != 1) return false;
      w.thickness = p[0];
      w.propsSet[0] |= (1u << 20);
      return true;
    case 21:  // radius
      if (len != 1) return false;
      w.radius = p[0];
      w.propsSet[0] |= (1u << 21);
      return true;
    case 22:  // icon
      if (len != 1) return false;
      w.icon = static_cast<Icon>(p[0]);
      w.propsSet[0] |= (1u << 22);
      return true;
    case 23:  // on_color
      if (len != 3) return false;
      w.onColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 23);
      return true;
    case 24:  // off_color
      if (len != 3) return false;
      w.offColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 24);
      return true;
    case 25:  // blink
      if (len != 1) return false;
      w.blink = p[0] != 0;
      w.propsSet[0] |= (1u << 25);
      return true;
    case 26:  // format
      w.format.assign(reinterpret_cast<const char*>(p), len);
      w.propsSet[0] |= (1u << 26);
      return true;
    case 27:  // border_color
      if (len != 3) return false;
      w.borderColor = Color{p[0], p[1], p[2]};
      w.propsSet[0] |= (1u << 27);
      return true;
    case 28:  // border_width
      if (len != 1) return false;
      w.borderWidth = p[0];
      w.propsSet[0] |= (1u << 28);
      return true;
    case 29:  // image
      if (len != 1) return false;
      w.image = p[0];
      w.propsSet[0] |= (1u << 29);
      return true;
    case 30:  // from_zero
      if (len != 1) return false;
      w.fromZero = p[0] != 0;
      w.propsSet[0] |= (1u << 30);
      return true;
    case 31:  // action
      if (len != 1) return false;
      w.action = static_cast<Action>(p[0]);
      w.propsSet[0] |= (1u << 31);
      return true;
    default:
      return true;
  }
}

}  // namespace s51
