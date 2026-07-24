#!/usr/bin/env python3
"""Encore heart pendant v3 — parametric generator (edit me, never the STLs).

A real 3D heart — emoji-like silhouette, softly rounded edges — split into
TWO HOLLOW SHELLS (front + back) at a clean side seam, not a lid:
  encore_back.stl    back shell: fitted pocket, snap lip + ridge, half bail
  encore_front.stl   front shell: raised pulse relief, snap channel + groove,
                     mic holes, USB-C slot, half bail

Geometry:
  - outer solid = loft of the implicit heart curve (x^2+y^2-1)^3 = x^2 y^3,
    inset per-z by an edge-rounding + gentle doming profile -> soft edges,
    no sharp corners anywhere
  - fitted pocket = outline of (battery ∪ board ∪ wire slack) + 0.6 mm,
    smoothed — the XIAO (camera removed, pins clipped) and the LiPo fit it
    exactly, stacked (LiPo at the back, board on foam tape, USB-C right)
  - snap-fit: continuous lip on the back shell with a 0.3 mm ridge that
    clicks into a groove inside the front shell — discreet, around the
    inner perimeter
  - integrated bail: Ø11 disc with a Ø5.5 hole bridging the cleft, split
    across both shells (strong when closed)
  - seam at mid-depth (z=0), visible and clean around the side

Run:  python pendant.py             STLs + fit report
      python pendant.py --render    + four_views.png (closed/side/open/dims)
      python pendant.py --viewer    + viewer.html (interactive, no network)
Requires: pip install trimesh shapely manifold3d numpy (+matplotlib to render).
"""
import argparse
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, box as shp_box
from trimesh.creation import extrude_polygon, cylinder, box, triangulate_polygon

# ---------------- components (mm) ----------------
BAT_L, BAT_W, BAT_T = 32.0, 20.5, 5.3       # LiPo LP502030, flat, at the back
TAPE = 0.8
PCB_L, PCB_W, PCB_T = 21.0, 17.8, 1.2       # XIAO ESP32-S3, pins clipped
SENSE_H = 7.5                               # PCB underside -> top of empty cam socket
USB_W, USB_H = 8.94, 3.26                   # USB-C connector (on the base PCB)
WIRE_GAP = 4.5                              # wire bay: leads + folded JST-PHR-02

# ---------------- case ----------------
H = 9.2                                     # half depth -> 18.4 mm closed
EDGE_R = 4.2                                # edge rounding radius
DOME = 0.8                                  # gentle face doming
WALL = 2.6                                  # min side wall at the seam
FLOORS = 2.2                                # pocket floor/ceiling thickness
FIT = 0.6                                   # pocket clearance around parts
POCKET = "hollow"                           # "hollow": max slack, fix parts with foam
                                            # "fitted": exact component pocket
MIC_POS = (4.5, 6.2)                        # PDM mic offset from XIAO center —
                                            # VERIFY on the real board, then adjust
LIP_H, LIP_T = 2.2, 1.0                     # snap lip (on the back shell)
RIDGE = 0.30                                # snap ridge / groove interference
SLIP = 0.15                                 # radial slip clearance
ENGRAVE = 1.2                               # pulse engraving depth in the face
LOOP_RO, LOOP_RI, LOOP_T = 5.5, 2.75, 6.0   # bail: Ø11 disc, Ø5.5 hole

N_SLICE, N_PTS = 40, 170                    # loft resolution

# ---------------- chain (print-in-place necklace loop) ----------------
CHAIN_LOOP = 640.0                          # closed-loop circumference, mm:
                                            # slips over the head (~575 mm max
                                            # head circ + margin), matinee drop
LINK_R, LINK_r = 5.0, 1.15                  # link ring: centerline R, wire r
LINK_TILT = 38.0                            # alternate ring tilt (deg)
LINK_PITCH = 6.8                            # center spacing along the loop


def heart_poly(width, n_ang=420):
    """Implicit heart, ray-sampled, scaled to `width`, bbox-centered."""
    f = lambda x, y: (x * x + y * y - 1) ** 3 - x * x * y ** 3
    cx, cy = 0.0, 0.15
    rr = np.linspace(1e-3, 1.9, 500)
    pts = []
    for th in np.linspace(0, 2 * np.pi, n_ang, endpoint=False):
        vals = f(cx + rr * np.cos(th), cy + rr * np.sin(th))
        i = np.argmax(vals > 0)
        lo, hi = rr[i - 1], rr[i]
        for _ in range(28):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if f(cx + mid * np.cos(th), cy + mid * np.sin(th)) <= 0 else (lo, mid)
        pts.append((cx + lo * np.cos(th), cy + lo * np.sin(th)))
    p = Polygon(pts)
    minx, miny, maxx, maxy = p.bounds
    s = width / (maxx - minx)
    return Polygon([((x - (minx + maxx) / 2) * s, (y - (miny + maxy) / 2) * s)
                    for x, y in pts]).buffer(0)


CHAMFER_DEG = 60.0                          # max printable overhang (expert advice)


def inset_at(z):
    """Outer-surface inset vs the seam silhouette: edge rounding + doming.
    Symmetric on both sides: the round is slope-capped — a straight <=60-deg
    chamfer takes over near each cap, so BOTH shells print flat on their
    OUTER faces with zero supports and identical bed-side finish (unified
    orientation so the joined halves match)."""
    a = abs(z)
    if a <= H - EDGE_R:
        e = 0.0
    else:
        sdist = a - (H - EDGE_R)
        tmax = np.tan(np.radians(CHAMFER_DEG))
        s60 = EDGE_R * np.sin(np.radians(CHAMFER_DEG))
        if sdist <= s60:
            e = EDGE_R - np.sqrt(max(EDGE_R ** 2 - sdist ** 2, 0))
        else:
            e60 = EDGE_R - np.sqrt(EDGE_R ** 2 - s60 ** 2)
            e = e60 + tmax * (sdist - s60)
    return e + DOME * (z / H) ** 2


def resample(poly, m):
    xy = np.asarray(poly.exterior.coords)
    if not poly.exterior.is_ccw:
        xy = xy[::-1]
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    t = np.linspace(0, d[-1], m, endpoint=False)
    pts = np.c_[np.interp(t, d, xy[:, 0]), np.interp(t, d, xy[:, 1])]
    return np.roll(pts, -int(np.argmin(pts[:, 1])), axis=0)   # start at the tip


