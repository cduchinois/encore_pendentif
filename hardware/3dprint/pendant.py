#!/usr/bin/env python3
"""Encore heart pendant — parametric generator (edit me, never the STLs).

Two-part ROUND heart case for the Seeed XIAO ESP32-S3 Sense + LiPo battery:
  encore_body.stl   back shell: cavity, USB-C side slot, integrated bail loop,
                    rim rebate the lid drops into, thumb notch at the tip
  encore_lid.stl    drop-in front plate: RAISED pulse-wave relief, mic holes,
                    friction bumps on the edge

Shape: the classic implicit heart (x^2+y^2-1)^3 = x^2*y^3 — full lobes,
bulging flanks, soft tip (much rounder than a diamond+circles heart).
The generator auto-scales the heart and auto-places the component stack:
  - LiPo 502030 (32 x 20.5 x 5.3) lies flat across the widest band
  - XIAO stacked on top (foam tape), component side out, USB-C edge against
    the right wall, reachable through a slot (charge without opening)
  - header pins clipped flush; camera removed
No texture/color at this stage — geometry only.

Run:  python pendant.py            regenerate STLs (+ fit report)
      python pendant.py --render   also write fit_preview.png
Requires: pip install trimesh shapely manifold3d numpy (matplotlib to render).
"""
import argparse
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, Point, box as shp_box
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
BACK_D = 16.0                               # back shell depth
RIM = 1.3                                   # remaining outer rim at the rebate
REBATE = 2.8                                # depth of the lid seat
LID_T = 2.6                                 # lid plate thickness
PULSE_H = 1.6                               # raised pulse relief height
CLEAR = 0.25                                # lid-to-rebate clearance
BUMP_R = 0.45                               # friction bumps on the lid edge
LOOP_RO, LOOP_RI, LOOP_T = 4.6, 2.3, 6.0    # bail ring (chain hole along Z)


def heart_poly(scale, n_ang=720):
    """Implicit heart (x^2+y^2-1)^3 = x^2 y^3, ray-sampled from an interior
    point (star-shaped there), scaled to `scale` mm of width."""
    f = lambda x, y: (x * x + y * y - 1) ** 3 - x * x * y ** 3
    cx, cy = 0.0, 0.15
    pts = []
    rr = np.linspace(1e-3, 1.9, 600)
    for th in np.linspace(0, 2 * np.pi, n_ang, endpoint=False):
        xs, ys = cx + rr * np.cos(th), cy + rr * np.sin(th)
        vals = f(xs, ys)
        idx = np.argmax(vals > 0)          # first crossing inside -> outside
        lo, hi = rr[idx - 1], rr[idx]
        for _ in range(30):                # bisection refine
            mid = (lo + hi) / 2
            if f(cx + mid * np.cos(th), cy + mid * np.sin(th)) > 0:
                hi = mid
            else:
                lo = mid
        pts.append((cx + lo * np.cos(th), cy + lo * np.sin(th)))
    p = Polygon(pts).buffer(0)
    minx, miny, maxx, maxy = p.bounds
    s = scale / (maxx - minx)
    pts = [((x - (minx + maxx) / 2) * s, (y - (miny + maxy) / 2) * s) for x, y in pts]
    return Polygon(pts).buffer(0)


def best_band(cavity):
    """Vertical center for the stack: deepest-margin fit for the battery."""
    best, best_m = None, -1
    for yc in np.arange(-10, 16, 0.5):
        bat = shp_box(-BAT_L / 2, yc - BAT_W / 2, BAT_L / 2, yc + BAT_W / 2)
        if cavity.contains(bat):
            m = cavity.exterior.distance(bat)
            if m > best_m:
                best, best_m = yc, m
    return best


