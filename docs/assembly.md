# Assembling the gripper

![Assembly render](images/neurogrip_render.png)

## What you need

- The 4 printed parts ([printing guide](printing.md))
- SG90 servo with its **single-arm horn**, the horn screw and the 2 tab screws
- About 25 mm of **1.75 mm filament** (the lock pin that holds the base on the rail)
- **No other screws or nuts.** The base slides onto a printed dovetail rail and the idler finger snaps onto a printed pin.
- About 30 cm of 25 mm velcro strap
- Rubber bands or grip tape for the fingertips
- Small Phillips screwdriver (servo screws only) and flush cutters for the filament pin
- A way to set the servo to 90° before fitting the horn: the flashed Nano is easiest ([software setup](software-setup.md))

## How the mechanism works

Each finger is printed in one piece with a 14-tooth gear. The **driver finger** sits on the SG90 horn. The **idler finger** meshes with it and turns freely on a printed snap-fit pin that is part of the base, so the two fingers always mirror each other. Servo travel is limited to about 35°, which takes the jaws from 2 mm to about 60 mm.

![Gear mesh](images/gear_mesh.png)

## Steps

1. **Servo into the base.** Feed the cable and plug out through one of the wire windows. Drop the servo into its pocket with the **output shaft toward the fingers** (the shaft lands next to the pillar). Screw down both tabs with the servo's tab screws.
2. **Centre the servo.** Wire the servo to the Nano ([wiring](wiring.md)), flash the firmware, open the Serial Monitor and type `a 90`. The servo moves to 90°.
3. **Driver finger.** Press the horn into the driver finger's pocket. Push the finger onto the servo spline with the **jaw pointing straight forward**, which is the closed position. Screw the horn screw in through the hub hole.
4. **Idler finger.** Line it up so its jaw mirrors the driver jaw with about a 2 mm gap and the teeth meshed, then **press it straight down over the split pin** on top of the pillar. The two halves of the pin squeeze together and the barb clicks over the gear. It should spin freely with a little end play. To take it off, pinch the pin halves together with pliers and lift.
5. **Grip surfaces.** Wrap rubber bands around each jaw so they sit in the two notches, or stick grip tape on the inner faces.
6. **Base onto the wrist mount.** Slide the dovetail groove under the base onto the dovetail rail on top of the wrist mount, from either end. Line up the cross hole in the side of the base with one of the holes in the rail. The rail holes are every 6 mm, so pick the position you want along the forearm. Push a 25 mm piece of 1.75 mm filament through the base and the rail, then snip it flush. To move the base, pull the filament out with pliers.
7. **Strap.** Thread the velcro up through one side slot, under the wrist, up through the other slot, and fold it back on itself.
8. **Find the opening direction.** Type `a 110`. If the jaws open, you're done. If they push into each other, your servo opens the other way, so use angles below 90 in [calibration](calibration.md).

Keep servo travel within about 35° of the closed angle (for example 90 closed, 120 open). The firmware refuses open/closed settings more than 40° apart.

## Fitting tips

- **Small or large wrist:** the saddle radius is 38 mm (adult wrist). Add 2–3 mm of foam inside, or change `WR_RI` and re-export ([cad.md](cad.md)).
- **20 mm velcro:** the slots are 26 mm long for 25 mm strap. Set `STRAP_LEN = 21` for 20 mm strap.
- **Horn fit:** the driver finger's horn pocket is a press fit. It has 0.1 mm clearance and five small crush ribs that the horn squashes as you push it in. Press it in with your thumb, or squeeze it in a vise. If it's too tight, shave the ribs with a knife. If it's still loose (an older print, or a smaller horn), any of these fixes it:
  - a drop of CA (super) glue or hot glue in the pocket before you press the horn in. Hot glue can be peeled out later.
  - a layer of masking or Kapton tape around the horn arm as a shim.
  - the horn's own tiny screws: drill through the horn's outer holes into the finger (1.5 mm pilot) and screw them in from below.
  - always fit the **horn screw** through the hub hole into the servo. That stops the finger lifting off the spline, which can feel like slop.
- **Base too loose or tight on the rail:** change `DT_FIT` (default 0.25 mm per side) and re-export, or lightly sand the rail tongue.
- **Snap pin too stiff:** widen the split with a craft knife or set `PIN_SLOT_W` to 2.0. If the idler lifts off, set `PIN_BARB_D` to 6.1.
- **No filament for the pin:** a straightened paperclip or a 2 mm drill bit shank also works.

Next: [wiring](wiring.md).
