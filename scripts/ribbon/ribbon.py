"""Contour ribbon router: traces follow lanes parallel to keepout outlines, so later traces bundle beside earlier ones.

    python ribbon.py board.json links.json out.json [prior_routes.json]

links.json: [{"net": .., "a": [ref, pad], "b": [ref, pad]}, ...] routed in order. Optional per link:
"layers" ('F', 'B' or 'FB'), "mult" (layer cost overrides), "via_cost", "drop": true (pad to a nearby via, no "b").
out.json: {"tracks": [[layer, x1, y1, x2, y2, net]], "vias": [[x, y, net]], "failed": [...]}

Links whose pads are already joined are skipped; a link may tee off copper already joined to its pad, and a
route much longer than the straight distance is retried with relaxed settings.

Lanes are the boundaries of the free space shrunk by k * PITCH (mitre joins keep them octilinear). Free space
is recomputed after each link, so a routed trace becomes lane 0's wall for the next one.
"""
import heapq
import json
import math
import os
import sys
import time
from collections import defaultdict

import shapely
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

W = float(os.environ.get('W', '0.2'))            # track width for this run (power runs use wider)
PITCH = float(os.environ.get('PITCH', '0.4'))    # lane spacing: width plus 0.2 mm gap
CLR, HCLR, ECLR = 0.205, 0.26, 0.5          # small margins over the DRC 0.2/0.25: pads are polygonised
VIA_R, VIA_COST = 0.225, 8.0
LANES, CLOSE, STEP = 5, 1.0, 0.2
GRID = 0.8            # open-space grid pitch beyond the lanes
WINDOW = float(os.environ.get('WINDOW', '6.0'))
TURN, LANE_COST = 0.35, 0.12
LAYER_MULT = {'F': 1.0, 'B': 1.25}
CUR_LAYERS, CUR_MULT, CUR_VIA = 'FB', LAYER_MULT, VIA_COST      # per-link overrides set in route()
MITRE = dict(join_style='mitre', mitre_limit=3.0)
EPS = 1e-3

d = json.load(open(sys.argv[1]))
links = json.load(open(sys.argv[2]))

edge = unary_union([Polygon(o) for o in d['outline']])
cut = unary_union([Polygon(h) for h in d['holes']])
inside = {}
for s in 'FB':
    inside[s] = edge.buffer(-(ECLR + W / 2), **MITRE).difference(cut.buffer(ECLR + W / 2, **MITRE))
inside_chk = {s: inside[s].buffer(EPS) for s in 'FB'}
for g in inside_chk.values():
    shapely.prepare(g)
via_inside = edge.buffer(-(ECLR + VIA_R)).difference(cut.buffer(ECLR + VIA_R))
shapely.prepare(via_inside)

pads = {}
pad_nets, net_pads = [], defaultdict(list)
static = {'F': [], 'B': []}          # (geom, net, clearance to its copper)
for p in d['pads']:
    if len(p['poly']) < 3:
        continue
    g = Polygon(p['poly']).buffer(0)
    key = (p['ref'], p['num'])
    item = {'geom': g, 'layers': p['layers'], 'id': ('P', len(pad_nets))}
    pads.setdefault(key, []).append(item)        # one entry per physical pad
    pad_nets.append(p['net'])
    net_pads[p['net']].append(item)
    for s in p['layers']:
        static[s].append((g, p['net'], HCLR if p['drill'] else CLR))
# keep-outs from the board JSON: {"poly": [[x, y], ...], "layers": "FB", "nets": [allowed nets]}
for k in d.get('keepouts', []):
    for s in k['layers']:
        static[s].append((Polygon(k['poly']), '__KO__' + '|'.join(k['nets']), 0.0))
static_tree = {s: STRtree([o[0] for o in static[s]]) for s in 'FB'}
# the board's .kicad_dru allows 0.127 mm copper clearance inside these courtyards (fine-pitch escape)
FINE_REFS, FINE_CLR = ('U1', 'J1', 'J2'), 0.13
fine = unary_union([box(*d['fps'][r]['crtyd']) for r in FINE_REFS if 'crtyd' in d['fps'].get(r, {})])
shapely.prepare(fine)


