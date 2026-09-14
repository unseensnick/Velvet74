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
- **DRC-clean is not routable.** A placement handed to the user for routing needs at least 0.8 mm between pads of different parts, a ~2 mm fanout ring around fine-pitch ICs, and proof with Freerouting (score several shuffled DSN orders and take the best; results swing a lot with order alone). The first RP2040 placement passed DRC and could not be routed.

## Machine load

Parallel autorouting or rendering jobs: **at most 6, idle priority, single-threaded each.** About 24 made the user's browser lag.
