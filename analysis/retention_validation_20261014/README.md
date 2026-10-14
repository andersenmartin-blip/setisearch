# Frozen local native-path retention control

One prospective conditional control is complete: 2,822 new physical injection placements on exposed 2017 backgrounds, paired A=0/2/8, and frozen k=5 versus k=1. The policy, code and source identities were published before execution at commit `0a6cf6578a1a8f8ee2f46d5a9b834bda39222a60`. Producer and independent QA each ran once. No policy was tuned after results.

Weak complete truth capture is 1,898 to 2,623 of 2,822. Strong capture is 2,822 for either rule. The rule remains conditional local engineering, with 199 weak misses and fivefold candidate workload. It does not qualify the original six-scan detector, physical sensitivity or telescope FAP.

## Complete delivery

The archive contains `stage/`, `metadata_code/`, the prior development-policy evidence and the unchanged `sources/SETI_NATIVE_SPOR_2026-10-14.zip` (SHA256 `52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3`). The inner archive supplies every required saved path-score array and source metadata. No full HDF5 file or new telescope access is needed for this stage. Python 3.12 and NumPy are required.

`GEOMETRY_MANIFEST.json` is the complete frozen identity/alias bank. `SCOPE.json` retains its historical proposed status; `GO.json` is the separate immutable execution authorization. All 8,466 trial rows and 42,330 retained-candidate rows are included in the complete delivery. The public repository carries code, compact evidence and candidate tables; it does not contain the full source arrays or identity manifest. See `PUBLIC_EVIDENCE.json` for exact complete-file hashes.

## Portable replay

From an extracted delivery, extract the inner source ZIP into `replay_inputs`. Copy only `producer.py`, `qa.py`, `SCOPE.json`, `GO.json`, `GEOMETRY_MANIFEST.json` and `PHYSICAL_NOVELTY_CENSUS.json` from `stage/` to a fresh directory named `replay_stage` (do not copy `results/`). Run:

```bash
python3 replay_stage/producer.py run replay_stage/results \
  --input-root replay_inputs/SETI_NATIVE_SPOR_2026-10-14 \
  --go-scope-sha256 de9c630212c77a2a83e28bead377d617fa58d5a24aea6cfa539e4fa2e7b8deba
python3 replay_stage/qa.py replay_inputs/SETI_NATIVE_SPOR_2026-10-14 replay_stage \
  --go-scope-sha256 de9c630212c77a2a83e28bead377d617fa58d5a24aea6cfa539e4fa2e7b8deba
```

The portable argument is implemented; this delivery has not executed an additional relocated replay. Actual original execution and independent recomputation are recorded by their receipts and logs. Optional raw501 helper `source_path_scores` was not used or tested and supports no result claim. The metadata scripts preserve original path arguments and can be consulted for provenance; ordinary score replay consumes the already frozen manifest.

Original A/B remains FAIL_CLOSED, protected 2016/closed 2019 unchanged, no new observing visit, checkpoint 20 October 2026.
