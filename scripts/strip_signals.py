"""Delete signal copper, keeping the power nets.

From a shell (pcbnew closed), one or more boards:
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/strip_signals.py sofle-choc-pro.kicad_pcb

Clears the board for hand routing while leaving the power architecture in place: the B.Cu rings round U1, the
In1 planes and island and the copper that ties them together. Those are built to the rules in
.claude/rules/kicad.md and are not worth rebuilding by hand.

Collects the items before removing any, because the SWIG track iterator is invalidated by Remove(). Restores
the neighbouring .kicad_pro, which BOARD.Save rewrites with defaults. Zones are never touched.
"""
import sys

import pcbnew

# matched on the name after the sheet path (/Left/GND -> GND), so both halves' power survives;
# VBUS_FUSED is the F1 -> D1 run, which had no name before and was stripped as a signal
POWER = {'GND', '+5V', '+3.3V', '+1V1', 'VBUS', 'VBUS_FUSED', 'LINK_VBUS'}

for path in sys.argv[1:]:
    pro = path.replace('.kicad_pcb', '.kicad_pro')
    keep = open(pro, encoding='utf-8', newline='').read()
    b = pcbnew.LoadBoard(path)
    doomed = [t for t in b.GetTracks() if t.GetNetname().rsplit('/', 1)[-1] not in POWER]
    length = sum(pcbnew.ToMM(t.GetLength()) for t in doomed if t.Type() != pcbnew.PCB_VIA_T)
    vias = sum(1 for t in doomed if t.Type() == pcbnew.PCB_VIA_T)
    kept = len(b.GetTracks()) - len(doomed)      # count before Save; the iterator does not survive it
    for t in doomed:
        b.Remove(t)
    b.Save(path)
    open(pro, 'w', encoding='utf-8', newline='').write(keep)
    print(f'{path}: removed {len(doomed)} signal items ({vias} vias, {length:.1f} mm), '
          f'{kept} power items kept')
