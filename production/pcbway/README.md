# PCBWay production files

Velvet74, one panel holding both halves. Regenerate the whole folder with
`scripts/export_pcbway.py velvet74.kicad_pcb`, which drives KiCad 10.0.3's own `kicad-cli`
rather than the Fabrication Toolkit plugin, because that plugin writes JLCPCB's conventions.

| File | What it is |
| --- | --- |
| `gerbers.zip` | 11 gerber layers, separate PTH and NPTH Excellon drill files, and drill maps |
| `positions.csv` | 312 placements, all bottom side |
| `bom.csv` | 23 lines keyed by manufacturer part number, PCBWay's turnkey columns |
| `assembly-top.pdf`, `assembly-bottom.pdf` | Fabrication-layer drawings with pad outlines and numbers |

## Read this before uploading

**The rotation convention differs from the JLCPCB set, on purpose.** `positions.csv` holds KiCad's
native angles: for a bottom-side part the angle is in the footprint's own frame, not mirrored into
a top view. JLCPCB wants the mirrored angle plus a per-part correction for its own library, which
is what `../jlcpcb/positions.csv` contains and why the two files disagree (U3 reads 180 here and 0
there). **Do not mix the two files.** PCBWay publishes no rotation convention of its own and their
guidance is to confirm orientation from assembly drawings, which is why both are included here.
Ask them to confirm against `assembly-bottom.pdf` before the run.

**The four USB-C rows sit on the part centroid**, not on the footprint anchor. Our mid-mount
footprint anchors at the connector mouth, 3.945 mm from the centre of the pad field, so
`kicad-cli`'s raw output would have placed all four connectors 3.945 mm out. Every other part's
anchor already is its centroid.

## Parts

Four lines had no MPN on the board and were filled from the value, description and datasheet in
the repo: RP2040 (Raspberry Pi), SK6812MINI-E (OPSCO Optoelectronics), SN74LV1T34DBVR (Texas
Instruments) and HC-TYPE-C-16P-C16B (HongCheng). Worth a second look if PCBWay queries them.

The passives, the 1N4148W and the SOD-123 Schottky are generic: any equivalent part in the same
package is fine, and naming a manufacturer there is only a starting point for sourcing. The parts
that are not interchangeable are the RP2040, the ZD25Q128C flash, the AP2112K, the SN74LV1T34, the
ABM8-272-T3 crystal, the USBLC6-2P6 and the SK6812MINI-E.

**Not in this BOM, and not assembled by anyone:** 74 Kailh Choc hotswap sockets, two 1x04 OLED
headers and two solder jumpers per keyboard. Those are hand soldering. The Choc switches, keycaps,
EC11 encoders and OLED modules are separate purchases too.

## Ordering notes

- PCBWay's assembly minimum is **5 boards**, where JLCPCB's is 2, so the option of proving two
  first does not exist here.
- Assembly is quoted by a person, typically 1 to 2 business days after upload, rather than priced
  instantly.
- The panel is 268 x 131 mm on 5 mm breakaway rails with mouse-bitten tabs. Tell them it is a
  customer panel and must not be re-panelised.
- Board is 4 layers, 1.6 mm, all 312 placements on the bottom side.
