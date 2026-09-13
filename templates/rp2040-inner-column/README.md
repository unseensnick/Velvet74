# RP2040 Inner Column Module

A KiCad 8 template for a chip-down RP2040 controller that lives on the back of a Choc split keyboard,
in the strip beside the inner key column, the way the Keebart Sofle Choc Pro does it. The layout
follows the ScottoModules idea: copy the schematic and board into a keyboard project, then wire the
GPIO labels to the matrix.

The circuit is the controller half of the audited `sofle-choc-pro.kicad_sch` in the repo root, so
reference designators and LCSC part numbers match the keyboard.

## Board

- 19.56 x 41.6 mm, measured from the free strip on the Sofle board. The top and right edges are real
  board edges there; the left and bottom meet the key area.
- Every part is on the back (B.Cu) for single-sided JLCPCB assembly.
- USB-C mouth sits on the top edge, ESD array directly behind it, then the RP2040. The flash faces
  the QSPI pins, the crystal sits at XIN/XOUT, and BOOT/RESET are along the bottom edge.
- Decoupling caps are within 1.5 mm of their pins where the space allows (all 1V1 caps are); the
  worst 3.3 V cap is 4.3 mm away.
- Silkscreen holds only the footprint outlines and a `JLCJLCJLCJLC` marker below the RP2040, which
  JLCPCB replaces with the order number. Reference designators are on B.Fab.
- **Parts are placed, not routed.**

## Checks

```bash
kicad-cli pcb drc --schematic-parity --severity-error RP2040InnerColumn.kicad_pcb
```

At placement: 0 schematic parity issues, no courtyard, clearance or edge errors, 0 silkscreen
warnings. Two known errors come from the USB-C footprint itself (C2927039, `TYPE-C-SMD_HX-TYPE-C-16PIN`):
its GND pads are 0.204 mm from the NPTH peg holes against the board's 0.25 mm hole clearance rule.
The same footprint is used on the Sofle board.

## Rebuilding the placement

`scripts/build_rp2040_module.py` generates the board from the schematic netlist. It overwrites the
board file, routing included, so only run it before routing:

```bash
kicad-cli sch export netlist -o module.net templates/rp2040-inner-column/RP2040InnerColumn.kicad_sch
```

```bash
"C:/Program Files/KiCad/8.0/bin/python.exe" scripts/build_rp2040_module.py module.net
```

## Bill of materials

| References | Qty | Value | Footprint | LCSC |
| --- | --- | --- | --- | --- |
| C1, C4 | 2 | 15pF | C_0402 | [C1548](https://jlcpcb.com/partdetail/C1548) |
| C3, C5, C6, C10, C11, C12, C13, C14, C15, C16, C17 | 11 | 100nF | C_0402 | [C1525](https://jlcpcb.com/partdetail/C1525) |
| C7, C8, C19, C20 | 4 | 1uF | C_0402 | [C52923](https://jlcpcb.com/partdetail/C52923) |
| C9, C18 | 2 | 10uF | C_0603 | [C19702](https://jlcpcb.com/partdetail/C19702) |
| D1 | 1 | B5819W SL | D_SOD-123 | [C8598](https://jlcpcb.com/partdetail/C8598) |
| F1 | 1 | 500mA | Fuse_1206_3216Metric | [C163512](https://jlcpcb.com/partdetail/C163512) |
| J1 | 1 | USB-C 16P | TYPE-C-SMD_HX-TYPE-C-16PIN | [C2927039](https://jlcpcb.com/partdetail/C2927039) |
| R2, R4 | 2 | 1k | R_0402 | [C11702](https://jlcpcb.com/partdetail/C11702) |
| R5, R6 | 2 | 5.1k | R_0402 | [C25905](https://jlcpcb.com/partdetail/C25905) |
| R7, R8 | 2 | 27 | R_0402 | [C25100](https://jlcpcb.com/partdetail/C25100) |
| SW1, SW2 | 2 | BOOT, RESET | SW_Push_1P1T_XKB_TS-1187A | [C318884](https://jlcpcb.com/partdetail/C318884) |
| U1 | 1 | RP2040 | QFN-56-1EP_7x7mm_P0.4mm | [C2040](https://jlcpcb.com/partdetail/C2040) |
| U3 | 1 | W25Q128 | SOIC-8 5.3 mm | [C97521](https://jlcpcb.com/partdetail/C97521) |
| U4 | 1 | SRV05-4 | SOT-23-6 | [C2836319](https://jlcpcb.com/partdetail/C2836319) |
| U5 | 1 | AP2112K-3.3 | SOT-23-5 | [C51118](https://jlcpcb.com/partdetail/C51118) |
| X1 | 1 | ABM8-272-T3 | Crystal SMD 3.2 x 2.5 | [C20625731](https://jlcpcb.com/partdetail/C20625731) |

## Libraries

- `PCM_JLCPCB` (CDFER JLCPCB-Kicad-Library, installed through the KiCad Plugin and Content Manager)
- `rp2040_module`, bundled in `lib/`: the TS-1187A button footprint and its 3D model
