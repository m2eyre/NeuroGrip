# CAD: changing the design

There are two copies of the same geometry. Use whichever fits your tools.

| | Where | Good for |
|---|---|---|
| **Python** (manifold3d + trimesh) | [`hardware/cad/python/`](../hardware/cad/python) | Regenerating STLs anywhere, clash checks, renders. Free |
| **SolidWorks** VBA macro | [`hardware/cad/solidworks/NeuroGrip_Build.bas`](../hardware/cad/solidworks/NeuroGrip_Build.bas) | A native, editable SolidWorks part set and a movable assembly with gear mates |

**Keep them in sync:** the numbers in `params.py` and the constants at the top of the macro are the same design. If you change one, change the other.

## Python

```bash
cd hardware/cad/python
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python export_stl.py     # rebuild hardware/stl/*.stl in print orientation
python check.py          # part volumes + interference between parts from 0° to 50° of opening
python render.py         # neurogrip_render.png and gear_mesh.png
```

| File | What it is |
|---|---|
| `params.py` | Every dimension, in mm, plus the involute gear profile |
| `build.py` | Builds each part (`base()`, `finger()`, `wrist_mount()`, a `servo()` stand-in) and `assembly(open_deg)` |
| `export_stl.py` | Writes the four printable STLs, centred and on the bed |
| `check.py` | Prints part-to-part intersection volumes. Every number should be 0 |
| `render.py` | Quick matplotlib renders |

## SolidWorks

1. **Tools → Macro → New…** and save `NeuroGrip.swp` in an empty folder.
2. In the VBA editor, delete the empty `Sub main()`, then **File → Import File… → `NeuroGrip_Build.bas`**. (If you paste the code instead, delete the first line, `Attribute VB_Name…`.)
3. Press **F5** to run `main`. It saves the parts and `NeuroGrip_Assembly.SLDASM` to `<macro folder>\NeuroGrip_CAD\`. A message box at the end lists anything that needed a fallback.
4. **Moving it:** drag either finger and both move.
   - `Gear_FingerSync`: 1:1 gear mate (the macro checks the fingers turn in opposite directions).
   - `Opening_Limit`: limit angle mate, 0–35°.
   - `Opening_Angle`: suppressed. Unsuppress and edit it to drive an exact opening.
   - `Slide_Limit_0-15mm`: lets the clamp slide along the rail.
5. You need default Part and Assembly templates set (**Tools → Options → Default Templates**). Mate names assume English SolidWorks, but the macro renames the default planes itself, so other languages work.

The macro was written alongside the Python model and hasn't been run in every SolidWorks version. If a feature or mate fails, it is listed in the final message box and the macro keeps going. Please open an issue with that message.

## Dimensions worth changing

Measure your servo with calipers first. SG90 clones vary.

| Python (`params.py`) | Macro | Default | What it is |
|---|---|---|---|
| `HORN_SEAT` | `HORN_SEAT` | 29.5 | Servo body bottom to the underside of the horn arm |
| `HORN_LEN`, `HORN_W0`, `HORN_W1`, `HORN_HUB_D` | same | 17.5, 6.4, 4.6, 7.6 | Single-arm horn size |
| `WR_RI` | `WR_RI` | 38 | Wrist saddle radius. Smaller for small wrists |
| `STRAP_LEN` | `STRAP_LEN` | 26 | Strap slot length. 26 for 25 mm velcro, 21 for 20 mm |
| `FIT` | `FIT` | 0.25 | Clearance per side on pockets |
| `CD_EXTRA`, `BACKLASH` | same | 0.2, 0.2 | Gear centre-distance allowance and tooth backlash for FDM |
| `M`, `Z` | `G_M`, `G_Z` | 1.5, 14 | Gear module and tooth count |
| `SV_*` | `SV_*` | SG90 | Servo body. Change for an MG90S or another micro servo |

After changing anything, run `python check.py` (all zeros) and `python export_stl.py`.