def loft_heart(heart):
    """Watertight rounded solid: stacked per-z insets of the heart outline."""
    zs = np.concatenate([[-H], -H + (2 * H) * (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, N_SLICE))), [H]])
    zs = np.unique(np.clip(zs, -H, H))
    rings, verts = [], []
    for z in zs:
        p = heart.buffer(-inset_at(z), quad_segs=24)
        assert p.geom_type == "Polygon" and not p.is_empty, f"slice at z={z} broke"
        r = resample(p, N_PTS)
        rings.append(r)
        verts.append(np.c_[r, np.full(N_PTS, z)])
    V = np.concatenate(verts)
    F = []
    for k in range(len(zs) - 1):
        a, b = k * N_PTS, (k + 1) * N_PTS
        for i in range(N_PTS):
            j = (i + 1) % N_PTS
            F += [[a + i, a + j, b + i], [a + j, b + j, b + i]]
    # flat caps
    for k, flip in ((0, True), (len(zs) - 1, False)):
        v2, f2 = triangulate_polygon(Polygon(rings[k]), engine="earcut")
        base = len(V)
        V = np.vstack([V, np.c_[v2, np.full(len(v2), zs[k])]])
        F += (f2[:, ::-1] + base).tolist() if flip else (f2 + base).tolist()
    m = trimesh.Trimesh(V, np.array(F), process=True)
    if m.volume < 0:
        m.invert()
    return m


def place_components(heart):
    """Stack placement inside the seam-plane silhouette."""
    region = heart.buffer(-(WALL + inset_at(H - FLOORS)))
    best, best_m = None, -1
    for yc in np.arange(-8, 14, 0.5):
        bat = shp_box(-BAT_L / 2, yc - BAT_W / 2, BAT_L / 2, yc + BAT_W / 2)
        if region.contains(bat):
            mg = region.exterior.distance(bat)
            if mg > best_m:
                best, best_m = yc, mg
    if best is None:
        return None
    yc = best
    x_right = 1e9
    for yy in np.linspace(yc - PCB_W / 2, yc + PCB_W / 2, 12):
        xs = LineString([(0, yy), (200, yy)]).intersection(region.exterior)
        pp = [pt.x for pt in getattr(xs, "geoms", [xs])]
        if pp:
            x_right = min(x_right, max(pp))
    x_right -= 1.0
    bat = shp_box(-BAT_L / 2, yc - BAT_W / 2, BAT_L / 2, yc + BAT_W / 2)
    board = shp_box(x_right - PCB_L, yc - PCB_W / 2, x_right, yc + PCB_W / 2)
    wires = shp_box(-BAT_L / 2 - WIRE_GAP, yc - 6, -BAT_L / 2, yc + 6)
    pocket = bat.union(board).union(wires).buffer(FIT).buffer(1.2, quad_segs=16).buffer(-1.2, quad_segs=16)
    if not region.buffer(-0.05).contains(pocket):
        return None
    return pocket, bat, board, wires, x_right, yc


def find_fit():
    for w in np.arange(46, 66, 0.5):
        heart = heart_poly(w, n_ang=260)
        r = place_components(heart)
        if r is not None:
            return w
    raise SystemExit("no width fits — check component dims")


def tz(m, dz):
    m.apply_translation([0, 0, dz])
    return m


def ring_prism(inner, outer, h, z0):
    """Extruded ring between two offsets of the pocket outline."""
    return tz(extrude_polygon(outer.difference(inner).buffer(0), h), z0)


