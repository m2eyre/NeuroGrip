# NeuroGrip website

**Live site:** https://neurogrip.base44.app

This folder has everything needed to rebuild the NeuroGrip landing page: a working HTML reference version, the design assets, section-by-section screenshots, and the prompt we used with [Base44](https://base44.com/) (an AI app/site builder). You can rebuild it in Base44, in any other site builder, or host the HTML directly.

| Path | What it is |
|---|---|
| `neurogrip-reference-site.html` | The full page as plain HTML/CSS. Open it in a browser (keep `assets/` next to it) |
| `style-guide.html` | Colours, type, buttons and logo on one page |
| `assets/` | Backgrounds, logos, 3D renders of the real CAD, icons |
| `reference-screens/` | Screenshots of every section, for uploading to Base44 as references |
| `audio/` | ElevenLabs narration MP3s (`story.mp3`, `calib-1…6.mp3`, all merged in `neurogrip-voice.mp3`) and the script they were made from |
| `source/` | Scripts that regenerate the backgrounds, the HTML and the screenshots (see the end of this file) |

## Three ways to put the site online

1. **Base44 (what we did):** follow the steps below.
2. **GitHub Pages, no builder at all:** turn on Pages for this repository (see the upload guide) and the page is live at `https://m2eyre.github.io/neurogrip/website/neurogrip-reference-site.html`.
3. **Any static host** (Netlify, Vercel, Cloudflare Pages): drag the `website/` folder in, and rename `neurogrip-reference-site.html` to `index.html` first.

Things to fill in before it goes public: the demo video (section 03), team photos and names (section 06), and the links on the "Download the STLs" and "View on GitHub" buttons (point them at your repository's Releases page and main page).

The look is a light lavender page with soft, grainy gradient backgrounds (like the iPhone 15 wallpapers), thin hairlines, mono "spec sheet" labels and ink-black pill buttons. The stats section and the arms logo are carried over from v1.

## How to use this with Base44 (the easy way)

1. **Upload these as reference images** in your first Base44 prompt:
   - `reference-screens/00-full-page-desktop.jpg`: the whole page, top to bottom
   - `reference-screens/10-style-guide.jpg`: colours, fonts, buttons, logo
2. **Upload these as site assets** so Base44 uses the real files rather than trying to redraw them:
   - `assets/bg-hero.jpg`, `assets/bg-hero-mobile.jpg`, `assets/bg-section-soft.jpg`, `assets/bg-card.jpg`, `assets/bg-cta-dark.jpg`, `assets/grain-overlay.png`
   - `assets/logo-mark.png` (the arms), `assets/logo-horizontal.png`, `assets/logo-mark-white.png`
   - `assets/render-hero.png` (smooth 3D render of the real CAD holding a ball, with a transparent background), plus `render-closed.png`, `render-open.png` and `render-top.png` for the build section
   - `assets/icons/*.svg` (already purple). `hero-gripper.png` is the older flat illustration, kept as a backup.
3. **Paste the master prompt below.**
4. If a section comes out wrong, upload that section's screenshot (`01-hero.jpg` … `08-cta-footer.jpg`) and say "make the ___ section match this image exactly".
5. **Optional shortcut:** `neurogrip-reference-site.html` is a working version of the whole page. If Base44 lets you paste code or a custom HTML block, it can copy styles from it directly. Open it in a browser to see it live (keep the `assets/` folder next to it).

## Master prompt (paste into Base44)

> Build a one-page landing site for **NeuroGrip**, a brain-controlled, 3D-printed prosthetic gripper. Match the attached full-page reference image and style guide closely. It should look like a premium tech product page (Apple / Linear style), not a generic template.
>
> **Style.** Light theme. Page background #F6F3FD. Text: headlines #16122B, body #4A4463, captions #8C86A6. Accent purple #6E4BFF, lilac #B9A5FF, lilac-soft #EDE7FF. Gradient for highlighted words: linear-gradient(120deg, #6E4BFF, #8E6CFF 40%, #B9A5FF 75%, #F4C6EA). Fonts from Google Fonts: **Geist** (headlines weight 500 with tight -0.035em letter spacing, body 400), **Instrument Serif italic** for the second line of every heading, and **Geist Mono** for small uppercase labels with 0.12em letter spacing. Cards are white with a 1px #E4DDF6 border, 32px corner radius and a soft purple shadow (0 20px 50px -24px rgba(59,42,143,.28)). Frosted cards on gradient backgrounds are white at 62% opacity with a 14px backdrop blur. All buttons are pills: the primary one is #16122B with white text, the secondary one is frosted white. Overlay the uploaded grain-overlay.png across the whole page at 50% opacity, multiply blend, for a film-grain texture. Use the uploaded gradient images as section backgrounds. Do not recreate them with CSS. Max content width 1200px. Generous spacing: 140px between sections on desktop and 84px on mobile.
>
> **Sections, in order:**
> 1. **Floating nav.** A frosted pill bar 24px from the top with the arms logo + "NeuroGrip", links (Demo, How it works, Impact, Build, Team), and a black pill button "Hear its story" with a sound-wave icon that plays the ElevenLabs narration.
> 2. **Hero** on bg-hero.jpg (bg-hero-mobile.jpg on phones). Left: a small frosted chip "● BUILT AT HACK THE NEST 2026"; a huge headline "Think it." with "Grip it." on the next line in Instrument Serif italic using the purple gradient; the line "A prosthetic gripper you control with a jaw clench, read straight from an EEG headset. Printed in an afternoon, under $15 in parts."; buttons "Watch the demo →" (black) and "Hear its story" (frosted); a 3-column spec row with hairline dividers: 8 ch / EEG INPUT, 1 servo / SG90 DRIVE, 2–60 mm / JAW RANGE. Right: render-hero.png (a transparent 3D render) with four small frosted mono label pills next to the parts (OBJECT · Ø 21 MM, 14T · M1.5 GEARS, SG90 SERVO, VELCRO WRIST SADDLE) and the caption "FIG. 01: NEUROGRIP, REV A". Small "+" crosshair marks in the top corners.
> 3. **Track strip.** A thin full-width band with hairline top and bottom borders, in mono: TRACKS · Mind & Machine · Best use of ElevenLabs · Best use of Base44 · g.tec Unicorn EEG.
> 4. **"01 · The problem".** Heading "Millions of people." / italic "Hands that cost too much." Three tall stat cards: **57.7M** "people live with a limb amputation caused by trauma alone" (this card uses bg-card.jpg and a gradient number); **1 in 10** "people who need assistive technology, prosthetics included, can actually get it"; **~1 in 4** "upper-limb prosthesis users stop using their device". Each card has a mono source line at the bottom above a hairline.
> 5. **"02 · How it works"** on bg-section-soft.jpg. Heading "From a thought to a grip," / italic "in five steps." A thin purple EEG signal line with one spike and a black tag "CLENCH DETECTED → CLOSE". Then 5 frosted step cards (01 Intent, 02 Detect, 03 Command, 04 Actuate, 05 Grip), each with a lilac-soft rounded icon tile.
> 6. **"03 · Demo".** A large rounded video frame on bg-cta-dark.jpg with a frosted round play button, "Watch it grab a cup." in white, and mono "● REC · LIVE DEMO" / "00:42" in the corners.
> 7. **"04 · The price gap".** Heading "A powered hand costs" / italic "as much as a car." Left card: a large outlined square labelled "$20,000+ Typical myoelectric hand" next to a tiny purple square labelled "<$15 NeuroGrip parts" (drawn to scale). Right card: huge "1,300×" in the gradient, "as many NeuroGrips", and a parts table with mono prices.
> 8. **"05 · The build".** Heading "Two gears. One servo." / italic "Zero supports." A white card holding three lavender tiles with render-closed.png, render-open.png and render-top.png (each with a mono caption), then a 4×2 spec grid with hairline dividers (Jaw range 2–60 mm, Tip force ≈0.35 kgf, Actuator 1×SG90, Gears 14T·m1.5, Print No supports, Mount Velcro wrist, Signal 8 ch EEG, Brain Arduino Nano).
> 9. **"06 · The team".** Heading "Built in 24 hours" / italic "at Hack the Nest." Four photo cards and mono track badges.
> 10. **Footer CTA** on bg-cta-dark.jpg. Huge white "Open source." / italic "Print one tonight." Buttons "Download the STLs ↓" (white pill) and "View on GitHub" (glass). A mono footer row with the white logo, "Hack the Nest 2026 · Ypsilanti, MI" and "Think it. Grip it."
>
> **Motion.** Subtle fade-up on scroll. The signal line draws from left to right when it comes into view. Buttons lift 2px on hover. Nothing flashy.
> **Mobile.** Single column, nav collapses to the logo and a round play button, and the hero buttons go full width.

## Design tokens

| Token | Value | Use |
|---|---|---|
| Background | `#F6F3FD` | Page |
| Surface | `#FFFFFF` | Cards |
| Glass | `rgba(255,255,255,.62)` + blur 14px | Cards and nav on gradients |
| Line | `#E4DDF6` | Borders, hairlines |
| Ink | `#16122B` | Headlines, primary buttons |
| Body | `#4A4463` | Paragraphs |
| Muted | `#8C86A6` | Sources, captions |
| Purple | `#6E4BFF` | Accent, labels, icons |
| Lilac | `#B9A5FF` | Secondary accent |
| Lilac soft | `#EDE7FF` | Icon tiles |
| Periwinkle | `#9DB2FF` | Gradient partner |
| Blush | `#F4C6EA` | Gradient partner |
| Gradient | `linear-gradient(120deg,#6E4BFF,#8E6CFF 40%,#B9A5FF 75%,#F4C6EA)` | Highlighted words, the big numbers |

Type: Geist (H1 132px, H2 68px, H3 24px, body 17px), Instrument Serif italic for one phrase per heading, Geist Mono 12px uppercase labels.

## Files

- `reference-screens/`: what Base44 should copy (full desktop page, full mobile page, 8 section crops, style guide)
- `assets/`: the real files the site should use (grainy backgrounds, logos, hero illustration, icons, CAD render, a phone wallpaper)
- `neurogrip-reference-site.html` + `style-guide.html`: the working source the screenshots were taken from
- `source/`: scripts that regenerate everything (the backgrounds come from `v2_bg.py`, the 3D renders come from `source/3d/`, which renders the real STLs with three.js)

## Sources for the numbers on the page

Check these before you publish, and keep the wording careful.

- **57.7 million** people living with limb amputation from traumatic causes (2017): McDonald et al., *Prosthetics and Orthotics International*, 2021. https://pubmed.ncbi.nlm.nih.gov/33274665/
- **1 in 10** people who need assistive products (including prostheses) have access: WHO, *Standards for Prosthetics and Orthotics*, 2017. https://www.who.int/publications/i/item/9789241512480 . Say "assistive devices like prostheses", never "1 in 10 amputees".
- **~1 in 4** adults abandon upper-limb prostheses (mean rejection ~26 % body-powered, ~23 % electric): Biddiss & Chau, *Prosthetics and Orthotics International*, 2007. https://pubmed.ncbi.nlm.nih.gov/17979010/
- **$20,000–$100,000+** for a powered (myoelectric) hand: a commonly reported US price range. It varies a lot by model and fitting, so present it as a range.
- **Parts cost:** the table adds up to $13.50 from typical online prices and excludes the EEG headset and laptop. Swap in your real receipts. The "1,300×" headline is $20,000 ÷ ~$15.


## Regenerating the assets (optional)

You only need this if you want to change colours, copy or renders.

```bash
pip install numpy pillow manifold3d trimesh
python source/v2_bg.py          # grainy gradient backgrounds -> assets/
python source/v2_build.py       # logos, icons, HTML -> neurogrip-reference-site.html, style-guide.html
npm install playwright          # once
node source/v2_render.js        # screenshots -> reference-screens/ (saved as .png; we converted them to .jpg)
```

The 3D renders (`render-*.png`) come from `source/3d/`: `export.py` exports posed STLs from the CAD, `scene.html` renders them with three.js, and `shoot.js` screenshots them with Playwright. These scripts were written for a one-off render and may need small path tweaks on your machine.
