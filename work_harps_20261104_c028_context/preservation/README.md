# Exact C028 input preservation

The existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip` restore all six merged spectra, the own April discovery native A product and original ancillary container. The hash-verified original batch04 evidence parts supply both 0260 order-2/3 raw containers.

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from the phase directory in a separate reproduction checkout. Archive/member sizes, hashes and source paths are in [the inventory](../inputs/INPUT_INVENTORY.json). No live ESO query is needed. Full restored FITS/TAR are excluded from Git. The prospective restoration reads FITS/NPY headers only. The delivered results will preserve eight bounded pre-interpolation windows, sixteen profiles and two byte-exact original raw containers; preserve all closed outputs rather than rerun them in place.