def build():
    w = find_fit()
    heart = heart_poly(w)
    pocket, bat, board, wires, x_right, yc = place_components(heart)
    minx, miny, maxx, maxy = heart.bounds
    z_floor = -H + FLOORS
    z_bat_top = z_floor + BAT_T
    z_pcb0 = z_bat_top + TAPE                # base PCB underside (pins clipped)
    z_pcb_top = z_pcb0 + 1.1                 # base PCB top face

    cavity_poly = heart.buffer(-WALL) if POCKET == "hollow" else pocket
    solid = loft_heart(heart)
    # bail: disc bridging the cleft, hole along Z, split later across shells
    cleft_y = max(p[1] for p in heart.exterior.coords if abs(p[0]) < 0.7)
    ring_c = [0, cleft_y + LOOP_RO * 0.5]
    disc = cylinder(radius=LOOP_RO, height=LOOP_T, sections=96)
    disc.apply_translation(ring_c + [0])
    bridge = box(extents=[9.0, 6.0, LOOP_T])
    bridge.apply_translation([0, cleft_y + 0.5, 0])
    hole = cylinder(radius=LOOP_RI, height=60, sections=96)
    hole.apply_translation(ring_c + [0])
    solid = trimesh.boolean.union([solid, disc, bridge])
    solid = trimesh.boolean.difference([solid, hole])

    # hollow with the fitted pocket, then split at the seam plane z=0
    hollow = trimesh.boolean.difference(
        [solid, tz(extrude_polygon(cavity_poly, 2 * H - 2 * FLOORS), z_floor)])
    half = 200
    back = trimesh.boolean.intersection(
        [hollow, tz(box(extents=[half, half, half]), -half / 2)])
    front = trimesh.boolean.intersection(
        [hollow, tz(box(extents=[half, half, half]), half / 2)])

    # snap-fit: lip + ridge on the back, channel + groove in the front
    lip = ring_prism(cavity_poly.buffer(SLIP), cavity_poly.buffer(SLIP + LIP_T), LIP_H, 0)
    ridge = ring_prism(cavity_poly.buffer(SLIP + LIP_T - 0.1),
                       cavity_poly.buffer(SLIP + LIP_T + RIDGE), 0.7, 0.8)
    back = trimesh.boolean.union([back, lip, ridge])
    channel = ring_prism(cavity_poly.buffer(0), cavity_poly.buffer(SLIP + LIP_T + SLIP),
                         LIP_H + 0.3, -0.05)
    groove = ring_prism(cavity_poly.buffer(SLIP + LIP_T - 0.1),
                        cavity_poly.buffer(SLIP + LIP_T + RIDGE + SLIP), 0.95, 0.72)
    # USB-C slot through the front wall, above the seam
    usb_slot = box(extents=[16, USB_W + 3.0, USB_H + 2.2])
    usb_slot.apply_translation([x_right + 8, yc, z_pcb_top + USB_H / 2 + 0.3])
    # engraved pulse (v3.2): prints against the bed -> crisp; wall under the
    # groove thins to ~1.0 mm so the copper electrode senses through it
    cap = heart.buffer(-inset_at(H))
    cminx, _, cmaxx, _ = cap.bounds
    cw = cmaxx - cminx
    pts = [(-.50, .02), (-.30, .02), (-.24, .11), (-.17, -.07), (-.10, .02),
           (-.03, .02), (.03, .37), (.11, -.33), (.17, .02), (.26, .02),
           (.32, .10), (.38, .02), (.50, .02)]
    line = LineString([(px * cw, py * cw * 0.62 + 1.0) for px, py in pts])
    pulse = line.buffer(1.5).intersection(cap.buffer(-1.2)).buffer(0)
    engrave = tz(extrude_polygon(pulse, ENGRAVE + 0.5), H - ENGRAVE)
    cuts = [channel, groove, usb_slot, engrave]
    # mic: acoustic chamber recess inside the front shell spanning the whole
    # plausible mic zone (exact mic XY unverified — chamber makes it non-critical),
    # vented by a 5-hole cluster centered on the best-estimate position
    mic_c = (x_right - PCB_L / 2 + MIC_POS[0], yc + MIC_POS[1])
    ch_poly = shp_box(x_right - PCB_L / 2 + 1.5 - 8, yc + 3.5 - 6,
                      x_right - PCB_L / 2 + 1.5 + 8, yc + 3.5 + 6) \
        .difference(pulse.buffer(1.2)).buffer(0)
    cuts.append(tz(extrude_polygon(ch_poly, 1.4), H - FLOORS - 0.01))
    for dx, dy in [(0, 0), (2.4, 0), (-2.4, 0), (0, 2.4), (0, -2.4)]:
        hcyl = cylinder(radius=0.8, height=14, sections=48)
        hcyl.apply_translation([mic_c[0] + dx, mic_c[1] + dy, H - 2])
        cuts.append(hcyl)
    front = trimesh.boolean.difference([front] + cuts)

    # ---------------- exact component models ----------------
    def rrect(cx2, cy2, L, Wd, r, h, z):
        p = shp_box(cx2 - L / 2, cy2 - Wd / 2, cx2 + L / 2, cy2 + Wd / 2) \
            .buffer(-r).buffer(r, quad_segs=16)
        return tz(extrude_polygon(p, h), z)

    def bx(L, Wd, h, cx2, cy2, z):
        b = box(extents=[L, Wd, h]); b.apply_translation([cx2, cy2, z + h / 2]); return b

    bx_c, by_c = 0.0, yc                     # battery center (32 along x)
    px_c = x_right - PCB_L / 2               # XIAO center x
    comps = {}
    # LP502030: pouch + PCM zone under Kapton at the wire end (left) + wires + JST
    comps["bat_pouch"] = (rrect(bx_c + 1.5, by_c, BAT_L - 3.0, BAT_W, 1.5, BAT_T, z_floor + 0.05),
                          (.72, .72, .76), -0.5)
    comps["bat_tape"] = (bx(3.4, BAT_W, BAT_T + 0.2, bx_c - BAT_L / 2 + 1.7, by_c, z_floor), (.85, .68, .2), -0.5)
    # final-assembly wiring: JST cut off, leads routed through the wire bay,
    # up into the foam-tape layer, along under the board to the BAT pads
    def tube(points, r):
        segs = []
        for p, q in zip(points[:-1], points[1:]):
            p, q = np.array(p, float), np.array(q, float)
            v = q - p
            L = np.linalg.norm(v)
            c = cylinder(radius=r, height=L, sections=20)
            c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], v / L))
            c.apply_translation((p + q) / 2)
            segs.append(c)
            j = trimesh.creation.icosphere(subdivisions=1, radius=r)
            j.apply_translation(q)
            segs.append(j)
        return trimesh.boolean.union(segs)

    wz = z_floor + BAT_T / 2
    z_wire = z_pcb0 - 0.45                   # runs inside the foam-tape layer
    for name, dy, pad_dy, col in (("wire_red", 1.1, 1.7, (.78, .13, .1)),
                                  ("wire_black", -1.1, -1.7, (.16, .16, .16))):
        pts = [(bx_c - BAT_L / 2, by_c + dy, wz),
               (bx_c - BAT_L / 2 - 2.4, by_c + dy, wz),
               (bx_c - BAT_L / 2 - 2.4, by_c + dy, z_wire),
               (x_right - 4.2, yc + pad_dy, z_wire)]
        comps[name] = (tube(pts, 0.62), col, -0.2)
    # BAT+/BAT- pads on the XIAO underside + solder joints
    pads2 = [bx(2.2, 1.6, 0.08, x_right - 3.4, yc + sgn * 1.7, z_pcb0 - 0.08) for sgn in (1, -1)]
    comps["bat_pads"] = (trimesh.boolean.union(pads2), (.80, .66, .25), 0.25)
    blobs = []
    for sgn in (1, -1):
        b2 = trimesh.creation.icosphere(subdivisions=2, radius=1.05)
        b2.apply_scale([1, 1, 0.55])
        b2.apply_translation([x_right - 3.4, yc + sgn * 1.7, z_pcb0 - 0.35])
        blobs.append(b2)
    comps["solder"] = (trimesh.boolean.union(blobs), (.88, .89, .92), -0.2)
    # XIAO ESP32-S3 Sense, camera removed, pins clipped flush
    g_pcb, g_gold = (.12, .40, .23), (.80, .66, .25)
    g_sil, g_dark = (.72, .74, .78), (.20, .20, .22)
    base = rrect(px_c, yc, PCB_L, PCB_W, 2.2, 1.1, z_pcb0)
    sense = rrect(px_c, yc, PCB_L, PCB_W, 2.2, 0.9, z_pcb0 + 3.5)
    comps["x_pcbs"] = (trimesh.boolean.union([base, sense]), g_pcb, 0.25)
    pads = [bx(15.3, 1.8, 0.08, px_c, yc + s2 * (PCB_W / 2 - 1.1), z_pcb_top) for s2 in (1, -1)]
    comps["x_pads"] = (trimesh.boolean.union(pads), g_gold, 0.25)
    comps["x_shield"] = (bx(13.2, 10.8, 2.0, px_c - 2.0, yc, z_pcb_top), g_sil, 0.25)
    comps["x_usb"] = (bx(7.35, USB_W, USB_H, x_right - 7.35 / 2 + 1.2, yc, z_pcb_top), g_dark, 0.25)
    small = [bx(2.6, 1.6, 0.8, x_right - 2.2, yc + s2 * 5.6, z_pcb_top) for s2 in (1, -1)]     # rst/boot
    small.append(bx(2.6, 2.6, 1.4, px_c - PCB_L / 2 + 2.2, yc - 4.5, z_pcb_top))              # U.FL
    small += [bx(2.0, 12.0, 2.4, px_c + s2 * 6.5, yc, z_pcb0 + 1.1) for s2 in (1, -1)]        # B2B
    small.append(bx(8.5, 6.5, 2.8, px_c - 1.5, yc - 1.0, z_pcb0 + 4.4))                       # empty cam socket
    small.append(bx(3.0, 2.0, 1.0, px_c + 4.5, yc + 6.2, z_pcb0 + 4.4))                       # PDM mic
    comps["x_parts"] = (trimesh.boolean.union(small), g_dark, 0.25)
    comps["x_sd"] = (bx(12.0, 12.0, 1.9, px_c - 2.5, yc + 3.0, z_pcb0 + 4.4), g_sil, 0.25)
    # copper tape electrode in the pulse recess (glued to the membrane) + lead to GPIO1
    foil = tz(extrude_polygon(pulse.buffer(1.0).buffer(0), 0.12), H - FLOORS - 0.15)
    comps["copper_tape"] = (foil, (.78, .48, .20), 1.0)
    fminx, fminy, fmaxx, fmaxy = pulse.bounds
    gpio1 = (px_c - PCB_L / 2 + 2.2, yc - PCB_W / 2 + 1.6, z_pcb_top + 0.1)
    comps["touch_wire"] = (tube([(fminx + 2.0, (fminy + fmaxy) / 2, H - FLOORS - 0.3),
                                 (fminx + 2.0, (fminy + fmaxy) / 2, 3.0),
                                 gpio1], 0.5), (.85, .72, .25), 0.6)
    # 2.4 GHz FPC WiFi antenna: glued flat under the front ceiling, upper band
    # spanning both lobes — clear of the copper touch zone (below), the acoustic
    # chamber (right) and far from the battery (back shell). Clipped to the
    # interior outline: the flexible sheet simply follows the ceiling.
    ant_poly = shp_box(-22, 16, 18, 28).intersection(cavity_poly.buffer(-1.0)).buffer(0)
    ant = tz(extrude_polygon(ant_poly, 0.4), H - FLOORS - 0.45)
    comps["antenna"] = (ant, (.13, .13, .15), 1.0)
    # U.FL pigtail: from the connector on the base PCB, gentle loop up to the sheet
    ufl = (px_c - PCB_L / 2 + 2.2, yc - 4.5, z_pcb_top + 1.2)
    comps["ant_cable"] = (tube([ufl,
                                (px_c - PCB_L / 2 - 4.0, yc - 4.0, 2.0),
                                (-19.0, 8.0, 5.2),
                                (-17.0, 17.5, H - FLOORS - 0.7)], 0.55),
                         (.07, .07, .08), 0.6)
    dummies = {k: v[0] for k, v in comps.items()}

    dims = dict(width=round(maxx - minx, 1),
                height=round((max(ring_c[1] + LOOP_RO, maxy)) - miny, 1),
                depth=round(2 * H, 1), engrave=ENGRAVE,
                hole=2 * LOOP_RI,
                pocket_h=round(2 * H - 2 * FLOORS, 1),
                stack=round(BAT_T + TAPE + SENSE_H, 1))
    print(f"heart {dims['width']} x {dims['height']} x {dims['depth']} mm "
          f"(pulse engraved {ENGRAVE} mm), bail hole Ø{dims['hole']}")
    print(f"pocket height {dims['pocket_h']} vs stack {dims['stack']} mm; "
          f"base PCB top at z={z_pcb_top:.2f}")
    return front, back, comps, dims


