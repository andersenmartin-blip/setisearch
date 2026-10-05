# Finished bootstrap B result retention

This administrative helper preserves a finished, reaped bootstrap root. It does not activate, reset, install, import a scientific package, contact a service, or allocate a bootstrap identity. Invoke it only after the sole admitted attempt has finished. Actual B root reads performed during preparation: zero.

`preserve_bootstrap_b.py` is the prior A preservation helper with explicit immutable installer-basis publication references and a separate old basis repository. Every source file is retained through exact UTF-8 bytes, canonical base64 segments, verified immutable installer-basis bytes, or verified byte equivalence to a retained wheel member. Incomplete and empty wheel files are retained. Full directory and file identities are recorded, and the full source tree is checked before and after. Final `supervisor-result.json` and `artifact-manifest.json` bytes are included despite their operational self-hash exclusions.

The immutable installer basis is repository `andersenmartin-blip/setisearch`, commit `c1ff02e8da9dae07b5711595df6d57fd7857e67c`, whole tree `6023d788555862b9616298dfb2eef44817ef5faa`, preparation subtree `3bd54744a801e3fb4e16c9922f49771ae48e2d31`. The complete remote subtree catalog is retained here; all 479 catalog path/mode/blob/size rows match the local full representation and decoded installer-byte pins. This is not a new remote body fetch for all 479 files. The helper repeats the basis raw-byte checks for every referenced actual-root seed file.

Copy this helper, `immutable-original-preparation-tree.json`, this document, `basis-verification.json`, the tests, and test log to the new preparation cohort's `administrative` directory before preparation publication if desired. They are administrative evidence, not scientific authority.

After the actual scope has finished and its child is reaped, invoke once with the externally frozen B identity:

```bash
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -B -S /workspace/scratch/66170938f826/setisearch/results_radio_runtime_bootstrap_preparation_20261005b/administrative/preserve_bootstrap_b.py \
  --root /workspace/scratch/66170938f826/radio-runtime-bootstrap-20261005b \
  --repository-root /workspace/scratch/66170938f826/setisearch \
  --output results_radio_runtime_bootstrap_preparation_20261005b/administrative/result-retention \
  --plan results_radio_runtime_bootstrap_preparation_20261005b/original-plan.json \
  --plan-sha256 fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25 \
  --basis-repository-root /workspace/scratch/a5b2addacbd5/setisearch-20261005 \
  --installer-preread results_radio_runtime_bootstrap_preparation_20261005a/installer-preread.json \
  --installer-preread-sha256 3e154b784424c215867b9d3a091e3e92ed8c1229a3b1ba7f838074c6e36bb1dc \
  --basis-tree-catalog results_radio_runtime_bootstrap_preparation_20261005b/administrative/immutable-original-preparation-tree.json \
  --basis-tree-catalog-sha256 450f70285e28d41a55365f20603551cdedc7d7fb71d61ac30250397cd1e2673a \
  --bootstrap-identity '<EXTERNALLY_FROZEN_B_IDENTITY>'
```

Output must not exist. It is created exclusively; failure retains partial output and cannot overwrite the previous result. Administrative reads, transformations and publication have their own accounting and do not alter the admitted attempt's wall time, I/O measurements, resources or spent status.

The helper limits individual raw files to 128 MiB, the source root to 1,536 MiB, files to 20,000, directories to 4,096, expanded wheel members to 512 MiB and member count to 24,576. Base64 transport segments contain at most 374,997 raw bytes, yielding at most 499,997 encoded bytes including the newline. All encoded segments have their own raw/encoded SHA-256 and Git blob pins. Empty files are explicitly represented by a zero-byte payload with no segments.

Publish every generated UTF-8 administrative artifact and independently verify its immutable Git body. `preservation-manifest.json` describes every final source object; its own publication transport contains separately pinned base64 segments. Keep the original standalone manifest too when supported. Also retain and hash exact caller stdout and stderr outside the actual root; the helper explicitly excludes only these external caller streams from its root preservation scope.

For restoration, fetch installer-basis paths at the recorded immutable commit, verify encoded length/SHA-256/Git blob, decode only the declared canonical encoding, and verify raw length/SHA-256. Concatenate retained base64 parts in index and offset order after verifying each segment. Verify complete wheel raw bytes before reading a named archive member and verify the expanded member bytes against the recorded equivalence pin. Exact UTF-8 copies are already the original raw bytes. Recreate directory and file modes from the manifest; device, inode and historical timestamps remain recorded provenance rather than reproducible identities. Restoration never installs or imports these packages.

Two pure local tests passed: full round trip across all four representation forms, terminal objects, an empty wheel, a partial wheel, multi-segment binary data and executable modes; and rejection of symlink or hardlink roots. They use temporary synthetic roots and never read the actual B root.