def component_rects(cavity):
    yc = best_band(cavity)
    if yc is None:
        return None
    bat = shp_box(-BAT_L / 2, yc - BAT_W / 2, BAT_L / 2, yc + BAT_W / 2)
    x_right = 1e9                            # tightest wall over the board band
    for yy in np.linspace(yc - PCB_W / 2, yc + PCB_W / 2, 12):
        xs = LineString([(0, yy), (200, yy)]).intersection(cavity.exterior)
        pp = [pt.x for pt in getattr(xs, "geoms", [xs])]
        if pp:
            x_right = min(x_right, max(pp))
    x_right -= 1.0
    board = shp_box(x_right - PCB_L, yc - PCB_W / 2, x_right, yc + PCB_W / 2)
    wires = shp_box(-BAT_L / 2 - WIRE_GAP, yc - 6, -BAT_L / 2, yc + 6)
    return bat, board, wires, x_right, yc


def find_fit():
    for scale in np.arange(46, 72, 0.5):
        heart = heart_poly(scale, n_ang=360)
        cavity = heart.buffer(-WALL)
        r = component_rects(cavity)
        if r is None:
            continue
        bat, board, wires, _, _ = r
        if cavity.contains(bat.union(board).union(wires).buffer(0.4)):
            return scale
    raise SystemExit("no scale fits — check component dims")


def tz(mesh, dz):
    mesh.apply_translation([0, 0, dz])
    return mesh


def build():
    scale = find_fit()
    heart = heart_poly(scale)
    cavity = heart.buffer(-WALL)
    bat, board, wires, x_right, yc = component_rects(cavity)
    minx, miny, maxx, maxy = heart.bounds
    z_pcb_top = FLOOR + BAT_T + TAPE + PCB_T
    seat = heart.buffer(-RIM)                # rebate opening the lid drops into

    # ---------------- back shell ----------------
    body = extrude_polygon(heart, BACK_D)
    pocket = tz(extrude_polygon(cavity, BACK_D), FLOOR)
    rebate = tz(extrude_polygon(seat, REBATE + 0.01), BACK_D - REBATE)
    usb_slot = box(extents=[14, USB_W + 3.0, USB_H + 2.6])
    usb_slot.apply_translation([x_right + 7, yc, z_pcb_top + USB_H / 2])
    # bail ring bridging the cleft, chain hole along Z
    cleft_y = max(p[1] for p in heart.exterior.coords if abs(p[0]) < 0.7)
    ring_c = [0, cleft_y + LOOP_RO * 0.55]
    ring = cylinder(radius=LOOP_RO, height=LOOP_T, sections=96)
    ring.apply_translation(ring_c + [FLOOR + LOOP_T / 2])
    bridge = box(extents=[8.0, 5.0, LOOP_T])
    bridge.apply_translation([0, cleft_y + 1.0, FLOOR + LOOP_T / 2])
    hole = cylinder(radius=LOOP_RI, height=80, sections=96)
    hole.apply_translation(ring_c + [0])
    # thumb notch at the tip rim so the lid can be pried out
    notch = box(extents=[12, 6, 2.6])
    notch.apply_translation([0, miny + 2.0, BACK_D - 1.3])
    body = trimesh.boolean.union([body, ring, bridge])
    body = trimesh.boolean.difference([body, pocket, rebate, usb_slot, hole, notch])

    # ---------------- front lid: drop-in plate, raised pulse ----------------
    plate_poly = seat.buffer(-CLEAR)
    lid = extrude_polygon(plate_poly, LID_T)
    # raised pulse-wave relief on the front (prints flat, relief up)
    w = maxx - minx
    pts = [(-.46, .02), (-.28, .02), (-.22, .10), (-.16, -.06), (-.09, .02),
           (-.03, .02), (.03, .34), (.10, -.30), (.16, .02), (.24, .02),
           (.30, .09), (.36, .02), (.46, .02)]
    pulse = LineString([(px * w, py * w * 0.60 + 1.0) for px, py in pts]).buffer(1.6)
    pulse = pulse.intersection(plate_poly.buffer(-1.8)).buffer(0)
    lid = trimesh.boolean.union([lid, tz(extrude_polygon(pulse, PULSE_H + 0.01), LID_T - 0.01)])
    # friction bumps around the plate edge (crush ribs for the fit)
    coords = list(plate_poly.exterior.coords)
    bumps = []
    for i in np.linspace(0, len(coords) - 1, 7)[:-1].astype(int):
        b = cylinder(radius=BUMP_R, height=LID_T - 0.6, sections=32)
        bumps.append(tz(b.apply_translation(list(coords[i]) + [0]) or b, LID_T / 2))
    lid = trimesh.boolean.union([lid] + bumps)
    # mic holes over the Sense PDM mic (no mirror: lid drops in as printed)
    cuts = []
    mic_c = (x_right - PCB_L / 2, yc + 4.5)
    for dx, dy in [(0, 0), (2.6, -1.6), (-2.6, -1.6)]:
        h = cylinder(radius=0.8, height=16, sections=48)
        h.apply_translation([mic_c[0] + dx, mic_c[1] + dy, 2])
        cuts.append(h)
    lid = trimesh.boolean.difference([lid] + cuts)

    # ---------------- dummy components (fit render only) ----------------
    def rbox(g, h, z):
        return tz(extrude_polygon(Polygon(g.exterior.coords), h), z)
    d_bat = rbox(bat, BAT_T, FLOOR + 0.1)
    d_pcb = rbox(board, PCB_T, FLOOR + 0.1 + BAT_T + TAPE)
    d_usb = box(extents=[7.5, USB_W, USB_H])
    d_usb.apply_translation([x_right - 3.75, yc, z_pcb_top + USB_H / 2])
    dummies = {"battery": d_bat, "board": d_pcb, "usb": d_usb}

    print(f"scale {scale:.1f} -> heart {maxx - minx:.1f} x {maxy - miny:.1f} mm, "
          f"depth {BACK_D:.1f} (+{PULSE_H} relief), stack band yc={yc:.1f}")
    print(f"cavity depth {BACK_D - REBATE - FLOOR:.1f} usable vs stack "
          f"{BAT_T + TAPE + PCB_T + TOP_H:.1f} mm; USB slot z center "
          f"{z_pcb_top + USB_H / 2:.1f}")
    return body, lid, dummies