# ---------------- four views ----------------
def render(front, back, dummies, dims, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def panel(ax, meshes, title, elev, azim, r=42, zc=0):
        allf, allc = [], []
        light = np.array([.35, .25, .9]); light = light / np.linalg.norm(light)
        alln = []
        for mesh, color in meshes:
            f = mesh.vertices[mesh.faces]
            lam = .45 + .55 * np.clip(mesh.face_normals @ light, 0, 1)
            allf.append(f)
            alln.append(mesh.face_normals)
            allc.append(np.clip(np.array(color) * lam[:, None], 0, 1))
        F = np.concatenate(allf); C = np.concatenate(allc)
        N = np.concatenate(alln)
        el, az = np.radians(elev), np.radians(azim)
        view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        keep = N @ view > -0.02          # cull back-faces: hidden interiors
        F, C = F[keep], C[keep]          # cannot bleed through the sort
        order = np.argsort(F.mean(axis=1) @ view)
        # edges painted like the faces: kills the anti-aliasing hairlines that
        # read as "rays" across flat surfaces in the PNG render
        ax.add_collection3d(Poly3DCollection(F[order], facecolors=C[order],
                                             edgecolors=C[order], linewidths=0.35))
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(zc - r, zc + r)
        ax.view_init(elev=elev, azim=azim); ax.set_title(title, fontsize=11)

    grey, dgrey = (.80, .81, .83), (.62, .63, .66)
    comp = [(m, c) for m, c, _ in dummies.values()]
    fig = plt.figure(figsize=(15, 12), dpi=110)

    panel(fig.add_subplot(2, 2, 1, projection="3d"),
          [(back, dgrey), (front, grey)],
          "1 · closed — front view (engraved pulse, bail)", 72, -90, 33)
    panel(fig.add_subplot(2, 2, 2, projection="3d"),
          [(back, dgrey), (front, grey)],
          "1b · side view — thickness + seam between the shells", 0, -90, 33)
    fb = front.copy(); fb.apply_translation([0, 0, 36])
    lifted = []
    for m, c, ex in dummies.values():
        mm = m.copy(); mm.apply_translation([0, 0, 14 if ex > 0 else 6])
        lifted.append((mm, c))
    open_meshes = [(back, dgrey), (fb, grey)] + lifted
    panel(fig.add_subplot(2, 2, 3, projection="3d"),
          open_meshes, "2 · open — two hollow shells + components", 24, -60, 40, 14)
    ax = fig.add_subplot(2, 2, 4, projection="3d")
    panel(ax, [(back, dgrey), (front, grey)], "3 · profile + dimensions", 8, -32, 34)
    for tx, ty, s in [(.04, .90, f"width  {dims['width']} mm"),
                      (.04, .84, f"height {dims['height']} mm (incl. bail)"),
                      (.04, .78, f"depth  {dims['depth']} mm (pulse engraved {dims['engrave']} mm)"),
                      (.04, .72, f"bail hole Ø{dims['hole']} mm"),
                      (.04, .66, f"pocket height {dims['pocket_h']} mm / stack {dims['stack']} mm")]:
        ax.text2D(tx, ty, s, transform=ax.transAxes, fontsize=11)
    fig.suptitle("Encore heart pendant v3 — two snap-fit shells, rounded edges "
                 "(XIAO ESP32-S3 Sense + LiPo 502030) — geometry only", fontsize=14)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("render ->", out)


# ---------------- interactive viewer (self-contained WebGL) ----------------
def write_viewer(front, back, dummies, dims, out):
    def pack(m):
        v = np.round(np.asarray(m.vertices), 2)
        return {"v": v.ravel().tolist(), "f": np.asarray(m.faces).ravel().tolist()}
    parts = {
        "back":  {"mesh": pack(back), "color": [0.62, 0.63, 0.68], "ex": -1.0},
        "front": {"mesh": pack(front), "color": [0.82, 0.83, 0.86], "ex": 1.0},
    }
    for name, (m, c, ex) in dummies.items():
        parts[name] = {"mesh": pack(m), "color": list(c), "ex": ex}
    html = VIEWER_TEMPLATE.replace("__DATA__", json.dumps(parts)) \
                          .replace("__DIMS__", json.dumps(dims))
    with open(out, "w") as fh:
        fh.write(html)
    print("viewer ->", out, f"({len(html)//1024} KB)")


VIEWER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Encore pendant — interactive assembly</title>
<style>
 html,body{margin:0;height:100%;background:#111;color:#ddd;
   font-family:system-ui,sans-serif;overflow:hidden}
 canvas{display:block;width:100vw;height:100vh;touch-action:none}
 #hud{position:fixed;left:14px;top:12px;max-width:330px}
 #hud h1{font-size:16px;margin:0 0 4px}
 #hud p{font-size:12px;color:#9a9a9a;margin:3px 0}
 #panel{position:fixed;left:14px;bottom:14px;background:#1b1b1bcc;
   border:1px solid #333;border-radius:10px;padding:12px 16px;width:300px}
 #panel label{font-size:12px;display:block;margin-bottom:4px;color:#bbb}
 #panel input[type=range]{width:100%}
 #panel button{margin-top:8px;margin-right:6px;background:#2c2c2c;color:#eee;
   border:1px solid #444;border-radius:7px;padding:6px 12px;font-size:12px;cursor:pointer}
 #panel button:hover{background:#3a3a3a}
 #dims{position:fixed;right:14px;top:12px;background:#1b1b1bcc;border:1px solid #333;
   border-radius:10px;padding:10px 14px;font-size:12px;line-height:1.7;color:#ccc}
</style></head><body>
<canvas id="c"></canvas>
<div id="hud"><h1>Encore pendant — assembly</h1>
 <p>drag = rotate · wheel/pinch = zoom · slider = open/close</p>
 <p>two snap-fit shells · XIAO ESP32-S3 (no camera, pins clipped) + LiPo 502030</p>
 <p style="color:#d98b3c"><b>orange sheet = copper tape</b> — the touch electrode, glued
 inside the recess behind the pulse (1.0 mm wall under the engraving); <b style="color:#cbb14a">yellow
 wire</b> → GPIO1 (T1). Tap the pulse = pin.</p>
 <p><b>black sheet = 2.4 GHz FPC WiFi antenna</b> — glued under the front ceiling,
 upper band: away from the copper (detuning), the mic chamber and the battery.
 Thin coax loops to the U.FL socket on the board.</p></div>
<div id="dims"></div>
<div id="panel">
 <label>open ⇠⇢ assemble</label>
 <input id="explode" type="range" min="0" max="1" step="0.001" value="1">
 <div>
  <button id="btnAnim">▶ open / close</button>
  <button id="btnSpin">↻ auto-rotate</button>
  <button id="btnWire">🔧 wiring / solder</button>
 </div>
</div>
<div id="solder" style="display:none;position:fixed;right:14px;bottom:14px;width:340px;
 background:#1b1b1bcc;border:1px solid #333;border-radius:10px;padding:12px 16px;
 font-size:12px;line-height:1.65;color:#ccc">
 <b>battery → XIAO soldering (shells hidden)</b><br>
 1 · cut the JST-PHR-02 off, trim leads to ~20 mm, strip 2 mm, tin them<br>
 2 · flip the XIAO: the two <b>BAT pads</b> (gold) are on the underside near the USB end<br>
 3 · tin both pads, then solder <b style="color:#e66">red → BAT+</b> and
 <b>black → BAT−</b> (the shiny blobs) — polarity is critical<br>
 4 · leads run in the foam-tape layer between battery and board (the routed path shown)<br>
 5 · charging then works through the USB-C slot — the XIAO's charge IC does the rest<br>
 6 · <b style="color:#d98b3c">touch</b>: copper tape (orange) glued behind the engraved pulse
 inside the front shell, yellow lead soldered to <b>GPIO1 (T1)</b> top-side
 through-hole — the pulse relief becomes the pin button (double tap = pin,
 long press = privacy)<br>
 7 · <b>antenna</b>: click the U.FL plug flat onto the board BEFORE placing it in
 the case (press straight down until it clicks, never at an angle), dab of hot
 glue on the plug, stick the FPC sheet under the front ceiling (upper band),
 coax in a loose loop — no tension when closing, ≥5 mm from the copper tape
</div>
<script>
"use strict";
const DATA = __DATA__, DIMS = __DIMS__;
document.getElementById("dims").innerHTML =
 `<b>dimensions</b><br>width ${DIMS.width} mm<br>height ${DIMS.height} mm (incl. bail)`+
 `<br>depth ${DIMS.depth} mm · pulse engraved ${DIMS.engrave} mm<br>bail hole Ø${DIMS.hole} mm`+
 `<br>pocket ${DIMS.pocket_h} mm / stack ${DIMS.stack} mm`;
const cv = document.getElementById("c"), gl = cv.getContext("webgl", {antialias:true});
const VS=`attribute vec3 p;attribute vec3 n;uniform mat4 mvp;uniform mat3 nm;
uniform float ez;varying vec3 vn;void main(){vn=nm*n;
gl_Position=mvp*vec4(p.x,p.y,p.z+ez,1.0);}`;
const FS=`precision mediump float;uniform vec3 col;varying vec3 vn;
void main(){vec3 n=normalize(vn);
float d=max(dot(n,normalize(vec3(.4,.3,.9))),0.0);
float d2=max(dot(n,normalize(vec3(-.5,-.2,-.6))),0.0);
vec3 c=col*(0.30+0.62*d+0.18*d2);gl_FragColor=vec4(c,1.0);}`;
function sh(t,s){const o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);
 if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))throw gl.getShaderInfoLog(o);return o;}
