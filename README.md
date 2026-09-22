# my-soffle

A personal Sofle-style split keyboard with Choc switches and a chip-down RP2040 on each half. Key positions,
the board outline and the case come from [Ergogen](https://github.com/ergogen/ergogen); parts, nets and
fabrication data live in a KiCad 10 project aimed at JLCPCB assembly.

## The board

One 4-layer board, 268 x 118 mm, holds both halves 10 mm apart. Each half has 37 keys: a 6 x 5 matrix, 5 thumb
keys and 2 EC11 encoders that double as keys, each with an SK6812MINI-E under it.

- **Controller (per half):** RP2040, W25Q128JV 16 MB QSPI flash, 12 MHz ABM8-272-T3 crystal, AP2112K-3.3 LDO,
  BOOTSEL and RESET buttons.
- **USB-C host port:** 1.1 A polyfuse, B5819W reverse-current diode into +5V, SMF5.0A TVS on VBUS, USBLC6-2P6 on
  the data pair.
- **USB-C link port:** joins the halves (+5V, ground and a one-wire link on GP12), protected by its own USBLC6-2P6.
- **Display:** a 0.91" SSD1306 module on the 4-pin J3 header (I2C1).
- **Stackup:** signals on F.Cu and B.Cu, the +5V plane on In1 (with a +3.3V island under the controller), GND on
  In2. Power runs through the planes.

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
- `lib/`: project symbols, footprints and 3D models.
- `ergogen/`: the live layout (`config.yaml`). `npm run build` writes both halves' points, outline and case to
  `ergogen/output/`.
- `scripts/`: KiCad Python scripts that place parts from the Ergogen points and snap LEDs, diodes and caps to their
  switches.
- `templates/rp2040-inner-column/`: the RP2040 module the controller block started from, with its own README.
- `production/`: JLCPCB Gerbers, drill files, BOM and placement, regenerated from the board before an order.

`CLAUDE.md` has the detailed file map, the rules for editing the design safely, and the checks.

## Checks

```bash
kicad-cli sch erc --severity-error --exit-code-violations sofle-choc-pro.kicad_sch
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations sofle-choc-pro.kicad_pcb
```

ERC is clean. DRC reports 26 known `courtyards_overlap` items: mounting holes H1-H5 against their neighbouring
switches, 13 per half.

## Requirements

- KiCad 10.0.3. Tag `kicad8-final` is the last state KiCad 8 can open.
- The JLCPCB symbol and footprint libraries (`PCM_JLCPCB-*`), from the KiCad Plugin and Content Manager.
- Node.js for Ergogen (pinned in `ergogen/package.json`).
