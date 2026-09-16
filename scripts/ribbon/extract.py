"""Dump pads, holes, board outline and key groups of a board to JSON for the ribbon planner.

    python extract.py board.kicad_pcb out.json
"""
import json
import re
import sys

import pcbnew

T = pcbnew.ToMM
ERR = pcbnew.ERROR_INSIDE


def pts(chain):
    return [(T(chain.CPoint(i).x), T(chain.CPoint(i).y)) for i in range(chain.PointCount())]


b = pcbnew.LoadBoard(sys.argv[1])
out = {'pads': [], 'outline': [], 'holes': [], 'fps': {}}
for f in b.GetFootprints():
    ref = f.GetReference()
    out['fps'][ref] = {'x': T(f.GetPosition().x), 'y': T(f.GetPosition().y), 'rot': f.GetOrientationDegrees(),
                       'side': 'B' if f.IsFlipped() else 'F', 'fp': f.GetFPID().GetLibItemName().wx_str()}
    cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox()
        out['fps'][ref]['crtyd'] = [T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())]
    for p in f.Pads():
        drill = p.GetDrillSize().x > 0
        layers = 'FB' if drill else ('B' if p.IsOnLayer(pcbnew.B_Cu) else 'F' if p.IsOnLayer(pcbnew.F_Cu) else '')
        if not layers:
            continue
        poly = p.GetEffectivePolygon(pcbnew.B_Cu if layers == 'B' else pcbnew.F_Cu, ERR)
        for i in range(poly.OutlineCount()):
            out['pads'].append({'ref': ref, 'num': p.GetNumber(), 'net': p.GetNetname(), 'layers': layers,
                                'drill': drill, 'poly': pts(poly.Outline(i))})
ol = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(ol, False)
for i in range(ol.OutlineCount()):
    out['outline'].append(pts(ol.Outline(i)))
    for h in range(ol.HoleCount(i)):
        out['holes'].append(pts(ol.Hole(i, h)))
json.dump(out, open(sys.argv[2], 'w'))
print(len(out['pads']), 'pads', len(out['holes']), 'cutouts')
