# Milestone 18 primary held-out result

Status: **PRIMARY SEARCH COMPLETE — FOUR ARITHMETIC-FAMILY CASES REQUIRE THE
FROZEN MORPHOLOGY REVIEW**.

GitHub Actions run `32574746066` executed the preregistered configuration at
commit `5f4ff886919465d2701dc4b4d3db34175f8d3db6`. Artifact `9476441210`, named
`milestone-18-held-out-results`, has verified digest
`sha256:d8035c01568eb4475adde7033f73f2fe9d0d9b6f167db2b01809e2c70f33ec76`.
All nine primary result files match `RESULTS_MANIFEST_M18.sha256`, and the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Frozen global result

- observed maximum S/N: **7.893494440**;
- empirical global p-value: **1/257 = 0.00389105**;
- scramble-null median: 6.412166;
- scramble-null 99th percentile and operational threshold: **7.288440**; and
- completeness: 4/32 recovery at ideal single-epoch S/N 8, and 32/32 at S/N
  12 and every higher preregistered level.

The maximum occurs in `m18_1425p0` at rest frequency 1425.213204339 MHz,
template 17 (scale 1.0, phase -0.1 cycles), width five channels, and active ON
epochs 2+3. The per-epoch values are `[-0.2233, 5.5815, 5.5826]`. The automated
same-track OFF check is null; the maximum OFF value on that frozen track is
only 0.2207. No receiver-frame alias was assigned.

## Cases fixed for review

Exactly four reported clusters exceed the global threshold. All are in the
1425 MHz window, all are tagged `arithmetic_frequency_family`, and none has an
automated adjacent-OFF or receiver-alias veto:

| Rest frequency (MHz) | Max S/N | Widths (channels) | Active ON epochs |
|---:|---:|---|---|
| 1425.213204339 | 7.893494 | 5, 9 | 2+3 |
| 1425.144117298 | 7.757697 | 3, 5, 9 | 1+2+3; 2+3 |
| 1425.201303731 | 7.619195 | 3, 5, 9 | 2+3 |
| 1425.191166806 | 7.355817 | 3, 5, 9 | 2+3 |

These are not detections. Their arithmetic-family flag is insufficient by
itself for a physical veto, while their global significance cannot be
increased by post-hoc inspection. The next permitted step is a separately
frozen, candidate-local ON/OFF morphology review of all four cases. Because
the frozen header screen contains no second qualifying GJ 649 cadence, any
case left unresolved cannot be called independently recurrent.
