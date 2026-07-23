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
TOP_H = 3.4                                 # USB-C connector height
USB_W, USB_H = 9.0, 3.4
WIRE_GAP = 3.0

# ---------------- case ----------------
H = 8.0                                     # half depth -> 16 mm closed
EDGE_R = 4.2                                # edge rounding radius
DOME = 0.8                                  # gentle face doming
WALL = 2.6                                  # min side wall at the seam
FLOORS = 2.2                                # pocket floor/ceiling thickness
FIT = 0.6                                   # pocket clearance around parts
LIP_H, LIP_T = 2.2, 1.0                     # snap lip (on the back shell)
RIDGE = 0.30                                # snap ridge / groove interference
SLIP = 0.15                                 # radial slip clearance
PULSE_H = 1.0                               # relief above the front face
LOOP_RO, LOOP_RI, LOOP_T = 5.5, 2.75, 6.0   # bail: Ø11 disc, Ø5.5 hole

N_SLICE, N_PTS = 40, 170                    # loft resolution


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


def inset_at(z):
    """Outer-surface inset vs the seam silhouette: edge rounding + doming."""
    a = abs(z)
    e = 0.0 if a <= H - EDGE_R else EDGE_R - np.sqrt(max(EDGE_R ** 2 - (a - (H - EDGE_R)) ** 2, 0))
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
    z_pcb_top = z_bat_top + TAPE + PCB_T

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
        [solid, tz(extrude_polygon(pocket, 2 * H - 2 * FLOORS), z_floor)])
    half = 200
    back = trimesh.boolean.intersection(
        [hollow, tz(box(extents=[half, half, half]), -half / 2)])
    front = trimesh.boolean.intersection(
        [hollow, tz(box(extents=[half, half, half]), half / 2)])

    # snap-fit: lip + ridge on the back, channel + groove in the front
    lip = ring_prism(pocket.buffer(SLIP), pocket.buffer(SLIP + LIP_T), LIP_H, 0)
    ridge = ring_prism(pocket.buffer(SLIP + LIP_T - 0.1),
                       pocket.buffer(SLIP + LIP_T + RIDGE), 0.7, 0.8)
    back = trimesh.boolean.union([back, lip, ridge])
    channel = ring_prism(pocket.buffer(0), pocket.buffer(SLIP + LIP_T + SLIP),
                         LIP_H + 0.3, -0.05)
    groove = ring_prism(pocket.buffer(SLIP + LIP_T - 0.1),
                        pocket.buffer(SLIP + LIP_T + RIDGE + SLIP), 0.95, 0.72)
    # USB-C slot through the front wall, above the seam
    usb_slot = box(extents=[16, USB_W + 3.0, 4.9])
    usb_slot.apply_translation([x_right + 8, yc, 0.55 + 4.9 / 2])
    cuts = [channel, groove, usb_slot]
    # mic holes over the Sense PDM mic
    mic_c = (x_right - PCB_L / 2, yc + 4.5)
    for dx, dy in [(0, 0), (2.6, -1.6), (-2.6, -1.6)]:
        hcyl = cylinder(radius=0.8, height=14, sections=48)
        hcyl.apply_translation([mic_c[0] + dx, mic_c[1] + dy, H - 2])
        cuts.append(hcyl)
    front = trimesh.boolean.difference([front] + cuts)

    # raised pulse relief, centered on the flat zone of the front face
    cap = heart.buffer(-inset_at(H))
    cminx, _, cmaxx, _ = cap.bounds
    cw = cmaxx - cminx
    pts = [(-.50, .02), (-.30, .02), (-.24, .11), (-.17, -.07), (-.10, .02),
           (-.03, .02), (.03, .37), (.11, -.33), (.17, .02), (.26, .02),
           (.32, .10), (.38, .02), (.50, .02)]
    line = LineString([(px * cw, py * cw * 0.62 + 1.0) for px, py in pts])
    pulse = line.buffer(1.5).intersection(cap.buffer(-1.2)).buffer(0)
    base = tz(extrude_polygon(pulse.buffer(0.45), H - 1.5), 0)          # chamfer step
    top = tz(extrude_polygon(pulse, H + PULSE_H), 0)
    front = trimesh.boolean.union([front, trimesh.boolean.intersection(
        [trimesh.boolean.union([base, top]),
         tz(box(extents=[half, half, half]), half / 2)])])
    # re-clip relief flanks to the outer silhouette so nothing juts sideways
    clip = tz(extrude_polygon(heart, 2 * H + 6), -H - 2)
    front = trimesh.boolean.intersection([front, clip])

    # dummies (renders + viewer)
    def rbox(g, h, z):
        return tz(extrude_polygon(Polygon(g.exterior.coords), h), z)
    d_bat = rbox(bat.buffer(-0.1), BAT_T, z_floor + 0.05)
    d_pcb = rbox(board.buffer(-0.1), PCB_T, z_bat_top + TAPE)
    d_usb = box(extents=[7.5, USB_W, USB_H])
    d_usb.apply_translation([x_right - 3.75, yc, z_pcb_top + USB_H / 2])
    dummies = {"battery": d_bat, "board": d_pcb, "usb": d_usb}

    dims = dict(width=round(maxx - minx, 1),
                height=round((max(ring_c[1] + LOOP_RO, maxy)) - miny, 1),
                depth=round(2 * H, 1), relief=PULSE_H,
                hole=2 * LOOP_RI,
                pocket_h=round(2 * H - 2 * FLOORS, 1),
                stack=round(BAT_T + TAPE + PCB_T + TOP_H, 1))
    print(f"heart {dims['width']} x {dims['height']} x {dims['depth']} mm "
          f"(+{PULSE_H} relief), bail hole Ø{dims['hole']}")
    print(f"pocket height {dims['pocket_h']} vs stack {dims['stack']} mm; "
          f"USB slot z 0.55..5.45 (pcb top at {z_pcb_top:.1f})")
    return front, back, dummies, dims