def cells_for(side):
    import re
    groups = defaultdict(list)
    for p in d['pads']:
        if side not in p['layers'] or len(p['poly']) < 3:
            continue
        g = Polygon(p['poly']).buffer(0).buffer((HCLR if p['drill'] else CLR) + W / 2, **MITRE)
        m = re.fullmatch(r'(SW|LED|D|C1)(\d\d)', p['ref'])
        groups[m.group(2) if m else p['ref']].append(oct_hull(g))
    return unary_union([unary_union(v).buffer(CLOSE, **MITRE).buffer(-CLOSE, **MITRE) for v in groups.values()])


def oct_hull(g):
    xs, ys = zip(*g.exterior.coords)
    s = [x + y for x, y in zip(xs, ys)]; t = [x - y for x, y in zip(xs, ys)]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s0, s1, t0, t1 = min(s), max(s), min(t), max(t)
    return Polygon([(s0 - y0, y0), (t1 + y0, y0), (x1, x1 - t1), (x1, s1 - x1),
                    (s1 - y1, y1), (t0 + y1, y1), (x0, x0 - t0), (x0, s0 - x0)]).buffer(0)


free = {s: inside[s].difference(cells_for(s)) for s in 'FB'}
routed = {'F': [], 'B': []}           # (geom, net, clearance)
parent = {}                           # union-find over pads and routed copper, per net
copper = defaultdict(list)            # net -> [(id, polygon, sides, sample points)]


def find(i):
    parent.setdefault(i, i)
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def add_copper(net, poly, sides, samples):
    """Register routed copper and join it to every same-net pad or copper it touches."""
    cid = ('C', net, len(copper[net]))
    find(cid)
    for item in net_pads[net]:
        if set(sides) & set(item['layers']) and poly.distance(item['geom']) < 0.01:
            parent[find(cid)] = find(item['id'])
    for oid, opoly, osides, _ in copper[net]:
        if set(sides) & set(osides) and poly.distance(opoly) < 0.01:
            parent[find(cid)] = find(oid)
    copper[net].append((cid, poly, sides, samples))


def track_samples(pts, step=0.5):
    out = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]
    return out
routed_tree = {'F': None, 'B': None}
out = {'tracks': [], 'vias': [], 'failed': []}


def blocked(geom, side, net, radius):
    """True when geom (a centreline or point) comes closer than clearance + radius to other-net copper."""
    for items, tree in ((static[side], static_tree[side]), (routed[side], routed_tree[side])):
        if tree is None:
            continue
        in_fine = not fine.is_empty and fine.intersects(geom)
        for i in tree.query(geom, predicate='dwithin', distance=HCLR + radius):
            g, onet, cl = items[i]
            if in_fine and cl == CLR:
                cl = FINE_CLR
            if onet.startswith('__KO__'):
                if net not in onet[6:].split('|') and geom.distance(g) < radius:
                    return True
                continue
            if onet != net and geom.distance(g) < cl + radius - EPS:
                return True
    return False


def seg_ok(side, a, b, net):
    ln = LineString([a, b]) if math.dist(a, b) > EPS else Point(a)
    return inside_chk[side].covers(ln) and not blocked(ln, side, net, W / 2)


def octant(dx, dy):
    ang = math.atan2(dy, dx)
    o = round(ang / (math.pi / 4))
    return o % 8, abs(ang - o * math.pi / 4)


