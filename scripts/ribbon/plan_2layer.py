"""Link lists for the 2-layer plan: +5V rows and switch-to-diode links on B.Cu, rows and LED data on either layer, columns prefer F.Cu;
LED and cap GND pads drop through a via to the F.Cu ground pour.

    python plan_2layer.py board.json outdir

Writes power_rows.json (GND drops, LED-cap and row +5V, run at W=0.3), power_spine.json (spine and U6 feed,
run at W=0.5) and matrix.json (switch, LED data, rows, columns, run at W=0.2).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
board, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
subprocess.run([sys.executable, os.path.join(HERE, 'make_links.py'), board, os.path.join(out, '_matrix.json')], check=True)
subprocess.run([sys.executable, os.path.join(HERE, 'make_power_links.py'), board, os.path.join(out, '_power.json')], check=True)
d = json.load(open(board))
matrix = json.load(open(os.path.join(out, '_matrix.json')))
power = json.load(open(os.path.join(out, '_power.json')))

drops = []
for p in d['pads']:
    if p['net'] == 'GND' and not p['drill'] and (
            (re.fullmatch(r'LED\d\d', p['ref']) and p['num'] == '1') or (re.fullmatch(r'C1\d\d', p['ref']) and p['num'] == '2')):
        xy = [sum(v) / len(p['poly']) for v in zip(*p['poly'])]
        drops.append({'net': 'GND', 'a': [p['ref'], p['num']], 'axy': xy, 'drop': True, 'kind': 'gnd'})

for l in power:
    l['layers'] = 'B'
rows = drops + [l for l in power if l['kind'] in ('cap', 'row')]
spine = [l for l in power if l['kind'] in ('spine', 'feed')]
order = {'switch': 0, 'led': 1, 'row': 2, 'column': 3}
for l in matrix:
    # rows and LED data must hop the +5V lane once per key (their pads interleave), so they keep both layers;
    # the switch-to-diode link stays beside its pads, and columns prefer F.Cu
    if l['kind'] == 'column':
        l['layers'], l['mult'] = 'FB', {'B': 3.0}
    elif l['kind'] == 'switch':
        l['layers'] = 'B'
    elif l['kind'] == 'led':
        l['via_cost'] = 2.0     # DIN is only reachable from above; a cheap via beats wrapping around the switch hole
matrix.sort(key=lambda l: order[l['kind']])
for name, links in (('power_rows', rows), ('power_spine', spine), ('matrix', matrix)):
    json.dump(links, open(os.path.join(out, name + '.json'), 'w'), indent=0)
    print(name, len(links))
