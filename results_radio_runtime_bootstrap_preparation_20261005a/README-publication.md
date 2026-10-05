# Lossless administrative publication preparation — 5 October 2026 A

The administrative scripts below preserve a finished one-shot package-bootstrap outcome and reconstruct its acquired wheel bytes. They do not acquire packages, invoke pip, import the installed scientific packages, read HDF5 data, reactivate a spent bootstrap, or grant scientific authority. Their reads, transforms and elapsed time are separate administrative work, outside the bootstrap's selected resource counters. All 11 scientific fields remain pending.

At this preparation checkpoint, neither script has been invoked and no actual-root object has been read by this work. Validation consists of AST parsing and independent read-only source review. No functional execution check is claimed.

## Frozen administrative sources

These source bodies are unchanged following the final independent review.

| Repository-relative source | Raw bytes | Raw SHA-256 |
| --- | ---: | --- |
| `results_radio_runtime_bootstrap_preparation_20261005a/administrative/preserve_bootstrap.py` | 34,025 | `cb4cfd8a1875d367ad94b3dbd7b5818d2eedb6994f2e69bb4fc2f4ff361b248a` |
| `results_radio_runtime_bootstrap_preparation_20261005a/administrative/reconstruct_wheels.py` | 14,821 | `ec36de3845953c1bcd2f75f5d034b61dd9bfa513cc5c1dfbe66a3e752cff4e4f` |

The input plan remains `results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json`, 24,739 raw bytes, SHA-256 `fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25`. Its three original wheel rows are read from `materialization.official_wheels`.

The prepared installer source manifest is `results_radio_runtime_bootstrap_preparation_20261005a/installer-preread.json`, 1,275,913 raw bytes, SHA-256 `3e154b784424c215867b9d3a091e3e92ed8c1229a3b1ba7f838074c6e36bb1dc`. Raw source bytes and the repository representation bytes in that manifest have separate pins. A base64 repository artifact is decoded canonically and its original raw length/hash is verified before it can represent an installer file.

## Independent static review

Reviewer `/root/bootstrap_wheel_io` inspected only these administrative source files. The reviewer executed neither script, performed no network operation and read no actual-root file. The initial review identified three blockers; each was corrected before the final source hashes above were reviewed.

| Initial finding | Implemented correction | Final static assessment |
| --- | --- | --- |
| Three internally consistent payloads could be accepted without equality to the frozen original-wheel cohort. | Reconstruction requires an exact filename bijection and exact equality of each payload's expected-original row to the manifest's frozen original row. Declared original-identity flags must agree with raw length/hash pins. | Resolved. |
| Reconstruction hashes described decoded input without verifying the final output file. | Exclusive regular, sole-link outputs receive held/named inode, mode, type, link and size checks, followed by a complete final-file SHA-256 and Git-blob readback under unchanged metadata. | Resolved. |
| Preservation artifact pins described supplied buffers without corresponding written-file custody checks. | Every administrative artifact receives equivalent full written-file readback and held/named checks. Nested output-directory descriptors remain held and are rechecked. | Resolved. |

The final verdict was **`NO_BLOCKING_FINDINGS_WITHIN_FIXED_ADMINISTRATIVE_SCOPE`**, against both exact source pins above. The reviewer also confirmed the 450,000-byte threshold for direct UTF-8 copies, the canonical segment bounds, the raw-versus-encoded pin distinction, complete terminal-root representation and the bounded manifest transport. This verdict is a static review of administrative code. The caller must still authenticate immutable input hashes and wait until the original outcome is finished and its child is reaped.

## Lossless representation

Preservation recursively inventories every terminal actual-root directory and sole-link regular file. Symlinks, hardlinked regular files, special objects, cross-device objects and substitutions are refused. Every object records device, inode, permissions, file type, link count, byte size, mtime, ctime and allocated bytes. Every regular file additionally records its complete raw SHA-256, Git blob SHA and UTF-8 observation. The root inventory is repeated after preservation and its names and identities must agree exactly. Reading does not qualify transient objects that disappeared before this terminal inventory.

