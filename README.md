# Velvet74

A 74-key split keyboard with Choc switches and a chip-down RP2040 on each half, in the Sofle layout. Key positions,
the board outline and the case come from [Ergogen](https://github.com/ergogen/ergogen); parts, nets and
fabrication data live in a KiCad 10 project aimed at JLCPCB assembly.

## The board

One 4-layer board, 268 x 118 mm before the panel rails, holds both halves 10 mm apart. Each half has 37 keys: a 6 x 5 matrix, 5 thumb
keys and 2 EC11 encoders that double as keys, each with an SK6812MINI-E under it.

- **Controller (per half):** RP2040, W25Q128JV 16 MB QSPI flash, 12 MHz ABM8-272-T3 crystal, AP2112K-3.3 LDO,
  BOOTSEL and RESET buttons.
- **USB-C host port:** 1.1 A polyfuse, B5819W reverse-current diode into +5V, SMF5.0A TVS on VBUS, USBLC6-2P6 on
  the data pair.
- **USB-C link port:** joins the halves (+5V, ground and a one-wire link on GP12), protected by its own USBLC6-2P6.
- **Display:** a 0.91" SSD1306 module on the 4-pin J3 header (I2C1).
- **Stackup:** signals on F.Cu and B.Cu, the +5V plane on In1 (with a +3.3V island under the controller), GND on
  In2. Power runs through the planes.
- **Panel:** the halves ship as one 268 x 131 mm panel. A 5 mm rail above and below carries the 2 mm tooling holes
  and three fiducials, and ten 5 mm tabs hold the halves, five per half, away from the USB-C cutouts. Mouse bites
  perforate each tab at the board edge: snap the tabs, then file the nubs flat. Nothing is left on the keyboard.

The schematic draws one half (`sofle-choc-pro-half.kicad_sch`) and uses it twice, as sheets `Left` and `Right`.
Left references are plain (U1, SW10); right ones add 200 (U201, SW210). Both halves share one pin map.

## Pin map (both halves)

| Function | Pins |
| --- | --- |
| Rows 1-5, thumb row | GP5, GP4, GP3, GP2, GP1, GP0 |
| Columns outer to inner | GP29, GP28, GP27, GP26, GP25, GP24 |
| Encoder 1 (SW16) | A GP13, B GP14, key column GP20 |
| Encoder 2 (SW65) | A GP18, B GP19 |
| Display I2C1 | SDA GP6, SCL GP7 |
| RGB data | GP10, through the U6 level shifter to 5 V |
| Split link | GP12 |
| VBUS sense | GP9 (10k/10k divider) |
| Handedness jumper JP1 | GP8 (3.3 V = left, GND = right) |

37 LEDs at full white exceed the USB budget, so firmware should cap RGB brightness (around 120 of 255).

## Layout

- `sofle-choc-pro.kicad_pro` / `.kicad_sch` / `.kicad_pcb` / `.kicad_dru`: the KiCad project, with the half sheet
  above.
- `lib/`: project symbols, footprints and 3D models (`my-soffle.*`), and the used JLCPCB library parts (`jlcpcb/`).
- `datasheets/`: manufacturer datasheets for every part on the board, synced from LCSC.
- `ergogen/`: the live layout (`config.yaml`). `npm run build` writes both halves' points, outline and case to
  `ergogen/output/`.
- `scripts/`: KiCad Python scripts that place parts from the Ergogen points and snap LEDs, diodes and caps to their
  switches.
- `templates/rp2040-inner-column/`: the RP2040 module the controller block started from, with its own README.
- `production/`: JLCPCB Gerbers, drill files, BOM and placement, regenerated from the board before an order.

`CLAUDE.md` has the detailed file map, the rules for editing the design safely, and the checks.

## Getting started

**To open, review or edit the design** you need only [KiCad 10](https://www.kicad.org/download/) (made with
10.0.3); open `sofle-choc-pro.kicad_pro`. Every library part the design uses is in the repo: the project's own parts
in `lib/my-soffle.*`, and the JLCPCB parts it uses in `lib/jlcpcb/` (copied from the JLCPCB library, MIT). The
remaining parts and 3D models are KiCad's stock ones. No Plugin and Content Manager packages, environment variables
or library setup are needed, and the 3D viewer shows every part. KiCad 8 cannot open these files; tag
`kicad8-final` is the last KiCad 8 state.

**To regenerate the layout** (key positions, outline, case): [Node.js](https://nodejs.org/) 18 or newer (Ergogen's `mathjs` dependency
requires it), then

```bash
cd ergogen && npm install && npm run build
```

Ergogen 4.2.1 is pinned in `ergogen/package.json`; the output lands in `ergogen/output/`.

**To run the scripts in `scripts/`:** KiCad's bundled Python (`<KiCad>/10.0/bin/python.exe` on Windows), with KiCad
closed. Each script's docstring says how to run it and what it overwrites.

**To regenerate `production/`:** the Fabrication Toolkit plugin (from the KiCad Plugin and Content Manager), with
its automatic translation left **off**. JLCPCB's zero degrees is the part's orientation in its own LCSC package
drawing, which differs from KiCad's for some packages, so each affected part carries an `FT Rotation Offset` or
`FT Position Offset` field checked against JLC's own footprint. The plugin's name-matching rules would rotate parts
that are already right.

**To commit:** activate the tracked commit-message hook once per clone with `git config core.hooksPath .githooks`
(see `CLAUDE.md` for the message format).

## Checks

```bash
kicad-cli sch erc --severity-error --exit-code-violations sofle-choc-pro.kicad_sch
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations sofle-choc-pro.kicad_pcb
```

Expected: ERC has no errors. DRC has 26 known `courtyards_overlap` errors (mounting holes H1-H5 against their
neighbouring switches, 13 per half) and no unconnected items or parity issues. With all severities shown there are
also known warnings: 24 ERC `pin_to_pin` warnings and 3 `lib_symbol_mismatch` (J201, J202 and JP201 differ from their
library copies), and DRC silkscreen and `lib_footprint_mismatch` warnings for parts edited on the board.

## License

The design files, scripts and documentation are released under the MIT license (see `LICENSE`): you may use,
modify, build and sell them as long as the copyright notice is kept. The design comes with no warranty; check it
yourself before ordering boards.

Credits and third-party parts:

- The layout follows the [Sofle keyboard](https://github.com/josefadamcik/SofleKeyboard) by Josef Adamcik
  (MIT, (c) 2019 Josef Adamcik).
- `lib/jlcpcb/` holds parts of [CDFER/JLCPCB-Kicad-Library](https://github.com/CDFER/JLCPCB-Kicad-Library)
  (MIT, (c) 2024 Chris Dirks, license in `lib/jlcpcb/LICENSE`).
- `lib/my-soffle.3dshapes/SW_Hotswap_Kailh_Choc_V1.wrl` and the Choc hotswap footprints derive from
  [kiswitch/keyswitch-kicad-library](https://github.com/kiswitch/keyswitch-kicad-library) (MIT and CC-BY-SA 4.0).
- `datasheets/` holds the manufacturers' datasheets. They are the manufacturers' copyright, included for reference
  only, and are not covered by this project's license.
