"""Add the 2-layer copper zones to a routed board copy and fill them. Restores the neighbouring .kicad_pro.

    python zones.py in.kicad_pcb out.kicad_pcb

Removes any existing zones first.

- F.Cu GND pour over the whole board: 0.5 mm clearance, 0.5 mm thermal gap and spokes, islands always removed
  (the Corne v4 / x2 settings; LED and cap GND pads reach it through their drop vias).
- B.Cu +3.3V ring inside U1's pad ring, solid-connected, higher priority: ties the IOVDD pins the way the
  Raspberry Pi design example and Splinky/rp-micro do.
"""
import math
import shutil
import sys

import pcbnew

mm = pcbnew.FromMM
src, dst = sys.argv[1:3]
pro_src, pro_dst = src.replace('.kicad_pcb', '.kicad_pro'), dst.replace('.kicad_pcb', '.kicad_pro')
b = pcbnew.LoadBoard(src)


def square(cx, cy, half, rot_deg):
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        a = math.radians(rot_deg)
        x, y = sx * half, sy * half
        pts.append(pcbnew.VECTOR2I(mm(cx + x * math.cos(a) - y * math.sin(a)), mm(cy + x * math.sin(a) + y * math.cos(a))))
    return pts


def zone(layer, net, outline, holes=(), clearance=0.5, min_width=0.25, priority=0, solid=False):
    z = pcbnew.ZONE(b)
    b.Add(z)
    z.SetLayer(layer)
    z.SetNetCode(b.FindNet(net).GetNetCode())
    poly = pcbnew.SHAPE_POLY_SET()
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for p in outline:
        chain.Append(p)
    chain.SetClosed(True)
    poly.AddOutline(chain)
    for h in holes:
        hc = pcbnew.SHAPE_LINE_CHAIN()
        for p in h:
            hc.Append(p)
        hc.SetClosed(True)
        poly.AddHole(hc)
    z.SetOutline(poly)
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(min_width))
    z.SetAssignedPriority(priority)
    if solid:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    else:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.5))
        z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    return z


for old in list(b.Zones()):
    b.Delete(old)          # the placement-era GND zone spans both layers; this plan replaces it

bb = b.GetBoardEdgesBoundingBox()
zone(pcbnew.F_Cu, 'GND', [pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()), pcbnew.VECTOR2I(bb.GetRight(), bb.GetTop()),
                          pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()), pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())])

u1 = b.FindFootprintByReference('U1')
ux, uy, rot = pcbnew.ToMM(u1.GetPosition().x), pcbnew.ToMM(u1.GetPosition().y), u1.GetOrientationDegrees()
# pad inner ends sit about 3.0 mm from the centre, the exposed pad is 3.2 mm square
zone(pcbnew.B_Cu, '+3.3V', square(ux, uy, 3.2, rot), holes=[square(ux, uy, 1.95, rot)], clearance=0.13, min_width=0.2,
     priority=2, solid=True)

b.BuildConnectivity()      # KiCad 10 segfaults filling on a large board without fresh connectivity
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
shutil.copy(pro_src, pro_dst + '.keep')
b.Save(dst)
shutil.copy(pro_dst + '.keep', pro_dst)
print('zones', len(b.Zones()))
