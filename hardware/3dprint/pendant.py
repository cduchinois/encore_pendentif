#!/usr/bin/env python3
"""Encore heart pendant — parametric generator (edit me, never the STLs).

Two-part heart case for the Seeed XIAO ESP32-S3 Sense + LiPo battery:
  encore_body.stl   back shell: cavity, USB-C side slot, integrated bail loop
  encore_lid.stl    front lid: friction lip, engraved pulse wave, mic holes

Component layout (decided here, documented in hardware/README.md):
  - LiPo 502030 (32 x 20.5 x 5.3) lies HORIZONTAL across the widest band
  - XIAO stacked ON TOP of it (foam tape), component side toward the lid,
    USB-C edge against the right lobe wall, reachable through a slot
  - header pins are assumed CLIPPED FLUSH (see README); camera removed
  - pulse wave is ENGRAVED in the lid: prints crisply face-down on the bed,
    and the thinned wall glows when the LED lights the inside
  - mic holes in the lid sit over the PDM mic of the Sense board

Run:  python pendant.py            regenerate STLs (+ fit report)
      python pendant.py --render   also write fit_preview.png
Requires: pip install trimesh shapely manifold3d numpy (matplotlib to render).
"""
import argparse
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, box as shp_box
from trimesh.creation import extrude_polygon, cylinder, box

# ---------------- components (mm, datasheets + margin) ----------------
BAT_L, BAT_W, BAT_T = 32.0, 20.5, 5.3      # LiPo LP502030, lying flat
TAPE = 0.8                                  # foam tape between battery & board
PCB_L, PCB_W, PCB_T = 21.0, 17.8, 1.2       # XIAO ESP32-S3, pins clipped flush
TOP_H = 3.4                                 # tallest top component (USB-C)
USB_W, USB_H = 9.0, 3.4                     # USB-C connector on the PCB
WIRE_GAP = 3.0                              # slack for the battery wires (left)

WALL = 2.2                                  # shell wall
FLOOR = 2.2                                 # back shell floor
BACK_D = 15.0                               # back shell depth
LID_FACE = 2.6                              # lid front wall
LIP_D = 2.4                                 # friction lip engagement
CLEAR = 0.30                                # lip-to-cavity fit clearance
PULSE_DEPTH = 1.2                           # pulse engraving depth in the lid
LOOP_RO, LOOP_RI, LOOP_T = 4.6, 2.3, 6.0    # bail ring (chain hole along Z)


Y_OFF = 6.0                                 # stack sits in the widest band


def heart_poly(d):
    """Full "boxy" heart: 45-deg rotated square (half-diagonal d) + two lobe
    circles on its upper edges. Much roomier than the classic curve — it has
    to swallow a 32 mm-wide battery. Tip and cusps lightly rounded."""
    from shapely.geometry import Point
    diamond = Polygon([(0, -d), (d, 0), (0, d), (-d, 0)])
    r = d / np.sqrt(2)
    lobes = [Point(sgn * d / 2, d / 2).buffer(r, quad_segs=64) for sgn in (1, -1)]
    p = diamond.union(lobes[0]).union(lobes[1])
    return p.buffer(-1.2, quad_segs=32).buffer(1.2, quad_segs=32).buffer(0)


def component_rects(cavity):
    """Battery + board footprints; the board hugs the right cavity wall."""
    bat = shp_box(-BAT_L / 2, Y_OFF - BAT_W / 2, BAT_L / 2, Y_OFF + BAT_W / 2)
    by = Y_OFF                               # board vertical band center
    # wall x at the tightest point of the board's whole y-band, 1.0 mm gap
    x_right = 1e9
    for yy in np.linspace(by - PCB_W / 2, by + PCB_W / 2, 12):
        xs = LineString([(0, yy), (200, yy)]).intersection(cavity.exterior)
        pts = [pt.x for pt in getattr(xs, "geoms", [xs])]
        if pts:
            x_right = min(x_right, max(pts))
    x_right -= 1.0
    board = shp_box(x_right - PCB_L, by - PCB_W / 2, x_right, by + PCB_W / 2)
    wires = shp_box(-BAT_L / 2 - WIRE_GAP, Y_OFF - 7, -BAT_L / 2, Y_OFF + 5)
    return bat, board, wires, x_right, by


