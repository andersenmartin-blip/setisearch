# Raw-power normalization and local-retention control

The prospectively frozen648-case control is complete. All raw injection, full-core normalization and local path scores were independently recomputed. See RESULTS_DA.md for central-path counts and the distinct power-capture interpretation.

The complete delivery includes this stage, its full GEOMETRY_MANIFEST.json, prior_placements/GEOMETRY_MANIFEST_TOP5.json, source_provenance/generator_original.py, all54baseline arrays,648case arrays, raw hashes, injected-cell recipes, code/scopes/GO/logs and the unchanged sources/SETI_NATIVE_SPOR_2026-10-14.zip (SHA25652b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3). The inner archive contains every needed source raw crop and metadata; no full HDF5 files or new telescope access are required. Python3.12 and NumPy are required.

To replay after extracting the delivery, unzip the inner source archive into replay_inputs and copy this stage to a fresh replay_stage directory EXCLUDING results/ and runtime logs. Preserve code, finalSCOPE.json,GO.json,GEOMETRY_MANIFEST.json and both prior_placements/ and source_provenance/ subdirectories. Run:

```bash
python3 replay_stage/producer.py run replay_stage/results \
  --input-root replay_inputs/SETI_NATIVE_SPOR_2026-10-14 \
  --go-scope-sha256 873d6b1fdd2a2d45af374a1bba24c309577883757c1f841b666584a13565f3d8
python3 replay_stage/qa.py replay_inputs/SETI_NATIVE_SPOR_2026-10-14 replay_stage \
  --go-scope-sha256 873d6b1fdd2a2d45af374a1bba24c309577883757c1f841b666584a13565f3d8
```

Portable arguments are implemented; a second relocated replay was not run for this delivery. Actual producer and independent QA each ran once, under source/code pins and caps. The metadata builder is preserved as provenance; ordinary score replay consumes the frozen identity/kernel bank. SCOPE retains its historical awaiting-GO status; immutableGO is its subsequent execution authorization. The final code/scope/review allow finite nonnegative power with positive normalizer scales, overriding the draft manifest's strict-positive adjective.

Public repository evidence contains code, compact geometry summary, source identities, tables and receipts. Full raw prerequisites and648array payloads are retained in the complete delivery, not in the public repository. No FAP, physical-sensitivity or qualified SETI-detection claim; original A/B remains FAIL_CLOSED.
