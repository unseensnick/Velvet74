"""Build the RP2040 inner-column module board from its schematic netlist and place every part (no routing).

Regenerating overwrites templates/rp2040-inner-column/RP2040InnerColumn.kicad_pcb, routing included:

    kicad-cli sch export netlist -o module.net templates/rp2040-inner-column/RP2040InnerColumn.kicad_sch
    "C:/Program Files/KiCad/8.0/bin/python.exe" scripts/build_rp2040_module.py module.net
"""
import math
import os
import re
import sys

import pcbnew

T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'rp2040-inner-column')
NET = sys.argv[1]
OUT = os.path.join(T, 'RP2040InnerColumn.kicad_pcb')
ENV = {'KICAD8_3RD_PARTY': os.path.expanduser(r'~\Documents\KiCad\8.0\3rdparty'),
       'KICAD8_FOOTPRINT_DIR': r'C:\Program Files\KiCad\8.0\share\kicad\footprints', 'KIPRJMOD': T}
W, H = 19.56, 41.6          # strip measured on the Sofle: right and top are real board edges
mm = pcbnew.FromMM


def libs():
    table = {}
    for path in (os.path.join(os.environ['APPDATA'], r'kicad\8.0\fp-lib-table'), os.path.join(T, 'fp-lib-table')):
        for name, uri in re.findall(r'\(name "([^"]+)"\)\(type "[^"]+"\)\(uri "([^"]+)"\)', open(path, encoding='utf-8').read()):
            table[name] = re.sub(r'\$\{(\w+)\}', lambda m: ENV.get(m.group(1), m.group(0)), uri)
    return table


def read_netlist(path):
    text = open(path, encoding='utf-8').read()
    comps = {}
    for block in re.findall(r'\(comp \(ref "[^"]+"\).*?\(tstamps "[^"]+"\)\)', text, re.S):
        ref = re.search(r'\(ref "([^"]+)"\)', block).group(1)
        comps[ref] = dict(
            value=re.search(r'\(value "([^"]*)"\)', block).group(1),
            footprint=re.search(r'\(footprint "([^"]*)"\)', block).group(1),
            uuid=re.search(r'\(tstamps "([^"]+)"\)', block).group(1),
            fields=dict(re.findall(r'\(field \(name "([^"]+)"\) "([^"]*)"\)', block)))
    nets = {}
    for block in re.split(r'\(net \(code', text)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', block).group(1)
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block):
            nets[(ref, pin)] = name
    return comps, nets


# ------------------------------------------------------------------ placement (mm, y down, back side)
# Rotation is applied after flipping to the back. Order matters: earlier parts claim space first.
# Each entry: ref -> (x, y, rot) preferred spot, or ('pin', ref, pin, distance) to sit outside that pad.
U1_AT = (8.0, 22.0, 90)   # after the flip, rot 90 puts USB/QSPI on the right side and XIN/XOUT on the left
PLACE = [
    ('J1', (W / 2, 5.0, 0)),                 # mouth exactly on the top edge
    ('U1', U1_AT),
    ('U4', (W / 2, 10.6, 0)),                # ESD right under the D+/D- pads
    ('C8', ('pin', 'U1', '45', 1.35)), ('C6', ('pin', 'U1', '50', 1.35)), ('C5', ('pin', 'U1', '23', 1.35)),  # 1V1 first
    ('R7', ('pin', 'U1', '47', 1.9)), ('R8', ('pin', 'U1', '46', 1.9)),   # 27R at the USB pins
    ('U3', (16.4, 27.0, 180)),               # flash pins 5-8 (DI, CLK, HOLD, VCC) face the QSPI pins
    ('X1', (1.9, 22.4, 90)),                 # crystal at XIN/XOUT
    ('C1', ('pin', 'X1', '3', 1.6)), ('C4', ('pin', 'X1', '1', 1.6)), ('R2', ('pin', 'U1', '21', 3.6)),
    ('C17', ('pin', 'U1', '43', 1.35)), ('C7', ('pin', 'U1', '44', 1.35)),
    ('C16', ('pin', 'U1', '48', 1.35)), ('C15', ('pin', 'U1', '49', 1.35)),
    ('C10', ('pin', 'U1', '1', 1.35)), ('C11', ('pin', 'U1', '10', 1.35)), ('C12', ('pin', 'U1', '22', 1.35)),
    ('C13', ('pin', 'U1', '33', 1.35)), ('C14', ('pin', 'U1', '42', 1.35)),
    ('C3', ('pin', 'U3', '8', 1.6)),
    ('R5', ('pin', 'J1', 'A5', 2.8)), ('R6', ('pin', 'J1', 'B5', 2.8)),
    ('F1', (2.2, 11.6, 90)), ('D1', (5.4, 12.2, 90)),
    ('U5', (2.4, 16.4, 0)), ('C20', ('pin', 'U5', '1', 1.6)), ('C19', ('pin', 'U5', '5', 1.6)),
    ('C18', (15.8, 16.0, 0)), ('C9', (15.8, 34.2, 0)),
    ('SW1', (4.4, 38.3, 0)), ('R4', ('pin', 'SW1', '2', 2.0)), ('SW2', (14.9, 38.3, 0)),
]
CLEAR = 0.0       # boxes already include PAD_GAP around every pad
PAD_GAP = 0.13    # touching boxes keep pads 0.26 mm apart (DRC copper clearance is 0.2)
EDGE = 0.4        # copper stays at least 0.53 mm off the outline (DRC wants 0.5); J1 sits on the edge on purpose


