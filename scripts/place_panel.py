"""Place the panel hardware on the breakoff tabs and rails: mouse bites, tooling holes and fiducials.

From a shell (pcbnew closed):
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/place_panel.py velvet74.kicad_pcb

Re-running it fails rather than duplicating parts. It overwrites the board it is given and rewrites the
neighbouring .kicad_pro, so run it on a scratch copy and put the board back.

Every part is board-only (not in the schematic), so the schematic parity check ignores them. Positions follow the
outline that make_both.js adds: 5 mm rails above and below the halves, joined by ten 5 mm tabs. It also adds the
keepouts that hold the pours off the rails and tabs, and unfills every zone (refill with kicad-cli or KiCad).
"""
import os
import sys

import pcbnew

F = pcbnew.FromMM
STOCK = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'KiCad', '10.0', 'share', 'kicad', 'footprints')
PROJ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', 'my-soffle.pretty')
# (library, footprint, reference, x, y, flip to the bottom side, rotation)
PARTS = [
    # mouse bites where each tab meets the board, rotated to lie along the horizontal edge
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB1', 77.0, 62.0, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB2', 113.0, 57.12, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB3', 149.0, 61.38, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB4', 218.0, 61.38, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB5', 254.0, 57.12, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB6', 290.0, 62.0, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB7', 95.0, 170.425, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB8', 135.0, 170.425, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB9', 232.0, 170.425, False, 90),
    (PROJ, 'MouseBite_5x0.5mm_P1mm', 'MB10', 272.0, 170.425, False, 90),
    # tooling holes in the rails, diagonally opposite (JLCPCB asks for 2 mm, as far apart as practical)
    (os.path.join(STOCK, 'MountingHole.pretty'), 'MountingHole_2.1mm', 'TH1', 60.0, 53.0, False, 0),
    (os.path.join(STOCK, 'MountingHole.pretty'), 'MountingHole_2.1mm', 'TH2', 307.0, 181.25, False, 0),
    # fiducials on the rails, on the bottom where every assembled part sits
    (os.path.join(STOCK, 'Fiducial.pretty'), 'Fiducial_1mm_Mask2mm', 'FID1', 75.0, 53.0, True, 0),
    (os.path.join(STOCK, 'Fiducial.pretty'), 'Fiducial_1mm_Mask2mm', 'FID2', 292.0, 53.0, True, 0),
    (os.path.join(STOCK, 'Fiducial.pretty'), 'Fiducial_1mm_Mask2mm', 'FID3', 183.5, 181.25, True, 0),
]

b = pcbnew.LoadBoard(sys.argv[1])
for lib, name, ref, x, y, flip, rot in PARTS:
    assert b.FindFootprintByReference(ref) is None, ref + ' already placed'
    fp = pcbnew.FootprintLoad(lib, name)
    assert fp, name
    nick = 'my-soffle' if lib == PROJ else os.path.basename(lib).replace('.pretty', '')
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    fp.SetParent(b)
    b.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
    if rot:
        fp.SetOrientationDegrees(rot)
    if flip:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetReference(ref)
    fp.Reference().SetVisible(False)
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    print(ref, name, 'at', x, y, 'bottom' if flip else 'top')
# The pours would flood the rails and tabs, leaving exposed copper and burrs where they snap, so keep every layer
# clear there: a band over each rail (both sit clear of the board, so no pour inside the board is touched) and one
# rectangle per tab, reaching 0.1 mm into the board edge.
KEEPOUTS = [('rail top keepout', 49.0, 50.0, 318.0, 56.0), ('rail bottom keepout', 49.0, 178.25, 318.0, 184.25)]
for x, edge in ((77.0, 62.0), (113.0, 57.12), (149.0, 61.38), (218.0, 61.38), (254.0, 57.12), (290.0, 62.0)):
    KEEPOUTS.append(('tab keepout x%g' % x, x - 2.6, 55.4, x + 2.6, edge + 0.1))
for x in (95.0, 135.0, 232.0, 272.0):
    KEEPOUTS.append(('tab keepout x%g' % x, x - 2.6, 170.325, x + 2.6, 178.85))
for name, x0, y0, x1, y1 in KEEPOUTS:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowZoneFills(True)   # KiCad 10 name for "keep out copper pours"
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)          # the tooling hole and fiducial live here
    z.SetDoNotAllowFootprints(False)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    z.SetZoneName(name)
    pts = z.Outline()
    pts.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.Append(F(x), F(y))
    b.Add(z)
    print(name, 'added')

for z in b.Zones():
    z.UnFill()
b.Save(sys.argv[1])
