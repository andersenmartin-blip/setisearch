# Portable DC-alternative reproduction

The deliverable preserves the original `analysis/` relative-path layout. The independent numerical replay requires **POSIX/Linux, NumPy 2.3.5** and the Python standard library. POSIX resource limits and signals enforce the frozen caps. It does not require SciPy, h5py, hdf5plugin or the original whole HDF5 files.

From the folder containing `analysis/`, inspect the runner without reading observation arrays:

```bash
python analysis/dc_alternatives/reproduction/replay_from_saved_frames.py --check-only
```

The included frozen GO and completed replay receipt record a successful run: 156,083 checks, zero mismatches, 34.66 CPU seconds, and zero HDF5 opens. To repeat the numerical reproduction, use a fresh output directory:

```bash
python analysis/dc_alternatives/reproduction/replay_from_saved_frames.py \
  --scope analysis/dc_alternatives/reproduction/portable_scope.json \
  --go analysis/dc_alternatives/reproduction/PORTABLE_GO.json \
  --out analysis/dc_alternatives/reproduction/your_replay
```

The runner refuses an existing output directory and authenticates every required byte pin before scoring. It recomputes all 11,120,310 original hypotheses at the 7,083 excluded carriers using the independent nearest501/full-prefix kernel, checks the eighteen preserved normalized-frame hashes, reconciles original and recovered winners exactly (including EMPTY sentinels), and reconstructs the merged TOP700, separatedTOP100, per-ON TOP3 and global nine. Scope, code, GO and input hashes must remain unchanged through completion. Limits are 600 CPU seconds, 900 wall seconds and 2 GiB RAM.

A `PASS_PORTABLE_NUMPY_ORIGINAL_FRAME_DC_REPLAY` receipt is a saved-frame numerical reproduction. Original HDF5 row/crop authentication belongs to the included completed source QA receipt and detailed audit. This archive intentionally omits the nine whole original HDF5 files. Previous clean-family coverage is authenticated through the prior full-map QA; this portable replay numerically examines only the eighteen affected maps.

`DC_RESULTS.md` and `SUMMARY.json` describe the completed source QA, successful portable replay and unchanged nine selections. `CONTEXT_REUSE_AUDIT.json` proves that the previous 54 profiles can be reused without a new DC context query. `MINIMAL_ARCHIVE_MANIFEST.json` lists the files needed for this module; preserve their paths under `analysis/`.
