# Exact C029 preservation

Existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip` / `SETI_HARPS_RAW_BATCH04_INPUTS_PART4_2026-11-02.zip` restore six merged spectra and three own discovery native/ancillary products. The original batch04 evidence archive part supplies six original raw containers.

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from the phase directory in a separate reproduction checkout. Exact archive/member names, sizes, hashes and provenance are in [the inventory](../inputs/INPUT_INVENTORY.json). No live ESO query is needed. Full restored FITS/TAR remain excluded from Git. Completed delivery will retain12bounded source windows,24profiles and6byte-exact raw containers,42NPZ files total. Preserve closed outputs; reproduce separately rather than overwrite them.
