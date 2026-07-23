import numpy as np, trimesh
from trimesh.creation import cylinder, box

S = 128  # segments courbes

def cyl(r, h, z0, x=0, y=0):
    c = cylinder(radius=r, height=h, sections=S)
    c.apply_translation([x, y, z0 + h/2]); return c

# ---------------- CORPS ----------------
# cylindre exterieur Ø42 x H18, paroi 2, fond 2
body  = cyl(21, 18, 0)
tab   = box(extents=[12, 10, 3]); tab.apply_translation([0, 24, 1.5])   # languette laniere, a plat sur le fond
body  = trimesh.boolean.union([body, tab])
cavity= cyl(19, 16.5, 2)                       # cavite Ø38, profondeur 16
hole  = cyl(2.2, 10, -1, y=24); hole.apply_transform(
        trimesh.transformations.rotation_matrix(0, [1,0,0]))            # trou laniere Ø4.4 vertical
body  = trimesh.boolean.difference([body, cavity, hole])

# encoche USB-C dans la paroi laterale (bas du corps, 10 x 4)
usb = box(extents=[10, 6, 4]); usb.apply_translation([0, -20, 5])
body = trimesh.boolean.difference([body, usb])

# ---------------- COUVERCLE ----------------
lid_face = cyl(21, 2.4, 0)
lip      = cyl(18.7, 3.0, 2.4)                 # jupe friction: Ø37.4 vs cavite Ø38
lid = trimesh.boolean.union([lid_face, lip])
mics = [cyl(0.8, 12, -2, x=6*np.cos(a), y=6*np.sin(a)) for a in (0, 2.09, 4.19)]
lid = trimesh.boolean.difference([lid] + mics)

for m, n in [(body, 'encore_body.stl'), (lid, 'encore_lid.stl')]:
    m.fix_normals()
    print(n, 'watertight:', m.is_watertight, '| dims:', np.round(m.extents,1))
    m.export(n)