const prog=gl.createProgram();
gl.attachShader(prog,sh(gl.VERTEX_SHADER,VS));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,FS));
gl.linkProgram(prog);gl.useProgram(prog);
const loc={p:gl.getAttribLocation(prog,"p"),n:gl.getAttribLocation(prog,"n"),
 mvp:gl.getUniformLocation(prog,"mvp"),nm:gl.getUniformLocation(prog,"nm"),
 ez:gl.getUniformLocation(prog,"ez"),col:gl.getUniformLocation(prog,"col")};
function buildPart(d,name){
 // flat shading: expand triangles so coplanar faces shade uniformly (smooth flat front)
 const iv=d.mesh.v, f=d.mesh.f, nT=f.length/3;
 const v=new Float32Array(nT*9), n=new Float32Array(nT*9);
 for(let t=0;t<nT;t++){
  const a=3*f[3*t],b=3*f[3*t+1],c=3*f[3*t+2];
  const ux=iv[b]-iv[a],uy=iv[b+1]-iv[a+1],uz=iv[b+2]-iv[a+2];
  const wx=iv[c]-iv[a],wy=iv[c+1]-iv[a+1],wz=iv[c+2]-iv[a+2];
  let nx=uy*wz-uz*wy,ny=uz*wx-ux*wz,nz=ux*wy-uy*wx;
  const l=Math.hypot(nx,ny,nz)||1;nx/=l;ny/=l;nz/=l;
  for(let k2=0;k2<3;k2++){
   const src=[a,b,c][k2],o=t*9+k2*3;
   v[o]=iv[src];v[o+1]=iv[src+1];v[o+2]=iv[src+2];
   n[o]=nx;n[o+1]=ny;n[o+2]=nz;}}
 const bv=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,bv);
 gl.bufferData(gl.ARRAY_BUFFER,v,gl.STATIC_DRAW);
 const bn=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,bn);
 gl.bufferData(gl.ARRAY_BUFFER,bn===null?n:n,gl.STATIC_DRAW);
 return {bv,bn,count:nT*3,color:d.color,ex:d.ex,name};}
