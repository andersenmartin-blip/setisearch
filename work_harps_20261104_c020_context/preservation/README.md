# Exact input preservation

The existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` restore seven merged spectra, the own May 15 native product and the original V2E2-0136 order-19 raw container. Exact sizes, hashes and members remain in `inputs/INPUT_INVENTORY.json`.

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` in a separate reproduction checkout. The helper validates full archives and selected members, preserves differing destinations and reads FITS/NPY headers only. No live ESO query is needed. Full restored FITS/TAR remain excluded from Git. Completed bounded inputs, profiles and the original raw container will be committed with the results.
