"""Build the RP2040 inner-column module board from its schematic netlist and place every part (no routing).

The template has no Edge.Cuts: it is pasted into a keyboard board. Like ScottoModules it holds two
groups, the USB and power module and the RP2040 module, which move as units on the host board.

Regenerating overwrites templates/rp2040-inner-column/RP2040InnerColumn.kicad_pcb, routing included:

    kicad-cli sch export netlist -o module.net templates/rp2040-inner-column/RP2040InnerColumn.kicad_sch
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/build_rp2040_module.py module.net
"""
import math
import os
import re
import sys

import pcbnew

T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'rp2040-inner-column')
NET = sys.argv[1]
OUT = os.path.join(T, 'RP2040InnerColumn.kicad_pcb')
# KiCad 10 resolves the KiCad 8 era ${KICAD8_3RD_PARTY} in older library tables to its own 3rdparty folder
THIRD_PARTY = os.path.expanduser(r'~\Documents\KiCad\10.0\3rdparty')
KICAD_SHARE = os.path.join(os.path.dirname(pcbnew.__file__), '..', '..', '..', 'share', 'kicad')   # bin\Lib\site-packages -> share\kicad
ENV = {'KICAD10_3RD_PARTY': THIRD_PARTY, 'KICAD8_3RD_PARTY': THIRD_PARTY, 'KIPRJMOD': T,
       'KICAD10_FOOTPRINT_DIR': os.path.normpath(os.path.join(KICAD_SHARE, 'footprints'))}
W, H = 19.56, 41.6          # placement area: the strip measured on the Sofle, whose top and right are board edges
GROUPS = {
    'USB and power': ['J1', 'U4', 'R5', 'R6', 'F1', 'D1', 'U5', 'C9', 'C18', 'C19', 'C20'],
    'RP2040': ['U1', 'U3', 'C3', 'X1', 'C1', 'C4', 'R2', 'R7', 'R8', 'C5', 'C6', 'C7', 'C8', 'C10', 'C11',
               'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'SW1', 'SW2', 'R4'],
}
mm = pcbnew.FromMM


def libs():
    # user table first (KiCad 10 nests the stock libraries as a "Table" row), then the project table wins
    table = {}
    def read(path):
        text = open(path, encoding='utf-8').read()
        for name, kind, uri in re.findall(r'\(name "([^"]+)"\)\s*\(type "([^"]+)"\)\s*\(uri "([^"]+)"\)', text):
            uri = re.sub(r'\$\{(\w+)\}', lambda m: ENV.get(m.group(1), m.group(0)), uri)
            if kind == 'Table':
                read(uri)
            else:
                table[name] = uri
    read(os.path.join(os.environ['APPDATA'], r'kicad\10.0\fp-lib-table'))
    read(os.path.join(T, 'fp-lib-table'))
    return table


def read_netlist(path):
    # KiCad 10 writes one token per indented line; fold the line breaks so both netlist styles parse alike
    text = re.sub(r'\s+\)', ')', re.sub(r'\s*\n\s*', ' ', open(path, encoding='utf-8').read()))
    comps = {}
    for block in re.findall(r'\(comp \(ref "[^"]+"\).*?\(tstamps "[^"]+"\)\)', text, re.S):
        ref = re.search(r'\(ref "([^"]+)"\)', block).group(1)
        comps[ref] = dict(
            value=re.search(r'\(value "([^"]*)"\)', block).group(1),
            footprint=re.search(r'\(footprint "([^"]*)"\)', block).group(1),
            uuid=re.search(r'\(tstamps "([^"]+)"\)', block).group(1),
            fields=dict(re.findall(r'\(field \(name "([^"]+)"\)(?: "([^"]*)")?\)', block)))   # empty fields have no value
    nets = {}
    for block in re.split(r'\(net \(code', text)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', block).group(1)
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block):
            nets[(ref, pin)] = name
    return comps, nets


