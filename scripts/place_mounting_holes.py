"""Place the M2 mounting holes from Ergogen's screw points.

    python place_mounting_holes.py <board.kicad_pcb> <ergogen_output_dir>

Reads screws.json (written by ergogen/export_points.js) and puts a MountingHole_2.2mm_M2 at each point, so
the PCB holes and the switch plate's holes come from the same geometry and cannot drift apart.

The holes are marked board_only: they carry no net and no schematic symbol, which is what that attribute is
for, and it keeps `drc --schematic-parity` clean without inventing symbols for a mechanical feature.

Re-running moves existing H* footprints rather than adding duplicates. Restores the neighbouring .kicad_pro,
which BOARD.Save rewrites with defaults.
"""
import json
import os
import sys

import pcbnew

ORIGIN = (60.0, 140.0)          # Ergogen (0, 0) in board mm, y flips
FP_LIB = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'KiCad', '10.0', 'share', 'kicad',
                      'footprints', 'MountingHole.pretty')
FP_NAME = 'MountingHole_2.2mm_M2'

board_path, out_dir = sys.argv[1], sys.argv[2]
screws = json.load(open(os.path.join(out_dir, 'screws.json')))
pro = board_path.replace('.kicad_pcb', '.kicad_pro')
keep = open(pro, encoding='utf-8', newline='').read()
b = pcbnew.LoadBoard(board_path)
existing = {f.GetReference(): f for f in b.GetFootprints() if f.GetReference().startswith('H')}

for s in screws:
    x = pcbnew.FromMM(ORIGIN[0] + s['x'])
    y = pcbnew.FromMM(ORIGIN[1] - s['y'])
    fp = existing.get(s['ref'])
    if fp is None:
        fp = pcbnew.FootprintLoad(FP_LIB, FP_NAME)
        if fp is None:
            raise SystemExit(f'could not load {FP_NAME} from {FP_LIB}')
        b.Add(fp)
        fp.SetReference(s['ref'])
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY
                         | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
        how = 'added'
    else:
        how = 'moved'
    fp.SetPosition(pcbnew.VECTOR2I(x, y))
    fp.Reference().SetVisible(False)
    print(f'{s["ref"]:4} {how:6} at ({pcbnew.ToMM(x):7.2f}, {pcbnew.ToMM(y):7.2f})  from {s["name"]}')
b.Save(board_path)
open(pro, 'w', encoding='utf-8', newline='').write(keep)
print(f'{len(screws)} mounting holes on {os.path.basename(board_path)}')
