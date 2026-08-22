# Milestone 16 independent-cadence follow-up plan

**FROZEN BEFORE INDEPENDENT SPECTRAL CONTACT**

This plan governs the targeted HD 219134 follow-up in the complete public GBT
L-band ABACAD cadence `--65393` beginning 2016-10-01 (MJD
57662.20481481482), approximately 40 days after the original Milestone 16
cadence. Catalogue identities and HDF5 headers were screened before the
Milestone 16 search; no spectral dataset value from this cadence has been read.

## Frozen inputs

- Config: `config/hd219134h_m16_independent_followup.json`
- Config SHA-256:
  `2ce40ea883f932766aeb0147b283d117fd0657a1dcb28811b12a3d0658c5d319`
- Analysis script: `scripts/m16_independent_cadence_followup.py`
- Script SHA-256:
  `b477c2e6dae5811322a3c550b55a9723bec2df48609508f091cfe7221aa87e93`
- Candidate-investigation input SHA-256:
  `ad408be5061e2f1272469cac03c81e1781e93d2c9bf22afaa18113ee4538ce6f`
- Cadence sequence: `A-B-A-C-A-D`, with three HD 219134 ON scans and three
  distinct OFF-source scans
- Extraction intervals: 1411.2-1413.8 and 1423.7-1426.3 MHz, reusing the
  validated Milestone 16 guards

The cadence is selected mechanically as the earliest complete qualifying
HD 219134 cadence after `--63424` in the corrected pre-contact header screen.

Exactly these two hypotheses are tested:

| Case | Original disposition | Rest frequency (MHz) | Scale | Phase | Width | Template |
|---:|---|---:|---:|---:|---:|---:|
| 1 | automated survivor | 1412.485745176673 | 0.75 | +0.1 | 9 ch | 14 |
| 2 | arithmetic-family review | 1425.1362785696983 | 1.0 | +0.1 | 9 ch | 19 |

No frequency, orbital template, phase, scale, spectral width, candidate,
cadence, scan, or threshold may be added or changed after spectral contact.

## Frozen measurements

For each hypothesis and all six independent scans:

1. Project the exact frozen planet-frame hypothesis to the scan times using the
   unchanged HD 219134 h orbit, target astrometry, and GBT location.
2. Apply the frozen nine-channel normalized boxcar.
3. Record predicted-track S/N, the local stationary maximum, all qualifying
   stationary peaks at S/N at least 5.5, and the bounded plus/minus 2 Hz/s
   free-drift diagnostic within plus/minus 100 Hz.
4. Compare every independent ON local peak with every OFF qualifying peak in
   the receiver frame using the fixed 20 Hz tolerance.

## Frozen dispositions

Rules are applied in this order:

1. **`RFI_OR_INSTRUMENTAL`** if any OFF qualifying peak lies within 20 Hz of
   any ON local peak, or if any OFF candidate-track S/N is at least 5.5.
2. **`PERSISTS_IN_INDEPENDENT_CADENCE_REQUIRES_FURTHER_FOLLOWUP`** if at
   least two of the three independent ON candidate-track S/N values are at
   least 3.0 and no OFF rule fires.
3. **`NOT_REDETECTED_IN_INDEPENDENT_CADENCE`** otherwise.

Free-drift maxima, widest-boxcar selection, arithmetic-family membership, and
visual impression cannot alone change a disposition.

## Interpretive boundary

This is a targeted follow-up chosen after the Milestone 16 result, not a new
blind search. It produces no new empirical global p-value and cannot increase
the frozen held-out significance. Persistence would remain a follow-up
condition, not a detection or technosignature claim. Non-redetection constrains
only this cadence, the two exact hypotheses, and the measured sensitivity.
