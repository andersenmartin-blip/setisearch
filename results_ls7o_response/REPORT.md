# LS7O six-reference centroid availability and response

**Input availability: FAIL. Native correction and pulse transfer: NOT EVALUATED. Independent audit: PASS.**

Twelve archived 20-second reference products from seven distinct stars were selected by metadata before reading their time series. The six-reference affine centroid estimator replaces the prior target POS_CORR input. The calibrated target PRF and protected plane retain their previous fixed rules. These are the same twenty closed contexts, with no added observing coverage or adopted detector.

## Fixed native comparison

| Sector | Field-column offset | Available / 210 | Motion / static energy | Plane / static | Combined / static | Improved backgrounds | Joint cell |
|---|---:|---:|---:|---:|---:|---:|---|
| 29 | 0 | 0 | unavailable | unavailable | unavailable | not evaluated | BLOCKED |
| 29 | -44 | 0 | unavailable | unavailable | unavailable | not evaluated | BLOCKED |
| 32 | 0 | 0 | unavailable | unavailable | unavailable | not evaluated | BLOCKED |
| 32 | -44 | 0 | unavailable | unavailable | unavailable | not evaluated | BLOCKED |

All four cells must meet the predeclared native requirements and pulse limits. The ledger reserves 840 paired slots sharing 420 windows and twenty backgrounds; unavailable slots are not measured model responses. The static denominator and every historical window are unchanged. No ablation replaces the primary model.

## Reference acquisition and geometry

The complete products would occupy 135,717,120 bytes for light curves and 3,719,056,320 bytes for matching target-pixel files. The frozen acquisition instead transfers exactly 4,812,000 raw table bytes: 48,120 reference rows in 120 ranges. No reference pixel time series is acquired.

| Sector | TIC | Tmag | Separation (degrees) | Centroid pixels | Valid rows / 4,010 |
|---|---:|---:|---:|---:|---:|
| 29 | 307780535 | 8.05 | 1.26764 | 22 | 3859 |
| 29 | 306739391 | 11.31 | 2.01753 | 13 | 3080 |
| 29 | 306577335 | 8.11 | 2.05258 | 22 | 3852 |
| 29 | 306739511 | 8.06 | 2.18279 | 24 | 3859 |
| 29 | 307087642 | 8.84 | 2.31925 | 21 | 3868 |
| 29 | 307785290 | 8.09 | 2.48341 | 23 | 3859 |
| 32 | 307780535 | 8.05 | 1.26764 | 22 | 3858 |
| 32 | 307441274 | 8.30 | 1.65571 | 20 | 3882 |
| 32 | 306739391 | 11.31 | 2.01753 | 14 | 3753 |
| 32 | 306577335 | 8.11 | 2.05258 | 23 | 3826 |
| 32 | 306739511 | 8.06 | 2.18279 | 23 | 3842 |
| 32 | 307785290 | 8.09 | 2.48341 | 24 | 3884 |

The target lies inside the reference convex hull in both sectors. The nearest centroid-contributing pixel is 236.916 pixels from its nominal position. All reference masks are pairwise disjoint. Exact CADENCENO joins pass; the maximum TIME-TIMECORR discrepancy is 0 seconds, below the frozen 0.001-second tolerance.

The published ranges retain raw bytes, SHA-256, product ETags and metadata. Whole-product FITS checksums are not verified by these partial reads. The independent struct parser exactly checks every preserved centroid, quoted error, quality, cadence and time field.

## Availability obstruction

| Sector | Windows with finite centroids and positive errors | All-six quality-zero event windows | All-six quality-zero sideband windows | Fully available windows |
|---|---:|---:|---:|---:|
| 29 | 210/210 | 72/210 | 0/210 | 0/210 |
| 32 | 210/210 | 101/210 | 0/210 | 0/210 |

