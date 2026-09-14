"""Copy hand-finished routing from a module test board onto the RP2040 module template.

The routability test board is the template plus a 3 mm margin on the left and bottom holding one
test pad per GPIO. This copies its tracks, vias and GND pour onto the template:

- GPIO nets are followed out from the RP2040 pin and cut where they first cross the strip edge,
  so each GPIO ends on the left or bottom edge, ready to continue into the keyboard's key area.
- Every other net is copied whole, including any short detour past the strip edge.
- The GND pour is clipped to the strip.

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/transfer_module_routing.py routed_test.kicad_pcb
"""
import math
import os
import sys

import pcbnew

T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'rp2040-inner-column')
OUT = os.path.join(T, 'RP2040InnerColumn.kicad_pcb')
W, H = 19.56, 41.6          # strip size; J1 sits at (W / 2, 5) inside it
EPS = 1e-3
mm, ToMM = pcbnew.FromMM, pcbnew.ToMM


def clip_to_rect(x1, y1, x2, y2, l, t, r, b):
    """Liang-Barsky: parameter range [t0, t1] of the segment inside the rectangle, or None."""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - l), (dx, r - x1), (-dy, y1 - t), (dy, b - y1)):
        if abs(p) < 1e-12:
            if q < 0:
                return None
            continue
        u = q / p
        if p < 0:
            t0 = max(t0, u)
        else:
            t1 = min(t1, u)
    return (t0, t1) if t0 <= t1 else None


