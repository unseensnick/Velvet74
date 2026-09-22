# Velvet74

The GitHub repo is `unseensnick/Velvet74` (renamed from `my-soffle`); the local folder and the `my-soffle` KiCad library keep the old name, because every part in the design references `my-soffle:...`.

A personal Sofle-style split keyboard with Choc switches and a chip-down RP2040 controller on the PCB. Key positions, board outline and case come from Ergogen; parts, nets and fabrication data live in a KiCad 10 project aimed at JLCPCB assembly. The user owns a Keebart Sofle Choc Pro and uses it as the physical reference.

## Working approach

- **Investigate before planning when context is thin.** Read the script, the relevant board or schematic section and `.claude/rules/kicad.md` first. For non-trivial work run `/scout`, which investigates and then plans. Present a plan only once confident, then wait for approval.
- **Cite before you claim.** Every concrete claim about a script, part, net, coordinate or clearance carries a `file:line` just read. Memory and `Handoff.md` are hypotheses until checked against current files.
- **Define done and the check that could fail**: an ERC/DRC count before and after, a reproduction on a scratch copy of the board, a Freerouting pass. "DRC is clean" does not prove a placement is routable.
- **Stop and replan when blocked.** Never circumvent a hook, a failing check or a tool denial.
- **Offload deep multi-file work to subagents** (`/code-research` for broad questions).
- **Claude places parts and checks; the user routes and fine-tunes by hand.** Treat every uncommitted design file as irreplaceable hand work.

## KiCad and Ergogen: the rules that bite

Full detail and the reasons are in [.claude/rules/kicad.md](.claude/rules/kicad.md), which loads when KiCad, script, Ergogen or template files are in play. The short version:

