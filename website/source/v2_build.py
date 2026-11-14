import math, os, sys, re, shutil, pathlib
REPO = pathlib.Path(__file__).resolve().parents[2]   # repository root
sys.path.insert(0, str(REPO / "hardware" / "cad" / "python"))
from params import *

ROOT = str(REPO / "website")
A = ROOT + "/assets"
os.makedirs(A + "/icons", exist_ok=True)

INK, PURPLE, LILAC, PERI, BLUSH = "#16122B", "#6E4BFF", "#B9A5FF", "#9DB2FF", "#F4C6EA"

def rot(p, a, c=(0, 0)):
    x, y = p[0] - c[0], p[1] - c[1]; ca, sa = math.cos(a), math.sin(a)
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)
def P(pts): return "M" + "L".join(f"{x:.2f},{-y:.2f}" for x, y in pts) + "Z"   # mm, y up -> svg y down

def arms(open_deg, fill):
    a = math.radians(open_deg)
    g1 = [rot(p, a) for p in gear_points(0)]; f1 = [rot(p, a) for p in FINGER_POLY]
    g2 = [rot((CD + x, y), -a, (CD, 0)) for x, y in gear_points(180 + 180 / Z)]
    f2 = [rot((CD - x, y), -a, (CD, 0)) for x, y in FINGER_POLY]
    return "".join(f'<path d="{P(p)}" fill="{fill}"/>' for p in (g1, f1, g2, f2))

def gap(open_deg, d):
    a = math.radians(open_deg)
    p = rot((JAW_IN, d), a); q = rot((CD - JAW_IN, d), -a, (CD, 0))
    return ((p[0] + q[0]) / 2, -(p[1] + q[1]) / 2, math.hypot(q[0] - p[0], q[1] - p[1]))

GRAD = f'''<linearGradient id="ng" x1="0" y1="1" x2="0.25" y2="0"><stop offset="0" stop-color="{PURPLE}"/><stop offset=".6" stop-color="#8E6CFF"/><stop offset="1" stop-color="{LILAC}"/></linearGradient>'''

def logo_svg(mono=None, pulse=True, open_deg=16):
    fill = mono or "url(#ng)"
    mx, my, w = gap(open_deg, JAW_D1 - 7)
    pc = mono or "#FF7AB6"
    pulse_p = (f'<path d="M{mx-w*.40:.2f},{my:.2f}H{mx-w*.12:.2f}L{mx-w*.03:.2f},{my-4.5:.2f}L{mx+w*.07:.2f},{my+3:.2f}'
               f'L{mx+w*.13:.2f},{my:.2f}H{mx+w*.40:.2f}" fill="none" stroke="{pc}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>') if pulse else ""
    hubs = "" if mono else f'<circle cx="0" cy="0" r="3.2" fill="#fff" opacity=".9"/><circle cx="{CD}" cy="0" r="1.6" fill="#fff" opacity=".9"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-14 -52 49.2 66"><defs>{GRAD}</defs>'
            f'{arms(open_deg, fill)}{hubs}{pulse_p}</svg>')

def hero_svg():
    od = 14
    mx, my, w = gap(od, (JAW_D0 + JAW_D1) / 2 + 2)
    r = w / 2 - 0.3
    base = (f'<rect x="{BASE_X0}" y="{-BASE_D1}" width="{BASE_X1-BASE_X0}" height="{BASE_D1-BASE_D0}" rx="2.5" fill="rgba(255,255,255,.55)" stroke="rgba(255,255,255,.9)" stroke-width=".25"/>'
            f'<rect x="-6.1" y="-5.6" width="12.2" height="22.5" rx="1.2" fill="rgba(110,75,255,.10)" stroke="rgba(110,75,255,.25)" stroke-width=".2"/>'
            f'<circle cx="{CD}" cy="0" r="{PILLAR_D/2}" fill="rgba(110,75,255,.12)"/>')
    ball = (f'<defs><radialGradient id="ball" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff"/><stop offset=".55" stop-color="#EDE7FF"/><stop offset="1" stop-color="{LILAC}"/></radialGradient>'
            f'<filter id="sh" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter></defs>'
            f'<ellipse cx="{mx+1}" cy="{my+2}" rx="{r}" ry="{r*.9}" fill="#3B2A8F" opacity=".22" filter="url(#sh)"/>'
            f'<circle cx="{mx}" cy="{my}" r="{r}" fill="url(#ball)"/>')
    hubs = f'<circle cx="0" cy="0" r="{HORN_HUB_D/2}" fill="#fff" opacity=".85"/><circle cx="{CD}" cy="0" r="1.7" fill="#fff" opacity=".85"/>'
    # technical callouts
    def call(x1, y1, x2, y2, label, anchor="start"):
        tx = x2 + (1.2 if anchor == "start" else -1.2)
        return (f'<circle cx="{x1}" cy="{y1}" r=".55" fill="{INK}"/><path d="M{x1},{y1}L{x2},{y2}" stroke="{INK}" stroke-width=".14"/>'
                f'<text x="{tx}" y="{y2+.55}" font-family="Geist Mono,monospace" font-size="2.0" fill="{INK}" text-anchor="{anchor}" letter-spacing=".08">{label}</text>')
    calls = (call(mx + r * .7, my - r * .7, 33, -55, f"OBJECT · Ø {2*r:.0f} mm")
             + call(CD + 9, -2, 34, -10, "14T · m1.5 GEARS")
             + call(-2, 9, -12, 19, "SG90 SERVO", "end")
             + call(-1.5, -38, -12, -46, "JAW 2–60 mm", "end"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-33 -61 92 85"><defs>{GRAD}</defs>{base}{ball}'
            f'{arms(od, "url(#ng)")}{hubs}{calls}</svg>')

open(A + "/logo-mark.svg", "w").write(logo_svg())
open(A + "/logo-mark-ink.svg", "w").write(logo_svg(mono=INK))
open(A + "/logo-mark-white.svg", "w").write(logo_svg(mono="#FFFFFF"))
open(A + "/hero-gripper.svg", "w").write(hero_svg())
WORD = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 330 66">'
        f'<g transform="translate(0,0) scale(1)">{logo_svg().replace("<svg ", "<svg width=\"49\" height=\"66\" ")}</g>'
        f'<text x="62" y="45" font-family="Geist,Inter,sans-serif" font-weight="600" font-size="38" letter-spacing="-1.2" fill="{INK}">NeuroGrip</text></svg>')
