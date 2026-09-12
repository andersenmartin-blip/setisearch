# LS7C: noise-aware TESS pixel qualification

Run: 2026-09-12T13:24:14.656467+00:00

**Restricted digital qualification: FAIL.** No event is promoted as a light-sail candidate.

L 98-59, TIC 307210830, sector 32, nominal 600–1000 nm, 20-second sampling. Observed 2020-11-20T17:10:18.955 to 2020-12-16T17:33:36.547 UTC.

24.4470 accepted cadence-days; **18.7771 searchable cadence-days**. Ten nonoverlapping 401-sample contexts span 25.640 days. These are summed sample durations, not exact photon live time.

All **1460** planned digital trials completed: 240 fixed-amplitude signals, 600 strength-matched signals, 600 strength-matched nuisances and 20 unchanged controls. Matched tests use observed screening scores 8.5, 12 and 20. Confounded and unmatched cases remain in their denominators.

## Matched-strength trials

| Kind | Score | Trials | Screen detections | Accepted | Recovered |
|---|---:|---:|---:|---:|---:|
| stellar | 8.5 | 40 | 40 | 3 | 3 |
| stellar | 12 | 40 | 40 | 12 | 12 |
| stellar | 20 | 40 | 40 | 27 | 27 |
| off_profile | 8.5 | 160 | 160 | 10 | 10 |
| off_profile | 12 | 160 | 160 | 50 | 50 |
| off_profile | 20 | 160 | 160 | 112 | 112 |
| single_pixel | 8.5 | 40 | 40 | 0 | 0 |
| single_pixel | 12 | 40 | 40 | 0 | 0 |
| single_pixel | 20 | 40 | 40 | 0 | 0 |
| block_2x2 | 8.5 | 40 | 40 | 0 | 0 |
| block_2x2 | 12 | 40 | 40 | 5 | 5 |
| block_2x2 | 20 | 40 | 40 | 11 | 11 |
| uniform | 8.5 | 40 | 40 | 0 | 0 |
| uniform | 12 | 40 | 40 | 0 | 0 |
| uniform | 20 | 40 | 40 | 0 | 0 |
| pointing | 8.5 | 80 | 80 | 0 | 0 |
| pointing | 12 | 80 | 80 | 0 | 0 |
| pointing | 20 | 80 | 80 | 0 | 0 |

Recovered means accepted without a pre-existing matched trigger. For nuisances the qualification endpoint is acceptance, irrespective of confounding.

![Matched-strength qualification](qualification.svg)

## Fixed-amplitude signals

| Shape | Added aperture flux | Screen / trials | Recovered / trials |
|---|---:|---:|---:|
| box100 | 1% | 20/20 | 5/20 |
| box100 | 3% | 20/20 | 14/20 |
| box100 | 10% | 20/20 | 14/20 |
| box30 | 1% | 1/20 | 0/20 |
| box30 | 3% | 20/20 | 11/20 |
| box30 | 10% | 20/20 | 16/20 |
| box60 | 1% | 13/20 | 1/20 |
| box60 | 3% | 20/20 | 14/20 |
| box60 | 10% | 20/20 | 14/20 |
| doublet30sep87 | 1% | 0/20 | 0/20 |
| doublet30sep87 | 3% | 20/20 | 14/20 |
| doublet30sep87 | 10% | 20/20 | 19/20 |

## Frozen requirements

| Requirement | Pass |
|---|---|
| complete_trial_count | True |
| unique_trial_ids | True |
| all_strengths_matched | True |
| stellar_8.5 | False |
| off_profile_8.5 | False |
| single_pixel_8.5 | True |
| block_2x2_8.5 | True |
| uniform_8.5 | True |
| pointing_8.5 | True |
| stellar_12 | False |
| off_profile_12 | False |
| single_pixel_12 | True |
| block_2x2_12 | False |
| uniform_12 | True |
| pointing_12 | True |
| stellar_20 | False |
| off_profile_20 | False |
| single_pixel_20 | True |
| block_2x2_20 | False |
| uniform_20 | True |
| pointing_20 | True |
| ten_percent_single_recovery | False |
| signal_confounding | True |
| null_acceptance | True |
| eligibility | True |
| no_event_overflow | True |

## Native data and geometry

Restored: 325 positive and 0 negative triggers; 0 positive and 0 negative spatial passes. Corrected: 0 positive and 0 negative triggers. All retained windows, same-window corrected scores, flags and spatial diagnostics are archived.

[Predetermined native review selection](native_review_selection.json) and [excess images](native_review.png). Spatial consistency alone cannot establish artificial origin or reject stellar flares and all unresolved contaminants.

The unchanged circular, edge-on, common-node approximation gives searched cadence coverage within one stellar radius in projected pair separation:

- b-c: 1.810% (0.33981 cadence-days).
- b-d: 1.106% (0.20764 cadence-days).
- c-d: 0.926% (0.17384 cadence-days).

Pair intervals overlap. Geometry is descriptive, omits inclination/node/ephemeris uncertainties, and does not select events or predict beam interception.

## Scope and reproducibility

This is a prospective evaluation on sector 32, selected using metadata after sectors 28/29 had closed. Scientific code and thresholds were published before the new arrays were retrieved. Original LS7/LS7B outputs remain unchanged. No result-dependent threshold adjustment is allowed.

The spatial model uses diagonal pixel variances and empirical aperture profiles, with fitted constant background and a fixed displacement grid. Its residual scores are not calibrated probabilities. Digital injections are deterministic additions after mission processing/quality selection; they do not add photon shot noise or measure processing survival. Strength-matched nuisances include amplified scene-shift patterns, not a complete physical spacecraft model; some controls share templates with the rejection model. The 2×2 block is an additional spatial mismatch absent from that library.

The ten backgrounds are shared by many trials. Passing would qualify only this finite challenge, not total transient completeness or an adopted SETI detector. TESS provides one optical band and cannot identify a laser spectrum; a 1.06-micron line lies outside its nominal band. The experiment complements LS1 radio work but supports no propulsion population limit.

- [Prospective protocol](../LS7C_TESS_PROTOCOL.md)
- [Input identities](source_manifest.json)
- [Full summary](summary.json)
- [All 1,460 trial records](trials.json)
- [Native records](restored_events.json)
- [Output checksums](SHA256SUMS)

Code commit: `baa514347c8466b78a82689a84ffb5b82f83237d`; freeze SHA-256: `7de50b9272a8cadebb6938a01dd8739c2d5854ff6f7f3c3c20df9c4be73d87b2`.

Processing: [NASA cosmic-ray documentation](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html), [MAST quality flags](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview).
