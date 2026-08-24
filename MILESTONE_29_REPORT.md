# Milestone 29 report: HD 11964 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 23 OVER-THRESHOLD CLUSTERS ARE VETOED BY CONTROL OR RECEIVER-FRAME EVIDENCE**.

Milestone 29 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 11964 cadence `--66653`. HD 11964 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32756939956` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9531770257`, named `milestone-29-held-out-results`, has verified digest
`sha256:9ad2730b8b2cd0752a4f8c5d7e14b47a7e744cb78d16ee57b8c193aadf1640d5`.
All nine primary result files match `RESULTS_MANIFEST_M29.sha256`; the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 13.784860** at 1400.038687989 MHz;
- scrambled-null median: **S/N 6.342153**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 7.567687**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **single adjacent-control RFI; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The maximum has a strong single adjacent-control track and receives the
automatic frozen physical veto.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | control-global S/N | Empirical p | Final maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 13.785 | 1400.038687989 | 9 | 5.313 | 0.003891 | single adjacent control |
| 1406.0-1407.0 | 5.724 | 1406.132316642 | 9 | 5.669 | 0.459144 | below threshold |
| 1412.0-1413.0 | 6.070 | 1412.518605031 | 9 | 5.354 | 0.081712 | below threshold |
| 1418.0-1419.0 | 6.080 | 1418.715361826 | 9 | 6.060 | 0.116732 | below threshold |
| 1424.5-1425.5 | 7.820 | 1425.239881687 | 9 | 7.063 | 0.003891 | receiver-frame/control RFI after fixed review |

Window p-values measure departure from the circular-shift null and do not
override physical control or receiver-frame evidence.

## Complete disposition accounting

The prospectively fixed 1200-cluster cap retained every one of the 344
clusters. **23** exceeded the global threshold:

| Final physical disposition | 1400 MHz | 1406 MHz | 1412 MHz | 1418 MHz | 1425 MHz | Total |
|---|---:|---:|---:|---:|---:|---:|
| single adjacent-control coincidence | 21 | 0 | 0 | 0 | 0 | 21 |
| receiver-frame alias plus adjacent-control coincidence | 0 | 0 | 0 | 0 | 2 | 2 |
| **survivors** | **0** | **0** | **0** | **0** | **0** | **0** |

The remaining 321 clusters were below threshold. The two 1425 MHz cases were
initially labelled `rfi_family_veto_pending_manual_review`, because arithmetic
family membership alone is not a physical veto. A separately frozen post-hoc
review then found that both hypotheses map to the identical receiver feature
in all three ON epochs and that an epoch-3 control peak lies only 16.764 Hz
away. Both therefore satisfy fixed physical RFI criteria. The investigation is
documented in `MILESTONE_29_CANDIDATE_INVESTIGATION.md`.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 4/32 (12.5%) |
| 12 | 31/32 (96.9%) | 23/32 (71.9%) |
| 16 | 32/32 (100%) | 29/32 (90.6%) |
| 20 | 32/32 (100%) | 29/32 (90.6%) |
| 24 | 32/32 (100%) | 29/32 (90.6%) |
| 32 | 32/32 (100%) | 31/32 (96.9%) |
| 40 | 32/32 (100%) | 31/32 (96.9%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.78** and **11.67**. The one-channel 50% and 90%
estimates are approximately **10.53** and **15.87**. These are grid
interpolations, not confidence bounds.

## Independent-cadence boundary

The frozen screen contains no second qualifying HD 11964 cadence. Rank 29 bet
UMi has a compatible L-band cadence, but it is a different sky target and
cannot test recurrence of an HD 11964 case. No primary case survives the fixed
physical review, so Milestone 29 closes as a primary-cadence null result.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute cadence on
  2016-12-24, not independent observing nights.
- The alternating controls are HIP10172, HIP8092, and HIP8144; they are
  control pointings, not independent target epochs.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 11964 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. Receiver-frame identity and control recurrence identify non-unique
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`ee8ba852a33d6c96b560649a0eca9e8038a6e5c7`; the successful execution commit
is `0c8977a971cf386933e8e2e23bb9f3d9b8ba0339`. The frozen configuration
SHA-256 is `d5e6da15f512957e1395fd201636fdc944d35e1c2fc99c70bed33ad10dc7a203`.
The complete search record SHA-256 is
`6537513cfc08f875328b9fc7887e95a1d130adbad5c14ebc2409b59d316d6ad9`.

The separately frozen candidate-investigation protocol is commit
`353b0dcf0a6bcb312bc1bb2ba8c4715d6576ea0e`; its successful execution commit
is `6f440e217615cdeca4fbc082d2d773d076dec190`. The machine-readable
investigation SHA-256 is
`29fe15c2895be14d2d43d40fab07c5cade53899e7d17c951aed8983e390941e2`.
Primary and investigation data manifests identify 30 and six reproducible
extracts; their result manifests identify nine and five published outputs.
Extracted telescope slices are not committed.

Publication verification workflow run `32760075189` independently revalidated
both result sets, all 14 result-file hashes, complete primary and post-hoc
disposition accounting, known-answer tests, execution provenance, and the
pre-verification report hash. Its machine-readable receipt is
`MILESTONE_29_PUBLICATION_VERIFICATION.json`.