1. **Ergogen owns geometry only** (points, outline, case). **The schematic owns parts, nets and LCSC fields.** Never move part or net data into Ergogen.
2. **Scripts overwrite work.** `place_from_ergogen.py` replaces the outline and switch/LED/cap/diode positions; `build_rp2040_module.py` wipes the template's routing. Never re-run either over hand edits without warning the user and getting a yes.
3. **Close KiCad** (or at least the file) before a script saves a board, and check `git status` first.
4. **`pcbnew.BOARD.Save` rewrites the neighbouring `.kicad_pro` with defaults** (net classes gone). Scripts that save a board inside a project back up and restore the `.kicad_pro`.
5. **KiCad 10.0.3 only.** Use `%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad-cli.exe` and `python.exe`. KiCad 8.0.9 is still installed but cannot open these files (tag `kicad8-final` is the last KiCad 8 state). API changes are in the rule file.
6. **Placements must be proven routable**, not only DRC-clean: every signal pin of a fine-pitch IC keeps a straight escape lane, support parts sit in line with the pin they serve (not across other pins' escapes), and routability is checked by routing a copy.
7. **Keep the machine usable**: at most 6 idle-priority, single-threaded heavy jobs (autorouting, renders) at once.
8. **Never edit or delete** `*-backups/` or `.history/`: they are the only way back from a bad script run.

## Where things live

| Path | What it is |
| --- | --- |
| `sofle-choc-pro.kicad_sch`, `sofle-choc-pro-half.kicad_sch` | The root sheet and the half it uses twice, as sheets Left and Right. **Edit the half**: both halves follow. Left keeps the references (U1, SW10), Right adds 200 (U201, SW210); every net is per half (`/Left/GP0`, `/Right/GND`), power included, through local power symbols |
| `sofle-choc-pro.kicad_pcb` / `.kicad_pro` / `.kicad_dru` | One board holding both halves 10 mm apart, the key area placed from Ergogen; net classes; custom DRC rules |
| `lib/my-soffle.kicad_sym`, `lib/my-soffle.pretty/`, `lib/my-soffle.3dshapes/` | Project symbols, footprints (Choc hotswap, EC11 combo, SK6812MINI-E, reset switch) and 3D models |
| `fp-lib-table`, `sym-lib-table` | Project library tables |
| `templates/rp2040-inner-column/` | KiCad template: RP2040 module (schematic, placed and routed 2-layer board, `README.md` with checks and routability, `meta/info.html`, `lib/`) |
| `ergogen/` | Pinned Ergogen 4.2.1: `config.yaml` (live layout; `points.mirror` puts the right half `half_gap` past the left's inner edge), `make_both.js` (twins every outline and case for the right half, since Ergogen cannot mirror a polygon), `export_points.js`, `npm run build`. One run writes both halves to `output/`; it and `config.both.yaml` are generated and gitignored |
| `scripts/place_from_ergogen.py` | On both halves: moves SWnn onto `points.json` and H1-H5, J1-J3 onto `mounts.json`, runs `snap_leds.py`, **replaces Edge.Cuts** |
| `scripts/snap_leds.py` | Snaps LEDnn, C1nn, Dnn onto each switch (back side), within each half |
| `scripts/halves.py` | Finds a footprint's (half, role) from its sheet path, so scripts say ('Right', 'SW10') and never compute SW210 |
| `scripts/render_keycaps.py` | Stdlib SVG render of keycaps and knobs from Ergogen output (read-only for the board) |
| `scripts/strip_signals.py` | **Deletes every track and via that is not on GND, +5V, +3.3V, +1V1, VBUS, VBUS_FUSED or LINK_VBUS** (either half), to clear a board for hand routing; zones are untouched; restores `.kicad_pro` |
| `scripts/build_rp2040_module.py` | Rebuilds the template board from a netlist and places parts; **overwrites the template board, routing included**; restores `.kicad_pro` |
| `scripts/transfer_module_routing.py` | Copies routing from a routed test board onto the template; **writes the template board** |
| `scripts/ribbon/` | Parked experiment: an octilinear router for the parallel-lane look, with its own pipeline and `README.md`. No script in it writes the project board (`apply.py` writes a copy) |
| `sofle-choc-pro-backups/`, `templates/rp2040-inner-column/RP2040InnerColumn-backups/` | KiCad's project backup zips, tracked in git on purpose (the user wants them kept) |

Run KiCad scripts from a shell with KiCad closed: `"%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/<script>.py <args>` (each docstring has the exact form). Plain-Python tooling: `uv run --no-project python`.

## Checks

- ERC: `kicad-cli sch erc --severity-error --exit-code-violations sofle-choc-pro.kicad_sch`
- DRC: `kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations sofle-choc-pro.kicad_pcb` (template: compare against the expected items in its README). Known items: 26 `courtyards_overlap`, the H1-H5 holes against their neighbouring switches, 13 per half
- Ergogen: `npm run build` in `ergogen/`

## Commit messages

Every commit follows [.claude/rules/workflow.md](.claude/rules/workflow.md): subject `type(scope): summary`, imperative, lower-case, no trailing period, `<=72` chars; body leads with 1-2 plain sentences, then benefit-first bullets; no em dashes; no AI watermarks; no bare `#N`. Enforced by `.githooks/commit-msg` and by the `Commit standards` workflow on PRs.

## Guardrails

- `.claude/hooks/` screens tool calls before they run, so an unexplained `Blocked:` comes from here.
  - `block-dangerous-commands.sh` (Bash **and** PowerShell): no push to `main`/`master`, no force push (`--force-with-lease` is allowed), no `gh pr merge` (merging is the user's call), no recursive deletes of roots, home or system dirs, no `git reset --hard` / `git clean -f`, no reading secret files through the shell, no deleting `*-backups/` or `.history/`. It asks before `git checkout -- ...`, `git checkout .`, `git restore` and forced switches, which discard uncommitted board edits.
  - `protect-files.sh` (Edit/Write): denies secrets, `.git/`, lock files, hook scripts, `*-backups/`, `.history/`, `ergogen/output/`; asks before `.claude/settings*.json`, `.githooks/`, and any KiCad design file (`*.kicad_pcb/sch/pro/sym/mod/dru`, `fp-lib-table`, `sym-lib-table`).
  - `warn-large-files.sh` blocks writes into dependency/build dirs and binary/archive files; `scan-secrets.sh` asks when content looks like a credential; `session-start.sh` prints branch and dirty state; `notify.sh` raises a desktop notification.
  - Test the guards after any hook change: `bash .claude/hooks/tests/run-all.sh` (fixtures in `.claude/hooks/tests/fixtures/<hook>/`). The hooks need `jq`.
- `.claude/settings.json` holds the allow/ask/deny lists: read-only git and `kicad-cli` checks are allowed; push, PR and issue writes, `gh api`, rebase, amend, reset, tag, `git checkout --` and `git restore` ask; secret files and history-destroying git commands are denied.
- `.githooks/commit-msg` is tracked; activate it once per clone with `git config core.hooksPath .githooks`.

## Skills

`/scout` plans one non-trivial task from evidence; `/code-research` answers broad questions across many files; `/debug-fix` (`--fast` for urgent fixes); `/ship` commits, pushes and opens a PR with a confirmation at every step and never merges; `/session-handoff` writes the gitignored `Handoff.md` and updates memory; `/tighten` trims docs and comments after planning the cuts.
