"""Snap each key's LED, LED decoupling cap and matrix diode onto its switch.

Place and rotate only the switches (SWnn), then run this. Pairing comes from the
reference numbers the schematic uses, SWnn -> LEDnn, C1nn, Dnn, within each half:
parts are matched by (half, role) through halves.py, so SW210 pairs with LED210.

Inside pcbnew:  Tools > Scripting Console, then
    exec(open(r"<project>/scripts/snap_leds.py").read())
From a shell (pcbnew closed):
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/snap_leds.py sofle-choc-pro.kicad_pcb
"""
import math
import os
import re
import sys

import pcbnew

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
except NameError:  # exec() from the scripting console has no __file__
    sys.path.insert(0, os.path.join(os.path.dirname(pcbnew.GetBoard().GetFileName()), 'scripts'))
import halves

# Offsets in the switch's own frame (mm, KiCad y down, 0,0 = key centre). Checked
# with DRC against the plain hotswap footprint, the Choc/EC11 combo footprint and
# neighbouring keys at 18 x 17 mm pitch. The LED must stay at 0,+4.7: the socket
# holes block the other side and the combo's bent A/C/B row sits just beyond it.
# Keys sit at 180 degrees with the LED north, so local +x is the key's left and +y its top.
# The diode offsets were scanned against every key's pads, holes and courtyards (0.3 mm gap).
LED = (0.0, 4.7)
CAP = (4.6, 4.7)     # 0402 standing vertical, beside the LED
DIODE = (7.6, 2.0)   # SOD-123 standing vertical, top-left of the key (as seen from the front)
DIODE_COMBO = (7.5, 5.0)   # combo keys: the EC11 tab slot at x 8 pushes the diode higher
DIODE_ROTATION = 90


def _local_to_board(sw, offset):
    pos = sw.GetPosition()
    angle = math.radians(sw.GetOrientationDegrees())
    dx, dy = offset
    # KiCad rotates counter-clockwise as seen on the y-down board
    x = dx * math.cos(angle) + dy * math.sin(angle)
    y = -dx * math.sin(angle) + dy * math.cos(angle)
    return pcbnew.VECTOR2I(pos.x + pcbnew.FromMM(x), pos.y + pcbnew.FromMM(y))


def _put(fp, sw, offset, extra_rotation):
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)  # everything snapped here lives on the back
    fp.SetOrientationDegrees(sw.GetOrientationDegrees() + extra_rotation)
    fp.SetPosition(_local_to_board(sw, offset))


def snap(board):
    parts = halves.by_role(board)
    moved, missing = 0, []
    for (half, role), sw in sorted(parts.items()):
        m = re.fullmatch(r'SW(\d{2})', role)
        if not m:
            continue
        n = m.group(1)
        diode = DIODE_COMBO if 'EC11_Combo' in sw.GetFPIDAsString() else DIODE
        for other, offset, rotation in ((f'LED{n}', LED, 0), (f'C1{n}', CAP, 90), (f'D{n}', diode, DIODE_ROTATION)):
            if (half, other) in parts:
                _put(parts[(half, other)], sw, offset, rotation)
                moved += 1
            else:
                missing.append(f'{half} {other}')
    return moved, missing


def main():
    if len(sys.argv) > 1:
        board = pcbnew.LoadBoard(sys.argv[1])
        moved, missing = snap(board)
        board.Save(sys.argv[1])
    else:
        board = pcbnew.GetBoard()
        moved, missing = snap(board)
        pcbnew.Refresh()
    print(f'snapped {moved} footprints' + (f'; not found: {", ".join(missing)}' if missing else ''))


# place_from_ergogen.py loads this file for snap() without running it
if not globals().get('SNAP_LEDS_NO_MAIN'):
    main()