def render(body, lid, dummies, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def panel(ax, meshes, title, elev, azim, r=44, zc=8):
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
        return tz(m, BACK_D - REBATE)

    grey, sil = (.78, .79, .81), (.68, .68, .72)
    grn, blk = (.16, .45, .26), (.22, .22, .24)
    comp = [(dummies["battery"], sil), (dummies["board"], grn), (dummies["usb"], blk)]
    fig = plt.figure(figsize=(16, 10), dpi=110)

    panel(fig.add_subplot(2, 3, 1, projection="3d"),
          [(body, grey), (closed_lid(), grey)],
          "closed — raised pulse relief, bail, USB slot", 32, -105)
    panel(fig.add_subplot(2, 3, 2, projection="3d"),
          [(body, grey)] + comp,
          "open — LiPo under XIAO (stacked), USB at the slot", 38, -62)
    panel(fig.add_subplot(2, 3, 3, projection="3d"),
          [(body, grey)] + comp,
          "open — top view (clearances + rim rebate)", 89, -90)
    panel(fig.add_subplot(2, 3, 4, projection="3d"),
          [(lid, grey)],
          "lid — drop-in plate, raised pulse, mic holes", 55, -80, 36, 2)
    panel(fig.add_subplot(2, 3, 5, projection="3d"),
          [(body, grey), (closed_lid(), grey)],
          "closed — front view", 88, -90)
    eb = [(body, grey)]
    for (d, c), dz in zip(comp, (12, 22, 22)):
        dc = d.copy(); eb.append((tz(dc, dz), c))
    lm = lid.copy(); eb.append((tz(lm, 38), grey))
    panel(fig.add_subplot(2, 3, 6, projection="3d"), eb,
          "exploded — body / battery / board / lid", 18, -58, 52, 25)

    fig.suptitle("Encore heart pendant v2 — round heart, raised pulse "
                 "(XIAO ESP32-S3 Sense + LiPo 502030) — no texture/color yet",
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
