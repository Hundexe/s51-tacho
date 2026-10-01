// Leere Hardware-Funktionen, damit LovyanGFX am PC ohne Display gebaut werden kann.
// Gezeichnet wird nur in Sprites im Speicher.
#define LGFX_USE_V1
#include <LovyanGFX.hpp>

namespace lgfx {
inline namespace v1 {
void delay(unsigned long) {}
void gpio_hi(uint32_t) {}
void gpio_lo(uint32_t) {}
void pinMode(int_fast16_t, pin_mode_t) {}
}  // namespace v1
}  // namespace lgfx