const parts=Object.entries(DATA).map(([k,d])=>buildPart(d,k));
let rx=-1.05,ry=0.0,dist=150,explode=0,spin=false,animT=null,wireMode=false;
const slider=document.getElementById("explode");
function m4mul(a,b){const o=new Float32Array(16);
 for(let r=0;r<4;r++)for(let c=0;c<4;c++){let s=0;
  for(let k=0;k<4;k++)s+=a[k*4+c]*b[r*4+k];o[r*4+c]=s;}return o;}
function persp(fov,asp,near,far){const t=1/Math.tan(fov/2);
 return new Float32Array([t/asp,0,0,0, 0,t,0,0, 0,0,(far+near)/(near-far),-1,
  0,0,2*far*near/(near-far),0]);}
function draw(){
 const w=cv.clientWidth,h=cv.clientHeight,dpr=devicePixelRatio||1;
 if(cv.width!==w*dpr||cv.height!==h*dpr){cv.width=w*dpr;cv.height=h*dpr;}
 gl.viewport(0,0,cv.width,cv.height);
 gl.clearColor(0.066,0.066,0.066,1);gl.enable(gl.DEPTH_TEST);
 gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
 const cx=Math.cos(rx),sx=Math.sin(rx),cy=Math.cos(ry),sy=Math.sin(ry);
 const rotY=new Float32Array([cy,0,-sy,0, 0,1,0,0, sy,0,cy,0, 0,0,0,1]);
 const rotX=new Float32Array([1,0,0,0, 0,cx,sx,0, 0,-sx,cx,0, 0,0,0,1]);
 const trans=new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,-6,-dist,1]);
 const mv=m4mul(trans,m4mul(rotX,rotY));
 const mvp=m4mul(persp(0.72,w/h,1,900),mv);
 gl.uniformMatrix4fv(loc.mvp,false,mvp);
 gl.uniformMatrix3fv(loc.nm,false,new Float32Array([
  mv[0],mv[1],mv[2], mv[4],mv[5],mv[6], mv[8],mv[9],mv[10]]));
 const e=(1-explode)*26;
 for(const p of parts){
  if(wireMode&&(p.name==="back"||p.name==="front"))continue;
  gl.uniform1f(loc.ez,p.ex*e);
  gl.uniform3fv(loc.col,p.color);
  gl.bindBuffer(gl.ARRAY_BUFFER,p.bv);
  gl.enableVertexAttribArray(loc.p);gl.vertexAttribPointer(loc.p,3,gl.FLOAT,false,0,0);
  gl.bindBuffer(gl.ARRAY_BUFFER,p.bn);
  gl.enableVertexAttribArray(loc.n);gl.vertexAttribPointer(loc.n,3,gl.FLOAT,false,0,0);
  gl.drawArrays(gl.TRIANGLES,0,p.count);}
 requestAnimationFrame(draw);}
slider.addEventListener("input",()=>{explode=+slider.value;});
const q=new URLSearchParams(location.search);
if(q.has("explode"))slider.value=q.get("explode");
if(q.has("wiring"))setTimeout(()=>document.getElementById("btnWire").click(),50);
explode=+slider.value;
document.getElementById("btnAnim").onclick=()=>{
 const target=explode>0.5?0:1,start=explode,t0=performance.now();
 const step=t=>{const k=Math.min((t-t0)/900,1);
  explode=start+(target-start)*(0.5-0.5*Math.cos(Math.PI*k));
  slider.value=explode;if(k<1)requestAnimationFrame(step);};
 requestAnimationFrame(step);};