The limits are 20,000 files, 4,096 directories, 128 MiB per file and 1,536 MiB for terminal root logical/allocated storage. Static archive-equivalence inspection permits at most 24,576 members and 512 MiB of aggregate declared expanded payload. These are administrative bounds and confer no additional installer, native-runtime, joined-I/O or scientific certificate.

| Actual-root object | Representation |
| --- | --- |
| Acquired original wheel archive | Exact original bytes split into canonical base64 parts; complete or failed/partial acquisition bytes are retained. Raw archive pins remain separate from encoded part pins. |
| Installer seed file equal to its frozen source row | Reference to the independently verified existing installer-basis artifact, including its representation pins, encoding and decoded raw pins. |
| Installed file equal to a verified member of a complete exact original archive | Explicit archive/member byte-equivalence mapping, with original archive hash and member length/hash. The actual file's own raw identity and mode remain in the inventory. This does not certify causal installation origin. |
| Other UTF-8 file of at most 450,000 raw bytes | Exact raw bytes in `actual/retained/<root-relative-path>`. |
| Other file, including UTF-8 content larger than 450,000 raw bytes | Exact raw bytes represented by canonical parts in `actual/other-file-parts/<root-relative-path>/`. The purpose is `unmatched-file-bytes`; the independent `raw_file_valid_utf8` flag avoids describing all encoded content as binary. |
| Directory | Complete recorded terminal identity and metadata. |

Each segment contains at most **374,997 raw bytes**. A full segment produces 499,996 canonical base64 bytes plus one newline, or **499,997 saved bytes**. Part pins include raw offset, raw length and raw SHA-256 separately from the encoded repository path, encoded length, encoded SHA-256 and encoded Git blob. Three complete original archives require 184 parts and 91,212,276 encoded bytes including their newlines, reconstructing 68,409,067 original bytes.

If archive-member inspection is refused, the archive's exact parts are retained, no member equivalence is admitted for that refused inspection, and unmatched installed files receive their own complete representation. A full manifest is written only after the final root identity comparison succeeds. Administrative failures retain partial output and an exclusive failure receipt where possible; no automatic retry, overwrite, cleanup or bootstrap reactivation occurs.

The parent must retain caller CLI stdout/stderr separately because they are outside the actual root. No outside CLI stream is silently claimed by this script's root coverage.

## Exact preservation CLI

All eight options are required:

| Option | Meaning |
| --- | --- |
| `--root` | Canonical absolute path of the finished actual bootstrap root. |
| `--repository-root` | Canonical absolute path of the repository containing the authenticated input artifacts and future output. |
| `--output` | Repository-relative output directory, which must be absent. Its parent directory must exist. Output must be separate from the actual root. |
| `--plan` | Repository-relative original materialization plan. |
| `--plan-sha256` | Externally authenticated raw plan SHA-256. |
| `--installer-preread` | Repository-relative frozen installer source manifest. |
| `--installer-preread-sha256` | Externally authenticated raw source-manifest SHA-256. |
| `--bootstrap-identity` | Expected lowercase 64-character bootstrap identity. Existing `spent.json` and `supervisor-result.json` must match it. |

The following command is a prospective invocation, to be used only after the original outcome is finished and reaped. It was not run for this preparation.

