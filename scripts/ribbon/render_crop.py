"""Render a square crop of a dump_board.py JSON to PNG: B.Cu red, F.Cu blue, GND green.

    SC=<px per mm> uv run --no-project --with pillow python render_crop.py dump.json out.png cx cy half
"""
import json, sys
from PIL import Image, ImageDraw
g = json.load(open(sys.argv[1])); cx, cy, half = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]); SC = float(__import__("os").environ.get("SC", "90"))
img = Image.new('RGB', (int(2 * half * SC), int(2 * half * SC)), (20, 20, 24)); dr = ImageDraw.Draw(img, 'RGBA')
P = lambda x, y: ((x - cx + half) * SC, (y - cy + half) * SC)
for x1, y1, x2, y2, w, layer, net in g['tracks']:
    col = ((230, 80, 80, 210) if layer == 'B.Cu' else (70, 140, 240, 150)) if net != 'GND' else ((120, 230, 120, 220) if layer == 'B.Cu' else (120, 230, 200, 120))
    dr.line([P(x1, y1), P(x2, y2)], fill=col, width=max(1, int(w * SC)))
for p in g['pads']:
    col = (80, 200, 90, 240) if p['net'] == 'GND' else (210, 160, 60, 240)
    if p['round']:
        (x, y), r = p['c'], p['r']; dr.ellipse([P(x - r, y - r), P(x + r, y + r)], fill=col)
    else:
        dr.polygon([P(x, y) for x, y in p['poly']], fill=col)
for x, y, r, net in g['vias']:
    dr.ellipse([P(x - r, y - r), P(x + r, y + r)], fill=(120, 230, 120) if net == 'GND' else (200, 200, 200))
for ref, x, y in g['refs']:
    if abs(x - cx) < half and abs(y - cy) < half: dr.text(P(x, y), ref, fill=(255, 255, 255))
img.save(sys.argv[2]); print('saved')