def stub_paths(a, b):
    """Octilinear ways from a to b: straight, or diagonal-then-straight, or straight-then-diagonal."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) < 0.02 or abs(dy) < 0.02 or abs(abs(dx) - abs(dy)) < 0.02:
        return [[a, b]]
    m = min(abs(dx), abs(dy))
    diag = (math.copysign(m, dx), math.copysign(m, dy))
    k1 = (a[0] + diag[0], a[1] + diag[1])
    k2 = (b[0] - diag[0], b[1] - diag[1])
    return [[a, k1, b], [a, k2, b]]


def pad_center(key, hint=None):
    """Centre of the physical pad with this number nearest hint (a footprint can repeat a pad number)."""
    items = pads[key]
    c = lambda it: (it['geom'].centroid.x, it['geom'].centroid.y)
    it = min(items, key=lambda it: math.dist(c(it), hint)) if hint else items[0]
    return c(it), it


class Graph:
    def __init__(self, win):
        self.xy, self.side, self.lane = [], [], []
        self.adj = defaultdict(list)          # i -> [(j, length)]
        self.hash = defaultdict(list)
        wbox = box(*win)
        for s in CUR_LAYERS:
            fw = free[s].intersection(wbox)
            if fw.is_empty:
                continue
            chk = fw.buffer(0.01)
            shapely.prepare(chk)
            for k in range(LANES):
                reg = fw.buffer(-k * PITCH, **MITRE) if k else fw
                for ring in rings(reg):
                    coords = list(shapely.segmentize(ring, STEP).coords)
                    ids = [self.node(s, k, c) for c in coords[:-1]]
                    n = len(ids)
                    for i in range(n):
                        a, b = ids[i], ids[(i + 1) % n]
                        L = math.dist(self.xy[a], self.xy[b])
                        self.adj[a].append((b, L)); self.adj[b].append((a, L))
            self.hops(s, chk)
            self.open_grid(s, fw, chk)

    def open_grid(self, s, fw, chk):
        """Coarse octilinear grid in open space beyond the lanes, so a route can cross an open area instead of
        following its contours all the way round."""
        inner = fw.buffer(-LANES * PITCH, **MITRE)
        if inner.is_empty:
            return
        shapely.prepare(inner)
        x0, y0, x1, y1 = inner.bounds
        cell = {}
        gx = int((x1 - x0) / GRID) + 1
        gy = int((y1 - y0) / GRID) + 1
        for i in range(gx):
            for j in range(gy):
                x, y = x0 + i * GRID, y0 + j * GRID
                if shapely.contains_xy(inner, x, y):
                    cell[(i, j)] = self.node(s, 1, (x, y))
        for (i, j), a in cell.items():
            for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
                b = cell.get((i + di, j + dj))
                if b is not None:
                    mx, my = (self.xy[a][0] + self.xy[b][0]) / 2, (self.xy[a][1] + self.xy[b][1]) / 2
                    if shapely.contains_xy(chk, mx, my):
                        L = math.dist(self.xy[a], self.xy[b])
                        self.adj[a].append((b, L)); self.adj[b].append((a, L))
        # join the grid to the outermost lane ring nodes nearby
        for a in cell.values():
            for q in self.near(s, self.xy[a], GRID * 1.2):
                if self.lane[q] >= LANES - 1 and self.side[q] == s:
                    L = math.dist(self.xy[a], self.xy[q])
                    self.adj[a].append((q, L)); self.adj[q].append((a, L))

    def node(self, s, k, c):
        i = len(self.xy)
        self.xy.append((c[0], c[1])); self.side.append(s); self.lane.append(k)
        self.hash[(s, int(c[0] // 0.25), int(c[1] // 0.25))].append(i)
        return i

    def near(self, s, pt, r):
        cx, cy = int(pt[0] // 0.25), int(pt[1] // 0.25)
        n = int(r // 0.25) + 1
        for i in range(cx - n, cx + n + 1):
            for j in range(cy - n, cy + n + 1):
                for q in self.hash.get((s, i, j), ()):
                    if math.dist(self.xy[q], pt) <= r:
                        yield q

    def hops(self, s, chk):
        # 45-degree lane changes: from each node to a node one pitch sideways and one pitch along
        for i in range(len(self.xy)):
            if self.side[i] != s or len(self.adj[i]) < 2:
                continue
            (ax, ay) = self.xy[self.adj[i][0][0]]; (bx, by) = self.xy[self.adj[i][1][0]]
            tx, ty = bx - ax, by - ay
            L = math.hypot(tx, ty)
            if L < EPS:
                continue
            tx, ty = tx / L, ty / L
            x, y = self.xy[i]
            for st in (1, -1):
                for sn in (1, -1):
                    q = (x + (tx * st - ty * sn) * PITCH, y + (ty * st + tx * sn) * PITCH)
                    best = min(self.near(s, q, 0.12), key=lambda j: math.dist(self.xy[j], q), default=None)
                    if best is None or math.dist(self.xy[best], (x, y)) < PITCH:
                        continue
                    mx, my = (x + self.xy[best][0]) / 2, (y + self.xy[best][1]) / 2
                    if shapely.contains_xy(chk, mx, my):
                        Lh = math.dist((x, y), self.xy[best])
                        self.adj[i].append((best, Lh)); self.adj[best].append((i, Lh))


def rings(g):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type != 'Polygon' or q.is_empty:
            continue
        yield q.exterior
        yield from q.interiors


def escape_points(s, c, key, net):
    """Fine-pitch pads (FINE_REFS) first leave straight along the line from the part centre through the pad,
    so the stub clears the neighbouring pins before it turns; returns the clear escape ends, farthest first."""
    fp = d['fps'][key[0]]
    ang = math.atan2(c[1] - fp['y'], c[0] - fp['x'])
    ang = round(ang / (math.pi / 4)) * (math.pi / 4)
    ux, uy = math.cos(ang), math.sin(ang)
    ends = []
    for k in range(4, 40):
        e = (c[0] + ux * 0.1 * k, c[1] + uy * 0.1 * k)
        if not seg_ok(s, c, e, net):
            break
        ends.append(e)
    return ends[::-4][:4]


def attach(G, key, net, hint, toward, radius=4.0, limit=10):
    """Stub options from a pad to lane nodes: [(node, cost, points pad->node)]."""
    c, item = pad_center(key, hint)
    res = []
    for s in item['layers']:
        if s not in CUR_LAYERS:
            continue
        starts = [[c]]
        if key[0] in FINE_REFS:
            starts = [[c, e] for e in escape_points(s, c, key, net)] + starts
        # copper already joined to this pad (a fanout stub, an earlier link): tee off it where it is closest to
        # the other end, so same-net links share a route instead of running side by side
        root = find(item['id'])
        tees = sorted((pt for cid, _, sides, samples in copper[net] if s in sides and find(cid) == root for pt in samples),
                      key=lambda pt: math.dist(pt, toward))
        picked = []
        for pt in tees:
            if all(math.dist(pt, q) > 1.0 for q in picked):
                picked.append(pt)
            if len(picked) == 4:
                break
        starts = [[pt] for pt in picked] + starts
        for head in starts:
            o = head[-1]
            cand = sorted(G.near(s, o, radius), key=lambda q: math.dist(G.xy[q], o))
            tried = 0
            for q in cand:
                if tried >= limit * 4 or len(res) >= limit * 2:
                    break
                tried += 1
                for tail in stub_paths(o, G.xy[q]):
                    pts = head[:-1] + tail
                    if all(seg_ok(s, pts[i], pts[i + 1], net) for i in range(len(pts) - 1)):
                        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
                        res.append((q, L * 1.5 + 0.3 * (len(pts) - 2), pts))
                        break
            if res:
                break
    return res


def via_ok(pt, net):
    p = Point(pt)
    return shapely.contains_xy(via_inside, *pt) and not blocked(p, 'F', net, VIA_R) and not blocked(p, 'B', net, VIA_R)


def route(link):
    global CUR_LAYERS, CUR_MULT, CUR_VIA
    CUR_LAYERS = link.get('layers', 'FB')
    CUR_VIA = link.get('via_cost', VIA_COST)
    CUR_MULT = {**LAYER_MULT, **link.get('mult', {})}
    net = link['net']
    ka, kb = tuple(link['a']), tuple(link['b'])
    cb, _ = pad_center(kb, link.get('bxy') or pad_center(ka, link.get('axy'))[0])
    ca, _ = pad_center(ka, link.get('axy') or cb)
    win = (min(ca[0], cb[0]) - WINDOW, min(ca[1], cb[1]) - WINDOW, max(ca[0], cb[0]) + WINDOW, max(ca[1], cb[1]) + WINDOW)
    ia, ib = pad_center(ka, ca)[1]['id'], pad_center(kb, cb)[1]['id']
    if find(ia) == find(ib):
        return ([], []), None                 # already joined by earlier copper
    G = Graph(win)
    starts = attach(G, ka, net, ca, cb)
    goals = {}
    for q, cost, pts in attach(G, kb, net, cb, ca):
        if q not in goals or cost < goals[q][0]:
            goals[q] = (cost, pts)
    if not starts or not goals:
        return None, f'no access ({len(starts)} start, {len(goals)} goal)'
    h = lambda i: math.dist(G.xy[i], cb)
    openq, best, came = [], {}, {}
    for q, cost, pts in starts:
        o, _ = octant(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
        st = (q, o)
        if cost < best.get(st, 1e18):
            best[st] = cost; came[st] = ('start', pts)
            heapq.heappush(openq, (cost + h(q), cost, st))
    via_cache, edge_ok = {}, {}
    while openq:
        f, cost, st = heapq.heappop(openq)
        if st == 'goal':
            break
        if cost > best.get(st, 1e18):
            continue
        i, o = st
        if i in goals:
            gc, gpts = goals[i]
            o2, _ = octant(gpts[-2][0] - gpts[-1][0], gpts[-2][1] - gpts[-1][1]) if len(gpts) > 1 else (o, 0)
            gdiff = min((o2 - o) % 8, (o - o2) % 8)
            nc = cost + gc + TURN * gdiff
            if (gdiff <= 2 or o < 0) and nc < best.get('goal', 1e18):
                best['goal'] = nc; came['goal'] = (st, ('stub', list(reversed(gpts))))
                heapq.heappush(openq, (nc, nc, 'goal'))
        s = G.side[i]
        for j, L in G.adj[i]:
            dx, dy = G.xy[j][0] - G.xy[i][0], G.xy[j][1] - G.xy[i][1]
            o2, off = octant(dx, dy)
            diff = min((o2 - o) % 8, (o - o2) % 8)
            if diff > 2:
                continue
            ek = (i, j) if i < j else (j, i)
            if ek not in edge_ok:
                # lanes come from polygon offsets; confirm exact clearance before trusting an edge
                edge_ok[ek] = seg_ok(s, G.xy[i], G.xy[j], net)
            if not edge_ok[ek]:
                continue
            nc = cost + L * CUR_MULT[s] * (1 + LANE_COST * G.lane[j]) + TURN * diff + (2.0 if off > 0.1 else 0)
            ns = (j, o2)
            if nc < best.get(ns, 1e18):
                best[ns] = nc; came[ns] = (st, None)
                heapq.heappush(openq, (nc + h(j), nc, ns))
        # via to the other layer, then a short stub onto its lanes
        if i not in via_cache:
            via_cache[i] = via_ok(G.xy[i], net)
        if via_cache[i] and len(CUR_LAYERS) == 2:
            other = 'B' if s == 'F' else 'F'
            for j in G.near(other, G.xy[i], 1.0):
                for pts in stub_paths(G.xy[i], G.xy[j]):
                    if all(seg_ok(other, pts[k], pts[k + 1], net) for k in range(len(pts) - 1)):
                        L = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
                        if L > EPS:
                            # the turn is counted through the via, so a path cannot double back on the other layer
                            o1, _ = octant(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
                            o2, _ = octant(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
                            vdiff = min((o1 - o) % 8, (o - o1) % 8) + (min((o2 - o1) % 8, (o1 - o2) % 8) if len(pts) > 2 else 0)
                        else:
                            o2, vdiff = o, 0
                        if vdiff > 2:
                            break
                        nc = cost + CUR_VIA + L * 1.5 + TURN * vdiff
                        ns = (j, o2)
                        if nc < best.get(ns, 1e18):
                            best[ns] = nc; came[ns] = (st, ('via', pts))
                            heapq.heappush(openq, (nc + h(j), nc, ns))
                        break
    if 'goal' not in best:
        return None, f'no path ({len(G.xy)} nodes)'
    # unwind into layer runs and vias
    seq = []
    st = 'goal'
    while True:
        prev, extra = came[st]
        if prev == 'start':
            seq.append(('stub', G.side[st[0]], extra))
            break
        if st == 'goal':
            seq.append(('stub', G.side[prev[0]], extra[1]))
        else:
            if extra and extra[0] == 'via':
                seq.append(('via', G.side[st[0]], extra[1]))
            else:
                seq.append(('edge', G.side[st[0]], [G.xy[prev[0]], G.xy[st[0]]]))
        st = prev
    seq.reverse()
    runs, vias = [], []
    cur_side, cur = None, []
    for kind, s, pts in seq:
        if kind == 'via':
            vias.append(pts[0])
            if cur:
                runs.append((cur_side, cur))
            cur_side, cur = s, list(pts)
            continue
        if cur_side is None:
            cur_side = s
        if cur and math.dist(cur[-1], pts[0]) < EPS:
            cur.extend(pts[1:])
        else:
            cur.extend(pts)
    if cur:
        runs.append((cur_side, cur))
    return (runs, vias), None


def simplify(pts):
    outp = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, outp[-1]) < EPS:
            continue
        if len(outp) >= 2:
            a, b = outp[-2], outp[-1]
            cross = (b[0] - a[0]) * (p[1] - b[1]) - (b[1] - a[1]) * (p[0] - b[0])
            dot = (b[0] - a[0]) * (p[0] - b[0]) + (b[1] - a[1]) * (p[1] - b[1])
            if abs(cross) < 1e-4 and dot > 0:
                outp[-1] = p
                continue
        outp.append(p)
    return outp


def pull_tight(s, pts, net):
    """Replace wiggles with the longest clear octilinear shortcuts (straight or one 45-degree bend)."""
    outp, i, n = [pts[0]], 0, len(pts)
    while i < n - 1:
        for j in range(n - 1, i, -1):
            ok = None
            for cand in stub_paths(pts[i], pts[j]):
                if all(seg_ok(s, cand[k], cand[k + 1], net) for k in range(len(cand) - 1)):
                    ok = cand
                    break
            if ok:
                outp.extend(ok[1:])
                i = j
                break
        else:
            outp.append(pts[i + 1])
            i += 1
    return simplify(outp)


def check(tag, net, s, pts):
    for a, b in zip(pts, pts[1:]):
        if not seg_ok(s, a, b, net):
            print(f'  BAD {tag} {net} {s} {a} -> {b}', flush=True)


def commit(net, runs, vias):
    for s, pts in runs:
        check('raw', net, s, pts)
        pts = pull_tight(s, simplify(pts), net)
        check('tight', net, s, pts)
        if len(pts) < 2:
            continue
        ln = LineString(pts)
        copper_poly = ln.buffer(W / 2, cap_style='round', join_style='round')
        routed[s].append((copper_poly, net, CLR))
        free[s] = free[s].difference(ln.buffer(W / 2 + CLR + W / 2, cap_style='square', **MITRE))
        for a, b in zip(pts, pts[1:]):
            out['tracks'].append([s, a[0], a[1], b[0], b[1], net, W])
        add_copper(net, copper_poly, s, track_samples(pts))
    for v in vias:
        g = Point(v).buffer(VIA_R)
        for s in 'FB':
            routed[s].append((g, net, CLR))
            free[s] = free[s].difference(Point(v).buffer(VIA_R + CLR + W / 2))
        out['vias'].append([v[0], v[1], net])
        add_copper(net, g, 'FB', [tuple(v)])
    for s in 'FB':
        routed_tree[s] = STRtree([o[0] for o in routed[s]]) if routed[s] else None


if len(sys.argv) > 4:
    # earlier routes as fixed obstacles, so a few links can be added without rerouting everything
    prior = json.load(open(sys.argv[4]))
    for s, x1, y1, x2, y2, net, *tw in prior['tracks']:
        tw = tw[0] if tw else 0.2
        ln = LineString([(x1, y1), (x2, y2)])
        routed[s].append((ln.buffer(tw / 2), net, CLR))
        free[s] = free[s].difference(ln.buffer(tw / 2 + CLR + W / 2, cap_style='square', **MITRE))
        out['tracks'].append([s, x1, y1, x2, y2, net, tw])
        add_copper(net, ln.buffer(tw / 2), s, track_samples([(x1, y1), (x2, y2)]))
    for x, y, net in prior['vias']:
        for s in 'FB':
            routed[s].append((Point(x, y).buffer(VIA_R), net, CLR))
            free[s] = free[s].difference(Point(x, y).buffer(VIA_R + CLR + W / 2))
        out['vias'].append([x, y, net])
        add_copper(net, Point(x, y).buffer(VIA_R), 'FB', [(x, y)])
    for s in 'FB':
        routed_tree[s] = STRtree([o[0] for o in routed[s]]) if routed[s] else None

def drop(link):
    """Short octilinear stub from a pad to the nearest clear via spot (power pads down to a pour)."""
    net, key = link['net'], tuple(link['a'])
    c, item = pad_center(key, link.get('axy'))
    s = item['layers'][0]
    fp = d['fps'][key[0]]
    out_ang = math.degrees(math.atan2(c[1] - fp['y'], c[0] - fp['x']))
    # try directions pointing away from the part first: a via beside the part blocks the signals that reach it
    angles = sorted(range(0, 360, 45), key=lambda a: abs((a - out_ang + 180) % 360 - 180))
    for ang in angles:
        for r in [0.9 + 0.1 * k for k in range(15)]:
            pt = (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))
            if via_ok(pt, net) and seg_ok(s, c, pt, net):
                return ([(s, [c, pt])], [pt]), None
    return None, 'no via spot'


for n, link in enumerate(links):
    t0 = time.time()
    res, why = drop(link) if link.get('drop') else route(link)
    if res and not link.get('drop') and res[0]:
        ca = pad_center(tuple(link['a']), link.get('axy'))[0]
        cb = pad_center(tuple(link['b']), link.get('bxy'))[0]
        length = lambda r: sum(math.dist(p, q) for _, pts in r[0] for p, q in zip(pts, pts[1:]))
        if length(res) > 2.0 * math.dist(ca, cb) + 6.0:
            # a long detour: retry with both layers, cheaper vias and a wider search, keep the shorter route
            global_window = WINDOW
            WINDOW = global_window * 2
            alt, _ = route({**link, 'layers': 'FB', 'mult': {}, 'via_cost': 3.0})
            WINDOW = global_window
            if alt and length(alt) < length(res):
                res = alt
    if not res:
        out['failed'].append(link)
        print(f"[{n}] {link['net']} {link['a']}->{link.get('b')} FAILED {why} ({time.time() - t0:.1f}s)", flush=True)
        continue
    runs, vias = res
    commit(link['net'], runs, vias)
    print(f"[{n}] {link['net']} {link['a']}->{link.get('b')} ok, {len(vias)} vias ({time.time() - t0:.1f}s)", flush=True)
    json.dump(out, open(sys.argv[3], 'w'))
json.dump(out, open(sys.argv[3], 'w'))
print('failed', len(out['failed']))
