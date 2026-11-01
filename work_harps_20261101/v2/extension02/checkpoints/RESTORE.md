# Restore the 100 extension02 inputs

Extract both `SETI_HARPS_EXTENSION02_INPUTS_PART*_2026-11-01.zip` archives into the `work_harps_20261101` directory. Member names already begin with project-relative paths such as `v2/extension02/data/main/`; do not add another copy of that directory prefix.

Every existing downloaded FITS file is retained, including any file excluded by header checks. Each selected exposure's final receipt is present exactly once. Shared frozen code, metadata, selection, provenance and final acquisition records are repeated identically in both archives. No spectral values are interpreted during packaging.

Verify the archive SHA256 values in `INPUT_CHECKPOINTS.json`, then verify the size and SHA256 of every extracted member against that part's member list. The final acquisition manifest and result determine which inputs are admitted for science; inclusion in an archive alone does not imply admission. Original production files are not replaced by this input checkpoint.

For scientific reruns, use the original published project environment and protocol. Existing output directories must not be overwritten. The acquisition and detector freezes remain authoritative; the packaging code does not relax them.
