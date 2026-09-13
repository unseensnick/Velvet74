"""Place the schematic's switches on Ergogen's key points and take its board outline.

Run `npm run build` in ergogen/ first; it writes ergogen/output/points.json and the
outline board. Then, with the PCB updated from the schematic:

Inside pcbnew:  Tools > Scripting Console, then
    exec(open(r"<project>/scripts/place_from_ergogen.py").read())
From a shell (pcbnew closed):
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/place_from_ergogen.py sofle-choc-pro.kicad_pcb

Each run replaces the board-level Edge.Cuts outline, moves every SWnn listed in
points.json, then snaps LEDs, caps and diodes with snap_leds.py.
"""
import json
import os
import re
import sys

import pcbnew

# Ergogen's origin (bottom-row pinky centre) lands here on the KiCad sheet, in mm
ORIGIN = (60.0, 140.0)
# The switch footprints put the socket north and the LED south at 0 degrees, so the
# extra rotation depends on which side of the key its LED should face (led: in config.yaml).
LED_FACING_ROTATION = {'south': 0.0, 'east': 90.0, 'north': 180.0, 'west': 270.0}

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exec() from the scripting console has no __file__
    HERE = os.path.dirname(os.path.abspath(pcbnew.GetBoard().GetFileName()))
    HERE = os.path.join(HERE, 'scripts')
PROJECT = os.path.dirname(HERE)
ERGOGEN_OUT = os.path.join(PROJECT, 'ergogen', 'output')


def _mm(x, y):
    # Ergogen is y-up, KiCad is y-down
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] - y))


def place_switches(board):
    points = json.load(open(os.path.join(ERGOGEN_OUT, 'points.json'), encoding='utf-8'))
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    missing = []
    for p in points:
        fp = by_ref.get(p['ref'])
        if fp is None:
            missing.append(p['ref'])
            continue
        if fp.IsFlipped():
            fp.Flip(fp.GetPosition(), False)  # switches sit on the front
        fp.SetOrientationDegrees(p['r'] + LED_FACING_ROTATION[p['led']])  # both tools rotate counter-clockwise as seen from the top
        fp.SetPosition(_mm(p['x'], p['y']))
    return len(points) - len(missing), missing


def _pt(x, y):
    # Ergogen's kicad8 template already writes KiCad (y-down) coordinates
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + float(x)), pcbnew.FromMM(ORIGIN[1] + float(y)))


def replace_outline(board):
    # read Ergogen's outline as text: loading a second board through pcbnew invalidates the first one's iterators
    text = open(os.path.join(ERGOGEN_OUT, 'pcbs', 'outline_only.kicad_pcb'), encoding='utf-8').read()
    num = r'(-?[\d.]+)'
    lines = re.findall(rf'\(gr_line \(start {num} {num}\) \(end {num} {num}\) \(layer Edge\.Cuts\)', text)
    arcs = re.findall(rf'\(gr_arc \(start {num} {num}\) \(mid {num} {num}\) \(end {num} {num}\) \(layer Edge\.Cuts\)', text)
    circles = re.findall(rf'\(gr_circle \(center {num} {num}\) \(end {num} {num}\) \(layer Edge\.Cuts\)', text)
    if not (lines or arcs or circles):
        raise RuntimeError('no Edge.Cuts outline found in the Ergogen output; run npm run build in ergogen/')
    removed = 0
    for item in list(board.GetDrawings()):
        if item.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(item)
            removed += 1
    width = pcbnew.FromMM(0.15)

    def add(shape_type, configure):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(shape_type)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(width)
        configure(shape)
        board.Add(shape)

    for x1, y1, x2, y2 in lines:
        add(pcbnew.SHAPE_T_SEGMENT, lambda s: (s.SetStart(_pt(x1, y1)), s.SetEnd(_pt(x2, y2))))
    for x1, y1, xm, ym, x2, y2 in arcs:
        add(pcbnew.SHAPE_T_ARC, lambda s: s.SetArcGeometry(_pt(x1, y1), _pt(xm, ym), _pt(x2, y2)))
    for cx, cy, ex, ey in circles:
        add(pcbnew.SHAPE_T_CIRCLE, lambda s: (s.SetCenter(_pt(cx, cy)), s.SetEnd(_pt(ex, ey))))
    return len(lines) + len(arcs) + len(circles), removed


def run(board):
    placed, missing = place_switches(board)
    snap_ns = {'__name__': 'snap_leds_module', 'SNAP_LEDS_NO_MAIN': True}
    exec(open(os.path.join(HERE, 'snap_leds.py'), encoding='utf-8').read(), snap_ns)
    snapped, snap_missing = snap_ns['snap'](board)
    outline, removed = replace_outline(board)
    print(f'placed {placed} switches, snapped {snapped} parts, outline: {outline} segments (replaced {removed} old Edge.Cuts items)')
    for label, refs in (('switches not on board', missing), ('snap targets not on board', snap_missing)):
        if refs:
            print(f'{label}: {", ".join(refs)}')


if len(sys.argv) > 1 and sys.argv[1].endswith('.kicad_pcb'):
    target = pcbnew.LoadBoard(sys.argv[1])
    run(target)
    target.Save(sys.argv[1])
else:
    run(pcbnew.GetBoard())
    pcbnew.Refresh()
