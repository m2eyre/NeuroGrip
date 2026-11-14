# Printing the parts

All four parts are in [`hardware/stl/`](../hardware/stl). They are already in print orientation: load them, don't rotate them, slice, print. **No supports are needed.**

| File | Part | Size (mm) | Solid volume |
|---|---|---|---|
| `NG_Base.stl` | Servo cradle, idler pillar, rail screw holes | 36 × 37 × 32 | 19.4 cm³ |
| `NG_FingerDriver.stl` | Finger + 14T gear, with the servo-horn pocket | 24 × 60 × 6 | 3.2 cm³ |
| `NG_FingerIdler.stl` | Mirrored finger + 14T gear, with the M3 pivot hole | 24 × 60 × 6 | 3.6 cm³ |
| `NG_WristMount.stl` | Curved wrist saddle with the T-slot rail and strap slots | 75 × 33 × 60 | 39.1 cm³ |

Expect about 35–45 g of filament for the set with the settings below.

## Material

- **PLA** works and is the easiest to print.
- **PETG** is tougher and better for the gear teeth, which take all the load. Use it if you have it.
- Avoid very flexible filaments for the fingers and base. TPU is fine for optional fingertip pads.

## Slicer settings

These are for a 0.4 mm nozzle on a typical FDM printer (Prusa, Bambu, Ender and so on). Start from your slicer's normal PLA or PETG profile and change only these:

| Setting | Base | Driver finger | Idler finger | Wrist mount |
|---|---|---|---|---|
| Orientation | As exported, flat bottom down | As exported, horn pocket **up** | As exported, flat | As exported, **standing on its end** |
| Layer height | 0.2 mm | 0.2 mm (0.15 for smoother teeth) | 0.2 mm (0.15 for smoother teeth) | 0.2 mm |
| Walls / perimeters | 3 | 4 | 4 | 3 |
| Top / bottom layers | 4 / 4 | 5 / 5 | 5 / 5 | 4 / 4 |
| Infill | 25–30 % | 40 % | 40 % | 25 % |
| Infill pattern | Gyroid or grid | Gyroid | Gyroid | Gyroid or grid |
| Supports | **Off** | **Off** | **Off** | **Off** |
| Adhesion | None (skirt) | None | None | **Brim, 5 mm** |

Why these choices:

- **4 walls on the fingers** means the gear teeth (module 1.5) are printed as solid plastic, not infill.
- **The wrist mount stands on its end** so the curved saddle and the rail profile print as clean outlines and the rail is strong along its length. It is tall and narrow, so the brim stops it from tipping.
- **No supports:** the strap slots, wire windows and the rail channel only need short bridges of 3–8.5 mm, which any printer handles.

## Tolerances

Clearances are already built into the models: 0.25 mm per side on the pockets, 0.2 mm of extra gear centre distance, and 0.2 mm of backlash on the teeth. If your printer is well calibrated, the parts fit as printed.

If parts are too tight:

1. **Elephant's foot** (first layer squashed outward) is the usual cause on the fingers. Turn on your slicer's elephant-foot compensation (about 0.15 mm) or lightly file the bottom edge of the gear.
2. If the servo horn won't go into the driver finger's pocket, use horizontal expansion / XY compensation of −0.05 to −0.1 mm on that part only, or open the pocket with a craft knife.
3. If the gears bind, check that the idler pivot screw isn't overtightened before you blame the print.

If the horn is loose in the pocket, a drop of CA (super) glue fixes it.

## Test before printing everything

The fingers are small, so print the **driver finger first** (about 20–30 minutes on most printers) and check that the SG90 horn presses into its pocket. That tells you your fit before you commit to the long wrist-mount print.

## Changing the size

The wrist curve, strap slot width and horn pocket are all parameters. See [cad.md](cad.md) to change them and export new STLs.

Next: [assembly](assembly.md).
