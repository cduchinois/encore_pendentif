# Wiring — Encore pendant

- LiPo 3.7 V 500-600 mAh -> BAT+ / BAT- pads under the XIAO (charge circuit is on-board, USB-C charges it). No-solder fallback: mini USB-C power bank.
- WS2812B: VCC -> 3V3 (ok at low brightness) or BAT+, GND -> GND, DIN -> GPIO2.
- Touch pad: copper tape inside the lid front -> wire -> GPIO1 (T1). No resistor needed.
- PDM mic is on-board (Sense daughter board). Camera stays unplugged.
- Case: hardware/3dprint/encore_body.stl + encore_lid.stl (regenerate via pendant.py).
