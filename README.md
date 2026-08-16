# SETI Repeater Pipeline

This package implements a transparent multi-epoch search for intermittent
narrowband signals that become coherent under the predicted motion of a
selected exoplanet. The planet supplies a motion hypothesis, not a proven
source location: a detected feature could instead arise from terrestrial or
spaceborne interference, an instrumental effect, or any source within the
telescope response. The working technosignature hypothesis is a transmitter
whose frequency is stable in the selected planet frame and whose beam is not
necessarily aimed at Earth.

Version 0.4.0 is the frozen detector used for both frequency and temporal
confirmation. The Milestone 7 recurrence statistic, spectral filters,
per-epoch interference mask, candidate clustering, and RFI-family flags were
retained without tuning.

## Milestone 10 result

Milestone 10 applies the frozen detector to five fresh 1 MHz planet-frame bands
using previously unextracted public Parkes observations from 30 April, 2 May,
and 3 May 2021. The searched intervals total 5 MHz and do not overlap any
Milestone 6–9 interval.

Across approximately 840,001,680 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 9.3115** at 1424.937812000 MHz;
- scrambled-null median: **S/N 9.2781**;
- scrambled-null 99th percentile and operational threshold: **S/N 12.6079**;
- empirical global p-value from 256 complete-search scrambles: **0.4942**;
- assessment: **no candidate**.

All five band maxima are below the global threshold and their matched OFF
hypotheses fail the recurrence floor. The real-noise completeness experiment
places coarse multichannel 50% and 90% recovery points near ideal single-epoch
S/N 20.44 and 28.8. A one-channel-only search does not reach 50% recovery by
S/N 40. A complete repeat run produced byte-identical primary outputs.

## Milestone 9 result

Milestone 9 applies the frozen detector to independent Parkes observations from
29 April, 30 April, and 1 May 2021. It retests the 1405.25–1405.75 MHz
Milestone 8 band at 2 Hz resolution, using three 30-minute Proxima scans and
their immediately following 5-minute 1421−490 blank-sky controls.

Across approximately 84,000,336 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 8.1271** at 1405.516462000 MHz;
- scrambled-null median: **S/N 8.1083**;
- scrambled-null 99th percentile and operational threshold: **S/N 9.0548**;
- empirical global p-value from 256 full-search scrambles: **0.4708**;
- assessment: **no candidate**.

The strongest fluctuation appears in all three ON epochs but is typical of the
complete-search null distribution. Its matched OFF hypothesis fails the
per-epoch recurrence floor. A post-hoc cross-check also finds that neither the
2019 nor the 2021 maximum recurs in the other campaign.

## Milestone 8 result

The confirmation search covers 1405.25–1405.75 and 1423.25–1423.75 MHz in the
planet frame at 3.814697 Hz resolution. The 1 MHz total bandwidth is independent
of Milestone 7 in frequency, but it reuses the same three observing epochs.

| Band | Best S/N | Width | Frequency (MHz) | Window p | OFF result |
|---|---:|---:|---:|---:|---|
| 1405.25–1405.75 | 6.154 | 9 ch | 1405.472141266 | 0.735 | fails recurrence floor |
| 1423.25–1423.75 | 6.335 | 9 ch | 1423.628288269 | 0.350 | fails recurrence floor |

Across approximately 88,081,056 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 6.3347**;
- empirical global p-value from 256 complete-search scrambles: **0.6031**;
- scrambled-null median: **S/N 6.4046**;
- scrambled-null 99th percentile and operational threshold: **S/N 7.2519**;
- assessment: **no candidate**.

Candidate reduction retained 75 hypothesis peaks above S/N 5.5 and merged them
into 69 frequency clusters. All 69 are below the global threshold. The frozen
single-epoch interference rule masked zero cells in either ON or OFF band, so
the confirmation null does not depend on RFI excision.

## Frozen confirmation record

The configuration was frozen at 2026-08-15T18:34:04Z with SHA-256
`2e9df9f13f5cf2a3c438f1ffbd20784e76355e66e3fcb90e70f2ff19658a3d6d`.
The eight detector tests passed before extraction. The configuration retained:

- S/N at least 3 in every claimed active epoch;
- `sqrt(N)` times the weakest active-epoch S/N as the recurrence statistic;
- a moving per-epoch mask for isolated S/N ≥ 10 features with a 9-channel guard;
- normalized 1-, 3-, 5-, and 9-channel filters;
- the same candidate clustering and arithmetic-family rules as Milestone 7.

The two bands, new random seeds, and extended completeness grid were the only
planned Milestone 8 changes.

## Real-noise completeness

