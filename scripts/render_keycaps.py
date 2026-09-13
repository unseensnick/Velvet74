"""Draw the Ergogen layout as keycaps: one panel with every combo spot as a 1u key,
one with encoder knobs there. Needs `npm run build` in ergogen/ first. Stdlib only.

    python scripts/render_keycaps.py [knob diameter mm, default 14]
"""
import json
import math
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, 'ergogen', 'output')
CAP_1U = (17.5, 16.5)      # MBK-style Choc keycap
CAP_TALL = (16.5, 26.5)    # 1.5u standing vertical
TALL_KEYS = {'SW64'}
LED_OFFSET = 4.7
FACING = {'north': (0, 1), 'south': (0, -1), 'east': (1, 0), 'west': (-1, 0)}
KNOB = float(sys.argv[1]) if len(sys.argv) > 1 else 14.0  # the user's knobs


def rotate(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def cap_polygon(p):
    w, h = CAP_TALL if p['ref'] in TALL_KEYS else CAP_1U
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    # Ergogen is y-up; SVG is y-down
    return ' '.join(f'{p["x"] + dx:.3f},{-(p["y"] + dy):.3f}' for dx, dy in (rotate(cx, cy, p['r']) for cx, cy in corners))


def outline_path():
    text = open(os.path.join(OUT, 'pcbs', 'outline_only.kicad_pcb'), encoding='utf-8').read()
    num = r'(-?[\d.]+)'
    parts = [f'M{x1},{y1} L{x2},{y2}' for x1, y1, x2, y2 in
             re.findall(rf'\(gr_line \(start {num} {num}\) \(end {num} {num}\) \(layer Edge\.Cuts\)', text)]
    if re.search(r'\(gr_(arc|circle)', text):
        raise SystemExit('outline has arcs; extend render_keycaps.py before using it')
    return ' '.join(parts)


def panel(points, dx, title, with_knobs, title_y):
    g = [f'<g transform="translate({dx} 0)">',
         f'<text x="{min(p["x"] for p in points) - 10:.1f}" y="{title_y:.1f}" font-size="5" font-family="sans-serif" fill="#222">{title}</text>',
         f'<path d="{outline_path()}" fill="none" stroke="#2b7a3a" stroke-width="0.6"/>']
    for p in points:
        knob_here = with_knobs and p['combo']
        if knob_here:
            g.append(f'<rect x="{p["x"] - 6:.3f}" y="{-p["y"] - 6:.3f}" width="12" height="12" fill="#bbb" stroke="#777" stroke-width="0.3"/>')
            g.append(f'<circle cx="{p["x"]:.3f}" cy="{-p["y"]:.3f}" r="{KNOB / 2}" fill="#555" stroke="#111" stroke-width="0.5"/>')
            g.append(f'<circle cx="{p["x"]:.3f}" cy="{-p["y"]:.3f}" r="{KNOB / 2 - 1.2}" fill="none" stroke="#888" stroke-width="0.3"/>')
            continue
        g.append(f'<polygon points="{cap_polygon(p)}" fill="#2a2a2a" stroke="#000" stroke-width="0.4"/>')
        fx, fy = FACING[p['led']]
        lx, ly = rotate(fx * LED_OFFSET, fy * LED_OFFSET, p['r'])
        g.append(f'<circle cx="{p["x"] + lx:.3f}" cy="{-(p["y"] + ly):.3f}" r="1.1" fill="#b388ff"/>')
        g.append(f'<text x="{p["x"]:.3f}" y="{-p["y"] + 2:.3f}" font-size="3" text-anchor="middle" font-family="sans-serif" fill="#888">{p["ref"]}</text>')
    g.append('</g>')
    return '\n'.join(g)


def main():
    points = json.load(open(os.path.join(OUT, 'points.json'), encoding='utf-8'))
    xs = [p['x'] for p in points]
    ys = [-p['y'] for p in points]
    pad = 25
    width = max(xs) - min(xs) + 2 * pad
    left, top = min(xs) - pad, min(ys) - pad - 20
    height = max(ys) - min(ys) + 2 * pad + 20
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {2 * width + 10} {height}" '
           f'width="{(2 * width + 10) * 4:.0f}" height="{height * 4:.0f}">',
           f'<rect x="{left}" y="{top}" width="{2 * width + 10}" height="{height}" fill="#f4f4f0"/>',
           panel(points, 0, 'All keys (combo spots as 1u keys)', False, top + 12),
           panel(points, width + 10, f'Two encoders ({KNOB:g} mm knobs)', True, top + 12),
           '</svg>']
    path = os.path.join(OUT, 'keycap_preview.svg')
    open(path, 'w', encoding='utf-8').write('\n'.join(svg))
    print(f'wrote {path}')


main()
