# Vendored JLCPCB library parts

Only the symbols, footprints and 3D models this project uses, copied from
[CDFER/JLCPCB-Kicad-Library](https://github.com/CDFER/JLCPCB-Kicad-Library) (MIT, see `LICENSE`) so the
project opens without the KiCad Plugin and Content Manager package. The library nicknames in `sym-lib-table`
and `fp-lib-table` (`PCM_JLCPCB-*`, `PCM_JLCPCB`) are unchanged and point here.

To add a part from the full library, install it through the Plugin and Content Manager and copy the symbol,
footprint and model in, pointing the footprint's model at `${KIPRJMOD}/lib/jlcpcb/JLCPCB.3dshapes/`.

The Choc hotswap model in `../my-soffle.3dshapes/SW_Hotswap_Kailh_Choc_V1.wrl` comes from
[kiswitch/keyswitch-kicad-library](https://github.com/kiswitch/keyswitch-kicad-library) (MIT / CC-BY-SA).
