"""+5V links for the key area: LED pad 3 to its cap, row chains, a spine along the inner column, and U6.

    python make_power_links.py board.json links.json

Rows are the first digit of the key number; each row chains left to right, the column-5 LEDs form the
spine (thumb row joins at its nearest key), and U6 (LED level shifter by LED65) joins the spine end nearest to it.
"""
import json
import math
import re
import sys
from collections import defaultdict

NET = '+5V'

d = json.load(open(sys.argv[1]))
pads = defaultdict(list)
for p in d['pads']:
    if p['net'] == NET:
        xy = (sum(x for x, _ in p['poly']) / len(p['poly']), sum(y for _, y in p['poly']) / len(p['poly']))
        pads[p['ref']].append((p['num'], xy))

links = []
rows = defaultdict(list)
for ref, items in pads.items():
    m = re.fullmatch(r'LED(\d)(\d)', ref)
    if not m:
        continue
    num, xy = next(i for i in items if i[0] == '3')
    rows[m.group(1)].append((xy, ref))
    cap = 'C1' + m.group(1) + m.group(2)
    for cnum, cxy in pads.get(cap, []):
        links.append({'net': NET, 'a': [ref, '3'], 'b': [cap, cnum], 'bxy': cxy, 'kind': 'cap'})
for row, keys in sorted(rows.items()):
    keys.sort()
    for (_, a), (_, b) in zip(keys, keys[1:]):
        links.append({'net': NET, 'a': [a, '3'], 'b': [b, '3'], 'kind': 'row'})
# spine: the column-5 LEDs straight down the inner edge of the key block (encoder LEDs sit in rows 1 and 6)
spine = sorted(((xy, r) for keys in rows.values() for xy, r in keys if r[-1] == '5' and r[-2] != '6'), key=lambda k: k[0][1])
for (_, a), (_, b) in zip(spine, spine[1:]):
    links.append({'net': NET, 'a': [a, '3'], 'b': [b, '3'], 'kind': 'spine'})
thumb = min(((k, s) for k in rows['6'] for s in spine), key=lambda e: math.dist(e[0][0], e[1][0]))
links.append({'net': NET, 'a': [thumb[1][1], '3'], 'b': [thumb[0][1], '3'], 'kind': 'spine'})
unum, uxy = pads['U6'][0]
end = min(spine + rows['6'], key=lambda k: math.dist(k[0], uxy))
links.append({'net': NET, 'a': ['U6', unum], 'b': [end[1], '3'], 'axy': uxy, 'kind': 'feed'})
json.dump(links, open(sys.argv[2], 'w'), indent=0)
from collections import Counter
print(len(links), Counter(l['kind'] for l in links), 'spine', [k[1] for k in spine], 'feed', end[1])
