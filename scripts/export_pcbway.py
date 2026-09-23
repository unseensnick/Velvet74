"""Write the PCBWay fabrication set: gerbers, drills, placement file, MPN BOM and assembly drawings.

From a shell (pcbnew closed, though this one only reads the board):
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" scripts/export_pcbway.py velvet74.kicad_pcb

Overwrites everything in production/pcbway/ beside the board. It never touches the board or the .kicad_pro.

Not the Fabrication Toolkit, because that plugin writes JLCPCB's conventions. Two differences matter and both are
deliberate:

- Rotation. The board's FT Rotation Offset fields correct for JLC's own part library, so they are NOT applied
  here; the placement file keeps KiCad's native angles, which for a bottom-side part are in the footprint's own
  frame rather than mirrored into a top view. Mixing this file with production/jlcpcb/positions.csv rotates parts.
- Origin. kicad-cli writes each footprint's anchor. That is the part centroid everywhere except the mid-mount
  USB-C, whose anchor sits at the connector mouth, so those four rows are moved onto the pad field instead.

PCBWay sources by manufacturer part number rather than LCSC code, so the BOM is keyed on MPN. Four parts have no
MPN field on the board and are filled from FILL below.
"""
import collections
import csv
import os
import re
import subprocess
import sys

import pcbnew

CLI = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'KiCad', '10.0', 'bin', 'kicad-cli.exe')
GERBER_LAYERS = ('F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,'
                 'F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts')

# Distance from the mid-mount USB-C footprint's anchor to the centre of its pad field, measured by fitting the
# manufacturer's own footprint (easyeda2kicad, C19274022) onto ours. Local frame, y down.
USB_LOCAL_DY = -3.945
CONNECTORS = ('J1', 'J2', 'J201', 'J202')

# LCSC code -> (MPN, manufacturer), for parts whose Part field the LCSC sync left empty
FILL = {
    'C2040': ('RP2040', 'Raspberry Pi'),
    'C5149201': ('SK6812MINI-E', 'OPSCO Optoelectronics'),
    'C100024': ('SN74LV1T34DBVR', 'Texas Instruments'),
    'C19274022': ('HC-TYPE-C-16P-C16B', 'HongCheng'),
}
MAKER = {'C720477': 'XUNPU'}                    # manufacturer the sync left blank
# footprint name -> the package string PCBWay expects
PACKAGE = (
    (r'^C_(\d{4})$', r'\1'), (r'^R_(\d{4})$', r'\1'), (r'^Fuse_(\d{4}).*$', r'\1'),
    (r'^D_(SOD-\S+)$', r'\1'), (r'^SOT-23-5.*', 'SOT-23-5'), (r'^SOT-563.*', 'SOT-563'),
    (r'^QFN-56.*', 'QFN-56 7x7mm'), (r'^WSON-8.*', 'WSON-8 6x5mm'),
    (r'^CRYSTAL-SMD_4P.*', 'SMD 3.2x2.5mm'), (r'^LED-SMD_4P.*', 'SK6812MINI-E 3.2x2.8mm'),
    (r'^SW_Push.*', 'SMD 4x3mm'), (r'^USB_C_Receptacle.*', 'USB-C 16P mid-mount'),
)


def _cli(*args):
    subprocess.run([CLI, 'pcb'] + list(args), check=True, capture_output=True)


