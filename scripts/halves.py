"""Tell the keyboard's two halves apart on the combined board.

The half sheet (sofle-choc-pro-half.kicad_sch) is used twice, as sheets Left and Right, so every part
exists twice: the same symbol in two sheet instances. A footprint's half is its sheet name, and its role
is the reference its symbol carries on the Left half, so SW10 is ('Left', 'SW10') and SW210 is
('Right', 'SW10'). Scripts address parts by (half, role) and never compute the Right half's numbers.

Imported by place_from_ergogen.py and snap_leds.py; stdlib plus pcbnew only.
"""

HALVES = ('Left', 'Right')


def half_of(fp):
    name = fp.GetSheetname().strip('/')
    if name not in HALVES:
        raise ValueError('%s is on sheet %r, not on a half' % (fp.GetReference(), fp.GetSheetname()))
    return name


def _symbol(fp):
    # /<sheet instance>/<symbol>: the symbol part is shared by both halves
    return fp.GetPath().AsString().rsplit('/', 1)[-1]


def by_role(board):
    """{(half, role): footprint} for every footprint on the board."""
    fps = list(board.GetFootprints())
    role = {_symbol(fp): fp.GetReference() for fp in fps if half_of(fp) == 'Left'}
    return {(half_of(fp), role[_symbol(fp)]): fp for fp in fps}
