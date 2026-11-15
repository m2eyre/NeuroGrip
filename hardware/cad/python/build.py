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

def horn_geom():
    jx = (JAW_IN+JAW_OUT)/2; ux, uy = jx, JAW_D0; L = math.hypot(ux,uy); ux/=L; uy/=L
    return ux, uy, uy, -ux          # u (along arm), n (sideways)

def horn_pocket():
    """Horn-arm pocket (tight, HORN_FIT per side) + hub hole. Crush ribs are added back by horn_ribs()."""
    ux, uy, nx, ny = horn_geom()
    h0, h1 = HORN_W0/2+HORN_FIT, HORN_W1/2+HORN_FIT
    ex, ey = ux*HORN_LEN, uy*HORN_LEN
    arm = [(nx*h0, ny*h0), (ex+nx*h1, ey+ny*h1), (ex-nx*h1, ey-ny*h1), (-nx*h0, -ny*h0)]
    tip = circ(ex, ey, h1, 32)
    return CS([arm]) + CS([tip]) + CS([circ(0,0,HORN_HUB_D/2+FIT,48)]), (ux,uy)

def horn_rib_centres():
    ux, uy, nx, ny = horn_geom()
    h0, h1 = HORN_W0/2+HORN_FIT, HORN_W1/2+HORN_FIT
    off = RIB_D/2 - RIB_IN
    pts = []
    for t in RIB_POS:
        h = h0 + (h1-h0)*t; cx, cy = ux*HORN_LEN*t, uy*HORN_LEN*t
        pts += [(cx+nx*(h+off), cy+ny*(h+off)), (cx-nx*(h+off), cy-ny*(h+off))]
    pts.append((ux*(HORN_LEN+h1+off), uy*(HORN_LEN+h1+off)))
    return pts

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
        for cx, cy in horn_rib_centres():                              # crush ribs
            body += cyl(cx, cy, RIB_D/2, 0, HORN_DEPTH, 24)
        body -= cyl(0,0,HORN_HUB_D/2+FIT, -1, GEAR_T+1)
    else:
        body -= cyl(0,0,PIN_HOLE_D/2, -1, GEAR_T+1, 48)
    return body

def base():
    b = box(BASE_X0, BASE_D0, BASE_X1, BASE_D1, 0, DECK)
    pc = -SV_SHAFT_OFF
    hx, hl = SV_W/2+FIT, SV_L/2+FIT
    b -= box(-hx, pc-hl, hx, pc+hl, FLOOR, BIG)                       # servo pocket
    b -= box(-WIRE_W/2, -BIG, WIRE_W/2, BIG, FLOOR, WIRE_TOP)          # wire windows (both ends)
    for dd in (pc - SV_TAB_HOLE_PITCH/2, pc + SV_TAB_HOLE_PITCH/2):    # tab screw pilots
        b -= cyl(0, dd, 0.9, DECK-6, BIG, 24)
    # dovetail groove along the full length of the underside (x, h) -> extruded along d
    slope = (DT_TOP - DT_NECK) / 2 / DT_H
    g = [(RAIL_X - (DT_NECK/2 + DT_FIT - slope), -1.0), (RAIL_X + (DT_NECK/2 + DT_FIT - slope), -1.0),
         (RAIL_X + DT_TOP/2 + DT_FIT + slope*0.3, DT_H + 0.3), (RAIL_X - DT_TOP/2 - DT_FIT - slope*0.3, DT_H + 0.3)]
    T = np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0]], float)
    b -= MF.extrude(CS([g]), BIG).translate((0,0,-BIG/2)).transform(T)
    # lock-pin hole, crosswise through the groove at d=0 (blind on the servo side)
    lp = MF.extrude(CS([circ(0, 0, LOCK_PIN_D/2, 24)]), BIG).transform(np.array([[0,0,1,0],[0,1,0,0],[1,0,0,0]], float))
    b -= lp.translate((RAIL_X - DT_TOP/2 - 0.8, 0, DT_H/2))
    # idler pillar with printed snap pin
    top = GEAR_Z - PILLAR_GAP
    b += cyl(CD, 0, PILLAR_D/2, DECK-0.5, top-0.5)
    b += cyl(CD, 0, PILLAR_BOSS_D/2, top-1, top)
    shank_top = GEAR_Z + GEAR_T + 0.3
    b += cyl(CD, 0, PIN_D/2, top-0.5, shank_top)
    z = shank_top
    for dia, h in ((PIN_BARB_D, 0.6), ((PIN_BARB_D+PIN_D)/2 + 0.05, 0.5), (PIN_D - 0.3, 0.5)):
        b += cyl(CD, 0, dia/2, z - 0.01, z + h); z += h
    b -= box(CD - PIN_SLOT_W/2, -BIG/2, CD + PIN_SLOT_W/2, BIG/2, top - 2.0, BIG)   # split pin
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
    pts += [(xr, RAIL_TOP)]
    n0, t0 = DT_NECK/2, DT_TOP/2
    pts += [(n0, RAIL_TOP), (t0, RAIL_TOP+DT_H), (-t0, RAIL_TOP+DT_H), (-n0, RAIL_TOP), (-xr, RAIL_TOP)]
    pts += arcpts(ro, -ar, -a)
    return pts

def wrist_mount():
    w = MF.extrude(CS([wrist_profile()]), WR_LEN).translate((0,0,-WR_LEN/2))
    # local: x, y=height, z=along arm. map to design (x, d, z_up): d=z? -> rotate later
    for sx in (1,-1):
        x0, x1 = sorted((sx*STRAP_X0, sx*STRAP_X1))
        w -= MF.cube((x1-x0, BIG, STRAP_LEN)).translate((x0, -BIG/2, -STRAP_LEN/2))
    # lock-pin cross holes through the tongue (along x)
    for k in range(-LOCK_N, LOCK_N+1):
        lp = MF.extrude(CS([circ(0, 0, LOCK_PIN_D/2, 24)]), 2*DT_TOP).transform(np.array([[0,0,1,0],[0,1,0,0],[1,0,0,0]], float))
        w -= lp.translate((-DT_TOP, RAIL_TOP + DT_H/2, k*LOCK_PITCH))
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
    off = np.array((-RAIL_X, slide, RAIL_TOP))
    parts = {}
    parts['wrist'] = wrist_mount()
    parts['base'] = base().translate(tuple(off))
    parts['servo'] = servo().translate(tuple(off + (0,0,FLOOR)))
    parts['driver'] = rotz(finger(True), open_deg).translate(tuple(off + (0,0,GEAR_Z)))
    parts['idler'] = rotz(finger(False), -open_deg).translate(tuple(off + (CD,0,GEAR_Z)))
    return parts
