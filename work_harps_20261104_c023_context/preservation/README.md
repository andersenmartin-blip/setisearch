# Exact input preservation

Existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` restore the seven merged spectra, the own February 5 native product and original V2E2-0122 order-57 raw container. Sizes, hashes and exact archive members remain in `inputs/INPUT_INVENTORY.json`.

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from a separate reproduction checkout. The helper validates complete archives and selected bytes, rejects differing destinations and reads FITS/NPY headers only. No live ESO query is needed. Full restored FITS/TAR remain excluded from Git. Completed bounded windows, profiles and the original raw container will be committed with the result.