open(A + "/logo-horizontal.svg", "w").write(WORD)

# icons recoloured for light theme
src = A + "/icons"   # line-icon SVGs (stroke="currentColor" originals give the best result)
ICON = {}
for f in os.listdir(src):
    if f.endswith("-cyan.svg"): continue
    s = open(f"{src}/{f}").read()
    ICON[f[:-4]] = s
    open(f"{A}/icons/{f}", "w").write(s.replace('stroke="currentColor"', f'stroke="{PURPLE}"'))

def ic(name, size=24):
    return ICON[name].replace('width="24" height="24"', f'width="{size}" height="{size}"')

def inl(svg): return re.sub(r"<svg ", '<svg class="fill" ', svg, count=1)

shutil.copy(str(REPO / "docs" / "images" / "neurogrip_render.png"), A + "/cad-render.png")

# signal trace for how-it-works
def trace(w=1200, h=120):
    import random
    rnd = random.Random(4); pts = []
    for i in range(0, w + 1, 3):
        t = i
        v = math.sin(t * .05) * .5 + math.sin(t * .13 + 1) * .3 + math.sin(t * .31 + 2) * .2
        v *= 10
        sx = 430
        v += 46 * math.exp(-((t - sx) / 14) ** 2) * math.sin((t - sx) / 14 * 3.2)
        pts.append(f"{i},{h/2 + v:.1f}")
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" class="trace"><defs><linearGradient id="tg" x1="0" x2="1">'
            f'<stop offset="0" stop-color="{LILAC}"/><stop offset=".36" stop-color="{PURPLE}"/><stop offset="1" stop-color="{PERI}"/></linearGradient></defs>'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="url(#tg)" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>')

STEPS = [("eeg-headset", "Intent", "Clench your jaw or blink hard. The g.tec Unicorn headset reads it: 8 channels at 250 Hz."),
         ("code", "Detect", "Python filters the raw EEG and flags the clench when it crosses your calibrated threshold."),
         ("usb", "Command", "A one-byte open or close command goes to the Arduino over USB serial."),
         ("chip", "Actuate", "The Arduino Nano turns it into a PWM pulse for the SG90 micro-servo."),
         ("gear-grip", "Grip", "Two printed gear-fingers mirror each other: 2 mm closed, about 60 mm open.")]

steps_html = "".join(f'''<div class="step"><div class="step-top"><span class="mono">0{i+1}</span><span class="dot"></span></div>
<div class="icon">{ic(n, 26)}</div><h3>{t}</h3><p>{d}</p></div>''' for i, (n, t, d) in enumerate(STEPS))

BOM = [("SG90 micro servo", "$2.50"), ("Arduino Nano (clone)", "$5.00"), ("PLA filament, ~40 g", "$1.00"),
       ("M3 screws, nuts + velcro strap", "$4.00"), ("Grip tape / rubber bands", "$1.00")]
bom_html = "".join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in BOM)

html = open(os.path.join(os.path.dirname(__file__), "v2_template.html")).read()
html = (html.replace("{{LOGO}}", logo_svg()).replace("{{LOGO_WHITE}}", logo_svg(mono="#FFFFFF"))
        .replace("{{HERO}}", hero_svg()).replace("{{TRACE}}", trace()).replace("{{STEPS}}", steps_html)
        .replace("{{BOM}}", bom_html).replace("{{IC_VOICE}}", ic("voice", 18)).replace("{{IC_PLAY}}", "▶"))
open(ROOT + "/neurogrip-reference-site.html", "w").write(html)
print("built")
st = open(os.path.join(os.path.dirname(__file__), "v2_style.html")).read()
st = st.replace("{{LOGO}}", logo_svg()).replace("{{LOGO_W}}", logo_svg(mono="#FFFFFF")).replace("{{LOGO_I}}", logo_svg(mono=INK))
open(ROOT + "/style-guide.html", "w").write(st)
print("style")
