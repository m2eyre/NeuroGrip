# Licensing: what we chose and your options

The repository ships with the **MIT License** in [`LICENSE`](../LICENSE), which covers everything in it: code, firmware, CAD, STLs, docs and images. That is a complete, valid setup and you can publish as-is.

Hardware projects often use a separate license for the physical design. Here are the three common setups, so you can switch before (or after) publishing.

## Option A: MIT for everything (current default)

- **What it means:** anyone can use, change, sell or close up any part of the project, as long as they keep the copyright notice.
- **Good for:** maximum adoption, hackathon projects, people who just want it used.
- **What to do:** nothing.

## Option B: MIT for code + CERN-OHL for hardware (recommended if you want a "proper" open-hardware project)

The CERN Open Hardware Licence v2 was written for physical designs (CAD, STLs, wiring). It comes in three strengths:

| Variant | In plain words |
|---|---|
| **CERN-OHL-P** (permissive) | Like MIT for hardware. Anyone can build, modify and sell, even closed |
| **CERN-OHL-W** (weakly reciprocal) | Changes to *your* design must stay open, but it can be combined with closed parts |
| **CERN-OHL-S** (strongly reciprocal) | Like GPL for hardware. Anyone who ships a modified version must publish their modified design files |

**What to do:**
1. Download the licence text from https://ohwr.org/cern_ohl_p_v2.txt (or `_w_v2.txt` / `_s_v2.txt`) and save it as `hardware/LICENSE`.
2. Add one line at the top of the root `LICENSE` file: `The contents of hardware/ are licensed under CERN-OHL-P-2.0, see hardware/LICENSE. Everything else is licensed under the MIT License below.`
3. Change the License section of `README.md` to say the same thing.

This is also what the [Open Source Hardware Association certification](https://certification.oshwa.org/) expects to see.

## Option C: MIT for code + CC BY-SA 4.0 for hardware, docs and images

Creative Commons licences are familiar and fine for docs, images and the website. They weren't written for hardware, but many printable-model sites (Printables, Thingiverse) use them.

- **CC BY 4.0:** anyone can reuse with credit.
- **CC BY-SA 4.0:** reuse with credit, and changed versions must use the same licence.

**What to do:** on GitHub, **Add file → Create new file**, name it `hardware/LICENSE`, click **Choose a license template**, pick *Creative Commons Attribution Share Alike 4.0*, and commit. Then add the same one-line note to the root `LICENSE` and the README as in Option B.

## Things the license doesn't cover

- **Third-party trademarks.** g.tec, Unicorn, OpenBCI, Muse, MyoWare, Arduino, Base44 and ElevenLabs are trademarks of their owners. The repo only mentions them, which is fine.
- **Medical claims.** No license makes it safe to sell this as a medical device. Keep the "not a medical device" note in the README.
- **Contributors.** Contributions are accepted under the same licence as the files they change (this is GitHub's default "inbound = outbound" rule).