def main():
    src = pcbnew.LoadBoard(sys.argv[1])
    pro = os.path.splitext(OUT)[0] + '.kicad_pro'
    kept_pro = open(pro, 'rb').read()
    dst = pcbnew.LoadBoard(OUT)

    sfp = {f.GetReference(): f for f in src.GetFootprints()}
    dfp = {f.GetReference(): f for f in dst.GetFootprints()}
    for ref, f in dfp.items():
        s = sfp[ref]
        assert (s.GetPosition(), s.GetOrientationDegrees(), s.IsFlipped()) == (f.GetPosition(), f.GetOrientationDegrees(), f.IsFlipped()), \
            f'{ref} differs between the routed board and the template; copy positions first'
    assert not list(dst.GetTracks()) and not list(dst.Zones()), 'template already has routing'

    j = dfp['J1'].GetPosition()
    L, Tp = ToMM(j.x) - W / 2, ToMM(j.y) - 5.0
    R, B = L + W, Tp + H
    inside = lambda x, y: L - EPS <= x <= R + EPS and Tp - EPS <= y <= B + EPS

    tracks = [t for t in src.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [t for t in src.GetTracks() if t.GetClass() == 'PCB_VIA']
    added_tracks = added_vias = cut = 0

    def add_track(t, a, b):
        n = pcbnew.PCB_TRACK(dst)
        n.SetLayer(t.GetLayer()); n.SetWidth(t.GetWidth())
        n.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); n.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        dst.Add(n); n.SetNet(dst.FindNet(t.GetNetname()))

    def add_via(v):
        n = pcbnew.PCB_VIA(dst)
        n.SetPosition(v.GetPosition()); n.SetWidth(v.GetWidth(pcbnew.F_Cu)); n.SetDrill(v.GetDrill())
        n.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        dst.Add(n); n.SetNet(dst.FindNet(v.GetNetname()))

    # non-GPIO nets: copied whole
    for t in tracks:
        if not t.GetNetname().startswith('GP'):
            add_track(t, (ToMM(t.GetStart().x), ToMM(t.GetStart().y)), (ToMM(t.GetEnd().x), ToMM(t.GetEnd().y)))
            added_tracks += 1
    for v in vias:
        if not v.GetNetname().startswith('GP'):
            add_via(v); added_vias += 1

    # GPIO nets: clip every piece to the strip, then keep only copper still connected to the RP2040 pin.
    # Connection is by copper overlap (a track may end inside a via or on the middle of another track).
    def seg_dist(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.dist(p, (a[0] + u * dx, a[1] + u * dy))

    u1 = dfp['U1']
    for pad in u1.Pads():
        net = pad.GetNetname()
        if not net.startswith('GP'):
            continue
        items = []   # (kind, geometry, layers, source item, clipped at the edge)
        for t in tracks:
            if t.GetNetname() != net:
                continue
            a = (ToMM(t.GetStart().x), ToMM(t.GetStart().y)); b = (ToMM(t.GetEnd().x), ToMM(t.GetEnd().y))
            span = clip_to_rect(a[0], a[1], b[0], b[1], L, Tp, R, B)
            if not span:
                continue
            ca = (a[0] + (b[0] - a[0]) * span[0], a[1] + (b[1] - a[1]) * span[0])
            cb = (a[0] + (b[0] - a[0]) * span[1], a[1] + (b[1] - a[1]) * span[1])
            if math.dist(ca, cb) > EPS or math.dist(a, b) <= EPS:
                items.append(('seg', (ca, cb, ToMM(t.GetWidth()) / 2), {t.GetLayer()}, t, span != (0.0, 1.0)))
        for v in vias:
            vp = (ToMM(v.GetPosition().x), ToMM(v.GetPosition().y))
            if v.GetNetname() == net and inside(*vp):
                items.append(('via', (vp, ToMM(v.GetWidth(pcbnew.F_Cu)) / 2), {pcbnew.F_Cu, pcbnew.B_Cu}, v, False))

        def touches(i, j):
            (ki, gi, li, _, _), (kj, gj, lj, _, _) = items[i], items[j]
            if not li & lj:
                return False
            if ki == 'via' and kj == 'via':
                return math.dist(gi[0], gj[0]) <= gi[1] + gj[1]
            if ki == 'via' or kj == 'via':
                (sa, sb, sw), (vp, vr) = (gi, gj) if ki == 'seg' else (gj, gi)
                return seg_dist(vp, sa, sb) <= sw + vr
            return min(seg_dist(gi[0], *gj[:2]), seg_dist(gi[1], *gj[:2]), seg_dist(gj[0], *gi[:2]), seg_dist(gj[1], *gi[:2])) <= gi[2] + gj[2]

        # fanout stubs may start at the pad's outer edge rather than inside it
        pc = (ToMM(pad.GetPosition().x), ToMM(pad.GetPosition().y))
        reach = math.hypot(ToMM(pad.GetSize().x), ToMM(pad.GetSize().y)) / 2
        on_pad = lambda it: it[0] == 'seg' and any(pad.IsOnLayer(l) for l in it[2]) and any(
            math.dist(q, pc) <= reach + it[1][2] for q in it[1][:2])
        keep = {i for i, it in enumerate(items) if on_pad(it)}
        todo = list(keep)
        while todo:
            i = todo.pop()
            for j in range(len(items)):
                if j not in keep and touches(i, j):
                    keep.add(j); todo.append(j)
        for i in sorted(keep):
            kind, g, _, s, _ = items[i]
            if kind == 'seg':
                add_track(s, g[0], g[1]); added_tracks += 1
            else:
                add_via(s); added_vias += 1
        edge = any(items[i][4] for i in keep)
        cut += edge
        if not edge:
            print(f'  WARNING: {net} does not reach the strip edge from U1 pin {pad.GetNumber()}')
        if len(items) - len(keep):
            print(f'  {net}: dropped {len(items) - len(keep)} piece(s) left unconnected after cutting at the edge')

    # GND pour, clipped to the strip
    for z in src.Zones():
        n = pcbnew.ZONE(dst)
        n.SetLayerSet(z.GetLayerSet()); n.SetNet(dst.FindNet(z.GetNetname()))
        n.SetLocalClearance(z.GetLocalClearance()); n.SetMinThickness(z.GetMinThickness())
        n.SetPadConnection(z.GetPadConnection()); n.SetThermalReliefGap(z.GetThermalReliefGap())
        n.SetThermalReliefSpokeWidth(z.GetThermalReliefSpokeWidth()); n.SetIslandRemovalMode(z.GetIslandRemovalMode())
        n.SetAssignedPriority(z.GetAssignedPriority())
        ol = n.Outline(); ol.NewOutline()
        for x, y in ((L, Tp), (R, Tp), (R, B), (L, B)):
            ol.Append(mm(x), mm(y))
        dst.Add(n)
    pcbnew.ZONE_FILLER(dst).Fill(dst.Zones())

    dst.Save(OUT)
    open(pro, 'wb').write(kept_pro)        # BOARD.Save rewrites the project file; keep the template's settings
    print(f'copied {added_tracks} track segments, {added_vias} vias, {len(list(src.Zones()))} pour(s); '
          f'{cut} GPIO trace(s) cut at the strip edge')


main()