# ------------------------------------------------------------------ placement (mm, y down, back side)
# Rotation is applied after flipping to the back. Order matters: earlier parts claim space first.
# Each entry: ref -> (x, y, rot) preferred spot, or ('pin', ref, pin, distance) to sit outside that pad.
# The RP2040 sits at 45 degrees (rot 135 after the flip): USB pins at the top corner toward J1, QSPI on
# the upper-right side toward the flash, GP18-29 up-left and GP12-17 down-left toward the key area,
# GP0-11 down-right toward the bottom edge, and the free corners next to the diamond take the caps.
# Chosen by autorouting shuffled variants with Freerouting (the only one that routed 100%).
U1_AT = (9.0, 26.0, 135)
PLACE = [
    ('J1', (W / 2, 5.0, 0)),                 # mouth exactly on the top edge
    ('U1', U1_AT),
    ('R7', ('pin', 'U1', '47', 2.2)), ('R8', ('pin', 'U1', '46', 2.2)),   # 27R at the USB pins, before caps crowd them
    ('U3', (14.6, 13.4, 315)),               # flash on the QSPI side, turned with the chip
    ('C3', ('pin', 'U3', '8', 1.8)),         # flash VCC cap
    ('X1', (4.6, 31.0, 45)),                 # crystal on the XIN/XOUT side
    ('SW1', (3.6, 38.3, 0)), ('SW2', (16.0, 38.3, 0)),
    # regulator group in the free corner beside the USB-C shell, out of the GP0-11 corridor on the right
    ('U5', (17.2, 4.4, 90)), ('C20', ('pin', 'U5', '1', 1.8)), ('C19', ('pin', 'U5', '5', 1.8)),
    ('C18', (17.4, 9.4, 0)), ('C9', (17.4, 11.2, 0)),
    ('U4', (6.6, 10.8, 0)),                  # ESD just behind J1's D+/D- pads
    ('C8', ('pin', 'U1', '45', 2.0)), ('C6', ('pin', 'U1', '50', 2.0)), ('C5', ('pin', 'U1', '23', 2.0)),  # 1V1 first
    ('C1', ('pin', 'X1', '3', 1.8)), ('C4', ('pin', 'X1', '1', 1.8)), ('R2', ('pin', 'U1', '21', 3.6)),
    ('C17', ('pin', 'U1', '43', 2.0)), ('C7', ('pin', 'U1', '44', 2.0)),
    ('C16', ('pin', 'U1', '48', 2.0)), ('C15', ('pin', 'U1', '49', 2.0)),
    ('C10', ('pin', 'U1', '1', 2.0)), ('C11', ('pin', 'U1', '10', 2.0)), ('C12', ('pin', 'U1', '22', 2.0)),
    ('C13', ('pin', 'U1', '33', 2.0)), ('C14', ('pin', 'U1', '42', 2.0)),
    ('R5', ('pin', 'J1', 'A5', 2.8)), ('R6', ('pin', 'J1', 'B5', 2.8)),
    ('F1', (2.0, 11.0, 90)), ('D1', (2.0, 15.6, 90)),
    ('R4', ('pin', 'SW1', '2', 2.0)),
]
CLEAR = 0.0       # boxes already include PAD_GAP around every pad
PAD_GAP = 0.4     # pads of different parts stay 0.8 mm apart: room for a 0.2 mm track with 0.2 mm clearance
RING = 1.2        # other parts' pads stay 1.6 mm (RING + PAD_GAP) off U1's pads, room to fan out and drop vias
EDGE = 0.4        # copper stays off the outline (DRC wants 0.5); J1 sits on the edge on purpose


