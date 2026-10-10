# Retained raw-input checkpoints for native chunks 153 and 154

Each ZIP contains one native frequency chunk from all six original scans of the 2016-03-17 HD 189733 / HIP 98505 ON/OFF visit. The six compact HDF5 files retain the original compressed spectral row payloads, with the HDF5 codec prefix adapted by the frozen acquisition helper. They are partial source files, not complete original telescope files. The original whole-file MD5 remains unverified.

The independent acquisition QA receipt authenticates six compact file hashes, 96 retained compressed row chunks, and 96 decoded row identities. The packager performs only opaque byte copying and verifies every ZIP member's SHA-256, size and CRC. It does not decode HDF5 or NPZ files, request source data, or rerun a search.

Extract each ZIP into the same clean project root, preserving member paths. Each archive includes the common frozen analysis scope and both source manifests/acquisition scopes, but contains compact source files only for its named chunk. Either archive supplies the pinned code and metadata needed to reproduce its own chunk. Extracting both supplies the complete two-chunk source input set. The imported historical detector, loader and profile code is included; historical chunk 151 spectra and protected chunks 156 and 159 are excluded.

The exact dependency versions are Python 3.12, NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, h5py 3.15.1, hdf5plugin 7.1.0 and HDF5 1.14.6. The compact files require the registered HDF5 plugin. Dependency wheels are excluded. Public source identities, exact range descriptors, acquisition code/scope hashes and prospective selection are in the source manifests, scopes and receipts. The metadata derivation/QA receipts retain historical metadata archive and parser pins; those historical index archives are not required to analyze these already retained source inputs.

For a later independent reproduction, in a separate clean extraction, run the frozen `native_search.py` for the chosen chunk and batch with these arguments (replace `CHUNK` with 153 or 154 and `BATCH` with 1 or 2):

```bash
python tools/radio_next_bands_20261010/native_search.py \
  --scope tools/radio_next_bands_20261010/scope.json \
  --expected-scope-sha256 60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4 \
  --chunk CHUNK --batch BATCH \
  --compact-dir results/radio_next_bands_20261010/chunkCHUNK/arrays \
  --acquisition-summary results/radio_next_bands_20261010/chunkCHUNK/arrays/ACQUISITION_RESULT.json \
  --outdir results/radio_next_bands_20261010/chunkCHUNK/batch_0BATCH/measurement
```

This documents reproducibility only; the current authorized stage runs each chunk/batch once and does not rerun a numerical measurement. The native search refuses an existing output directory. Its fixed family consists of safe cores 1–254, 763 drift values from −4 to +4 Hz/s and widths 1 and 3 native channels. The two edge cores remain closed. Results remain exploratory: original A/B qualification is FAIL_CLOSED, and no calibrated significance, sensitivity, source origin or independent observation claim follows from an archive.

`RAW_CHECKPOINT_PAYLOAD_MANIFEST.json` inside each ZIP lists payload member hashes, sizes and CRCs, excluding itself. The separate `RAW_CHECKPOINT_ARCHIVE_MANIFEST.json` records the full ZIP SHA-256 and the manifest member hash. The full ZIP hash is deliberately excluded from the ZIP to avoid circular hashing. Both member ordering and ZIP timestamps are fixed by the packager; execution timing remains external.
