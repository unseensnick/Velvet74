"""Matrix links for the ribbon router: switch-to-diode, rows, columns (MST per net), LED data chain.

    python make_links.py board.json links.json [NET ...]
"""
import json
import math
import re
import sys
from collections import defaultdict

d = json.load(open(sys.argv[1]))
only = set(sys.argv[3:])
cent = defaultdict(list)
net_of = {}
for p in d['pads']:
    k = (p['ref'], p['num'])
    cent[k].extend(p['poly'])
    net_of[k] = p['net']
c = {k: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for k, v in cent.items()}


def mst(keys):
    keys = sorted(keys, key=lambda k: c[k])
    done, edges = [keys[0]], []
    rest = keys[1:]
    while rest:
        a, b = min(((a, b) for a in done for b in rest), key=lambda e: math.dist(c[e[0]], c[e[1]]))
        edges.append((a, b)); done.append(b); rest.remove(b)
    return edges


links = []
refs = {p['ref'] for p in d['pads']}
for r in sorted(refs):
    m = re.fullmatch(r'D(\d\d)', r)
    if m and ('SW' + m.group(1), '2') in net_of:
        sw = 'SW' + m.group(1)
        # encoder combo keys repeat pad 2 (hotswap pad plus a through pin): link the hotswap pad, then the pin
        phys = [p for p in d['pads'] if p['ref'] == sw and p['num'] == '2']
        xy = [(sum(x for x, _ in p['poly']) / len(p['poly']), sum(y for _, y in p['poly']) / len(p['poly'])) for p in phys]
        smd = next((xy[i] for i, p in enumerate(phys) if not p['drill']), xy[0])
        links.append({'net': net_of[(r, '2')], 'a': [sw, '2'], 'b': [r, '2'], 'axy': smd, 'kind': 'switch'})
        for i, p in enumerate(phys):
            if p['drill']:
                links.append({'net': p['net'], 'a': [sw, '2'], 'b': [sw, '2'], 'axy': smd, 'bxy': xy[i], 'kind': 'switch'})
for kind, pat, num in (('row', r'D\d\d', '1'), ('column', r'SW\d\d', '1')):
    groups = defaultdict(list)
    for r in refs:
        if re.fullmatch(pat, r) and (r, num) in net_of:
            groups[net_of[(r, num)]].append((r, num))
    for net, keys in sorted(groups.items()):
        for a, b in sorted(mst(keys), key=lambda e: math.dist(c[e[0]], c[e[1]])):
            links.append({'net': net, 'a': list(a), 'b': list(b), 'kind': kind})
din = {net_of[(r, '2')]: r for r in refs if re.fullmatch(r'LED\d\d', r)}
net, prev = 'LED_D0', None
while net in din:
    r = din[net]
    if prev:
        links.append({'net': net, 'a': [prev, '4'], 'b': [r, '2'], 'kind': 'led'})
    prev, net = r, net_of[(r, '4')]
if only:
    links = [l for l in links if l['net'] in only]
json.dump(links, open(sys.argv[2], 'w'), indent=0)
from collections import Counter
print(len(links), Counter(l['kind'] for l in links))
