"""Straighten routed tracks after all routing: each run is lifted out, pulled tight against everything else on the
board with octilinear shortcuts of up to two bends, and put back, until nothing changes.

    python tidy.py board.json routes.json out.json

Runs are chains of same-net, same-layer, same-width segments joined end to end with no third segment at the joint
(a tee or a via ends a run). Endpoints stay where they are, so pad, via and tee connections are kept.
"""
import json
import math
import sys
from collections import defaultdict

import shapely
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

CLR, HCLR, ECLR, FINE_CLR, VIA_R = 0.205, 0.26, 0.5, 0.13, 0.225
FINE_REFS = ('U1', 'J1', 'J2')
EPS = 1e-3

d = json.load(open(sys.argv[1]))
r = json.load(open(sys.argv[2]))
edge = unary_union([Polygon(o) for o in d['outline']])
cut = unary_union([Polygon(h) for h in d['holes']])
fine = unary_union([shapely.box(*d['fps'][x]['crtyd']) for x in FINE_REFS if 'crtyd' in d['fps'].get(x, {})])
shapely.prepare(fine)
static = {'F': [], 'B': []}
for p in d['pads']:
    if len(p['poly']) > 2:
        for s in p['layers']:
            static[s].append((Polygon(p['poly']).buffer(0), p['net'], HCLR if p['drill'] else CLR))
for k in d.get('keepouts', []):
    for s in k['layers']:
        static[s].append((Polygon(k['poly']), '__KO__' + '|'.join(k['nets']), 0.0))

key = lambda pt: (round(pt[0], 3), round(pt[1], 3))
segs = [list(t) for t in r['tracks']]
vias = {key((v[0], v[1])) for v in r['vias']}


def build_runs():
    by = defaultdict(list)
    for i, (s, x1, y1, x2, y2, net, *w) in enumerate(segs):
        by[(s, net, round(w[0] if w else 0.2, 3))].append(i)
    runs = []
    for (s, net, w), idx in by.items():
        deg = defaultdict(list)
        for i in idx:
            deg[key(segs[i][1:3])].append(i); deg[key(segs[i][3:5])].append(i)
        used = set()
        for i in idx:
            if i in used:
                continue
            chain = [i]; used.add(i)
            for direction in (0, 1):
                cur = i
                end = key(segs[cur][3:5]) if direction == 0 else key(segs[cur][1:3])
                while len(deg[end]) == 2 and end not in vias:
                    nxt = [j for j in deg[end] if j != cur][0]
                    if nxt in used:
                        break
                    used.add(nxt)
                    chain = chain + [nxt] if direction == 0 else [nxt] + chain
                    cur = nxt
                    a, b = key(segs[nxt][1:3]), key(segs[nxt][3:5])
                    end = b if a == end else a
            runs.append((s, net, w, chain))
    return runs


def polyline(chain):
    if len(chain) == 1:
        return [tuple(segs[chain[0]][1:3]), tuple(segs[chain[0]][3:5])]
    a0, b0 = key(segs[chain[0]][1:3]), key(segs[chain[0]][3:5])
    a1, b1 = key(segs[chain[1]][1:3]), key(segs[chain[1]][3:5])
    start = a0 if a0 not in (a1, b1) else b0
    pts = [start]
    for i in chain:
        a, b = key(segs[i][1:3]), key(segs[i][3:5])
        pts.append(b if a == pts[-1] else a)
    return pts


def oct_paths(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) < 0.02 or abs(dy) < 0.02 or abs(abs(dx) - abs(dy)) < 0.02:
        return [[a, b]]
    m = min(abs(dx), abs(dy))
    diag = (math.copysign(m, dx), math.copysign(m, dy))
    out = [[a, (a[0] + diag[0], a[1] + diag[1]), b], [a, (b[0] - diag[0], b[1] - diag[1]), b]]
    # two bends: straight, diagonal, straight split around the middle
    rest = (dx - diag[0], dy - diag[1])
    p1 = (a[0] + rest[0] / 2, a[1] + rest[1] / 2)
    out.append([a, p1, (p1[0] + diag[0], p1[1] + diag[1]), b])
    return out


def make_checker(skip):
    copper = {'F': [], 'B': []}
    for i, (s, x1, y1, x2, y2, net, *w) in enumerate(segs):
        if i not in skip:
            copper[s].append((LineString([(x1, y1), (x2, y2)]).buffer((w[0] if w else 0.2) / 2), net, CLR))
    for v in r['vias']:
        for s in 'FB':
            copper[s].append((Point(v[0], v[1]).buffer(VIA_R), v[2], CLR))
    items = {s: static[s] + copper[s] for s in 'FB'}
    trees = {s: STRtree([o[0] for o in items[s]]) for s in 'FB'}
    inside = {}

    def ok(s, a, b, net, w):
        if s not in inside:
            inside[s] = edge.buffer(-(ECLR + w / 2)).difference(cut.buffer(ECLR + w / 2)).buffer(EPS)
            shapely.prepare(inside[s])
        ln = LineString([a, b]) if math.dist(a, b) > EPS else Point(a)
        if not inside[s].covers(ln):
            return False
        in_fine = fine.intersects(ln)
        for i in trees[s].query(ln, predicate='dwithin', distance=HCLR + w / 2):
            g, onet, cl = items[s][i]
            if onet.startswith('__KO__'):
                if net not in onet[6:].split('|') and ln.distance(g) < w / 2:
                    return False
                continue
            if in_fine and cl == CLR:
                cl = FINE_CLR
            if onet != net and ln.distance(g) < cl + w / 2 - EPS:
                return False
        return True
    return ok


def tighten(pts, s, net, w, ok):
    outp, i, n = [pts[0]], 0, len(pts)
    while i < n - 1:
        for j in range(n - 1, i, -1):
            cand = next((c for c in oct_paths(pts[i], pts[j]) if all(ok(s, c[k], c[k + 1], net, w) for k in range(len(c) - 1))), None)
            if cand and (j > i + 1 or len(cand) <= 2):
                outp.extend(cand[1:]); i = j
                break
        else:
            outp.append(pts[i + 1]); i += 1
    return outp


length = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
done, changed = set(), 0
while True:
    progress = False
    for s, net, w, chain in build_runs():         # indices shift after every edit, so rebuild after each one
        pts = polyline(chain)
        sig = (s, net, tuple(key(p) for p in pts))
        if len(pts) < 3 or sig in done:
            continue
        done.add(sig)
        new = tighten(pts, s, net, w, make_checker(set(chain)))
        if length(new) < length(pts) - 0.05:
            keep = [x for i, x in enumerate(segs) if i not in set(chain)]
            keep += [[s, a[0], a[1], b[0], b[1], net, w] for a, b in zip(new, new[1:]) if math.dist(a, b) > EPS]
            segs[:] = keep
            changed += 1
            progress = True
            break
    if not progress:
        break
print('runs straightened', changed)
r['tracks'] = segs
json.dump(r, open(sys.argv[3], 'w'))
