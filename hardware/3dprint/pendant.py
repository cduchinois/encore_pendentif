import numpy as np, trimesh
from trimesh.creation import cylinder, box

S = 128  # curved-surface segments

def cyl(r, h, z0, x=0, y=0):
    c = cylinder(radius=r, height=h, sections=S)
    c.apply_translation([x, y, z0 + h/2]); return c

# ---------------- BODY ----------------
# outer cylinder Ø42 x H18, wall 2, floor 2
body  = cyl(21, 18, 0)
tab   = box(extents=[12, 10, 3]); tab.apply_translation([0, 24, 1.5])   # lanyard tab, flat on the floor
body  = trimesh.boolean.union([body, tab])
cavity= cyl(19, 16.5, 2)                       # cavity Ø38, depth 16
hole  = cyl(2.2, 10, -1, y=24); hole.apply_transform(
        trimesh.transformations.rotation_matrix(0, [1,0,0]))            # vertical lanyard hole Ø4.4
body  = trimesh.boolean.difference([body, cavity, hole])

# USB-C notch in the side wall (bottom of body, 10 x 4)
usb = box(extents=[10, 6, 4]); usb.apply_translation([0, -20, 5])
body = trimesh.boolean.difference([body, usb])

# ---------------- LID ----------------
lid_face = cyl(21, 2.4, 0)
lip      = cyl(18.7, 3.0, 2.4)                 # friction skirt: Ø37.4 vs Ø38 cavity
lid = trimesh.boolean.union([lid_face, lip])
mics = [cyl(0.8, 12, -2, x=6*np.cos(a), y=6*np.sin(a)) for a in (0, 2.09, 4.19)]
lid = trimesh.boolean.difference([lid] + mics)

for m, n in [(body, 'encore_body.stl'), (lid, 'encore_lid.stl')]:
    m.fix_normals()
    print(n, 'watertight:', m.is_watertight, '| dims:', np.round(m.extents,1))
    m.export(n)
