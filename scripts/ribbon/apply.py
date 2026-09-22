"""Write ribbon router output (tracks, vias) onto a copy of a board. Restores the neighbouring .kicad_pro.

    python apply.py in.kicad_pcb routes.json out.kicad_pcb
"""
import json
import shutil
import sys

import pcbnew

mm = pcbnew.FromMM
src, routes, dst = sys.argv[1:4]
pro = dst.replace('.kicad_pcb', '.kicad_pro')
shutil.copy(src.replace('.kicad_pcb', '.kicad_pro'), pro)
b = pcbnew.LoadBoard(src)
r = json.load(open(routes))
for s, x1, y1, x2, y2, net, *w in r['tracks']:
    t = pcbnew.PCB_TRACK(b); t.SetLayer(pcbnew.F_Cu if s == 'F' else pcbnew.B_Cu); t.SetWidth(mm(w[0] if w else 0.2))
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1))); t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    b.Add(t); t.SetNet(b.FindNet(net))
for x, y, net in r['vias']:
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(pcbnew.F_Cu, mm(0.6)); v.SetDrill(mm(0.3)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    b.Add(v); v.SetNet(b.FindNet(net))
b.Save(dst)
shutil.copy(src.replace('.kicad_pcb', '.kicad_pro'), pro)
print(len(r['tracks']), 'tracks', len(r['vias']), 'vias')