def find_scale():
    """Smallest heart whose cavity holds battery + board + wire slack."""
    for s in np.arange(19.0, 31.0, 0.25):
        cavity = heart_poly(s).buffer(-WALL)
        bat, board, wires, _, _ = component_rects(cavity)
        if cavity.contains(bat.union(board).union(wires).buffer(0.4)):
            return s
    raise SystemExit("no scale fits — check component dims")


def tz(mesh, dz):
    mesh.apply_translation([0, 0, dz])
    return mesh


def build():
    s = find_scale()
    heart = heart_poly(s)
    cavity = heart.buffer(-WALL)
    bat, board, wires, x_right, by = component_rects(cavity)
    minx, miny, maxx, maxy = heart.bounds
    z_pcb_top = FLOOR + BAT_T + TAPE + PCB_T

    # ---------------- back shell ----------------
    body = extrude_polygon(heart, BACK_D)
    pocket = tz(extrude_polygon(cavity, BACK_D), FLOOR)
    usb_slot = box(extents=[12, USB_W + 3.0, USB_H + 2.6])
    usb_slot.apply_translation([x_right + 6, by, z_pcb_top + USB_H / 2])
    cleft_y = s - 1.0                        # dip between the two lobes
    ring_c = [0, cleft_y + LOOP_RO * 0.55]
    ring = cylinder(radius=LOOP_RO, height=LOOP_T, sections=96)
    ring.apply_translation(ring_c + [FLOOR + LOOP_T / 2])
    bridge = box(extents=[7.5, 4.5, LOOP_T])
    bridge.apply_translation([0, cleft_y + 0.8, FLOOR + LOOP_T / 2])
    hole = cylinder(radius=LOOP_RI, height=80, sections=96)
    hole.apply_translation(ring_c + [0])
    # thumb notch at the tip rim so the friction-fit lid can be pried open
    notch = box(extents=[12, 6, 2.6])
    notch.apply_translation([0, miny + 2.0, BACK_D - 1.3])
    body = trimesh.boolean.union([body, ring, bridge])
    body = trimesh.boolean.difference([body, pocket, usb_slot, hole, notch])

    # ---------------- front lid ----------------
    lip_ring = cavity.buffer(-CLEAR).difference(cavity.buffer(-CLEAR - 2.0))
    lid = trimesh.boolean.union([
        extrude_polygon(heart, LID_FACE),
        tz(extrude_polygon(lip_ring, LIP_D), LID_FACE),
    ])
    # engraved pulse wave across the front face (z=0 side -> prints on the bed)
    w = maxx - minx
    pts = [(-.44, .02), (-.26, .02), (-.20, .10), (-.14, -.06), (-.07, .02),
           (-.01, .02), (.05, .30), (.12, -.26), (.18, .02), (.26, .02),
           (.32, .08), (.38, .02), (.44, .02)]
    pulse = LineString([(px * w, py * w * 0.55 + 2.0) for px, py in pts]).buffer(1.15)
    pulse = pulse.intersection(heart.buffer(-3.2)).buffer(0)
    cuts = [tz(extrude_polygon(pulse, PULSE_DEPTH + 0.01), -0.005)]
    # mic holes over the Sense PDM mic (lid is mirrored when closed: x -> -x)
    mic_c = (-(x_right - PCB_L / 2), by + 4.5)
    for dx, dy in [(0, 0), (2.6, -1.6), (-2.6, -1.6)]:
        h = cylinder(radius=0.8, height=12, sections=48)
        h.apply_translation([mic_c[0] + dx, mic_c[1] + dy, 1])
        cuts.append(h)
    lid = trimesh.boolean.difference([lid] + cuts)

    # ---------------- dummy components (fit render only) ----------------
    def rbox(g, h, z):
        return tz(extrude_polygon(Polygon(g.exterior.coords), h), z)
    d_bat = rbox(bat, BAT_T, FLOOR + 0.1)
    d_pcb = rbox(board, PCB_T, FLOOR + 0.1 + BAT_T + TAPE)
    d_usb = box(extents=[7.5, USB_W, USB_H])
    d_usb.apply_translation([x_right - 3.75, by, z_pcb_top + USB_H / 2])
    dummies = {"battery": d_bat, "board": d_pcb, "usb": d_usb}

    print(f"d {s:.2f} -> heart {maxx - minx:.1f} x {maxy - miny:.1f} mm, "
          f"closed depth {BACK_D + LID_FACE:.1f} mm, bail adds ~{LOOP_RO * 1.3:.0f} mm top")
    print(f"cavity depth {BACK_D - FLOOR:.1f} vs component stack "
          f"{BAT_T + TAPE + PCB_T + TOP_H:.1f} mm; USB slot center z "
          f"{z_pcb_top + USB_H / 2:.1f} mm")
    return body, lid, dummies


