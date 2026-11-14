"""Grainy soft-gradient backgrounds in the style of a phone wallpaper: big blurred colour fields + film grain."""
import numpy as np, os
from PIL import Image, ImageDraw, ImageFilter

import pathlib
REPO = pathlib.Path(__file__).resolve().parents[2]   # repository root
OUT = str(REPO / "website" / "assets")
os.makedirs(OUT, exist_ok=True)

def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def field(w, h, base, blobs, blur=0.11, grain=9.0, seed=0, name="bg"):
    k = 4  # draw small, blur, upscale -> silky gradients
    sw, sh = w // k, h // k
    img = Image.new("RGB", (sw, sh), hexrgb(base))
    for (cx, cy, rx, ry, col, alpha) in blobs:
        mask = Image.new("L", (sw, sh), 0)
        d = ImageDraw.Draw(mask)
        x, y, a, b = cx * sw, cy * sh, rx * sw, ry * sh
        d.ellipse([x - a, y - b, x + a, y + b], fill=int(255 * alpha))
        mask = mask.filter(ImageFilter.GaussianBlur(blur * sw))
        img = Image.composite(Image.new("RGB", (sw, sh), hexrgb(col)), img, mask)
    img = img.filter(ImageFilter.GaussianBlur(blur * sw * 0.35)).resize((w, h), Image.BICUBIC)
    a = np.asarray(img).astype(np.float32)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, grain, (h, w, 1)) + rng.normal(0, grain * 0.35, (h, w, 3))  # mostly mono grain
    a = np.clip(a + n, 0, 255).astype(np.uint8)
    Image.fromarray(a).save(f"{OUT}/{name}.jpg", quality=90, subsampling=0)
    print(name, w, h)

LAV = "#F3EFFC"
# hero: lilac / periwinkle / pink petals, light centre-left for text
field(2400, 1350, LAV, [
    (0.85, 0.25, 0.42, 0.55, "#B9A5FF", .95),
    (1.02, 0.85, 0.40, 0.45, "#9DB2FF", .85),
    (0.62, 1.05, 0.38, 0.30, "#F4C6EA", .85),
    (0.72, 0.45, 0.20, 0.25, "#8E6CFF", .70),
    (0.10, -0.10, 0.35, 0.25, "#E3D9FF", .9),
], name="bg-hero", seed=1)
field(1170, 2532, LAV, [
    (0.80, 0.70, 0.75, 0.30, "#B9A5FF", .95),
    (0.20, 0.95, 0.70, 0.22, "#F4C6EA", .85),
    (0.95, 1.0, 0.50, 0.25, "#9DB2FF", .8),
    (0.60, 0.75, 0.35, 0.12, "#8E6CFF", .7),
], name="bg-hero-mobile", seed=2)
# soft section wash (very subtle)
field(2400, 1350, "#F7F5FD", [
    (0.0, 0.0, 0.45, 0.5, "#E6DDFF", .9),
    (1.0, 1.0, 0.45, 0.5, "#E9E2FF", .9),
    (0.9, 0.1, 0.25, 0.3, "#F7E3F3", .7),
], grain=7.0, name="bg-section-soft", seed=3)
# dark CTA wallpaper
field(2400, 1350, "#1B1438", [
    (0.20, 1.00, 0.55, 0.55, "#6E4BFF", .95),
    (0.85, 0.15, 0.45, 0.50, "#8E6CFF", .75),
    (0.55, 0.70, 0.30, 0.35, "#D58BD6", .55),
    (1.05, 1.05, 0.35, 0.35, "#6C86FF", .7),
], grain=11.0, name="bg-cta-dark", seed=4)
# card / tile texture
field(1200, 1200, "#F1ECFF", [
    (0.9, 0.1, 0.6, 0.6, "#CDBFFF", .9),
    (0.1, 1.0, 0.6, 0.5, "#F4D3EE", .8),
], grain=8.0, name="bg-card", seed=5)
# phone/desktop wallpapers as brand assets (nice for slides too)
field(1290, 2796, "#EDE6FF", [
    (0.5, 0.35, 0.60, 0.22, "#8E6CFF", .9),
    (0.1, 0.65, 0.60, 0.25, "#F4C6EA", .9),
    (0.95, 0.80, 0.55, 0.25, "#9DB2FF", .9),
], grain=10.0, name="wallpaper-phone", seed=6)

# transparent grain overlay tile for CSS (background-repeat)
rng = np.random.default_rng(9)
t = rng.normal(128, 40, (256, 256)).clip(0, 255).astype(np.uint8)
alpha = np.full((256, 256), 22, np.uint8)
Image.fromarray(np.dstack([t, t, t, alpha]), "RGBA").save(f"{OUT}/grain-overlay.png")
print("grain tile")
