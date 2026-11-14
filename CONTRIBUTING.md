# Contributing to NeuroGrip

Thanks for helping. This started as a 24-hour hackathon build, so there's plenty to improve.

## Good first contributions

- Print it and report what didn't fit (with your printer, material and slicer).
- Try a new input source and add it to `software/sources/` (see [docs/alternative-inputs.md](docs/alternative-inputs.md)).
- Compile the sketches on other boards (Nano clone, Uno, ESP32) and tell us what needed changing.
- Fix a typo or an unclear step in the docs.

## How to send a change

1. Fork the repository and create a branch.
2. Make your change. Keep CAD numbers in `hardware/cad/python/params.py` and the constants at the top of `hardware/cad/solidworks/NeuroGrip_Build.bas` in sync.
3. If you changed geometry, run `python export_stl.py` and `python check.py` in `hardware/cad/python/` and commit the new STLs.
4. If you changed the bridge, run `python neurogrip_bridge.py --source sim --no-serial` and check that holding J still triggers.
5. Open a pull request that says what you changed and how you tested it.

## Safety

Please don't market or describe changes as medical-grade. If you test with people, follow your institution's rules for human-subject testing.
