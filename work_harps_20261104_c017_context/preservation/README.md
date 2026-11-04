# Input preservation

The existing saved archives SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip and SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip restore seven merged spectra, the own February5 native product and two byte-exact historical raw containers. Original custody and hashes are in inputs/INPUT_INVENTORY.json. Run inputs/restore_inputs.py --archive-dir /path/to/archive/cache in a separate checkout. No live ESO query is needed.

Completed bounded source windows, derived profiles and original containers will be committed with the results; full restored FITS/TAR are excluded from Git. Restore differing inputs only in a separate copy; preserve old outputs and one-shot guards.