document.getElementById("btnSpin").onclick=()=>{spin=!spin;};
document.getElementById("btnWire").onclick=()=>{
 wireMode=!wireMode;
 document.getElementById("solder").style.display=wireMode?"block":"none";
 if(wireMode){explode=1;slider.value=1;dist=Math.min(dist,110);}};
setInterval(()=>{if(spin)ry+=0.012;},16);
let dragging=false,px=0,py=0;
cv.addEventListener("pointerdown",e=>{dragging=true;px=e.clientX;py=e.clientY;});
addEventListener("pointerup",()=>dragging=false);
addEventListener("pointermove",e=>{if(!dragging)return;
 ry+=(e.clientX-px)*0.008;rx+=(e.clientY-py)*0.008;
 rx=Math.max(-2.8,Math.min(0.6,rx));px=e.clientX;py=e.clientY;});
cv.addEventListener("wheel",e=>{e.preventDefault();
 dist=Math.max(60,Math.min(420,dist*Math.exp(e.deltaY*0.001)));},{passive:false});
requestAnimationFrame(draw);
</script></body></html>
"""


def portrait(dims, out):
    """Human-scale wearing view: average French adult woman (164 cm, INSEE;
    man 177 cm) wearing the pendant on the 640 mm closed-loop chain."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse, Polygon as MplPoly
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    HGT = 164.0                              # cm — INSEE average adult woman
    loop_cm = CHAIN_LOOP / 10
    chin, clav = 145.0, 133.5
    neck_hw = 5.5
    front_half = (loop_cm - 19.0) / 2        # ~19 cm rides around the neck/back
    drop = np.sqrt(max(front_half ** 2 - neck_hw ** 2, 1))
    bail_y = clav - drop
    pw, ph = dims["width"] / 10, dims["height"] / 10
    pend_c = bail_y - ph / 2 + 0.4

    half = [(2.0, 138.0), (6.0, 137.0), (19.0, 133.0), (21.5, 106.0), (20.5, 85.0),
            (19.5, 76.0), (17.5, 77.0), (18.0, 86.0), (16.5, 122.0), (13.5, 103.0),
            (18.0, 86.0), (15.5, 55.0), (13.5, 45.0), (12.5, 25.0), (10.0, 5.0),
            (13.0, 0.0), (5.0, 0.0), (6.0, 5.0), (4.5, 45.0), (2.5, 70.0), (1.0, 83.0)]
    body = half + [(-x, y) for x, y in reversed(half)]

    fig = plt.figure(figsize=(15, 9), dpi=110)

    # ---- panel A: full body at true scale ----
    axA = fig.add_subplot(1, 3, 1)
    axA.add_patch(MplPoly(body, closed=True, facecolor="#cfd2d6", edgecolor="none"))
    axA.add_patch(Ellipse((0, 155.5), 17.5, 21, facecolor="#cfd2d6", edgecolor="none"))
    for sgn in (1, -1):
        t = np.linspace(0, 1, 40)
        xs = sgn * neck_hw * (1 - t) + 0.0 * t
        ys = (clav + 2) * (1 - t) + bail_y * t - 3.0 * np.sin(np.pi * t) * 0.4
        axA.plot(xs, ys, color="#6b6e73", lw=1.4)
    hp = np.asarray(heart_poly(pw, n_ang=160).exterior.coords)
    axA.add_patch(MplPoly(np.c_[hp[:, 0], hp[:, 1] + pend_c], closed=True,
                          facecolor="#8f939a", edgecolor="#5c5f64", lw=0.8))
    axA.annotate("", xy=(-30, 0), xytext=(-30, HGT),
                 arrowprops=dict(arrowstyle="<->", lw=1))
    axA.text(-31.5, HGT / 2, f"{HGT:.0f} cm\nfemme adulte,\nmoyenne France (INSEE)\n(homme: 177 cm)",
             ha="right", va="center", fontsize=9)
    axA.annotate("", xy=(8, bail_y), xytext=(8, chin),
                 arrowprops=dict(arrowstyle="<->", lw=1, color="#c0392b"))
    axA.text(9, (bail_y + chin) / 2, f"{chin - bail_y:.0f} cm\nsous le menton",
             fontsize=9, color="#c0392b", va="center")
    axA.set_xlim(-45, 32); axA.set_ylim(-4, 172)
    axA.set_aspect("equal"); axA.axis("off")
    axA.set_title(f"portee — chaine boucle {loop_cm:.0f} cm (matinee)", fontsize=11)

    # ---- panel B: chest zoom ----
    axB = fig.add_subplot(1, 3, 2)
    axB.add_patch(MplPoly(body, closed=True, facecolor="#e3e5e8", edgecolor="none"))
    for sgn in (1, -1):
        t = np.linspace(0, 1, 60)
        xs = sgn * neck_hw * (1 - t)
        ys = (clav + 2) * (1 - t) + bail_y * t - 3.0 * np.sin(np.pi * t) * 0.4
        axB.plot(xs, ys, color="#6b6e73", lw=3)
        for k in range(0, 58, 3):
            axB.add_patch(Ellipse((xs[k], ys[k]), 0.9, 0.55,
                                  angle=np.degrees(np.arctan2(ys[min(k + 3, 59)] - ys[k],
                                                              xs[min(k + 3, 59)] - xs[k])),
                                  facecolor="none", edgecolor="#4a4d52", lw=1.0))
    hp2 = np.asarray(heart_poly(pw, n_ang=240).exterior.coords)
    axB.add_patch(MplPoly(np.c_[hp2[:, 0], hp2[:, 1] + pend_c], closed=True,
                          facecolor="#b9bcc2", edgecolor="#5c5f64", lw=1.2))
    cap = heart_poly(pw, n_ang=160).buffer(-0.45)
    cminx, _, cmaxx, _ = cap.bounds
    cw = cmaxx - cminx
    pp = [(-.50, .02), (-.30, .02), (-.24, .11), (-.17, -.07), (-.10, .02),
          (-.03, .02), (.03, .37), (.11, -.33), (.17, .02), (.26, .02),
          (.32, .10), (.38, .02), (.50, .02)]
    px = [a * cw for a, b in pp]; py = [b * cw * 0.62 + 0.1 + pend_c for a, b in pp]
    axB.plot(px, py, color="#5c5f64", lw=2)
    axB.annotate("", xy=(-pw / 2, pend_c - ph / 2 - 1.6), xytext=(pw / 2, pend_c - ph / 2 - 1.6),
                 arrowprops=dict(arrowstyle="<->", lw=1))
    axB.text(0, pend_c - ph / 2 - 2.6, f"{dims['width']} mm", ha="center", fontsize=9)
    axB.annotate("", xy=(pw / 2 + 1.6, pend_c - ph / 2), xytext=(pw / 2 + 1.6, pend_c + ph / 2),
                 arrowprops=dict(arrowstyle="<->", lw=1))
    axB.text(pw / 2 + 2.4, pend_c, f"{dims['height']} mm", va="center", fontsize=9)
    axB.set_xlim(-14, 15); axB.set_ylim(pend_c - 10, clav + 6)
    axB.set_aspect("equal"); axB.axis("off")
    axB.set_title("zoom poitrine — pendentif + chaine a l'echelle", fontsize=11)

    # ---- panel C: chain segment 3D ----
    axC = fig.add_subplot(1, 3, 3, projection="3d")
    proto = trimesh.creation.torus(major_radius=LINK_R, minor_radius=LINK_r,
                                   major_sections=40, minor_sections=12)
    seg = []
    for i in range(8):
        m = proto.copy()
        T = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
        T = trimesh.transformations.rotation_matrix(
            np.radians(LINK_TILT) * (1 if i % 2 == 0 else -1), [1, 0, 0]) @ T
        T = trimesh.transformations.translation_matrix([i * LINK_PITCH - 3.5 * LINK_PITCH, 0, 0]) @ T
        m.apply_transform(T)
        seg.append(m)
    segm = trimesh.util.concatenate(seg)
    f = segm.vertices[segm.faces]
    light = np.array([.35, .25, .9]); light = light / np.linalg.norm(light)
    lam = .45 + .55 * np.clip(segm.face_normals @ light, 0, 1)
    col = np.clip(np.array([.75, .76, .8]) * lam[:, None], 0, 1)
    el, az = np.radians(28), np.radians(-55)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    order = np.argsort(f.mean(axis=1) @ view)
    axC.add_collection3d(Poly3DCollection(f[order], facecolors=col[order],
                                          edgecolors=col[order], linewidths=0.3))
    axC.set_box_aspect((1, 1, 1)); axC.set_axis_off()
    axC.set_xlim(-26, 26); axC.set_ylim(-26, 26); axC.set_zlim(-26, 26)
    axC.view_init(elev=28, azim=-55)
    axC.set_title(f"chaine imprimee en place — anneaux Ø{2 * LINK_R:.0f}, fil Ø{2 * LINK_r:.1f} mm,\n"
                  f"inclines ±{LINK_TILT:.0f}°, boucle fermee {CHAIN_LOOP:.0f} mm sans fermoir", fontsize=10)

    fig.suptitle("Encore — portrait a l'echelle humaine + chaine assortie (geometrie seule)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("portrait ->", out)


def _link_transform(i, n, rn, tilt, z0):
    phi = 2 * np.pi * i / n
    T = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    T = trimesh.transformations.rotation_matrix(
        np.radians(tilt) * (1 if i % 2 == 0 else -1), [1, 0, 0]) @ T
    T = trimesh.transformations.rotation_matrix(phi + np.pi / 2, [0, 0, 1]) @ T
    T = trimesh.transformations.translation_matrix(
        [rn * np.cos(phi), rn * np.sin(phi), z0]) @ T
    return T


def _chain_pair_check(n, rn, tilt):
    """Numeric clearance + linkage check on consecutive centerline rings."""
    th = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    ring = np.c_[LINK_R * np.cos(th), np.zeros_like(th), LINK_R * np.sin(th), np.ones_like(th)]
    a = (ring @ _link_transform(0, n, rn, tilt, 0).T)[:, :3]
    b = (ring @ _link_transform(1, n, rn, tilt, 0).T)[:, :3]
    d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)).min()
    clearance = d - 2 * LINK_r
    # linked if B's centerline crosses A's disk plane inside the ring radius
    Ta = _link_transform(0, n, rn, tilt, 0)
    inv = np.linalg.inv(Ta)
    bl = (np.c_[b, np.ones(len(b))] @ inv.T)[:, :3]
    sgn = np.sign(bl[:, 1])
    crossings = np.where(np.diff(sgn) != 0)[0]
    linked = any(np.hypot(bl[i, 0], bl[i, 2]) < LINK_R for i in crossings)
    return clearance, linked