Signals are injected into independently shifted real 1405.5 MHz planet-frame
noise. They use continuous fractional-channel frequencies and a time-averaged
sinc-squared response while sweeping during each 16.777216 s integration. Four
exact orbital templates span 0.34–5.02 swept channels per integration.

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 4/32 (12.5%) |
| 12 | 25/32 (78.1%) | 9/32 (28.1%) |
| 16 | 32/32 (100%) | 17/32 (53.1%) |
| 20 | 32/32 (100%) | 21/32 (65.6%) |
| 24 | 32/32 (100%) | 28/32 (87.5%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Coarse piecewise-linear estimates put multichannel 50% and 90% recovery near
ideal S/N 10.29 and 14.17. The corresponding one-channel estimates are 15.5
and 25.6. These are point estimates rather than confidence bounds; 32/32 has a
Wilson 95% lower bound of 89.3%.

## Install and reproduce

Requirements are Python 3.10+, NumPy, Astropy, Matplotlib, GCC, and OpenMP.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
seti-repeater validate --tsamp 15 --channel-width 2 \
  --output results_m10/validation.json
seti-repeater extract \
  --config config/proxima_small_survey_m10.json \
  --data-dir data_m10 --workers 12
sha256sum -c DATA_MANIFEST_M10.sha256
seti-repeater search \
  --config config/proxima_small_survey_m10.json \
  --data-dir data_m10 --output-dir results_m10
python -m unittest discover -s tests -v
```

`extract` uses HTTP byte-range requests and downloads only selected channels,
not the multi-gigabyte filterbanks in full. Existing slices are cached. Source
URLs and filterbank header metadata are preserved in every extract.

## Statistical calibration

Each null realization circularly shifts epoch spectra independently before
repeating the complete width/orbit/activity search. The per-epoch RFI mask is
shifted by the same amount. This preserves each epoch's noise and interference
while destroying the inter-epoch coherence being tested. The empirical p-value
is `(1 + exceedances) / (N + 1)` and is not converted to Gaussian sigma.

## Limits

- Milestone 10 covers five disjoint bands totaling 5 MHz, not the full receiver
  band.
- The three Milestone 10 epochs all belong to the April–May 2021 follow-up
  campaign. November 2020 and January 2021 filterbanks were not returned by the
  public API when preregistered, so this is not an independent long-baseline
  confirmation.
- The Milestone 10 global null has a heavy tail dominated empirically by the
  1400.0–1401.0 MHz band; no physical cause is assigned without a separate
  full-band diagnostic.
- Milestone 9 is independent in observing epoch, not frequency; it directly
  retests the lower Milestone 8 band.
- Milestone 9 covers 0.5 MHz total, not the full receiver band.
- The 2021 OFF scans are only 5 minutes, versus 30 minutes ON, so the OFF veto
  is less sensitive.
- Completeness assumes an exact orbital-bank member and activity in epochs 1
  and 3.
- In Milestone 9, the frozen RFI rule masked 45 ON and 44 OFF
  template/epoch/frequency cells; these are only about 2.9 parts per million of
  the corresponding banks.
- Boxcars are approximations, not exact matched filters for every swept profile.
- Arithmetic-frequency families are triage flags, not proof of interference.
- A null result constrains only the signal class, epochs, frequencies, and
  sensitivity actually tested.

## Key files

- `MILESTONE_10_PREREGISTRATION.md` — frozen five-band survey design.
- `config/proxima_small_survey_m10.json` — Milestone 10 scan and search config.
- `DATA_MANIFEST_M10.sha256` — checksums for all 30 reproducible extracts.
- `results_m10/search_summary.json` — complete five-band search evidence.
- `results_m10/completeness.json` — aggregate and per-injection recovery data.
- `results_m10/completeness_thresholds.json` — coarse recovery thresholds.
- `results_m10/reproducibility_audit.json` — deterministic rerun evidence.
- `results_m10/scramble_nulls.npz` — empirical global and per-band null maxima.
- `MILESTONE_10_REPORT.md` — scientific handoff.
- `MILESTONE_9_PREREGISTRATION.md` — frozen design and config hash.
- `config/proxima_temporal_confirmation_m9.json` — temporal confirmation config.
- `DATA_MANIFEST_M9.sha256` — checksums for all six reproducible extracts.
- `results_m9/search_summary.json` — complete search evidence.
- `results_m9/completeness.json` — aggregate and per-injection recovery data.
- `results_m9/completeness_thresholds.json` — coarse recovery thresholds.
- `results_m9/temporal_crosscheck.json` — labelled post-hoc campaign comparison.
- `results_m9/reproducibility_audit.json` — deterministic rerun evidence.
- `results_m9/scramble_nulls.npz` — empirical null maxima.
- `MILESTONE_9_REPORT.md` — scientific handoff.

The extracted telescope slices are not included in the distributable archive;
the extractor and checksum manifest reproduce and verify them from public URLs.
