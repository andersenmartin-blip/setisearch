# Retained raw-input checkpoints for native chunks 155 and 157

Each ZIP contains the six compact HDF5 source inputs for its named native frequency chunk from the same 2016-03-17 HD 189733 / HIP 98505 ON/OFF visit. Retained compressed spectral row payloads are copied exactly; the frozen acquisition helper adapts the HDF5 codec prefix. These are partial source files. The whole original telescope-file MD5 remains unverified.

The complete independent acquisition QA receipt authenticates six compact file hashes, 96 retained compressed row chunks and 96 decoded row identities. The checkpoint packager uses only opaque byte copies and verifies all ZIP-member SHA-256 values, sizes and CRCs plus the full ZIP hash. It imports no HDF5/NPZ decoder, performs no source HTTP request, and reruns no detector search, normalization or profile measurement.

Extract the archive into a separate clean project root and preserve member paths. It contains the frozen analysis/acquisition scopes, source manifests, exact detector/loader/profile implementation, dependency provenance, and acquisition/QA receipts. It includes compact source files only for its named chunk. Protected chunks 156 and 159 and other historical spectral files are excluded. The frozen scopes retain the original source identities and exact byte-range descriptors. Pinned metadata and provenance receipts document the source-index derivation; those source-index payloads are not required to analyze the retained input spectra.

Use Python 3.12 with exact NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, h5py 3.15.1, hdf5plugin 7.1.0 and HDF5 1.14.6. Dependency wheels are excluded. Register the specified HDF5 plugin when reading compact inputs, as the pinned loader does.

For a later independent reproduction, start in the root of a separate clean extraction. Set CHUNK to 155 or 157 and BATCH to 1 or 2. Every filesystem CLI argument below uses absolute PROJECT_ROOT, including the output directory:

```bash
PROJECT_ROOT="$(pwd -P)"
CHUNK=155
BATCH=1
python "$PROJECT_ROOT/tools/radio_rolling_bands_20261010/native_search.py" \
  --scope "$PROJECT_ROOT/tools/radio_rolling_bands_20261010/scope.json" \
  --expected-scope-sha256 9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a \
  --chunk "$CHUNK" --batch "$BATCH" \
  --compact-dir "$PROJECT_ROOT/results/radio_rolling_bands_20261010/chunk${CHUNK}/arrays" \
  --acquisition-summary "$PROJECT_ROOT/results/radio_rolling_bands_20261010/chunk${CHUNK}/arrays/ACQUISITION_RESULT.json" \
  --outdir "$PROJECT_ROOT/results/radio_rolling_bands_20261010/chunk${CHUNK}/batch_0${BATCH}/measurement"
```

This command documents independent reproduction; it does not authorize a numerical rerun in the current stage. The current stage performs one numerical search/profile pass per chunk/batch. Initial zero-measurement path-preflight invocations, where applicable, are preserved separately. The search refuses an existing output directory. Its fixed family is safe cores 1–254, 763 drift values from −4 to +4 Hz/s, and widths 1 and 3 native channels; two edge cores remain closed.

The original A/B gate remains FAIL_CLOSED. These exploratory raw-input checkpoints establish retained source-part identity and reproducibility. They do not establish source origin, calibrated significance, sensitivity, or an independent observation visit.

The embedded RAW_CHECKPOINT_PAYLOAD_MANIFEST.json lists payload hashes, sizes and CRCs, excluding itself. The separate RAW_CHECKPOINT_ARCHIVE_MANIFEST.json records the full ZIP SHA-256 and the embedded manifest-member hash. The full ZIP hash is outside the ZIP to avoid circular hashing. ZIP member order and timestamps are fixed. Execution timing and the final archive manifest remain external.
