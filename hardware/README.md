# hardware/ — case, wiring, power

[← Main README](../README.md) · Firmware pins: [firmware/](../firmware/README.md)

The physical pendant: a translucent 3D-printed case (Ø42 × ~23 mm, integrated lanyard tab, mic holes, USB-C notch) around the XIAO ESP32-S3 Sense, one WS2812B LED behind the frosted shell, LiPo or mini power-bank inside.

## Contents

- **[`3dprint/pendant.py`](3dprint/pendant.py)** — the parametric generator (trimesh): body (Ø42 wall 2 mm, lanyard tab + Ø4.4 hole, USB-C notch) and friction-fit lid (Ø37.4 lip in a Ø38 cavity, 3 mic holes). It prints watertightness on export as a self-check.
- **`3dprint/encore_body.stl` + `encore_lid.stl`** — the generated meshes, committed so the fablab needs nothing but the files. **Rule (CLAUDE.md): never edit the STLs, edit `pendant.py` and regenerate.** Run it from inside `3dprint/` (it exports to the current directory) — boolean ops need a backend (`pip install manifold3d`).
- **[`wiring.md`](wiring.md)** — full hookup: LiPo → BAT pads (on-board charge circuit, USB-C), WS2812B → 3V3/GND/GPIO2, touch pad (copper tape inside the lid) → GPIO1, on-board PDM mic (camera stays unplugged).

## Print settings (42 fablab)

Transparent/translucent PETG or PLA, 0.2 mm layers, 2–3 perimeters, no supports, ~1h30. Sand the inside for the diffuse-glow LED effect.

## Tasks to be accomplished (before the 25th — Jade)

- [ ] Print `encore_body.stl` + `encore_lid.stl` at the 42 fablab (ask staff for slicer help).
- [ ] Buy the WS2812B (1-pixel breakout or 8-LED mini ring) + lanyard/cord.
- [ ] Power: solder the LiPo to the BAT pads, or fall back to a mini USB-C power bank in the case.
- [ ] Assemble: copper touch pad wired to GPIO1, LED on GPIO2, verify against `wiring.md`.
- [ ] Validate 1 h of streaming on battery (test plan).

**Roadmap (post-hackathon)**: autonomous listening (deep sleep + music-onset wake via RMS + spectral regularity), final enclosure, multi-night battery.