def main():
    table = libs()
    comps, nets = read_netlist(NET)
    board = pcbnew.BOARD()
    netinfo = {}
    def net(name):
        if name not in netinfo:
            n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); netinfo[name] = n
        return netinfo[name]
    # outline
    for (x1, y1), (x2, y2) in (((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1))); s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2))); s.SetWidth(mm(0.15))
        board.Add(s)
    fps = {}
    for ref, c in sorted(comps.items()):
        lib, name = c['footprint'].split(':', 1)
        fp = pcbnew.FootprintLoad(table[lib], name)
        fp.SetFPIDAsString(c['footprint'])
        fp.SetReference(ref); fp.SetValue(c['value'])
        for k, v in c['fields'].items():
            if k not in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description'):
                fp.SetField(k, v)
                field = fp.GetFieldByName(k)
                field.SetLayer(pcbnew.F_Fab); field.SetVisible(False)   # SetField defaults to visible silkscreen text
        fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        fp.SetSheetname('/'); fp.SetSheetfile('RP2040InnerColumn.kicad_sch')
        board.Add(fp)
        for pad in fp.Pads():
            if (ref, pad.GetNumber()) in nets:
                pad.SetNet(net(nets[(ref, pad.GetNumber())]))
        fps[ref] = fp
    def courtyard(fp):
        # some JLC footprints draw courtyards tighter than their pads, so take the union with padded pad boxes
        boxes = [fp.GetCourtyard(l).BBox() for l in (pcbnew.B_CrtYd, pcbnew.F_CrtYd) if fp.GetCourtyard(l).OutlineCount()]
        edges = [(pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom())) for b in boxes]
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            edges.append((pcbnew.ToMM(b.GetLeft()) - PAD_GAP, pcbnew.ToMM(b.GetTop()) - PAD_GAP,
                          pcbnew.ToMM(b.GetRight()) + PAD_GAP, pcbnew.ToMM(b.GetBottom()) + PAD_GAP))
        return (min(e[0] for e in edges), min(e[1] for e in edges), max(e[2] for e in edges), max(e[3] for e in edges))
    def put(ref, x, y, rot):
        fp = fps[ref]
        if not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        return courtyard(fp)
    placed = {}
    def free(box, ref):
        l, tp, r, b = box
        if ref != 'J1' and (l < EDGE or tp < EDGE or r > W - EDGE or b > H - EDGE):
            return False
        return all(l >= pr + CLEAR or r <= pl - CLEAR or tp >= pb + CLEAR or b <= pt - CLEAR for pl, pt, pr, pb in placed.values())
    report = []
    for ref, spec in PLACE:
        if spec[0] == 'pin':
            _, host, pin, dist = spec
            h = fps[host]; hc = h.GetPosition()
            pad = next(p for p in h.Pads() if p.GetNumber() == pin)
            pp = pad.GetPosition()
            dx, dy = pcbnew.ToMM(pp.x - hc.x), pcbnew.ToMM(pp.y - hc.y)
            n = math.hypot(dx, dy) or 1
            ux, uy = dx / n, dy / n
            if abs(dx) >= abs(dy):
                ux, uy, rot = (1 if dx > 0 else -1), 0, 90
            else:
                ux, uy, rot = 0, (1 if dy > 0 else -1), 0
            x0, y0 = pcbnew.ToMM(pp.x) + ux * dist, pcbnew.ToMM(pp.y) + uy * dist
            rots = (rot, (rot + 90) % 180)
        else:
            x0, y0, rot = spec
            rots = (rot,) if ref in ('J1', 'U1', 'U3', 'SW1', 'SW2') else (rot, (rot + 90) % 180)
        best = None
        for radius_i in range(0, 41):                       # spiral out to 10 mm in 0.25 mm rings
            rr = radius_i * 0.25
            steps = max(1, int(2 * math.pi * rr / 0.25))
            for s in range(steps):
                a = 2 * math.pi * s / steps
                for rt in rots:
                    x, y = x0 + rr * math.cos(a), y0 + rr * math.sin(a)
                    box = put(ref, x, y, rt)
                    if free(box, ref):
                        best = (x, y, rt, box, rr)
                        break
                if best: break
            if best: break
        if best is None:
            report.append(f'{ref}: NO FREE SPOT near ({x0:.1f},{y0:.1f})')
            put(ref, x0, y0, rot); placed[ref] = courtyard(fps[ref])
            continue
        x, y, rt, box, rr = best
        put(ref, x, y, rt); placed[ref] = box
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
    u1 = courtyard(fps['U1'])
    for dy in [i * 0.25 for i in range(40)]:
        for dx in [0] + [s * i * 0.25 for i in range(1, 20) for s in (1, -1)]:
            jlc.SetPosition(pcbnew.VECTOR2I(mm(U1_AT[0] + dx), mm(u1[3] + 0.6 + dy)))
            bb = jlc.GetBoundingBox()
            box = (pcbnew.ToMM(bb.GetLeft()) - 0.15, pcbnew.ToMM(bb.GetTop()) - 0.15, pcbnew.ToMM(bb.GetRight()) + 0.15, pcbnew.ToMM(bb.GetBottom()) + 0.15)
            if free(box, 'JLC'):
                break
        else:
            continue
        break
    else:
        print('  JLC marker: NO FREE SPOT below U1')
    print(f'  JLC marker at ({pcbnew.ToMM(jlc.GetPosition().x):.2f}, {pcbnew.ToMM(jlc.GetPosition().y):.2f})')
    board.Save(OUT)
    missing = sorted(set(comps) - {r for r, _ in PLACE})
    print(f'placed {len(PLACE)} of {len(comps)} parts; unplaced: {missing}')


main()
