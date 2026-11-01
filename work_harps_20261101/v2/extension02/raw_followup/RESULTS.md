# Extension02: initial raw/native follow-up results

The selected eight exposures have now received complete raw/native inspection for all 65 accepted detector records: six V1E2 and 59 V2E2 events. The baseline review finds 43 provisional detector artifacts, 11 provisional atmospheric O I records, two unresolved spectral features and nine records with insufficient prescribed local mapping. These are descriptive follow-up categories. No physical origin is final, and no technosignature is confirmed.

| Baseline category | V1E2 records | Selected V2E2 records | Combined records |
|---|---:|---:|---:|
| Provisional detector artifact | 2 | 41 | 43 |
| Provisional atmospheric O I | 3 | 8 | 11 |
| Unresolved spectral feature | 0 | 2 | 2 |
| Insufficient local raw mapping | 1 | 8 | 9 |
| Total reviewed | 6 | 59 | 65 |

The entire extension02 V2 output has 336 records. BASELINE_V2_ALL336_DISPOSITIONS.csv accounts for all of them: 59 selected records receive the categories above, while **277 remain explicitly unreviewed in raw data because they were outside the fixed subset**. This is not complete raw triage of the new 100 spectra.

Every V1E2 event has a nearby same-exposure V2E2 record describing the same raw feature. V1_V2_CROSS_LINKS.json retains the six pairings and their native-pixel/wavelength differences. The 65 records therefore must not be counted as 65 independent physical features, and raw/native products add no independent observing time beyond the existing exposures.

## What the images show

Most provisional artifact records have compact charge-like pixels, a short or long trail crossing the science trace, or a sharp feature in one native overlap order absent from the other. Some occur on top of broader spectral structure; the category does not imply that all surrounding flux is an artifact. All judgments retain their individual explanation in PRIMARY_VISUAL_REVIEW.json and the baseline table.

The eleven O I records lie within 0.00924 Å of the adopted topocentric-air 5577.339 or 6300.304 Å positions and show raw excess compatible with the science-fiber spatial profile. Both position and raw morphology informed the provisional interpretation; no automatic wavelength veto was applied. All eight exposures use FP calibration in fiber B. **There is no independent simultaneous sky control in this subset**, and the earlier sky-control result from another exposure cannot be transferred to these observations as confirmation.

The two unresolved spectral records are V2E2-0104 (HD114386, approximately 3859.555 Å barycentric) and V2E2-0129 (HD114783, approximately 3881.615 Å barycentric). Their broader structures appear consistently in both overlapping orders and follow the science traces. That supports spectral structure rather than an obvious isolated charge event; it does not identify their physical origin or make them laser detections.

The nine mapping-limited records remain in that category even when an artifact-like trail or photon-compatible broad feature is visible. They are V1E2-0003 and V2E2-0001, 0128, 0130, 0131, 0132, 0208, 0225 and 0228. Any subsequent wider mapping analysis belongs in the separate mapping_followup directory; these baseline files stay unchanged.

## Acquisition, provenance and anomaly

The rule was frozen before this agent read the new accepted-event contents: choose up to eight V1-bearing exposures in MAIN100 order, then fill from remaining V2-bearing exposures in that order. The selected MAIN100 indices are 14, 33, 38, 51, 53, 55, then 1 and 2. Selection did not use event strength, wavelength, target preference or product availability.

The amended plan/code/selection was published and independently verified by the root agent before acquisition at commit [0b988bfd80db1af068654d640459868c34af2875](https://github.com/andersenmartin-blip/setisearch/commit/0b988bfd80db1af068654d640459868c34af2875). FOLLOWUP_FREEZE.json SHA-256 is `bb6b57f4d769db3d08fe5b9ea8797b8520a8c410ed4a8e4e909b1702e1524cfd`.

All eight raw and eight ancillary products passed identity, container, length and SHA-256 checks. Acquisition receipts record one successful attempt per product and 210,108,924 known-returned/charged payload bytes, below the 350,000,000-byte cap. No selected exposure was replaced. The code prohibits response-body-draining redirects, conservatively charges the complete reserved read allowance after a read error, and records known-returned versus charged bytes separately. Eleven offline guard tests preceded acquisition. Initial unpublished code and the explicit amendment are preserved.

After the final manifest, three unexplained partial-name files totaling 4,194,304 bytes remained on disk. Each is an exact prefix of its corresponding verified final product, and its timestamp precedes the manifest. Normal successful rename should remove those names; their persistence cause and network provenance remain unknown. They were preserved in diagnostics/stale_partial_files and included as non-science checkpoint evidence. They were never admitted to extraction or review. PARTIAL_FILE_ANOMALY.json and the independent anomaly audit record the hashes and timeline. Reconciliation of the recorded payload ledger does **not** independently verify wire traffic or establish whether the surviving prefixes imply additional transfers.

## Checks and review limits

The fixed extraction generated 86 covering-order cutouts for all 65 records, with no edge-truncated order. Seventy-seven order mappings pass the inherited checks. The baseline local usable flag gates two spatial offsets with sufficient samples; local correlations are reported but not thresholded. This remains distinct from the later mapping43 wider-reference method.

The independent numeric audit verifies all 16 product identities/hashes, every native-array correspondence and all 86 saved cutout structures. For three preselected exposures it exactly reconstructs 35 raw order cutouts, all three reference grids and 35 local audits. It verifies the disjoint 59-selected/277-not-selected V2 ledger and that protected prior files remain unchanged. This is fresh-process reconstruction of the frozen conventions, not an independent detector implementation, physical-origin validation or sensitivity estimate.

Two AI agents inspected all 17 neutral pages independently of each other's initial judgments. Their 65 category assignments agree after normalizing the names for insufficient mapping. Both agents knew the selection and detector context; this is **separate agent review**, not blinded scientific validation or human review. A root-agent nine-record spot check, made before seeing their categories, also agrees with the baseline. Original judgments, figure hashes, comparison rules and limitations are preserved. There were no category disagreements requiring a forced resolution.

## Reproducibility artifacts

- BASELINE_SELECTED_EVENT_DISPOSITIONS.csv: all 65 event records and individual reasons.
- BASELINE_V2_ALL336_DISPOSITIONS.csv: complete V2 accounting including the 277 not selected.
- PRIMARY_VISUAL_REVIEW.json, audit/INDEPENDENT_VISUAL_NOTES.json, REVIEW_AGREEMENT.json and ROOT_VISUAL_CHECK.json: separate review records.
- NATIVE_MAPPING.json, LOCAL_TRACE_AUDIT.json, FIBER_INVENTORY.json and native/: all 86 numerical cutouts and provenance.
- figures/REVIEW_01.png through REVIEW_17.png and FIGURE_INDEX.json: complete neutral image pages, each kept individually.
- audit/NUMERIC_SUMMARY.json: exact verification scope and remaining limitations.
- RAW_BASELINE_EVIDENCE.zip and RAW_BASELINE_EVIDENCE_MANIFEST.json: compact baseline code, arrays, metadata, receipts and audits; image pages are listed by hash and delivered individually.

Original extension02 production, frozen README/code and earlier project catalogs are unchanged. The baseline archive excludes evolving mapping_followup work, source raw/TAR binaries and partial-prefix binaries; those source/diagnostic bytes have separate verified input checkpoints.
