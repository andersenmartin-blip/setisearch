# Exact C029 inputs and bounded evidence

Existing archives `SETI_HARPS_EXTENSION02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip` / `SETI_HARPS_RAW_BATCH04_INPUTS_PART4_2026-11-02.zip` restore all six merged spectra and three own native/ancillary discovery products. The original batch04 evidence archive part supplies all six original event/order raw containers. Exact member names,sizes,hashes and provenance remain in [the inventory](../inputs/INPUT_INVENTORY.json).

Run `python3 inputs/restore_inputs.py --archive-dir /path/to/cache` from the phase directory in a separate reproduction checkout. No live ESO query is needed. Full restored FITS/TAR are excluded from Git. Never rerun a closed diagnostic in place.

Delivered numerical evidence comprises12pre-interpolation source windows,24profiles and6byte-exact original raw containers:42NPZs. Original indices,signed flux,ERR,wavelength lineage and full-source spacing remain. Six scientific PNGs have visual and full-decode QA. Preserve the public plan,original methods,release,first-run outputs,audits and all historical evidence unchanged.

Eight source windows share original points with C028; four additional native/order windows are existing May discovery observations. The source-index audit reads prior metadata only. Previous C028 files remain unchanged except the two authorized current root documents. Next C030 already shares current broad context,requires its own differing member-core geometry,and must not inherit0261's event-specific blend caution or current full-support/normalization outcomes.
