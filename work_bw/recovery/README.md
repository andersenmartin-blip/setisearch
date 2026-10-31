# OFF5 resume preparation — BW

**Status: offline specification only. No archive access or production execution is released.** The current network allowlist excludes `bldata.berkeley.edu`. This preparation made no archive requests, opened no power arrays and changed no coverage. The separate BW q254 partial search does not satisfy the missing OFF5 requirement.

[RESUME_SPEC_BW.json](RESUME_SPEC_BW.json) records the exact locators, known ranges, source pins, preflight and completion gates. It preserves HIP44295 / cadence65133 at **88 of96 rows**, with **five of six repeat checks** complete.

## Remaining input

| Item | Exact scope |
|---|---|
| Missing source | Scan5, HIP43223, archive65143 |
| Missing coordinates | Time rows8–15, feed0, channel179306496, 1,048,576 channels per row |
| First missing TREE read | Bytes9241886720–9241903103;16,384 bytes |
| Remaining genuine repeat | Row7 bytes8154457534–8157574411;3,116,878 bytes |
| Original source identity | ETag `"5ac56577-40d1a6aa0"`;17,399,704,224 bytes |
| Required lineage | BB87 + BC1 + later8 =96;five prior repeats +one new repeat |

The original URL is stored verbatim in the JSON. Keep the original hostname and route. The historical tunnel403 occurred before an archive HTTP response; it does not establish a denial by the telescope server.

**The missing payload offsets cannot all be declared now.** The failed16KiB request addresses TREE metadata while locating row8; it is not a known row8 payload range. Obtain descriptors from genuine metadata using the original pinned traversal, and request only gaps in verified cached coverage. Cached internal TREE nodes may identify later leaf locations but cannot replace unreceived leaf contents. Do not estimate offsets from neighbouring chunks.

Row7 already consists of a BC prefix of3,103,298 bytes and a BB tail of13,580 bytes. Preserve those source segments and their scope addendum; do not claim a whole-chunk HTTP receipt for the union. The remaining full-row7 repeat must have a separate genuine206 receipt and match the assembled compressed bytes exactly. Previously contacted rows or metadata-overlapping bytes cannot be relabelled fresh or held out.

## Restore and preflight

1. Resolve BB index `libfile_6c943f4960b081918aa1d1a6a788af90` (`SETI_DELIVERY_INDEX_BB_PARTIAL_2026-10-29.json`, SHA256 `4d2186f0a62b86fe51334ab3acec4bce7bbca064f60ce7a6371a8011d990d2dd`). Its nine archive entries are the authoritative per-package IDs and hashes; this aid does not guess unverified IDs.
2. Restore all nine BB packages and verify the989-entry inventory. The current local ZIPs1–4+9 and BU extraction subset are insufficient for BE recovery.
3. Restore BC package `libfile_78f062d9caf08191a1468b0f934b49c5`:34,765,851 bytes, SHA256 `201847af5cc70e3662c2bfd54649d89abf319b9d7cdcb912c2717d0b42b698f9`. Its index is `libfile_f7f526bcb6c88191afbc56106c7fef5b`. Preserve both historical partial arrays, failures and scope corrections.
4. Restore the [existing BE source tree](https://github.com/andersenmartin-blip/setisearch/tree/d44afffa8f462b3e9c559cedc2ad2eb88baf7dfa/work_be) at commit `d44afffa8f462b3e9c559cedc2ad2eb88baf7dfa`. Verify the1,124 source/evidence pins and241 retained HTTP receipts, including five repeats. Use the pinned cp312 wheels for NumPy2.3.5, h5py3.16.0 and bitshuffle0.5.2; keep Python optimization disabled.
5. Supply an explicit `SETI_BE_EXPLICIT_RELOCATIONS_V1` mapping for historical paths and verify all resolved hashes. Preserve immutable originals. No transfer or archive-probe command is supplied by this preparation.
6. In an environment with genuine normal archive permission, prepare and review a new prospective protocol variant. Preserve selection, configuration, cache-union rules, provenance and lineage; bind current paths, source hashes, normal-access evidence and execution receipts. The original BE zero-request protocol remains unchanged.

The existing implementation is `work_be/recover_missing_rows_be.py`, SHA256 `01975a56d1f833907e8d8047829ff33123a9ad48f6da3851e68adb1e608679b5`, with `work_be/capture_recovery_be.py`. Its interface is `work_be/science_handoff/INTERFACE_BE_V2.json`. Reuse those reviewed components; this directory adds no replacement acquisition code.

## Execution and proof gates

A later `SETI_BE_RECOVERY_DISPATCH_GATE_V1` must bind the reviewed source/protocol and a genuine normal-access receipt. The original runner requires a separately authorized protocol variant with60 requests and numerical execution still disabled. Merely writing a permission-shaped JSON file does not establish permission.

Transport limits remain60 requests,64MiB total requested,8MiB per request, one connection, one attempt per range and a600-second Python signal limit. The latter is not an externally enforced absolute deadline. First failure stops further archive contact; preserve partial files and failure evidence. No automatic retry or alternate access route is permitted.

After permitted acquisition, every gate remains necessary:

1. **Acquisition:** actual subprocess exit0, stdout EOF, completed wait, exact log hash/length, production completion marker bound to the manifest,96 distinct selected coordinates, six retained canonical arrays, six genuine repeats, real source-slice provenance, backend close and unchanged-input checks. Acquisition adds no science credit.
2. **Native proof:** separate `SETI_BE_NATIVE_GO_V1`, reconstruction and descriptor/provenance checks for all96 rows, all repeats, retained BB/BC partial proofs and arrays, original failed actual exits, header/selection pins and the row7 addendum. Capture native actual0 and its exact result hash. Simulation is rejected.
3. **Binding:** separate `SETI_BE_BINDING_GO_V1` binding the production native proof, new headers/manifest and unchanged scientific configuration/sources. Binding does not release a detector phase.
4. **Science:** separate `SETI_BE_SINGLE_PHASE_EXECUTION_GO_V1` for each authorized phase; unchanged six-scan search, forced ON/OFF triage, bounded independent numerical review, required main and remaining local context, figure QA and final artifact audit.
5. **Closure:** only successful complete scientific closure may alter authority or advance the queue.

The native result must be `SETI_BE_RECOVERY_NATIVE_INPUT_PROOF_V1`, mode `PRODUCTION`, scope `COMPLETE_PRODUCTION_ACQUISITION_NATIVE_RECONSTRUCTION`. Consumers require valid completion markers; exit0 alone is insufficient.

BA remains the completed authority:486 unique archive IDs and268.50128173828125 technical MHz-visits. Shared codec/TREE helpers are not independent model qualification. This preparation establishes no original-file MD5, astronomical sensitivity, completeness, global false-alarm probability, new epoch or signal origin. **Pause before production.**
