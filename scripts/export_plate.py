"""Write production/plate/: gerbers and drill for the FR4 top plate, both halves on the PCB panel's rails and tabs.

Run `npm run build` in ergogen/ first; it writes ergogen/output/pcbs/plate_only.kicad_pcb, the plate outline
(switch, screw and screen openings cut out) on the same rails and tabs as the PCB. From a shell:
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/export_plate.py

It moves that outline onto the PCB's sheet position, adds the PCB panel's mouse bites and tooling holes (not the
fiducials: nothing is assembled on the plate), sets the thickness to plate_t (0.8 mm) and exports with kicad-cli.
Overwrites production/plate/velvet74-plate.zip. Reads the design files only; the board it builds lives in a temp
folder, so no .kicad_pro in the repo is touched.
"""
import os
import subprocess
import sys
import tempfile
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from place_panel import PARTS, add_part  # noqa: E402  (the same holes as the PCB panel)

F = pcbnew.FromMM
# Ergogen's origin lands here on the KiCad sheet, as in place_from_ergogen.py
ORIGIN = (60.0, 140.0)
PLATE_T = 0.8   # ergogen/config.yaml plate_t
CLI = os.path.join(os.path.dirname(sys.executable), 'kicad-cli.exe')
LAYERS = 'F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts'


def main():
    b = pcbnew.LoadBoard(os.path.join(REPO, 'ergogen', 'output', 'pcbs', 'plate_only.kicad_pcb'))
    shift = pcbnew.VECTOR2I(F(ORIGIN[0]), F(ORIGIN[1]))
    for d in b.GetDrawings():
        d.Move(shift)
    for part in PARTS:
        if not part[2].startswith('FID'):
            add_part(b, *part)
    b.GetDesignSettings().SetBoardThickness(F(PLATE_T))
    tb = b.GetTitleBlock()
    tb.SetTitle('Velvet74 FR4 plate')
    tb.SetComment(3, 'https://github.com/unseensnick/Velvet74')

    out = os.path.join(REPO, 'production', 'plate')
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        board = os.path.join(tmp, 'velvet74-plate.kicad_pcb')
        b.Save(board)
        gerb = os.path.join(tmp, 'gerbers')
        os.makedirs(gerb)
        subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--no-protel-ext', '-o', gerb, board], check=True)
        subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
                        '--generate-map', '--map-format', 'gerberx2', '-o', gerb + os.sep, board], check=True)
        target = os.path.join(out, 'velvet74-plate.zip')
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(os.listdir(gerb)):
                z.write(os.path.join(gerb, f), f)
        print('wrote', target, 'with', ', '.join(sorted(os.listdir(gerb))))


if __name__ == '__main__':
    main()