def render(body, lid, dummies, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def panel(ax, meshes, title, elev, azim, r=42, zc=10):
        """Painter-sorted composite render of several (mesh, color) pairs."""
        allf, allc = [], []
        light = np.array([.35, .25, .9]); light = light / np.linalg.norm(light)
        for mesh, color in meshes:
            f = mesh.vertices[mesh.faces]
            lam = .45 + .55 * np.clip(mesh.face_normals @ light, 0, 1)
            allf.append(f)
            allc.append(np.clip(np.array(color) * lam[:, None], 0, 1))
        F = np.concatenate(allf); C = np.concatenate(allc)
        el, az = np.radians(elev), np.radians(azim)
        view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        order = np.argsort(F.mean(axis=1) @ view)
        ax.add_collection3d(Poly3DCollection(F[order], facecolors=C[order],
                                             edgecolor="none"))
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(zc - r, zc + r)
        ax.view_init(elev=elev, azim=azim); ax.set_title(title, fontsize=11)

    def closed_lid():
        m = lid.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
        tz(m, BACK_D + LID_FACE)
        return m

    grey, sil = (.80, .82, .85), (.70, .70, .74)
    grn, blk = (.16, .45, .26), (.22, .22, .24)
    comp = [(dummies["battery"], sil), (dummies["board"], grn), (dummies["usb"], blk)]
    fig = plt.figure(figsize=(16, 10), dpi=110)

    panel(fig.add_subplot(2, 3, 1, projection="3d"),
          [(body, grey), (closed_lid(), grey)],
          "closed — front-right (pulse face, bail, USB slot)", 28, -118)
    panel(fig.add_subplot(2, 3, 2, projection="3d"),
          [(body, grey)] + comp,
          "open — LiPo under XIAO (stacked), USB at the slot", 38, -62)
    panel(fig.add_subplot(2, 3, 3, projection="3d"),
          [(body, grey)] + comp,
          "open — top view (clearances)", 89, -90)
    panel(fig.add_subplot(2, 3, 4, projection="3d"),
          [(lid, grey)],
          "lid outer face — pulse engraving + mic holes", 55, -80, 36, 2)
    m = lid.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
    panel(fig.add_subplot(2, 3, 5, projection="3d"),
          [(m, grey)],
          "lid inner face — friction lip", 55, -90, 36, -2)
    eb = [(body, grey)]
    for (d, c), dz in zip(comp, (12, 22, 22)):
        dc = d.copy(); eb.append((tz(dc, dz), c))
    eb.append((tz(closed_lid(), 28), grey))
    panel(fig.add_subplot(2, 3, 6, projection="3d"), eb,
          "exploded — body / battery / board / lid", 18, -58, 50, 25)

    fig.suptitle("Encore heart pendant — fit check (XIAO ESP32-S3 Sense + LiPo 502030)",
                 fontsize=14)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("render ->", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    body, lid, dummies = build()
    for m, name in [(body, "encore_body.stl"), (lid, "encore_lid.stl")]:
        try:
            m.fix_normals()          # needs scipy; manifold output is already sane
        except BaseException:
            pass
        print(name, "watertight:", m.is_watertight, "| dims:", np.round(m.extents, 1))
        m.export(name)
    if args.render:
        render(body, lid, dummies, "fit_preview.png")


if __name__ == "__main__":
    main()