def export_gerbers(board_path, out_dir):
    """Gerbers plus separate PTH and NPTH Excellon drills, zipped the way PCBWay wants them uploaded."""
    import zipfile

    raw = os.path.join(out_dir, 'gerbers')
    _cli('export', 'gerbers', '--output', raw, '--layers', GERBER_LAYERS,
         '--no-protel-ext', '--subtract-soldermask', board_path)
    _cli('export', 'drill', '--output', raw, '--format', 'excellon', '--drill-origin', 'absolute',
         '--excellon-units', 'mm', '--excellon-separate-th', '--generate-map',
         '--map-format', 'gerberx2', board_path)
    with zipfile.ZipFile(os.path.join(out_dir, 'gerbers.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(raw)):
            z.write(os.path.join(raw, name), name)
    for name in os.listdir(raw):
        os.remove(os.path.join(raw, name))
    os.rmdir(raw)


def export_drawings(board_path, out_dir):
    """Fab-layer drawings. PCBWay's own advice is to settle component orientation from these."""
    for side, layers, mirror in (('bottom', 'B.Fab,Edge.Cuts', True), ('top', 'F.Fab,Edge.Cuts', False)):
        args = ['export', 'pdf', '--output', os.path.join(out_dir, 'assembly-%s.pdf' % side),
                '--layers', layers, '--sketch-pads-on-fab-layers', '--black-and-white',
                '--mode-single', '--include-border-title']
        if mirror:
            args.append('--mirror')
        _cli(*(args + [board_path]))


def export_positions(board, board_path, out_dir):
    """kicad-cli's placement file, with the connector rows moved from the anchor onto the part centroid."""
    import math

    path = os.path.join(out_dir, 'positions.csv')
    _cli('export', 'pos', '--output', path, '--format', 'csv', '--units', 'mm',
         '--side', 'both', '--exclude-dnp', board_path)

    centre = {}
    for ref in CONNECTORS:
        fp = board.FindFootprintByReference(ref)
        ly = -USB_LOCAL_DY if fp.IsFlipped() else USB_LOCAL_DY
        a = math.radians(fp.GetOrientationDegrees())
        centre[ref] = (pcbnew.ToMM(fp.GetPosition().x) + ly * math.sin(a),
                       pcbnew.ToMM(fp.GetPosition().y) + ly * math.cos(a))

    with open(path, encoding='utf-8', newline='') as fh:
        rows = list(csv.reader(fh))
    ix, iy = rows[0].index('PosX'), rows[0].index('PosY')
    for r in rows[1:]:
        ref = r[0].strip('"')
        if ref in centre:
            r[ix], r[iy] = '%.6f' % centre[ref][0], '%.6f' % -centre[ref][1]
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        csv.writer(fh, lineterminator='\n').writerows(rows)
    return len(rows) - 1


def _package_of(name):
    for pattern, replacement in PACKAGE:
        if re.match(pattern, name):
            return re.sub(pattern, replacement, name)
    return name


def _natural(ref):
    m = re.match(r'([A-Za-z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def export_bom(board, out_dir):
    """One line per manufacturer part number, in PCBWay's turnkey columns."""
    lines = collections.defaultdict(list)
    for fp in board.GetFootprints():
        if fp.GetAttributes() & (pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES):
            continue
        f = {x.GetName(): x.GetText() for x in fp.GetFields()}
        lcsc = f.get('LCSC', '')
        mpn, maker = f.get('Part', ''), f.get('Manufacturer', '')
        if not mpn:
            mpn, maker = FILL[lcsc]
        maker = re.sub(r'\s*\(.*', '', maker or MAKER.get(lcsc, '')).strip()
        kinds = {p.GetAttribute() for p in fp.Pads()}
        # only the USB-C mixes lead types; the RP2040's through-holes are its thermal vias, not leads
        hybrid = fp.GetReference().startswith('J') and kinds >= {pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_SMD}
        key = (mpn, maker, f.get('Description', '').strip() or f.get('Value', ''),
               _package_of(fp.GetFPIDAsString().split(':')[-1]), 'Hybrid' if hybrid else 'SMD')
        lines[key].append(fp.GetReference())

    rows = sorted(lines.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))
    with open(os.path.join(out_dir, 'bom.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Line#', 'Qty', 'Designator', 'MPN', 'Manufacturer', 'Description', 'Package', 'Type'])
        for i, (key, refs) in enumerate(rows, 1):
            w.writerow([i, len(refs), ','.join(sorted(refs, key=_natural))] + list(key))
    return len(rows), sum(len(r) for _, r in rows)


board_path = os.path.abspath(sys.argv[1])
out_dir = os.path.join(os.path.dirname(board_path), 'production', 'pcbway')
os.makedirs(out_dir, exist_ok=True)
board = pcbnew.LoadBoard(board_path)

export_gerbers(board_path, out_dir)
export_drawings(board_path, out_dir)
placed = export_positions(board, board_path, out_dir)
bom_lines, bom_parts = export_bom(board, out_dir)
print('%s: %d placements, %d BOM lines covering %d parts' % (out_dir, placed, bom_lines, bom_parts))
