# RP2040 Inner Column Module

A KiCad 8 template for a chip-down RP2040 controller that lives on the back of a Choc split keyboard,
in the strip beside the inner key column, the way the Keebart Sofle Choc Pro does it. The layout
follows the ScottoModules idea: copy the schematic and board into a keyboard project, then wire the
GPIO labels to the matrix.

The circuit is the controller half of the audited `sofle-choc-pro.kicad_sch` in the repo root, so
reference designators and LCSC part numbers match the keyboard.

## Board

- No Edge.Cuts: the modules are pasted into an existing keyboard board, which brings its own outline.
- Two groups, like ScottoModules, each moving as one unit on the host board:
  - **USB and power**: J1, U4, R5, R6, F1, D1, U5, C9, C18, C19, C20
  - **RP2040**: U1, the flash U3 with C3, the crystal X1 with C1, C4 and R2, the USB series resistors
    R7 and R8, all RP2040 decoupling caps, BOOT/RESET (SW1, SW2, R4) and the JLC marker
- As placed, the two groups fill a 19.56 x 41.6 mm strip measured from the free space on the Sofle
  board, whose top and right are real board edges; the left and bottom meet the key area. That
  arrangement is the one the routability check below covers. Pull the groups apart only if the host
  board needs it, and leave room for the traces between them.
- Every part is on the back (B.Cu) for single-sided JLCPCB assembly.
- The RP2040 sits at 45 degrees. USB pins point at the USB-C connector on the top edge, QSPI pins at
  the flash (also at 45 degrees) up and to the right, GP18-29 and GP12-17 fan out to the left and
  bottom-left, and GP0-11 run straight down to the bottom edge. BOOT/RESET are along the bottom edge
  and the regulator group sits beside the USB-C shell.
- Routing room is built in: pads of different parts are at least 0.6 mm apart (mostly 0.8 mm), and
  other parts keep 1.6 mm off the RP2040 pins for fanout and vias.
- The price of that room: decoupling caps are 2.4 to 6.7 mm from their pins (3.9 mm on average), the
  crystal is 2.9 mm from XIN, the 27 ohm USB resistors are within 3.7 mm, and the longest flash line
  (SS) is about 15 mm.
- Silkscreen holds only the footprint outlines and a `JLCJLCJLCJLC` marker, which JLCPCB replaces with
  the order number. Reference designators are on B.Fab.
- `RP2040InnerColumn.kicad_dru` allows 0.15 mm clearance inside the RP2040 and USB-C courtyards
  (0.4 and 0.5 mm pitch pins); 0.2 mm applies everywhere else. JLCPCB's standard 2-layer minimum is
  0.127 mm.
- **Parts are placed, not routed.**

## Checks

```bash
kicad-cli pcb drc --schematic-parity --severity-error RP2040InnerColumn.kicad_pcb
```

At placement: 0 schematic parity issues, no courtyard or clearance errors, 0 silkscreen warnings.
Known and expected:

- `invalid_outline`: the template has no Edge.Cuts on purpose; it goes away inside the host board.
- Two errors from the USB-C footprint itself (C2927039, `TYPE-C-SMD_HX-TYPE-C-16PIN`): its GND pads
  are 0.204 mm from the NPTH peg holes against the board's 0.25 mm hole clearance rule. The same
  footprint is used on the Sofle board.

## Routability

The placement was chosen by autorouting many variants (RP2040 straight or at 45 degrees, positions,
flash and USB resistor placement, spacing) with Freerouting, on a copy of the board with every GPIO
forced out to a pad in a 3 mm strip on the left and bottom edges, where the key area continues.
This placement was the only one that routed completely on 2 layers. The autorouted copy was
imported back into KiCad and checked there at 0.15 mm clearance: every signal and power net
connected with no clearance errors. With GND pours on both layers and stitching vias, all GND pads
joined except the GND pads of C6 and C11, where the autorouter's traces left no room for a via.
When routing by hand, drop a GND via beside each decoupling cap before routing the signals.

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
