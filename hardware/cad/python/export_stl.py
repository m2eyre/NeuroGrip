"""Regenerate the printable STLs in ../../stl from params.py + build.py.

    pip install -r requirements.txt
    python export_stl.py          # writes NG_*.stl into hardware/stl/

Each part is centred on X/Y and dropped onto Z=0 in its print orientation, so
you can load it straight into a slicer without rotating it.
"""
import pathlib
import numpy as np
from build import base, finger, wrist_mount, tm

OUT = pathlib.Path(__file__).resolve().parents[2] / "stl"


def on_bed(mesh):
    lo, hi = mesh.bounds
    mesh.apply_translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    return mesh


def main():
    OUT.mkdir(exist_ok=True)
    wrist = tm(wrist_mount())
    # stand the wrist mount on its end: the saddle profile goes on the bed
    wrist.apply_transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    parts = {
        "NG_Base": tm(base()),
        "NG_FingerDriver": tm(finger(True)),
        "NG_FingerIdler": tm(finger(False)),
        "NG_WristMount": wrist,
    }
    for name, mesh in parts.items():
        on_bed(mesh).export(OUT / f"{name}.stl")
        print(f"{name}.stl  {mesh.volume / 1000:.1f} cm3  size {np.round(mesh.extents, 1).tolist()} mm")


if __name__ == "__main__":
    main()
