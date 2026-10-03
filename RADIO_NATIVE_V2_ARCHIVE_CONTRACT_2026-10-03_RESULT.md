# Archive closure and current metadata-copy storage — 3 October 2026

**635 tests across 24 modules pass with zero failures, errors or skips and process exit 0. The separate archive-only contract verifies and accounts for 15 copied metadata files. Original b/c admission remains blocked: the original repository and private journals are unavailable. No protected control or telescope analysis ran.**

## Explicit contract

`radio_native_v2_archive_storage_contract.py` requires the fixed **b and c** label set, separately retained archive roots, exact per-file byte/SHA256 pins and current observation pins. It detaches caller values, checks complete file and directory membership, rejects private journal/spent-record names, original-root overlap, cross-copy root overlap and device/inode aliases, and applies the unchanged **1536 MiB / 32,768-entry** ceiling. Its semantic roles are `archival_b_metadata_copy` and `archival_c_metadata_copy`; the existing `historical_scope` role is only the read-only observation transport.

The result charges only the two current metadata packages and their directories once. **Missing original storage remains unaccounted for.** Original-scope/journal observation, original identity continuity, storage-join eligibility, whole-control/lifetime qualification, reconstruction, activation, retry, native, scientific and telescope authority all remain false. The component is separate from the production observer, worker, launcher and spender; no production admission path imports it.

The existing archival closure verifier is hardened against correctly re-pinned but semantically invalid records. It verifies the 68-file/21-directory inventory rows, canonical paths and ancestry, 49 frozen files, eight empty case labels, counts/totals/hash formats/link counts, strict integer types, isolated launch argv/config/environment/ledger labels, ordered UTC timestamps and preservation fields. The same five immutable public c records still return CLOSED_FAILED, one invocation, 0/8 and permanently spent. Its `archive_evidence_complete` field concerns this exact five-record metadata bundle and internally consistent inventory claims; it does not mean the original files or journal were observed.

## Recovery and actual read-only result

The original `/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002` no longer exists. A distinct engineering working copy is recovered from immutable public checkpoint `53174aab9708ecb4969f952892aa25e63afe5fed`: 3,045 source/engineering files, 163,515,107 raw bytes. All 1,187 previously selected source/test/helper pins match before edits. The [recovery manifest](results_radio_native_v2_archive_contract_20261003a/public-recovery-manifest.json) and [recovery review](results_radio_native_v2_archive_contract_20261003a/public-recovery-review.json) are public-byte evidence, not original inode or private-journal custody. Unpublished failed-control stores and original journals were not reconstructed.

An independently reviewed [15-file provenance receipt](results_radio_native_v2_archive_contract_20261003a/review-provenance.json) binds every selected metadata source path, Git blob and 189,645 raw copied bytes to that exact commit/tree/parent. The qualifier separately fixes the 5,329-byte input package by literal SHA256 `735e7ced5e69a46e084526406f188b09a83ce9060c09b1f4c4126d657ea2934d`, checks raw source pins/Git blob identities and rechecks the input bytes after qualification. Fresh current observation pins are retained point-in-time pins; they are explicitly not historical authority.

| Current metadata copy | Files / directories | Logical bytes including directories | Allocated bytes |
| --- | --- | ---: | ---: |
| b selected metadata | 5 / 1 | 109,837 | 122,880 |
| c selected metadata | 10 / 1 | 88,000 | 114,688 |
| Total | 15 / 2 | **197,837** | **237,568** |

These totals concern the selected copies only, not either complete historical scope, an original private journal, the full recovered checkout or complete future-control overhead. The existing held descriptor observer verifies all package membership, modes, identities and raw pins; before/after observations match. The active read-only audit records no denied mutation, process or network events. Ordinary filesystem read-atime is outside its stable metadata contract; no continuous custody or whole resource lifetime is claimed.

Both untouched frozen b/c spending implementations are loaded from pinned archived bytes and called only through `observe_spend_storage` against their exact original receipt/witness/root. Both refuse with **FileNotFoundError, errno 2** because an original path component is unavailable. The earlier inode-mismatch refusal remains retained in the preceding checkpoint. No witness is re-pinned or rebound; no public record is installed as a private claim. Original a/b/c identities remain permanently spent and refused by the unchanged current production guards. No real d marker, ledger, fixed launch config, control scope or invocation exists in either root.

## Selected verification and retained failures

[Suite attempt 2](results_radio_native_v2_archive_contract_20261003a/suite-attempt-2-summary.json) runs **635 tests / 24 modules** in 156.045397 seconds, using Python `-I -S -B`, the exact ten-value public environment and held source/test loaders. All **1,190** source/test/helper pins, the input package, original-state absence and d absence remain unchanged. The increase is 12 archival validation tests plus 15 archive-accounting tests beyond the preceding 608. The reused runtime snapshot supplies reviewed paths/import primitives; **no fresh complete runtime freeze, material d preparation or execution preread is qualified** by this archive-only run.

Attempt 1 is retained: 593 tests, zero failures, one setUpClass error, because the recovered sparse working copy lacked the existing HD189733 metadata test inputs. The [26-file recovery](results_radio_native_v2_archive_contract_20261003a/adjacent-metadata-recovery.json) restores the exact 25 public metadata inputs plus their pin map, 753,180 raw bytes, from the same checkpoint; it opens no telescope value blob. The first fetch's shared Git shallow-lock failure is retained separately, and recovery succeeds through a fresh object database. The first wrapper's exact source is retained as `qualify_archive-attempt-1.py`. Its loose input-package trust and misleading observation-pin label were corrected after independent review before selected attempt 2.

The focused archival attempt first rejected valid frozen-directory modes; its two nominal errors and log are retained. The final corrected focused run passes 20 tests; the new pure contract passes 15 adversarial tests. Historical records and production guards are unchanged. Independent final machine review rehashes the selected sources and checks provenance, copied payloads, false authority fields and original/d absence; it discloses the same agent's earlier provenance review and is not a human review or a full runtime/lifetime qualification.

## Exact continuation and scientific boundary

The archival-closure/current-copy distinction is qualified as a **separate, non-authorizing preparation component**. Existing production d admission still requires original history and remains blocked. Any future protocol change needs its own explicit custody policy, independent review, complete current source/runtime qualification and immutable public execution preread before a wholly distinct engineering activation. Do not silently accept copied history through the current observer, replace old witnesses, reconstruct/rearm/retry a/b/c, raise caps or infer original custody from matching bytes. If these requirements cannot be met, preserve missing continuity as the terminal engineering blocker at consolidation.

Whole resource lifetime, host transport, native physical/recovery/RFI/null and the 127/24 scientific qualification remain open. HD189733/HIP98505 cadence85030 stays selected; HD1461 HOLD; GJ724 untouched reserve; spectra/holdouts unopened; native8 unreserved; 127/24 inactive; LS paused; CHEOPS UNSENT. There were no new telescope data, candidates, protected invocations, scientific cases, RNG draws or person-directed messages. Public Git recovery of deterministic engineering artifacts is not a telescope read.

The 30 September–3 October astronomical pilot window was missed. Stop and consolidate **9 October 2026**, without automatic extension, restart or target change.

## Reproduction

Within this exact current working root and independently retained archive input package, run `python -B results_radio_native_v2_archive_contract_20261003a/qualify_archive.py --attempt <fresh-number>`. Existing attempts are exclusive and immutable. A different checkout/root must obtain its own separately authenticated current-copy inputs/observations; do not relocate or reuse original private-journal witnesses. Selected summary raw SHA256: `ac72adb462e29f533d5006b1fb924f6e4d5a745fb49afb395f1a69022e2ac41e`.
