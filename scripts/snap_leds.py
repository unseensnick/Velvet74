"""Snap each key's LED, LED decoupling cap and matrix diode onto its switch.

Place and rotate only the switches (SWnn), then run this. Pairing comes from the
reference numbers the schematic uses: SWnn -> LEDnn, C1nn, Dnn.

Inside pcbnew:  Tools > Scripting Console, then
    exec(open(r"<project>/scripts/snap_leds.py").read())
From a shell (pcbnew closed):
    "C:/Program Files/KiCad/8.0/bin/python.exe" scripts/snap_leds.py sofle-choc-pro.kicad_pcb
"""
import math
import re
import sys

import pcbnew

# Offsets in the switch's own frame (mm, KiCad y down, 0,0 = key centre). Checked
# with DRC against the plain hotswap footprint, the Choc/EC11 combo footprint and
# neighbouring keys at 18 x 17 mm pitch. The LED must stay at 0,+4.7: the socket
# holes block the other side and the combo's bent A/C/B row sits just beyond it.
LED = (0.0, 4.7)
CAP = (4.6, 4.7)     # 0402 standing vertical, beside the LED
DIODE = (-6.0, 8.0)  # SOD-123 lying horizontal, below-left of the LED


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
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    moved, missing = 0, []
    for ref, sw in sorted(by_ref.items()):
        m = re.fullmatch(r'SW(\d{2})', ref)
        if not m:
            continue
        n = m.group(1)
        for other, offset, rotation in ((f'LED{n}', LED, 0), (f'C1{n}', CAP, 90), (f'D{n}', DIODE, 0)):
            if other in by_ref:
                _put(by_ref[other], sw, offset, rotation)
                moved += 1
            else:
                missing.append(other)
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


main()