def main():
    table = libs()
    comps, nets = read_netlist(NET)
    board = pcbnew.BOARD()
    netinfo = {}
    def net(name):
        if name not in netinfo:
            n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); netinfo[name] = n
        return netinfo[name]
    fps = {}
    for ref, c in sorted(comps.items()):
        lib, name = c['footprint'].split(':', 1)
        fp = pcbnew.FootprintLoad(table[lib], name)
        fp.SetFPIDAsString(c['footprint'])
        fp.SetReference(ref); fp.SetValue(c['value'])
        for k, v in c['fields'].items():
            if k in ('Datasheet', 'Description'):
                fp.GetField(k).SetText(v)   # built-in hidden fields; KiCad 10 DRC compares them with the symbol
            elif k not in ('Reference', 'Value', 'Footprint'):
                fp.SetField(k, v)
                field = fp.GetField(k)
                field.SetLayer(pcbnew.F_Fab); field.SetVisible(False)   # SetField defaults to visible silkscreen text
        fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        fp.SetSheetname('/'); fp.SetSheetfile('RP2040InnerColumn.kicad_sch')
        board.Add(fp)
        for pad in fp.Pads():
            if (ref, pad.GetNumber()) in nets:
                pad.SetNet(net(nets[(ref, pad.GetNumber())]))
        fps[ref] = fp
    def extents(fp, gap, with_courtyard):
        # some JLC footprints draw courtyards tighter than their pads, so take the union with padded pad boxes
        edges = []
        if with_courtyard:
            for layer in (pcbnew.B_CrtYd, pcbnew.F_CrtYd):
                if fp.GetCourtyard(layer).OutlineCount():
                    b = fp.GetCourtyard(layer).BBox()
                    edges.append((pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom())))
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            edges.append((pcbnew.ToMM(b.GetLeft()) - gap, pcbnew.ToMM(b.GetTop()) - gap,
                          pcbnew.ToMM(b.GetRight()) + gap, pcbnew.ToMM(b.GetBottom()) + gap))
        return (min(e[0] for e in edges), min(e[1] for e in edges), max(e[2] for e in edges), max(e[3] for e in edges))
    def put(ref, x, y, rot):
        fp = fps[ref]
        if not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    # Parts are rotated rectangles so a 45 degree RP2040 keeps its free corners. Each footprint's box is
    # measured once unrotated; on these flipped footprints orientation +t turns the board frame by -t.
    local = {}
    def box_at_zero(ref, gap, with_courtyard):
        put(ref, 0, 0, 0)
        l, t, r, b = extents(fps[ref], gap, with_courtyard)
        return ((l + r) / 2, (t + b) / 2, (r - l) / 2, (b - t) / 2)
    def rect(ref, x, y, rot, grow=0.0, key=None):
        ox, oy, hw, hh = local[key or ref]
        a = math.radians(-rot)
        return (x + ox * math.cos(a) - oy * math.sin(a), y + ox * math.sin(a) + oy * math.cos(a), hw + grow, hh + grow, a)
    def aabb(r):
        cx, cy, hw, hh, a = r
        ex, ey = hw * abs(math.cos(a)) + hh * abs(math.sin(a)), hw * abs(math.sin(a)) + hh * abs(math.cos(a))
        return (cx - ex, cy - ey, cx + ex, cy + ey)
    def overlap(r1, r2):
        # separating axis test for two rotated rectangles
        dx, dy = r2[0] - r1[0], r2[1] - r1[1]
        for _, _, _, _, a in (r1, r2):
            for ux, uy in ((math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))):
                ext = sum(hw * abs(math.cos(b) * ux + math.sin(b) * uy) + hh * abs(-math.sin(b) * ux + math.cos(b) * uy)
                          for _, _, hw, hh, b in (r1, r2))
                if abs(dx * ux + dy * uy) >= ext + CLEAR:
                    return False
        return True
    placed = {}
    ring = []
    def free(r, ref):
        l, tp, rt, b = aabb(r)
        if ref != 'J1' and (l < EDGE or tp < EDGE or rt > W - EDGE or b > H - EDGE):
            return False
        if ref not in ('U1', 'JLC') and ring and overlap(r, ring[0]):
            return False
        return not any(overlap(r, other) for other in placed.values())
    report = []
    for ref, spec in PLACE:
        local[ref] = box_at_zero(ref, PAD_GAP, True)
        if spec[0] == 'pin':
            _, host, pin, dist = spec
            h = fps[host]; hc = h.GetPosition(); hrot = h.GetOrientationDegrees()
            pad = next(p for p in h.Pads() if p.GetNumber() == pin)
            pp = pad.GetPosition()
            dx, dy = pcbnew.ToMM(pp.x - hc.x), pcbnew.ToMM(pp.y - hc.y)
            # which side of the host the pin is on, in the host's own frame, then back to the board frame
            a = math.radians(-hrot)
            lx, ly = dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)
            nlx, nly = ((1 if lx > 0 else -1), 0) if abs(lx) >= abs(ly) else (0, (1 if ly > 0 else -1))
            ux, uy = nlx * math.cos(a) - nly * math.sin(a), nlx * math.sin(a) + nly * math.cos(a)
            x0, y0 = pcbnew.ToMM(pp.x) + ux * dist, pcbnew.ToMM(pp.y) + uy * dist
            rot = (90 - math.degrees(math.atan2(uy, ux))) % 180   # pads stacked along the pin's outward direction
            rots = (rot, (rot + 90) % 180)
        else:
            x0, y0, rot = spec
            rots = (rot,) if ref in ('J1', 'U1', 'U3', 'SW1', 'SW2') else (rot, (rot + 90) % 360)
        best = None
        for radius_i in range(0, 41):                       # spiral out to 10 mm in 0.25 mm rings
            rr = radius_i * 0.25
            steps = max(1, int(2 * math.pi * rr / 0.25))
            for s in range(steps):
                ang = 2 * math.pi * s / steps
                for rt in rots:
                    x, y = x0 + rr * math.cos(ang), y0 + rr * math.sin(ang)
                    r = rect(ref, x, y, rt)
                    if free(r, ref):
                        best = (x, y, rt, r, rr)
                        break
                if best: break
            if best: break
        if best is None:
            report.append(f'{ref}: NO FREE SPOT near ({x0:.1f},{y0:.1f})')
            put(ref, x0, y0, rot); placed[ref] = rect(ref, x0, y0, rot)
            continue
        x, y, rt, r, rr = best
        put(ref, x, y, rt); placed[ref] = r
        if ref == 'U1':
            # other parts' padded boxes stay RING off U1's bare pads: room to fan out and drop vias
            local['U1_pads'] = box_at_zero('U1', 0.0, False)
            put(ref, x, y, rt)
            ring[:] = [rect(ref, x, y, rt, grow=RING, key='U1_pads')]
        if rr > 1.0:
            report.append(f'{ref}: moved {rr:.2f} mm from its preferred spot')
    for line in report:
        print('  ' + line)
    # reference designators crowd a board this dense; keep them on the fab layer for assembly drawings
    for fp in fps.values():
        fp.Reference().SetLayer(pcbnew.B_Fab)
    # JLCPCB replaces this marker with the order number instead of printing it somewhere random
    jlc = pcbnew.PCB_TEXT(board)
    jlc.SetText('JLCJLCJLCJLC'); jlc.SetLayer(pcbnew.B_SilkS); jlc.SetMirrored(True)
    jlc.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); jlc.SetTextThickness(mm(0.15))
    board.Add(jlc)
    # nearest free spot to just below U1, anywhere on the board, horizontal or vertical text
    u1 = aabb(placed['U1'])
    target = (U1_AT[0], u1[3] + 1.0)
    spots = sorted(((i * 0.25, j * 0.25, rot) for i in range(int(W / 0.25) + 1) for j in range(int(H / 0.25) + 1) for rot in (0, 90)),
                   key=lambda s: math.hypot(s[0] - target[0], s[1] - target[1]))
    for x, y, rot in spots:
        jlc.SetTextAngleDegrees(rot)
        jlc.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        bb = jlc.GetBoundingBox()
        l, t, r, b = (pcbnew.ToMM(bb.GetLeft()) - 0.15, pcbnew.ToMM(bb.GetTop()) - 0.15, pcbnew.ToMM(bb.GetRight()) + 0.15, pcbnew.ToMM(bb.GetBottom()) + 0.15)
        if free(((l + r) / 2, (t + b) / 2, (r - l) / 2, (b - t) / 2, 0.0), 'JLC'):
            break
    else:
        board.Remove(jlc)
        jlc = None
        print('  JLC marker: NO FREE SPOT on the board, left out')
    if jlc:
        print(f'  JLC marker at ({pcbnew.ToMM(jlc.GetPosition().x):.2f}, {pcbnew.ToMM(jlc.GetPosition().y):.2f})')
    grouped = {ref for refs in GROUPS.values() for ref in refs}
    assert grouped == set(fps), f'parts missing from GROUPS: {sorted(set(fps) - grouped)}, unknown: {sorted(grouped - set(fps))}'
    for name, refs in GROUPS.items():
        group = pcbnew.PCB_GROUP(board)
        group.SetName(name)
        board.Add(group)
        for ref in refs:
            group.AddItem(fps[ref])
        if name == 'RP2040' and jlc:
            group.AddItem(jlc)
    # BOARD.Save also rewrites the .kicad_pro beside it with default settings, wiping the net classes
    pro = os.path.splitext(OUT)[0] + '.kicad_pro'
    kept = open(pro, 'rb').read() if os.path.exists(pro) else None
    board.Save(OUT)
    if kept is not None:
        open(pro, 'wb').write(kept)
    missing = sorted(set(comps) - {r for r, _ in PLACE})
    print(f'placed {len(PLACE)} of {len(comps)} parts; unplaced: {missing}')


main()
