# FR4 top plate

`velvet74-plate.zip`: gerbers and drill for both halves' top plates on one panel, the same 268 x 133.25 mm rails,
tabs, mouse bites and tooling holes as the PCB panel. Built by `scripts/export_plate.py` from Ergogen's
`plate_outline`; rebuild with `npm run build` in `ergogen/`, then that script.

Order settings: FR4, 2 layers (no copper is drawn), **0.8 mm thick**, any solder mask colour. Nothing is assembled.

- Switch cutouts are 14.0 mm, so Choc v1 (13.80 mm body) and v2 (13.95 mm) both fit. The plate is a cover: at
  0.8 mm the switch clips do not grip it (they take 1.30 mm on v1, 1.65 mm on v2), so the hotswap sockets hold the
  switches, and the rims sit 0.2 mm above their natural seat on the 1.6 mm spacer.
- Five 2.2 mm M2 holes per half, on the PCB's H1-H5 and the case pillars. Meant for M2 x 6 wafer-head screws
  (3.8-4.1 mm head) into heat-set inserts; at H2 and left H3 a head reaches up to about 0.35 mm under the
  neighbouring switch rims; if one sits high, notch its rim edge or leave that screw out.
- The screen opening is 10.0 x 28.5 mm and overlaps the OLED glass by 0.75 mm all round.
