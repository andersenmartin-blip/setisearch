# Restore C031 inputs without a live archive query

`inputs/restore_inputs.py --archive-dir ARCHIVE_DIRECTORY` restores the existing six merged spectra, four own native/ancillary discovery products and eight original event/order raw containers. The exact archive filenames, hashes and members are in `inputs/INPUT_INVENTORY.json` and the prior archive manifests.

Required original archives are `SETI_HARPS_EXTENSION02_INPUTS_PART2_2026-11-01.zip` and `SETI_HARPS_RAW_BATCH04_INPUTS_PART3_2026-11-02.zip` / `PART4_2026-11-02.zip`. Original batch04 evidence parts remain in the repository. Full restored FITS/TAR inputs are ignored. Results retain bounded original source windows with source indices and signed flux, 28 profiles, and eight byte-exact original raw containers.

Original local/baseline mapping is true only for V2E2-0277/order3 and V2E2-0282/order3; global/later support is true throughout. No event identity, source hash, negative sample or event-specific uncertainty is discarded. Preserve every completed result. Reproduce only in a separate checkout or output location; never overwrite the original one-shot results.
