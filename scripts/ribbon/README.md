# Ribbon router

Experimental router for the Reddit-style look: traces run as octilinear lanes parallel to each key's keepout outline, so later traces bundle beside earlier ones. None of these scripts write the project board; `apply.py` writes a copy.

Pipeline (KiCad 10 Python for pcbnew steps, `uv run --no-project --with shapely` for the rest):

1. `extract.py board.kicad_pcb board.json`: pads, board outline and cutouts.
2. `channels.py board.json map`: optional channel-map renders per layer.
3. `make_links.py board.json links.json [NET ...]`: matrix links (switch to diode, rows and columns as MST, LED data chain).
4. `ribbon.py board.json links.json routes.json [prior_routes.json]`: routes links in order; prior routes stay fixed. `WINDOW` env widens the search box (default 6 mm).
5. `apply.py in.kicad_pcb routes.json out.kicad_pcb`: writes tracks and vias onto a copy, restores the `.kicad_pro`.
6. `dump_board.py` and `render_crop.py`: PNG review renders.

Rules baked in: 0.2 mm tracks at 0.4 mm pitch, 0.45/0.2 mm vias, clearances 0.205 / 0.26 / 0.5 mm (small margins over DRC because pads are polygonised), no turn sharper than 90 degrees including through a via.

Status: the 2-layer key matrix routes completely (136 links, 124 vias, DRC 0 clearance errors on a scratch copy). Power, controller area and U1-to-matrix bundles are not done.
