# LS7B: L 98-59 TESS sector 29 qualification

Run: 2026-09-12T11:03:58.869814+00:00

**Restricted digital qualification: FAIL.** No event is promoted as a light-sail candidate.

Public TESS/SPOC 20-second products, TIC 307210830, sector 29: 2020-08-26T17:41:59.413 to 2020-09-21T22:22:48.799 UTC. Nominal band 600–1000 nm.

Explicitly allowing only quality bits 64/1024 retains 21.9912 cadence-days; 19.6620 cadence-days remain after run and edge guards. Ten nonoverlapping 401-sample backgrounds span 24.682 days. Coverage is summed cadence duration, not exact photon live time.

The frozen method executed **420 digital trials**: 240 baseline signals, 80 displaced-profile signals, 80 instrumental controls and 20 unchanged controls. Bright single pulses recovered: **5/60** at 1% added aperture flux. Displaced-profile recovery: **0/80**. Instrumental controls accepted: **0/80**; unchanged controls accepted: **0/20**.

| Baseline pulse | Added flux | Recovered / trials | Screen detections | Confounded |
|---|---:|---:|---:|---:|
| box30 | 0.1% | 0/20 | 0 | 0 |
| box30 | 0.3% | 0/20 | 0 | 0 |
| box30 | 1% | 0/20 | 0 | 0 |
| box60 | 0.1% | 0/20 | 0 | 0 |
| box60 | 0.3% | 0/20 | 0 | 0 |
| box60 | 1% | 2/20 | 9 | 0 |
| box100 | 0.1% | 0/20 | 0 | 0 |
| box100 | 0.3% | 0/20 | 0 | 0 |
| box100 | 1% | 3/20 | 16 | 0 |
| doublet30sep87 | 0.1% | 0/20 | 0 | 0 |
| doublet30sep87 | 0.3% | 0/20 | 0 | 0 |
| doublet30sep87 | 1% | 0/20 | 0 | 0 |

## Frozen gates

| Gate | Passed |
|---|---|
| bright_single_recovery | False |
| off_profile_recovery | False |
| null_acceptance | True |
| baseline_confounding | True |
| no_event_overflow | True |
| single_pixel_acceptance | True |
| uniform_acceptance | True |
| pointing_acceptance | True |
| eligibility | True |

Per-class instrumental controls:

- single_pixel: 0/20 accepted.
- uniform: 0/20 accepted.
- pointing: 0/40 accepted.

The baseline and extra trials share ten backgrounds. Noise, quality selection, and mission processing precede digital injection. Shifted profiles and two simple pointing motions are limited models. These results do not measure hardware/SPOC survival, complete transient sensitivity, all kinds of interference, or a physical population limit.

![Digital qualification](qualification.svg)

## Native screening

Restored screen: 343 positive and 0 negative events; 0 positive events pass the provisional pixel screen. Corrected diagnostic screen: 0 positive and 0 negative events. Counts may differ because correction and robust noise both affect screening; same-window corrected scores are also recorded.

All retained events are in the ledgers. The fixed visual review selects the strongest six positive pixel passes and four positive failures, when available. A pixel pass does not distinguish every stellar flare, unresolved source or instrumental fluctuation from an artificial transient. No retrospective veto changes a gate or event count.

[Native review selection](native_review_selection.json) and [time/excess-image figure](native_review.png).

## Geometry and LS1 comparison

The unchanged circular, edge-on, common-node approximation gives these fractions of searched cadence centers within one stellar radius in projected pair separation:

- b-c: 2.113% (0.41551 cadence-days).
- b-d: 1.890% (0.37153 cadence-days).
- c-d: 1.231% (0.24213 cadence-days).

Geometry uses BJD_TDB and the existing LS3 ephemerides without inclination, nodal or ephemeris uncertainty. It did not select windows or promote an event and does not predict beam interception. This red-optical short-transient experiment complements LS1's radio work; it has separate sensitivity and exposure denominators. TESS supplies one broad band and cannot establish a narrow laser spectrum. A narrow 1.06-micron beam lies outside the nominal band.

## Provenance and continuation

The method was fixed and published before opening sector 29. Sector 28 remains closed development evidence with its original failure unchanged. No threshold, anchor, amplitude or quality mask was retuned after this evaluation. Later interpretation of native plots is explicitly retrospective and will be reported separately from the fixed ledgers.

Code commit: `dcec9bc0d450ce5938a3a23e4005991415f640c9`. Freeze SHA-256: `c7c069c5c1472bbb7faaae824b152eb2379351e3896838b5eee2206f20109610`.

- [Frozen protocol](../LS7B_TESS_PROTOCOL.md)
- [Full summary and environment](summary.json)
- [Source identities](source_manifest.json)
- [Eligibility preflight](preflight.json)
- [Baseline trials](baseline_trials.json)
- [Additional trials](extended_trials.json)
- [Restored native ledger](restored_events.json)
- [Corrected native ledger](corrected_events.json)
- [Output checksums](SHA256SUMS)

Processing references: [MAST flags](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview), [NASA TESS cosmic-ray processing](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html).
