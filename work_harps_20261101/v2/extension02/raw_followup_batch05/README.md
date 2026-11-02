# Extension02 raw follow-up batch05 — final pending pair recovered

**Both previously unavailable records, V2E2-0332 and V2E2-0333 on HD141937, now have complete original-product raw review.** The primary and secondary visual reviews independently proposed **2 provisional detector artefacts (A)**; root inspected both records/all covering-order displays and adopts the same codes without overrides. Both covering orders pass the unchanged mapping gates. [Adopted decisions](ADOPTED_DISPOSITIONS.csv), [review comparison](REVIEW_COMPARISON.json), [root visual check](ROOT_VISUAL_CHECK.json) and [summary](SUMMARY.json) retain the decisions. Original batch04 failures and results remain intact.

This follow-up adds no exposures or observing time to the survey. All **669 of 669** V2 records now have initial raw review. Current totals are **403 A / 46 O / 185 U / 35 M / 0 N**; the new336 cohort is **194 A / 21 O / 90 U / 31 M / 0 N**. All340 predecessor selected decisions remain unchanged and the reviewed-selected table grows to342. The existing **185 unresolved structures and 35 mapping limitations** remain explicit follow-up work. There is no qualified laser candidate or calibrated null result.

## Selection, acquisition and provenance

The fixed selection is the entire remaining N queue: MAIN100 index **99**, exposure **ADP.2023-07-07T01:08:58.252**, target HD141937. The two exact original products are raw **HARPS.2023-07-06T04:02:59.524** and ancillary **ADP.2023-07-07T01:08:58.253**. No target substitution, strength ranking or availability-based replacement occurred.

Batch04's two HTTP503 HEAD failures remain historical evidence. [This separate plan](PLAN.json) prospectively allowed at most two new HEAD attempts and two payload attempts per exact product, one acquisition worker, no redirects, terminal HTTP401/403 handling and a **100,000,000-byte** total charged-payload limit. Both HEAD requests succeeded on their first attempts. [Selection](SELECTION.json), [HEAD metadata](REMOTE_PRODUCT_METADATA.json), [frozen sources](FOLLOWUP_FREEZE.json) and [the visual plan](VISUAL_REVIEW_PLAN.json) precede payload acquisition.

