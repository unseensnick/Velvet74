# Prototype print set (left half)

STLs for test-printing the left half's stack before ordering boards. All files share Ergogen's x/y frame, so
importing them together without moving them puts every part in place.

| File | Part | Print |
| --- | --- | --- |
| `velvet74-left-1-case.stl` | Case: 2.05 mm floor, M2 pillars, closed USB-C slots | open side up |
| `velvet74-left-2-pcb-dummy.stl` | PCB stand-in cut from the real board: every hole, LED window and USB-C slot, plus the back-side hotswap sockets, USB-C bodies and reset/boot buttons | already flipped, top face on the bed |
| `velvet74-left-3-spacer.stl` | 1.6 mm spacer between PCB and plate | flat |
| `velvet74-left-4-plate.stl` | 0.75 mm top plate (FR4 in the real build) | flat, about 0.15 mm layers |
| `velvet74-left-5-oled-standin.stl` | 0.91" OLED module (12 x 38 mm board plus glass), lies over J3 | flat |
| `velvet74-left-6-encoder-standins.stl` | EC11 body, bushing and 20 mm shaft at SW16 and SW65 (typical EC11 sizes, not a datasheet) | upright |
| `velvet74-left-7-keebart-fit-gauge.stl` | 1.2 mm frame with a 15.4 mm window per switch that Keebart's board shares; with the caps off it drops flush over the Keebart's switches if our positions match | flat |

Stack heights above the case bottom: PCB underside 4.25, spacer 5.85, plate 7.45, top 8.2.

The case, spacer and plate are Ergogen's own `ergogen/output/cases/` parts, unchanged: the case's USB-C ports are
closed 9.0 x 3.2 mm slots with a chamfer stepped in three. They were converted with manifold-3d instead of JSCAD's CSG,
which leaves T-junctions in the mesh.

The PCB dummy is KiCad's board-only STL of the left half plus blocks for the back-side parts; the stand-ins and the
gauge are drawn from the board's footprint positions. All of it was made with scratch tools outside the repo.
