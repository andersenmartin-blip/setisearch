# Milestone 13 outcome: held-out execution aborted

Status: **ABORTED — no candidate result was produced**.

Milestone 13 preregistered a first independent detector-v0.5.0 application to
the public 2016-06-03 GBT L-band ABACAD cadence for GJ 411. The preregistration
was committed as `b0e9e051fcfa9fbcddc2d5bc34ffc87470e93a2a` before any
selected HDF5 spectral slice was read.

GitHub Actions run `32389992770` then passed the complete detector test suite
and known-answer validation, extracted and hashed all 30 configured slices,
and stopped fail-closed at the first search window. The search raised:

```text
RuntimeError: data_m13/m13_1400p5/epoch1_on.npz does not cover the rest grid
for scale=1.0, phase=-0.2
```

The frozen 350 kHz extraction guard transferred from Milestone 11 is therefore
insufficient for at least one extreme GJ 411 b orbital template. This is a
preregistration/preflight error, not a detector-v0.5.0 validation result.

## Evidential boundary

- All 30 configured NPZ extracts completed, and their SHA-256 values are
  preserved in `DATA_MANIFEST_M13.sha256`.
- The synthetic one-channel and multichannel known-answer tests passed.
- No window bank completed.
- No observed maximum, scramble distribution, empirical p-value, candidate
  cluster, veto disposition, or completeness estimate was produced.
- No selected spectral values were manually inspected, plotted, summarized,
  or used to change detector settings.
- The failed run artifact is `9414605970`, digest
  `sha256:0bfe0b9aa507e5a753b6e5f8f8ec6bcd5f9b8f43cf2d9f3b91308a1dfa041aab`.

Changing the frozen extraction ranges after spectral contact would violate the
Milestone 13 boundary. The run is not retried with wider guards and cannot be
reported as a null result or a candidate search.

## Corrective action

Before the next held-out preregistration, a metadata-only preflight must apply
every frozen orbital template to every scan timestamp and prove that each
proposed extraction interval covers the full rest grid plus dedoppler margins.
The next held-out target must use a previously uninspected cadence; detector
v0.5.0, its thresholds, vetoes, and statistical calibration remain frozen.

