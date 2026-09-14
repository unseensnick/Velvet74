"""Step 1 of ribbon routing: per-layer keepout cells (octilinear) and the contour lanes around them.

    python channels.py board.json out_prefix [cx cy half scale]

Writes <prefix>_F.png, <prefix>_B.png and <prefix>.pkl (cells and free space per layer, reused by later steps).
"""
import json
import pickle
import re
import sys
from collections import defaultdict

from PIL import Image, ImageDraw
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union

W, PITCH = 0.2, 0.4
CLR_SMD, CLR_HOLE, CLR_EDGE = 0.2, 0.25, 0.5
CLOSE = 1.0          # merge keepout gaps narrower than 2*CLOSE so each key reads as one cell
LANES = 6
MITRE = dict(join_style='mitre', mitre_limit=3.0)

d = json.load(open(sys.argv[1]))
prefix = sys.argv[2]


def oct_poly(g):
    xs = [p[0] for p in g.exterior.coords]; ys = [p[1] for p in g.exterior.coords]
    s = [x + y for x, y in zip(xs, ys)]; t = [x - y for x, y in zip(xs, ys)]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s0, s1, t0, t1 = min(s), max(s), min(t), max(t)
    # vertices of the octilinear hull, walking clockwise from the top edge
    v = [(s0 - y0, y0), (t1 + y0, y0), (x1, x1 - t1), (x1, s1 - x1), (s1 - y1, y1), (t0 + y1, y1), (x0, x0 - t0), (x0, s0 - x0)]
    return Polygon(v).buffer(0)


def key_of(ref):
    m = re.fullmatch(r'(SW|LED|D|C1)(\d\d)', ref)
    return m.group(2) if m else ref


maps = {}
edge = unary_union([Polygon(o) for o in d['outline']])
cut = unary_union([Polygon(h) for h in d['holes']])
for side in 'FB':
    groups = defaultdict(list)
    for p in d['pads']:
        if side not in p['layers'] or len(p['poly']) < 3:
            continue
        g = Polygon(p['poly']).buffer(0)
        g = g.buffer((CLR_HOLE if p['drill'] else CLR_SMD) + W / 2, **MITRE)
        groups[key_of(p['ref'])].append(oct_poly(g))
    cells = [unary_union(v).buffer(CLOSE, **MITRE).buffer(-CLOSE, **MITRE) for v in groups.values()]
    keep = unary_union(cells + [cut.buffer(CLR_EDGE + W / 2, **MITRE)])
    free = edge.buffer(-(CLR_EDGE + W / 2), **MITRE).difference(keep)
    maps[side] = {'cells': keep, 'free': free}

pickle.dump(maps, open(prefix + '.pkl', 'wb'))

if len(sys.argv) > 3:
    cx, cy, half, SC = map(float, sys.argv[3:7])
    X0, Y0, X1, Y1 = cx - half, cy - half, cx + half, cy + half
else:
    X0, Y0, X1, Y1 = edge.bounds; SC = 9.0
P = lambda x, y: ((x - X0 + 1) * SC, (y - Y0 + 1) * SC)
size = (int((X1 - X0 + 2) * SC), int((Y1 - Y0 + 2) * SC))


def rings(g):
    gs = g.geoms if hasattr(g, 'geoms') else [g]
    for q in gs:
        if q.is_empty or q.geom_type != 'Polygon':
            continue
        yield q.exterior
        yield from q.interiors


for side, col in (('F', (90, 150, 250)), ('B', (240, 90, 90))):
    img = Image.new('RGB', size, (18, 18, 22)); dr = ImageDraw.Draw(img, 'RGBA')
    for q in (maps[side]['cells'].geoms if hasattr(maps[side]['cells'], 'geoms') else [maps[side]['cells']]):
        dr.polygon([P(*c) for c in q.exterior.coords], fill=(70, 70, 80, 255))
    for p in d['pads']:
        if side in p['layers'] and len(p['poly']) > 2:
            dr.polygon([P(*c) for c in p['poly']], fill=(200, 160, 60, 255) if not p['drill'] else (150, 150, 150, 255))
    for h in d['holes']:
        dr.polygon([P(*c) for c in h], fill=(0, 0, 0, 255))
    for k in range(LANES):
        reg = maps[side]['free'].buffer(-k * PITCH, **MITRE)
        a = int(230 - k * 30)
        for r in rings(reg):
            dr.line([P(*c) for c in r.coords], fill=col + (a,), width=max(1, int(W * SC)))
    for ref, f in d['fps'].items():
        if X0 < f['x'] < X1 and Y0 < f['y'] < Y1 and re.fullmatch(r'SW\d\d|U\d|J\d', ref):
            dr.text(P(f['x'], f['y']), ref, fill=(255, 255, 255))
    img.save(f'{prefix}_{side}.png')
print('ok', {s: round(maps[s]['free'].area, 1) for s in maps})
