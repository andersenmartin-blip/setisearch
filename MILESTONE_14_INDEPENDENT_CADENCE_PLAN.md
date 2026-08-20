# Milestone 14 partial independent-cadence follow-up plan

**FROZEN BEFORE INDEPENDENT SPECTRAL CONTACT**

This plan governs the targeted 2016-07-15 GJ 687 follow-up. The catalogue and
HDF5 headers have been inspected, but no spectral dataset values from cadence
`--517803` have been read.

## Frozen inputs

- Config: `config/gj687b_m14_partial_independent_followup.json`
- Config SHA-256: `2c652ce41f66b3c0cc0c1963061a92c01a04d297f35b9319da6acb9ee848a228`
- Analysis script: `scripts/m14_independent_cadence_followup.py`
- Script SHA-256: `5cbc1e2fcc9ddb3482c6832e0638631e8fd211f82f9e6fec5c9ee48ee84f79d9`
- Cadence: `--517803`, 2016-07-15, sequence `A-B-A-D`
- Available scans: two GJ 687 ON scans, one adjacent HIP85098 OFF scan, and
  one later HIP85612 OFF scan
- Extraction interval: 1423.9–1426.1 MHz, the already validated Milestone 14
  1425 MHz extraction guard

Exactly these three hypotheses are tested:

| Original candidate | Rest frequency (MHz) | Scale | Phase | Width | Template |
|---:|---:|---:|---:|---:|---:|
| 1 | 1425.3152769058943 | 1.0 | 0.1 | 9 ch | 19 |
| 3 | 1425.1348843798041 | 1.0 | -0.1 | 9 ch | 17 |
| 5 | 1425.3288304433227 | 0.25 | 0.2 | 9 ch | 5 |

No frequency, orbital template, phase, scale, spectral width, candidate count,
or scan may be added after spectral contact.

## Frozen measurements

For each hypothesis and each of the four scans:

1. Project the exact frozen planet-frame hypothesis to the scan times using the
   unchanged GJ 687 b orbit, target astrometry, and GBT location.
2. Apply the frozen nine-channel normalized boxcar.
3. Record the predicted-track S/N, local stationary peak, qualifying peaks at
   S/N at least 5.5, and a labelled free-drift diagnostic bounded to ±2 Hz/s.
4. Compare every available OFF qualifying peak with each ON local peak in the
   receiver frame using the already fixed 20 Hz tolerance.

The later `D` scan is explicitly labelled non-adjacent. It is usable as a
secondary receiver-frame control but is not represented as the missing `C`
scan or as an adjacent control for the second `A` scan.

## Frozen dispositions

Rules are applied in this order:

1. **`RFI_OR_INSTRUMENTAL`** if any available OFF qualifying peak lies within
   20 Hz of either ON local peak, or if either OFF candidate-track S/N is at
   least 5.5.
2. **`PERSISTS_IN_PARTIAL_INDEPENDENT_CADENCE_REQUIRES_FURTHER_FOLLOWUP`** if
   both independent ON candidate-track S/N values are at least 3.0 and no OFF
   rule fires.
3. **`NOT_REDETECTED_IN_PARTIAL_INDEPENDENT_CADENCE`** otherwise.

The free-drift diagnostic, widest-boxcar selection, and arithmetic-family
membership cannot alone change a disposition.

## Interpretive boundary

This is a targeted follow-up chosen after Milestone 14, not a blind search.
It produces no new empirical global p-value and cannot increase the frozen
significance. Persistence in two ON scans would remain a follow-up condition,
not a detection or technosignature claim. Non-redetection constrains only this
partial cadence and sensitivity. A complete independent ABACAD observation
would still be preferable.
