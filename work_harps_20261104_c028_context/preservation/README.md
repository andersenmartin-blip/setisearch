# Exact C028 inputs and bounded evidence

Existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip` restore all six merged spectra and own April discovery native A/ancillary products. The original batch04 evidence archive part supplies the two byte-exact0260 order-2/3 raw containers. Hashes, member names and provenance are in [the inventory](../inputs/INPUT_INVENTORY.json).

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from the phase directory in a separate reproduction checkout. No live ESO query is needed. Restore only exact existing files; full FITS/TAR remain excluded from Git. Never rerun a closed diagnostic in place.

The delivered numerical evidence includes eight bounded pre-interpolation input windows, sixteen frame profiles and two exact original raw containers: 26 NPZ files. Original signed flux, ERR, wavelength provenance, indices and source hashes remain. Four original scientific PNGs and two separate caption-corrected copies are delivered. The correction changes only R021 to R029 in two titles, preserving all pixels below the title band. All six PNGs have full-decode and visual QA.

Keep the public plan, original method, release, numerical outputs, audits and corrections unchanged. One pre-array release-format validation failure and its newline-only metadata repair are recorded; no source-array access or result creation occurred in that failed validation. The one successful observed execution is closed. Previous C020 files remain unchanged except the two authorized current root documents.

C029 reuses overlapping windows and source products; preserve the documented dependence and use its own complete three-record/three-reference scope rather than copying0260 mapping or quality outcomes.
