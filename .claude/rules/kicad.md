---
paths:
  - "**/*.kicad_*"
  - "**/fp-lib-table"
  - "**/sym-lib-table"
  - "scripts/**"
  - "ergogen/**"
  - "templates/**"
---

# KiCad and Ergogen work

The detail behind the traps listed in `CLAUDE.md`. Every point here cost a session once.

## Who owns what

- **Ergogen owns geometry only**: key points, board outline, case. `ergogen/config.yaml` (Ergogen 4.2.1, pinned in `ergogen/package.json`). Rows are bottom-up; each point carries `row_code` / `col_index`, which form the schematic reference (`SW` + row + col), and `led: north|east|south|west`.
- **The schematic owns parts, nets and LCSC fields.** It was audited against the RP2040 and part datasheets. Never move nets or part data into Ergogen, and never "fix" a part by editing the board: change the schematic, then update the PCB from it.
- `scripts/place_from_ergogen.py` is the bridge: it moves the schematic's SWnn footprints onto `ergogen/output/points.json`, snaps LEDs, caps and diodes with `snap_leds.py`, and replaces the board's Edge.Cuts with Ergogen's outline.
- To change geometry: edit `ergogen/config.yaml`, run `npm run build` in `ergogen/`, then re-run the placement script (after warning the user, see below).
- The root `soffle-*.yaml` files are the older standalone Ergogen configs described in `README.md`; `ergogen/config.yaml` is the live one.

## Scripts overwrite work

- `scripts/place_from_ergogen.py` replaces Edge.Cuts and moves every listed switch plus its LED, cap and diode. The user fine-tunes some positions by hand in KiCad (TH4 / SW64 in particular). **Never re-run it over hand edits without warning the user first.**
- `scripts/build_rp2040_module.py` regenerates `templates/rp2040-inner-column/RP2040InnerColumn.kicad_pcb` from the netlist and **deletes all routing** on it. The template is routed now; do not run it unless the user asks for a rebuild and has confirmed losing the routing.
- `scripts/transfer_module_routing.py` writes tracks, vias and the GND pour onto the template from a routed test board.
- **KiCad must be closed** (or the file not open) before a script saves a board. KiCad holds the file in memory and a later save from the GUI silently overwrites the script's result, or the script overwrites unsaved GUI work.
- Before a script writes a design file, check `git status`: uncommitted hand edits in that file are unrecoverable except through `*-backups/` zips and `.history/`.

## KiCad 10 traps

- The project is on **KiCad 10.0.3** (`%LOCALAPPDATA%\Programs\KiCad\10.0\bin`: `kicad-cli.exe`, `python.exe`). KiCad 8.0.9 is still installed in `C:\Program Files\KiCad\8.0` but cannot open these files; tag `kicad8-final` marks the last KiCad 8 state. Never run a script with KiCad 8's Python.
- **`pcbnew.BOARD.Save` on a fresh `pcbnew.BOARD()` rewrites the neighbouring `.kicad_pro` with defaults**, deleting the user's net classes (Power3.3V, Power5V, USB) and rules. Any script that saves a board inside a project must back up and restore the `.kicad_pro` (see `build_rp2040_module.py`). `LoadBoard` then `Save` migrates the `.kicad_pro` properly instead.
- API: `FOOTPRINT.GetFieldByName` is gone, use `GetField(name)`; Datasheet and Description are built-in fields. Netlists put one token per indented line and write empty fields as `(field (name "X"))`. DRC adds `footprint_symbol_field_mismatch`.
- KiCad 10 resolves `${KICAD8_3RD_PARTY}` to `Documents\KiCad\10.0\3rdparty`, so older library tables still load. The global fp-lib-table nests stock libraries as a `Table` row using `${KICAD10_FOOTPRINT_DIR}`; scripts that read tables must follow that (see `libs()` in `build_rp2040_module.py`).
- KiCad 10 keeps a `.history/` local-history git repo in project folders. It is gitignored and must never be edited or deleted.
- `kicad-cli pcb drc --refill-zones --save-board` writes the board. A read-only check never passes `--save-board`.

## Verification

- ERC: `kicad-cli sch erc --severity-error --exit-code-violations <file>.kicad_sch`
- DRC: `kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations <file>.kicad_pcb`. The template has known expected items (listed in its `README.md` under Checks); compare against that list instead of treating every violation as new.
- Ergogen: `npm run build` in `ergogen/` must finish and write `output/points.json`.
- **DRC-clean is not routable.** The first RP2040 placement passed DRC and could not be routed: parts sat across other pins' escapes. What works, measured on the RP2040 Community Edition controllers (Splinky, Frood, Sea-Picro, Helios in `keyboard-refs`):
  - Every signal pin keeps a straight escape lane. USB (46/47) and QSPI (51-56) always stay clear.
  - Supply pins escape **inward**, as on Raspberry Pi's RP2040 Minimal R3: B.Cu zones "U1 +3V3 ring" and "U1 +1V1 ring" sit between the exposed pad and the pin tips, and four 0.55/0.25 mm corner vias join the +3V3 ring to the In1 +3.3V island (a 0.6/0.3 via cannot meet the 0.35 mm hole rule there, see U1's 4.5 mm F.Cu thermal pad). Pins 1, 10, 22 and 33 are decoupled through the ring and the plane, so no cap sits in the matrix, encoder or flash escapes. Caps go where no signal leaves: the corners, in front of power-only pin runs (42-45, 48/49), and under pin 23. Each 3.3 V cap gets its own via to the island. Pins 48/49 sit on a ring arc cut off by the +1V1 fingers and reach +3.3V only through C16.
  - Power widths: 0.2 mm for +3.3V and +1V1 (each under 100 mA, RP2040 datasheet p.156/p.624), 0.5 mm for +5V/VBUS. Every +5V pin drops to the In1 +5V plane, which is why the +3.3V island only covers the U1/flash block plus a west strip to U5.
  - Support parts may be 0.3-0.5 mm apart; the old blanket 0.8 mm gap is dropped (the user confirmed it was never their rule).
  - Signal vias may go in the ring between the exposed pad and the pin ring.
  - Prove routability by routing a copy (the ribbon router, KiCad Routing Tools, or Freerouting; Freerouting results swing a lot with DSN order, so score several shuffled orders).

## Machine load

Parallel autorouting or rendering jobs: **at most 6, idle priority, single-threaded each.** About 24 made the user's browser lag.
