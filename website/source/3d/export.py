import sys, json, math
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "hardware" / "cad" / "python"))
import build
from build import *
import numpy as np
info = {}
for ang in (0, 14, 25, 32):
    P = assembly(ang)
    for k, mf in P.items():
        tm(mf).export(f"p_{ang}_{k}.stl")
# jaw gap centre for a held object at 14 deg (in assembly frame)
def jaw(ang, d):
    a = math.radians(ang)
    off = np.array((-RAIL_X, 0.0, RAIL_TOP))
    p = (JAW_IN*math.cos(a) - d*math.sin(a), JAW_IN*math.sin(a) + d*math.cos(a))
    q0 = (CD - JAW_IN, d); a2 = -a
    q = (CD + (q0[0]-CD)*math.cos(a2) - q0[1]*math.sin(a2), (q0[0]-CD)*math.sin(a2) + q0[1]*math.cos(a2))
    c = ((p[0]+q[0])/2 + off[0], (p[1]+q[1])/2 + off[1], off[2] + GEAR_Z + GEAR_T/2)
    return c, math.dist(p, q)
for ang in (14, 25, 32):
    c, g = jaw(ang, (JAW_D0 + JAW_D1)/2 + 2)
    info[ang] = {"c": c, "gap": g}
json.dump(info, open("info.json", "w"))
print(info)