# ---------------- four views ----------------
def render(front, back, dummies, dims, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def panel(ax, meshes, title, elev, azim, r=42, zc=0):
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
        ax.add_collection3d(Poly3DCollection(F[order], facecolors=C[order], edgecolor="none"))
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(zc - r, zc + r)
        ax.view_init(elev=elev, azim=azim); ax.set_title(title, fontsize=11)

    grey, dgrey = (.80, .81, .83), (.62, .63, .66)
    sil, grn, blk = (.68, .68, .72), (.16, .45, .26), (.22, .22, .24)
    comp = [(dummies["battery"], sil), (dummies["board"], grn), (dummies["usb"], blk)]
    fig = plt.figure(figsize=(15, 12), dpi=110)

    panel(fig.add_subplot(2, 2, 1, projection="3d"),
          [(back, dgrey), (front, grey)],
          "1 · closed — front view (raised pulse, bail)", 90, -90, 40)
    panel(fig.add_subplot(2, 2, 2, projection="3d"),
          [(back, dgrey), (front, grey)],
          "1b · side view — thickness + seam between the shells", 0, -90, 40)
    fb = front.copy(); fb.apply_translation([0, 0, 34])
    open_meshes = [(back, dgrey), (fb, grey)] + comp
    panel(fig.add_subplot(2, 2, 3, projection="3d"),
          open_meshes, "2 · open — two hollow shells + components", 24, -60, 48, 14)
    ax = fig.add_subplot(2, 2, 4, projection="3d")
    panel(ax, [(back, dgrey), (front, grey)], "3 · profile + dimensions", 8, -32, 42)
    for tx, ty, s in [(.04, .90, f"width  {dims['width']} mm"),
                      (.04, .84, f"height {dims['height']} mm (incl. bail)"),
                      (.04, .78, f"depth  {dims['depth']} mm (+{dims['relief']} relief)"),
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
        "back":    {"mesh": pack(back), "color": [0.62, 0.63, 0.68], "ex": -1.0},
        "front":   {"mesh": pack(front), "color": [0.82, 0.83, 0.86], "ex": 1.0},
        "battery": {"mesh": pack(dummies["battery"]), "color": [0.72, 0.72, 0.76], "ex": -0.45},
        "board":   {"mesh": pack(dummies["board"]), "color": [0.15, 0.5, 0.28], "ex": 0.25},
        "usb":     {"mesh": pack(dummies["usb"]), "color": [0.2, 0.2, 0.22], "ex": 0.25},
    }
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
 <p>two snap-fit shells · XIAO ESP32-S3 (no camera, pins clipped) + LiPo 502030</p></div>
<div id="dims"></div>
<div id="panel">
 <label>open ⇠⇢ assemble</label>
 <input id="explode" type="range" min="0" max="1" step="0.001" value="1">
 <div>
  <button id="btnAnim">▶ open / close</button>
  <button id="btnSpin">↻ auto-rotate</button>
 </div>
</div>
<script>
"use strict";
const DATA = __DATA__, DIMS = __DIMS__;
document.getElementById("dims").innerHTML =
 `<b>dimensions</b><br>width ${DIMS.width} mm<br>height ${DIMS.height} mm (incl. bail)`+
 `<br>depth ${DIMS.depth} mm (+${DIMS.relief} relief)<br>bail hole Ø${DIMS.hole} mm`+
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
function buildPart(d){
 const v=new Float32Array(d.mesh.v), f=new Uint32Array(d.mesh.f);
 const n=new Float32Array(v.length);
 for(let i=0;i<f.length;i+=3){const a=3*f[i],b=3*f[i+1],c=3*f[i+2];
  const ux=v[b]-v[a],uy=v[b+1]-v[a+1],uz=v[b+2]-v[a+2];
  const wx=v[c]-v[a],wy=v[c+1]-v[a+1],wz=v[c+2]-v[a+2];
  const nx=uy*wz-uz*wy,ny=uz*wx-ux*wz,nz=ux*wy-uy*wx;
  for(const k of [a,b,c]){n[k]+=nx;n[k+1]+=ny;n[k+2]+=nz;}}
 for(let i=0;i<n.length;i+=3){const l=Math.hypot(n[i],n[i+1],n[i+2])||1;
  n[i]/=l;n[i+1]/=l;n[i+2]/=l;}
 const bv=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,bv);
 gl.bufferData(gl.ARRAY_BUFFER,v,gl.STATIC_DRAW);
 const bn=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,bn);
 gl.bufferData(gl.ARRAY_BUFFER,n,gl.STATIC_DRAW);
 const bf=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bf);
 gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,f,gl.STATIC_DRAW);
 return {bv,bn,bf,count:f.length,color:d.color,ex:d.ex};}
