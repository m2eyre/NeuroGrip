import math
# ---- shared NeuroGrip parameters (mm) -- keep in sync with the VBA macro ----
M = 1.5          # gear module
Z = 14           # teeth per gear
CD_EXTRA = 0.2   # extra centre distance for FDM
BACKLASH = 0.2   # arc length removed from each tooth at pitch circle
GEAR_T = 6.0     # gear/finger thickness
CD = M*Z + CD_EXTRA   # 21.2 centre distance
# SG90 (verify with calipers)
SV_L, SV_W, SV_H = 22.5, 12.2, 22.7
SV_SHAFT_OFF = 5.35      # shaft centre from body centre (toward finger side)
SV_TAB_SPAN, SV_TAB_T, SV_TAB_Z = 32.2, 2.5, 15.9   # tab underside height from body bottom
SV_TAB_HOLE_PITCH, SV_TAB_HOLE_D = 27.8, 2.0
SV_BUMP_D, SV_BUMP_H = 11.8, 4.0
SV_SPLINE_D, SV_SPLINE_TOP = 4.8, 30.5
HORN_SEAT = 29.5          # underside of horn arm above servo bottom = gear bottom
FIT = 0.25               # clearance per side for pockets
# horn pocket (single-arm SG90 horn)
HORN_HUB_D, HORN_LEN, HORN_W0, HORN_W1, HORN_DEPTH = 7.6, 17.5, 6.4, 4.6, 2.0
# base
FLOOR = 3.0
DECK = FLOOR + SV_TAB_Z           # 18.9 deck top (tabs rest here)
GEAR_Z = FLOOR + HORN_SEAT        # 32.5 gear bottom in base frame
BASE_X0, BASE_X1, BASE_D0, BASE_D1 = -9.5, CD + 5.5, -24.0, 13.0
PILLAR_D, PILLAR_BOSS_D, PILLAR_GAP = 10.0, 6.0, 0.3
PIVOT_PILOT_D = 2.6               # M3 self-tap pilot
RAIL_X = 12.5                     # rail axis in base frame
MOUNT_HOLES_D = (2.0, -18.0)
CB_D, CB_FLOOR = 6.6, 5.0
M3_CLR = 3.4
WIRE_W, WIRE_TOP = 8.5, 12.5
# finger (driver, local frame, pivot at origin, d forward)
JAW_IN, JAW_OUT, JAW_D0, JAW_D1 = CD/2 - 1.0, CD/2 - 8.0, 26.0, 48.0
FINGER_POLY = [(5.5,-1.5),(JAW_IN,JAW_D0),(JAW_IN,JAW_D1),(JAW_OUT,JAW_D1),(JAW_OUT,JAW_D0),(-5.5,1.5)]
NOTCHES = [(31.0,34.0),(41.0,44.0)]
NOTCH_DEPTH = 1.2
# wrist mount
WR_RI, WR_T, WR_ANG = 38.0, 3.5, 65.0
WR_LEN = 60.0
RAIL_W = 40.0
SLOT_W, LIP, CH_W, CH_H, CH_FLOOR = 3.4, 2.5, 5.9, 4.0, 5.0
RAIL_TOP = CH_FLOOR + CH_H + LIP   # 11.5
STRAP_X0, STRAP_X1, STRAP_LEN = 29.0, 33.0, 26.0

def gear_points(phase_deg, n_flank=7, n_root=4):
    rp = M*Z/2; ra = rp + M; rf = rp - 1.25*M; rb = rp*math.cos(math.radians(20))
    inv = lambda a: math.tan(a)-a
    psi = math.pi/(2*Z) - BACKLASH/(2*rp)
    ap = math.radians(20)
    def th(r):
        r = max(r, rb)
        return psi + inv(ap) - inv(math.acos(rb/r))
    p = 2*math.pi/Z
    r0 = max(rf, rb)
    rs = [r0 + (ra-r0)*i/(n_flank-1) for i in range(n_flank)]
    pts = []
    for k in range(Z):
        c = math.radians(phase_deg) + k*p
        if rf < rb: pts.append((rf, c - th(rb)))
        for r in rs: pts.append((r, c - th(r)))
        for r in reversed(rs): pts.append((r, c + th(r)))
        if rf < rb: pts.append((rf, c + th(rb)))
        a0, a1 = c + th(rb), c + p - th(rb)
        for i in range(1, n_root):
            pts.append((rf, a0 + (a1-a0)*i/n_root))
    return [(r*math.cos(a), r*math.sin(a)) for r,a in pts]
