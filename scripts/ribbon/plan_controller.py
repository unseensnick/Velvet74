"""Link lists for everything the key-area runs left open: controller nets, power, GND drops and U1-to-matrix trunks.

    python plan_controller.py board.json prior_routes.json outdir

Pads already joined by prior routes (same net, touching copper) form groups; each net's groups are joined by a
minimum spanning tree between their closest pads. Writes, in routing order:
  c1_gnd.json   GND drops for SMD GND pads not yet dropped (W=0.3)
  c2_fine.json  USB, crystal, flash (W=0.2, routed first so they stay short and via-free where possible)
  c3_power.json +1V1 and +3.3V (W=0.3)
  c4_5v.json    +5V, VBUS, fuse/diode and link VBUS nets (W=0.5)
  c5_signal.json other controller signals (W=0.2)
  c6_trunks.json U1 to matrix rows and columns (W=0.2, last so they bundle around the rest)
"""
import json
import math
import os
import re
import sys
from collections import defaultdict

from shapely.geometry import LineString, Point, Polygon

board, prior_file, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
d = json.load(open(board))
prior = json.load(open(prior_file))

pads = []
for p in d['pads']:
    if len(p['poly']) < 3 or not p['net'] or p['net'].startswith('unconnected-'):
        continue
    g = Polygon(p['poly']).buffer(0)
    pads.append({'ref': p['ref'], 'num': p['num'], 'net': p['net'], 'geom': g, 'xy': (g.centroid.x, g.centroid.y),
                 'drill': p['drill'], 'layers': p['layers']})

# union-find over pads, tracks and vias of the same net that touch
items = [('pad', p['net'], p['geom']) for p in pads]
for s, x1, y1, x2, y2, net, *w in prior['tracks']:
    items.append(('track', net, LineString([(x1, y1), (x2, y2)]).buffer((w[0] if w else 0.2) / 2)))
for x, y, net in prior['vias']:
    items.append(('via', net, Point(x, y).buffer(0.3)))
parent = list(range(len(items)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


by_net = defaultdict(list)
for i, (_, net, g) in enumerate(items):
    by_net[net].append(i)
for net, idx in by_net.items():
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            ia, ib = idx[a], idx[b]
            if find(ia) != find(ib) and items[ia][2].distance(items[ib][2]) < 1e-3:
                parent[find(ia)] = find(ib)

groups = defaultdict(lambda: defaultdict(list))        # net -> root -> [pad]
for i, p in enumerate(pads):
    groups[p['net']][find(i)].append(p)


def kind(net):
    if re.match(r'D_USB_|Net-\(U1-USB|Net-\(J1-CC|XTAL|Net-\(C4-|SD\d|^SS$|^CLK$', net):
        return 'c2_fine'
    if net in ('+1V1', '+3.3V'):
        return 'c3_power'
    if net in ('+5V', 'VBUS', 'LINK_VBUS') or net.startswith('Net-(D1') or net.startswith('Net-(F'):
        return 'c4_5v'
    if re.fullmatch(r'GP(1[89]|2\d)', net):
        return 'c6_trunks'
    return 'c5_signal'


links = defaultdict(list)
for net, roots in groups.items():
    if net == 'GND':
        continue
    comps = list(roots.values())
    if len(comps) < 2:
        continue
    # Prim over components, edge weight = closest pad pair
    done, rest = [comps[0]], comps[1:]
    while rest:
        best = None
        for ca in done:
            for cb in rest:
                for pa in ca:
                    for pb in cb:
                        dd = math.dist(pa['xy'], pb['xy'])
                        if best is None or dd < best[0]:
                            best = (dd, pa, pb, cb)
        dd, pa, pb, cb = best
        done.append(cb); rest.remove(cb)
        if net == '+3.3V' and pa['ref'] == pb['ref'] == 'U1':
            continue        # zones.py's +3.3V ring inside the pad ring joins these
        links[kind(net)].append({'net': net, 'a': [pa['ref'], pa['num']], 'axy': list(pa['xy']),
                                 'b': [pb['ref'], pb['num']], 'bxy': list(pb['xy']), 'kind': kind(net), 'len': dd})

# GND: every SMD GND pad not already joined to a via gets a drop (the F.Cu pour does the rest)
via_roots = {find(i) for i, it in enumerate(items) if it[0] == 'via' and it[1] == 'GND'}
for i, p in enumerate(pads):
    if p['net'] == 'GND' and not p['drill'] and find(i) not in via_roots and p['geom'].area < 4.0:
        links['c1_gnd'].append({'net': 'GND', 'a': [p['ref'], p['num']], 'axy': list(p['xy']), 'drop': True, 'kind': 'gnd'})

for name in ('c1_gnd', 'c2_fine', 'c3_power', 'c4_5v', 'c5_signal', 'c6_trunks'):
    ls = sorted(links[name], key=lambda l: l.get('len', 0))
    if name == 'c6_trunks':
        ls.sort(key=lambda l: -int(l['net'][2:]))       # GP29 (row 1) first, outermost pins peel first
    json.dump(ls, open(os.path.join(out, name + '.json'), 'w'), indent=0)
    print(name, len(ls))