Every complete window fails the fixed requirement that all six stars have QUALITY=0 throughout all 110 sideband rows. All selected centroids and quoted positive errors are numerically present. There are at least three individually usable references at every saved cadence, but that does not satisfy the frozen all-six, all-sideband rule. These descriptive counts do not evaluate a relaxed rule.

Observed bits are 64 (an optimal-aperture cosmic ray), 512 (an outlier removed before cotrending), 1024 (a collateral-pixel cosmic ray), and 4096 (scattered-light exclusion), as defined in [SDPDD Rev F, table 32](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf). Flags describe different processing conditions; their presence alone does not identify the astrometric error of a retained centroid. No flag is waived here.

## Conditional error accounting

| Sector | Axis | Median formal error (pixels) | Largest displacement (pixels) | Median reference residual / 3 | Largest reference residual / 3 |
|---|---|---:|---:|---:|---:|

No reference field was fitted, so this table has no measured conditional-error or affine-residual values.


Where available, these summaries repeat selected cadences across windows. The specified formal errors assume independent quoted reference errors and condition on fitted sideband centers and weights. Center uncertainty, shared calibration, centroid response, focus, crowding and target PRF errors remain outside that conditional model.

## Pulse protection and audit

| Sector | Offset | Nominal maximum distortion | Entry-stress maximum distortion | Failed or blocked slots |
|---|---:|---:|---:|---:|
| 29 | 0 | unavailable | unavailable | 3150 |
| 29 | -44 | unavailable | unavailable | 3150 |
| 32 | 0 | unavailable | unavailable | 3150 |
| 32 | -44 | unavailable | unavailable | 3150 |

Limits are 1% for nominal calibration and 5% for entry stresses. **0 of 12,600 planned pulse-response slots were evaluated.** Unavailable slots count against the joint requirement but are not measured pulse distortions. Target photons are excluded from the final reference combination; shared upstream calibration and optical cross-talk remain unbounded.

The audit passes 916 numerical comparisons and 384,960 exact raw-field comparisons. It independently reconstructs metadata coordinates, mask exclusion, raw rows, eligibility and every available numerical branch. Here the native numerical comparisons concern the unchanged static baseline; no new affine/PRF/pulse branch was reached. 237 manifest entries, including the new input packages, agree. Execution used Python 3.12.14 locally; no GitHub Actions run is claimed.

The frozen producer has a coarse stage flag named native_pixel_response_evaluated which is true when its evaluator runs, including a fully blocked run. [Explicit scope accounting](scope_accounting.json) records zero evaluated corrections and zero evaluated pulse transfers. The original output is preserved; the blocked ledger must not be read as a measured correction failure.

## Reproduction and decision

Source freeze: `f2d7aef6e82f90a357ec7f54e349cfc2b43953dc`. The response result directory and reference time-series extracts are absent from that checkpoint. Run acquisition, evaluation and audit in order using requirements_ls7g.txt. Frozen membership, product/range limits, model equations and claim boundaries are in [LS7O_SPEC.md](../LS7O_SPEC.md).

[Native availability ledger](native.jsonl.gz), [reference availability](reference_motion.jsonl.gz), [pulse slots](pulses.jsonl.gz), [gates](summary.json), [audit](audit.json), [quality attribution](quality_diagnosis.json), [per-window attribution](quality_windows.jsonl.gz), [raw input provenance](../results_ls7o_inputs/sources.json), [metadata inventory](../results_ls7o_metadata/inventory.json), [continuation](../LS7O_CONTINUATION.md).

Close the exact all-six/all-sideband eligibility formulation. The archive contains simultaneous reference measurements, but the frozen input contract is unusable on these windows. No empirical success or failure of the reference-driven physical correction was measured. The next work is a pixel/product quality and centroid-response contract using these fixed reference identities, or a different optical product if that contract cannot be established. Do not drop stars, waive flags or reweight this completed experiment to manufacture an available result. LS7J and LS7N remain separate measured failures; unused sectors and M43 panels remain closed.
