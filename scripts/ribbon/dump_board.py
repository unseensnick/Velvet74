"""Dump pads (as rectangles), tracks and vias of a board to JSON for render_crop.py. Read-only.

    python dump_board.py board.kicad_pcb out.json
"""
import json, math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM
out = {'pads': [], 'tracks': [], 'vias': [], 'refs': []}
for fp in b.GetFootprints():
    out['refs'].append((fp.GetReference(), T(fp.GetPosition().x), T(fp.GetPosition().y)))
    for p in fp.Pads():
        sx, sy = T(p.GetSize().x) / 2, T(p.GetSize().y) / 2; a = math.radians(-p.GetOrientationDegrees())
        px, py = T(p.GetPosition().x), T(p.GetPosition().y)
        out['pads'].append({'net': p.GetNetname(), 'ref': fp.GetReference(), 'num': p.GetNumber(), 'round': p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE, 'c': (px, py), 'r': sx,
                            'poly': [(px + cx * math.cos(a) - cy * math.sin(a), py + cx * math.sin(a) + cy * math.cos(a)) for cx, cy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy))]})
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        out['vias'].append((T(t.GetPosition().x), T(t.GetPosition().y), T(t.GetWidth(pcbnew.F_Cu)) / 2, t.GetNetname()))
    else:
        out['tracks'].append((T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y), T(t.GetWidth()), b.GetLayerName(t.GetLayer()), t.GetNetname()))
json.dump(out, open(sys.argv[2], 'w')); print('ok')