gl.getExtension("OES_element_index_uint");
const parts=Object.values(DATA).map(buildPart);
let rx=-1.05,ry=0.0,dist=150,explode=0,spin=false,animT=null;
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
  gl.uniform1f(loc.ez,p.ex*e);
  gl.uniform3fv(loc.col,p.color);
  gl.bindBuffer(gl.ARRAY_BUFFER,p.bv);
  gl.enableVertexAttribArray(loc.p);gl.vertexAttribPointer(loc.p,3,gl.FLOAT,false,0,0);
  gl.bindBuffer(gl.ARRAY_BUFFER,p.bn);
  gl.enableVertexAttribArray(loc.n);gl.vertexAttribPointer(loc.n,3,gl.FLOAT,false,0,0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,p.bf);
  gl.drawElements(gl.TRIANGLES,p.count,gl.UNSIGNED_INT,0);}
 requestAnimationFrame(draw);}
slider.addEventListener("input",()=>{explode=+slider.value;});
const q=new URLSearchParams(location.search);
if(q.has("explode"))slider.value=q.get("explode");
explode=+slider.value;
document.getElementById("btnAnim").onclick=()=>{
 const target=explode>0.5?0:1,start=explode,t0=performance.now();
 const step=t=>{const k=Math.min((t-t0)/900,1);
  explode=start+(target-start)*(0.5-0.5*Math.cos(Math.PI*k));
  slider.value=explode;if(k<1)requestAnimationFrame(step);};
 requestAnimationFrame(step);};
document.getElementById("btnSpin").onclick=()=>{spin=!spin;};
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--viewer", action="store_true")
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


if __name__ == "__main__":
    main()
