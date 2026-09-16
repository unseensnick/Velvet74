"""Add router keep-outs to a board JSON (from extract.py).

    python add_keepouts.py board.json

- Under X1: crystal nets and GND only (Corne v4 keeps its crystal area clear of other signals).
- F.Cu trunk corridor between the key block and the controller strip: only the matrix trunks (rows GP18-GP23,
  columns GP24-GP29) and GND, so key-area lines and strip vias leave the bundle its lanes.
"""
import json
import sys

d = json.load(open(sys.argv[1]))
x = d['fps']['X1']
h = 2.0         # 3225 crystal body rotated 45 degrees, kept out of the corridor
trunks = [f'GP{n}' for n in range(18, 30)]
d['keepouts'] = [
    {'poly': [[x['x'] - h, x['y'] - h], [x['x'] + h, x['y'] - h], [x['x'] + h, x['y'] + h], [x['x'] - h, x['y'] + h]],
     'layers': 'FB', 'nets': ['XTAL_IN', 'XTAL_OUT', 'Net-(C4-Pad2)', 'GND']},
    {'poly': [[156.4, 60.0], [159.6, 60.0], [159.6, 152.0], [156.4, 152.0]], 'layers': 'F', 'nets': trunks + ['GND']},
]
json.dump(d, open(sys.argv[1], 'w'))
print('keepouts', len(d['keepouts']))
