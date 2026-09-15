"""Export a board's tracks and vias as router routes JSON (e.g. a QFN fanout made by another tool).

    python export_routes.py board.kicad_pcb out.json
"""
import json
import sys

import pcbnew

T = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
out = {'tracks': [], 'vias': [], 'failed': []}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        out['vias'].append([T(t.GetPosition().x), T(t.GetPosition().y), t.GetNetname()])
    elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
        out['tracks'].append(['F' if t.GetLayer() == pcbnew.F_Cu else 'B', T(t.GetStart().x), T(t.GetStart().y),
                              T(t.GetEnd().x), T(t.GetEnd().y), t.GetNetname(), T(t.GetWidth())])
json.dump(out, open(sys.argv[2], 'w'))
print(len(out['tracks']), 'tracks', len(out['vias']), 'vias')