```bash
"$CODEX_PRIMARY_RUNTIME_PYTHON" -I -B -S \
  /workspace/scratch/d804553c0e89/setisearch-status-20261004/results_radio_runtime_bootstrap_preparation_20261005a/administrative/preserve_bootstrap.py \
  --root /workspace/scratch/d804553c0e89/radio-runtime-bootstrap-20261005a \
  --repository-root /workspace/scratch/d804553c0e89/setisearch-status-20261004 \
  --output results_radio_runtime_bootstrap_preparation_20261005a/actual \
  --plan results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json \
  --plan-sha256 fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25 \
  --installer-preread results_radio_runtime_bootstrap_preparation_20261005a/installer-preread.json \
  --installer-preread-sha256 3e154b784424c215867b9d3a091e3e92ed8c1229a3b1ba7f838074c6e36bb1dc \
  --bootstrap-identity 7e4a63f99adcb7a9725211960b368db972e92b16c60bdf1a3d5220e49df2d52b
```

The exclusive output contains `preservation-manifest.json`, retained files, wheel/file byte parts, and `publication-transport/preservation-manifest.transport.json` with its bounded parts. The CLI reports raw manifest and transport-descriptor pins. It does not print the full manifest or archived bytes.

## Immutable manifest transport and readback

The raw manifest is an ordinary repository artifact whose complete body may exceed a single supported fetch response. Its descriptor uses the common schema **`radio-runtime-bootstrap-lossless-publication-transport-v1`**:

- `path`, `bytes`, `sha256`, `git_blob` pin the whole raw repository target.
- `encoding` is `canonical-base64-segments`.
- Each part pins `path`, `raw_offset`, `raw_bytes`, `raw_sha256`, `bytes`, `sha256` and `git_blob`.
- `scientific_authority` is false.

The descriptor and parts are under `actual/publication-transport/`. They are separate artifacts, avoiding a manifest self-hash cycle. The raw preservation manifest explicitly excludes its own pin; its external CLI pin and transport descriptor supply that binding.

For full immutable readback, fetch every encoded part at the specific publication commit. Verify every encoded length, SHA-256 and Git blob against that commit's tree. Require canonical base64 plus exactly one newline, decode, check each raw segment hash and extent, and concatenate in increasing offset order without gaps or overlap. The concatenated body's raw length/SHA-256/Git blob must equal the descriptor's whole-target pins. Bind that raw Git blob to the specific target path in the same immutable tree. This reconstructs and verifies the complete raw body; it must not be reported as a successful single whole-file fetch.

The same raw/encoded distinction applies to wheel and operational byte parts in the preservation manifest. All published root-file representations require full immutable body readback before final publication review can claim complete custody.

## Exact wheel reconstruction CLI

Required options are `--repository-root`, `--manifest`, `--manifest-sha256` and `--output`. The manifest path is repository-relative; its SHA-256 must be supplied externally after full immutable raw-body reconstruction/readback. The output is a canonical absolute path whose parent exists and whose directory must be absent. There is no resume or overwrite mode.

```bash
"$CODEX_PRIMARY_RUNTIME_PYTHON" -I -B -S \
  /workspace/scratch/d804553c0e89/setisearch-status-20261004/results_radio_runtime_bootstrap_preparation_20261005a/administrative/reconstruct_wheels.py \
  --repository-root /workspace/scratch/d804553c0e89/setisearch-status-20261004 \
  --manifest results_radio_runtime_bootstrap_preparation_20261005a/actual/preservation-manifest.json \
  --manifest-sha256 '<externally-verified-raw-preservation-manifest-sha256>' \
  --output /workspace/scratch/d804553c0e89/radio-runtime-bootstrap-20261005a-wheel-readback
```

The placeholder must be replaced by the authenticated raw manifest SHA-256. The command above was not run for this preparation. The script refuses unsafe paths, unexpected archive cohorts, part gaps/overlap, noncanonical encodings, raw/encoded pin mismatches and changed files. It rereads each finished reconstructed file in full before emitting `reconstruction-receipt.json`. It never extracts wheel members, installs packages or imports the scientific packages.

Default reconstruction requires all three complete exact original archives. Optional **`--allow-partial`** is reserved for lossless reconstruction of retained failed-acquisition bytes; its receipt cannot claim three complete originals unless all three original raw identities actually match. This option does not retry acquisition, installation or a spent engineering attempt.
