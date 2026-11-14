import math, numpy as np, manifold3d as m3, trimesh
from params import *
CS, MF = m3.CrossSection, m3.Manifold

def prism(pts, z0, z1):
    return MF.extrude(CS([pts]), z1-z0).translate((0,0,z0))
def rect(x0,y0,x1,y1): return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
def box(x0,y0,x1,y1,z0,z1): return prism(rect(x0,y0,x1,y1), z0, z1)
def circ(cx,cy,r,n=64): return [(cx+r*math.cos(2*math.pi*i/n), cy+r*math.sin(2*math.pi*i/n)) for i in range(n)]
def cyl(cx,cy,r,z0,z1,n=64): return prism(circ(cx,cy,r,n), z0, z1)
BIG = 200

def horn_pocket():
    # along finger link centreline
    jx = (JAW_IN+JAW_OUT)/2; ux, uy = jx, JAW_D0; L = math.hypot(ux,uy); ux/=L; uy/=L
    nx, ny = uy, -ux
    h0, h1 = HORN_W0/2+FIT, HORN_W1/2+FIT
    ex, ey = ux*HORN_LEN, uy*HORN_LEN
    arm = [(nx*h0, ny*h0), (ex+nx*h1, ey+ny*h1), (ex-nx*h1, ey-ny*h1), (-nx*h0, -ny*h0)]
    tip = circ(ex, ey, h1, 32)
    return CS([arm]) + CS([tip]) + CS([circ(0,0,HORN_HUB_D/2+FIT,48)]), (ux,uy)

def finger(driver=True):
    s = 1 if driver else -1
    phase = 0.0 if driver else 180.0 + 180.0/Z
    g = [(x, y) for x, y in gear_points(phase)]
    body = MF.extrude(CS([g]) + CS([[(s*x, y) for x, y in (FINGER_POLY if driver else FINGER_POLY[::-1])]]), GEAR_T)
    for d0, d1 in NOTCHES:
        xa, xb = s*(JAW_OUT-2), s*(JAW_OUT+NOTCH_DEPTH)
        body -= box(min(xa,xb), d0, max(xa,xb), d1, -1, GEAR_T+1)
    if driver:
        hp, _ = horn_pocket()
        body -= MF.extrude(hp, HORN_DEPTH+1).translate((0,0,-1))
        body -= cyl(0,0,HORN_HUB_D/2+FIT, -1, GEAR_T+1)
    else:
        body -= cyl(0,0,M3_CLR/2, -1, GEAR_T+1, 32)
    return body

def base():
    b = box(BASE_X0, BASE_D0, BASE_X1, BASE_D1, 0, DECK)
    pc = -SV_SHAFT_OFF
    hx, hl = SV_W/2+FIT, SV_L/2+FIT
    b -= box(-hx, pc-hl, hx, pc+hl, FLOOR, BIG)                       # servo pocket
    b -= box(-WIRE_W/2, -BIG, WIRE_W/2, BIG, FLOOR, WIRE_TOP)          # wire windows (both ends)
    for dd in (pc - SV_TAB_HOLE_PITCH/2, pc + SV_TAB_HOLE_PITCH/2):    # tab screw pilots
        b -= cyl(0, dd, 0.9, DECK-6, BIG, 24)
    for dd in MOUNT_HOLES_D:                                           # rail screws
        b -= cyl(RAIL_X, dd, M3_CLR/2, -1, BIG, 32)
        b -= cyl(RAIL_X, dd, CB_D/2, CB_FLOOR, BIG, 48)
    top = GEAR_Z - PILLAR_GAP
    b += cyl(CD, 0, PILLAR_D/2, DECK-0.5, top-0.5)                     # idler pillar
    b += cyl(CD, 0, PILLAR_BOSS_D/2, top-1, top)
    b -= cyl(CD, 0, PIVOT_PILOT_D/2, top-12, top+1, 24)
    return b

def servo():
    pc = -SV_SHAFT_OFF
    s = box(-SV_W/2, pc-SV_L/2, SV_W/2, pc+SV_L/2, 0, SV_H)
    t = box(-SV_W/2, pc-SV_TAB_SPAN/2, SV_W/2, pc+SV_TAB_SPAN/2, SV_TAB_Z, SV_TAB_Z+SV_TAB_T)
    for dd in (pc - SV_TAB_HOLE_PITCH/2, pc + SV_TAB_HOLE_PITCH/2):
        t -= cyl(0, dd, SV_TAB_HOLE_D/2, 0, 40, 24)
    s += t + cyl(0,0,SV_BUMP_D/2, SV_H-1, SV_H+SV_BUMP_H) + cyl(0,0,SV_SPLINE_D/2, SV_H, SV_SPLINE_TOP, 32)
    return s

def wrist_profile():
    ro = WR_RI + WR_T; cy = -WR_RI; a = math.radians(WR_ANG)
    def arcpts(r, a0, a1, n=48):
        return [(r*math.sin(a0+(a1-a0)*i/n), cy + r*math.cos(a0+(a1-a0)*i/n)) for i in range(n+1)]
    xr = RAIL_W/2
    ar = math.asin(xr/ro)
    pts = []
    pts += arcpts(WR_RI, -a, a)                 # inner arc left->right
    pts += arcpts(ro, a, ar)                    # outer arc right end -> rail side
    hs, hc = SLOT_W/2, CH_W/2
    pts += [(xr, RAIL_TOP), (hs, RAIL_TOP), (hs, RAIL_TOP-LIP), (hc, RAIL_TOP-LIP), (hc, CH_FLOOR),
            (-hc, CH_FLOOR), (-hc, RAIL_TOP-LIP), (-hs, RAIL_TOP-LIP), (-hs, RAIL_TOP), (-xr, RAIL_TOP)]
    pts += arcpts(ro, -ar, -a)
    return pts

def wrist_mount():
    w = MF.extrude(CS([wrist_profile()]), WR_LEN).translate((0,0,-WR_LEN/2))
    # local: x, y=height, z=along arm. map to design (x, d, z_up): d=z? -> rotate later
    for sx in (1,-1):
        x0, x1 = sorted((sx*STRAP_X0, sx*STRAP_X1))
        w -= MF.cube((x1-x0, BIG, STRAP_LEN)).translate((x0, -BIG/2, -STRAP_LEN/2))
    # to design frame: (x, h, z) -> (x, -z, h)
    T = np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0]], float)
    return w.transform(T)

def tm(mf):
    m = mf.to_mesh(); return trimesh.Trimesh(m.vert_properties[:,:3], m.tri_verts)

def rotz(mf, deg, cx=0, cy=0):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return mf.translate((-cx,-cy,0)).transform(np.array([[c,-s,0,0],[s,c,0,0],[0,0,1,0]])).translate((cx,cy,0))

def assembly(open_deg=0.0, slide=0.0):
    """Returns dict of parts in wrist-mount design frame."""
    # base sits on rail top, its RAIL_X line on mount x=0
    off = np.array((-RAIL_X, -sum(MOUNT_HOLES_D)/2 + slide, RAIL_TOP))
    parts = {}
    parts['wrist'] = wrist_mount()
    parts['base'] = base().translate(tuple(off))
    parts['servo'] = servo().translate(tuple(off + (0,0,FLOOR)))
    parts['driver'] = rotz(finger(True), open_deg).translate(tuple(off + (0,0,GEAR_Z)))
    parts['idler'] = rotz(finger(False), -open_deg).translate(tuple(off + (CD,0,GEAR_Z)))
    return parts