Root published and independently verified all **33 frozen source files** at commit [5d41596](https://github.com/andersenmartin-blip/setisearch/commit/5d41596a3c11bed6d169ed2c5dd2a4213345041b); [the receipt](PREREGISTRATION_RECEIPT.json) also records a corrected pre-acquisition publication-format issue. Freeze SHA-256 is `4bd8f69133cb795c50003a50dbbc03edb23d975f3292f3101c8c1041d39db1a8`.

Both original products downloaded on their first payload attempts. [The canonical manifest](products/MANIFEST.json) records **27,804,441 actual and charged bytes**, zero unknown-byte charges, zero replacements and two successful receipts. The [independent acquisition inventory](independent_audit/ACQUISITION_INVENTORY.json) verifies both hashes and lengths, all stdout completion/status lines, no residual partial files and the unchanged selection. The source merged FITS was restored from its prior checkpoint and verified as **5,261,760 bytes**, SHA-256 `ce41eb4190e9a4599ef610ae6f7b2f7daa13edd83d7bb114dffe8750e6ec73d9`.

## Mapping, images and visual judgments

Native extraction, global registration, descriptive local checks and five-window mapping arithmetic are **byte-identical to batch04**. The inherited 24-region global grid fixes orientation. Event support requires the global gate, every covering-order five-window gate and complete cutouts. No coordinates or thresholds were adjusted to selected morphology.

Both selected events have one covering native order and complete 31×33 raw cutouts. The exact nested 21×25 baseline, both background conventions and 41 native samples are preserved. [Mapping](NATIVE_MAPPING.json), [five-window references](FIVE_WINDOW_MAPPING_AUDIT.json) and [local descriptive checks](LOCAL_TRACE_AUDIT.json) retain the numerical evidence.

| Record | Covering order | Adopted code | Observed morphology |
|---|---:|---|---|
| V2E2-0332 | 64 | A | Thin oblique charge-like trail crosses the predicted trace at the narrow native spike. |
| V2E2-0333 | 66 | A | Compact off-center deposit has a thin diagonal tail extending to the predicted trace near the weak native enhancement. |

The [primary review](PRIMARY_VISUAL_REVIEW.json) and [secondary review](SECONDARY_VISUAL_REVIEW.json) were saved without reading one another's labels. Each actually inspected the complete [atlas](figures/REVIEW_01.png), both covering-order panels and the shared unlabeled [fixed central enlargement](primary_enlarged/CENTRAL_01.png). Both propose the same two A codes, adopted by root after inspecting both records and all covering-order displays. The primary reviewer also prepared and ran extraction; independence here concerns judgments, not independent data production. Separate AI-agent agreement is not blinded external validation or human peer review.

Full-cutout scales are dominated by bright adjacent-trace pixels. The fixed central display keeps all 31 rows and columns −8 through +8 for every available order, with [exact display scales](primary_enlarged/DISPLAY_SCALES.json). It reveals charge-like features without altering coordinates, arrays or classification thresholds. The [fiber inventory](FIBER_INVENTORY.json) records `STAR,WAVE,G1`, an e2ds_B product and FP calibration context. No independent sky fiber is documented. A remains a provisional explanation of the selected component; weaker photon/background components and blends are not excluded.

## Independent numerical validation

[The audit](independent_audit/SUMMARY.json) passes all scoped reconstruction and coverage checks:

| Scope | Count |
|---|---:|
| Selected records / available exposure pairs | 2 / 1 |
| Verified source files: raw, ancillary, merged FITS | 3 |
| Reconstructed full raw/native cutouts | 2 |
| Unique exposure/order pairs | 2 |
| Recomputed global region/orientation cases | 192 |
| Recomputed five-window references | 10 |
| Unchanged frozen source files | 33 |

The checker does not import project analysis modules. It independently reconstructs raw detector joins, direct-power wavelength/trace polynomials, cutouts/backgrounds, native profiles, global grids and five-window checks. NumPy/SciPy/Astropy primitives are shared. Legacy local checks are audited for coverage and gate arithmetic, not full numerical reconstruction. Numeric agreement does not determine physical origin. [Thirteen offline transport/identity guards](GUARD_TEST_RESULTS.json) also pass for both actual frozen jobs.

## Saved inputs and restoration

[One saved input package](checkpoints/SAVED_INPUTS.md) contains both canonical products and receipts: **25,499,413 archive bytes**, SHA-256 `1b05cb6852de3239570ca46b85d91de233f090738f03c1e0607c73e0dcbf1fcc`. [Exact save identities and member hashes](checkpoints/LIBRARY_INPUTS.json) are retained. The merged science FITS remains in the earlier extension02 science checkpoint.

The small GitHub evidence archive has **3 members: 2 native NPZ cutouts and 1 reference JSON grid**, **27,768 bytes**, SHA-256 `b21fc1ada34390145c9623f252cdb05538136b8c5fd47f027360fc885587f76e`. [Archive members](EVIDENCE_ARCHIVE.json), [ordered binary part](EVIDENCE_PARTS.json) and [six passing restoration checks](EVIDENCE_RESTORE_VALIDATION.json) preserve deterministic packaging, exact-byte reconstruction, identical-file retention and refusal of changed files, symlinks or corrupt parts.

Restore archives into staging first. `v2/extension02/` members are relative to `work_harps_20261101`; verify all archive/member hashes and copy only canonical inputs/receipts. Do not overwrite current status with historical archive metadata. In a separate working copy with original products restored, run:

```bash
python3 restore_evidence.py
python3 independent_audit/check_batch05.py
python3 independent_audit/check_inventory.py
```

Audits rewrite their own reports, so preserve published originals. Runtime: Python3.12.14, NumPy2.3.5, SciPy1.17.0, Astropy8.0.2, Matplotlib3.10.8. Completed raw or epoch analysis need not be repeated merely to resume.

The main survey remains **300 unique exposures of 20 targets, 70.874650833 hours**; V2 contains **669 records in 200 exposures**. After this pair, continuation proceeds to mapping limitations and unresolved structures under separately frozen methods, then the approved Rubin week (8–14 November). No unattended background worker is configured. All origin judgments are provisional and post-detection; no survey sensitivity, global false-alarm rate, qualified laser exclusion or calibrated null result follows.

[The continuation state](CONTINUATION_STATE.json) preserves the empty pending-raw queue, all35 mapping-limited records and185 unresolved structures. [Current-state reconciliation](update_current.py) changes only the two previously N records; [verification](CONTINUITY_VALIDATION.json) checks all667 other combined-master rows, all340 predecessor selected rows and unchanged original catalogs. Root separately maintains the project entry point and diagnostic next actions.