def build_chain():
    n = int(round(CHAIN_LOOP / LINK_PITCH))
    n += n % 2                               # even count so tilts alternate cleanly
    rn = CHAIN_LOOP / (2 * np.pi)
    clearance, linked = _chain_pair_check(n, rn, LINK_TILT)
    print(f"chain: {n} links, loop {CHAIN_LOOP:.0f} mm, print circle "
          f"Ø{2 * rn + 2 * LINK_R + 2 * LINK_r:.0f} mm, "
          f"link clearance {clearance:.2f} mm, linked={linked}")
    assert linked and clearance > 0.35, "chain geometry broken — tune LINK_PITCH/LINK_TILT"
    proto = trimesh.creation.torus(major_radius=LINK_R, minor_radius=LINK_r,
                                   major_sections=48, minor_sections=14)
    links = []
    for i in range(n):
        m = proto.copy()
        m.apply_transform(_link_transform(i, n, rn, LINK_TILT, 0))
        links.append(m)
    chain = trimesh.util.concatenate(links)
    chain.apply_translation([0, 0, -chain.bounds[0][2]])
    return chain, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--viewer", action="store_true")
    ap.add_argument("--chain", action="store_true")
    ap.add_argument("--portrait", action="store_true")
    args = ap.parse_args()
    front, back, dummies, dims = build()
    for m, name in [(back, "encore_back.stl"), (front, "encore_front.stl")]:
        try:
            m.fix_normals()
        except BaseException:
            pass
        print(name, "watertight:", m.is_watertight, "| dims:", np.round(m.extents, 1))
        m.export(name)
    if args.render:
        render(front, back, dummies, dims, "four_views.png")
    if args.viewer:
        write_viewer(front, back, dummies, dims, "viewer.html")
    if args.chain:
        chain, n = build_chain()
        chain.export("encore_chain.stl")
        print("encore_chain.stl watertight:", chain.is_watertight,
              "| dims:", np.round(chain.extents, 1))
    if args.portrait:
        portrait(dims, "portrait_scale.png")


if __name__ == "__main__":
    main()
