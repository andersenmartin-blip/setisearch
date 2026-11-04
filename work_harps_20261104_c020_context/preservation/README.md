# Exact C020 inputs and bounded evidence

The existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` restore seven merged spectra, the own May 15 native product and original V2E2-0136 order-19 raw container. Exact archive/member sizes and hashes remain in [the inventory](../inputs/INPUT_INVENTORY.json).

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from the phase directory in a separate reproduction checkout. The helper validates full archives and selected members, preserves differing destinations and reads FITS/NPY headers only. No live ESO query is needed. Full restored FITS/TAR remain excluded from Git.

The delivered results preserve eight pre-interpolation bounded inputs, sixteen derived frame profiles and one byte-exact original raw container: 25 NPZ files in total. Original indices, signed flux, ERR, wavelength provenance and hashes remain in the bounded input index and output manifest. Four PNGs and their full-decode QA are delivered. Preserve the published plan, method, release, first-run outputs and audit; do not overwrite them by rerunning a closed diagnostic. Reproduce separately.

The exact C020/C021 source-index dependence is retained, including 17 shared July points. The previous C023 state and its bound outputs remain unchanged. Next HD126093 uses its own batch04 archives; these HD114783 inputs are not transferred to that star.
