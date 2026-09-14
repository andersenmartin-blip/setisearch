# LS7M calibrated PRF and exposure benchmark — PASS

Completed 14 September 2026 from source freeze
`b6fea2889d792d6c1980335f5e83b27c54ca22c7`, after original-model acquisition
freeze `99c2cc107d2c621ec015ef8b6de1ba5803ffd1b3`.

**The declared numerical operator passes.** All 144 calibration-only cases and
4,050 phase reconstructions pass an independent original-MATLAB/SciPy/Simpson
audit. This verifies an explicit local PRF translation and exposure family.
It does not measure native prediction improvement or qualify a detector.

## Implementation

The operator interpolates mission pixel-response images across subpixel
position and the surrounding CCD field nodes. Source motion evaluates the
response at pixel minus source position. It preserves the calibration's
amplitude and finite extent, without a second pixel-box convolution. The local
optical shape remains fixed during translation.

The temporal operator integrates a piecewise linear trajectory through ten
1.98-second live intervals in a twenty-second cadence, with an optional
top-hat pulse. It splits at trajectory knots and PRF interpolation-cell
crossings, then integrates each quadratic segment with two Gauss samples.
The denominator is all 19.8 seconds of live time, including pulse-off time.
The three readout placements are assumptions, not measured telemetry timing.
[Frozen contract](../LS7M_RESPONSE_SPEC.md).

## Verification

| Check | Result |
|---|---:|
| Synthetic known-answer tests | 10/10 pass |
| Original MATLAB models / FITS pairs | 50/50 exactly equal, no transpose |
| Original image and uncertainty scalar values | 1,368,900 exactly equal |
| Reconstructed phase images | 4,050/4,050 pass |
| Maximum phase-image absolute discrepancy | 5.56e-17 |
| Fixed position/coordinate/path/pulse/readout cases | 144/144 pass |
| Independent coverage Boolean checks | 17,424/17,424 agree |
| Independent finite flux/uncertainty comparisons | 32,604 pass |
| Maximum independent flux discrepancy | 1.39e-16 |
| Maximum independent uncertainty-entry discrepancy | 1.05e-17 |
| Frozen absolute numerical tolerance | 2e-12 |
| Inherited LS7K/LS7L manifest entries | 113/113 unchanged |

The producer uses sealed FITS images and Gauss integration. The auditor uses
original MATLAB arrays, SciPy interpolation and independently constructed
**per-pixel** Simpson intervals. It imports neither the producer nor the new
PRF operator. Exact axis/annotation metadata and every case identity are
checked. These counts describe validation work, not extra observations or
independent astronomical trials.

## Coordinates and stamp coverage

The original axes are [-58/9, 58/9] pixels, with 117 samples and zero at index
58. All fifty original images match the mission FITS export exactly. Three
nodes retain nonzero rowShift annotations; none contributes to these target
kernels. The operator rejects a positive field weight on such a node until
the annotation is understood.

The mission README's 44-column warning and the exporter's direct RAWX/RAWY
references still do not establish one absolute origin. Both predeclared
field-column offsets, 0 and -44, were evaluated. No native data selected one.

| Geometry | Fully covered cases | Relative L2 change between column conventions |
|---|---:|---:|
| Sector 29 nominal target | 42/72 | 0.6546–0.6883% |
| Sector 32 nominal target | 0/72 | 0.6568–0.7946% |

The L2 comparison uses pixels covered in both variants and divides by the
offset-zero norm. This measures sensitivity within the fixed panel; it is
not absolute calibration accuracy or a bound on every coordinate error.

Every case has either 110 or 121 supported stamp pixels. In sector 32 the
nominal source is 6.458344 pixels from the left column, beyond the table's
6.444444-pixel support. That column cannot be supplied by this finite table.
Some sector-29 moving paths likewise leave the supported domain. No missing
tail is zero-filled or renormalized. An uncovered pixel's integrated result
is NaN with a saved Boolean mask.

Stationary, full-duration source; integration starts 0.01 seconds after each
frame boundary:

| Sector | Column offset | Supported pixels | Sum of calibrated response |
|---|---:|---:|---:|
| 29 | 0 | 121 | 0.989840488695 |
| 29 | -44 | 121 | 0.989769110252 |
| 32 | 0 | 110 | 0.982375907973 |
| 32 | -44 | 110 | 0.982451587417 |

Sector-32 sums are **partial-footprint sums**, not whole-stamp throughput.
The historical 13-by-13 phase accounting remains unchanged.

## Short pulses and readout

A declared 30 ms pulse spanning [-0.015,0.015] seconds straddles a frame
boundary. Its overlap with live integration is:

| Integration begins after frame boundary | Live pulse duration | Duration / 19.8 s |
|---|---:|---:|
| 0 ms | 15 ms | 0.000757576 |
| 10 ms | 10 ms | 0.000505051 |
| 20 ms | 15 ms | 0.000757576 |

The readout assumption changes the stationary modeled pulse amplitude by a
factor of 1.5 between extremes in this example. This is synthetic timing
sensitivity, not a new observed event. Ten quaternion rows per cadence do
not identify the correct readout placement or telemetry kernel.

## Interpretation and limits

Uncertainty entries use the same positive interpolation/integration weights.
Their sum is an **uncertainty-entry envelope**. Spatial correlations and
sector-specific derivative errors remain unknown; this is not a calibrated
confidence interval. Small coordinate sensitivity does not remove that limit.

The mission PRFs were derived from commissioning data and represent a science
pointing profile according to the archived mission README. Their status as an
instantaneous, de-jittered optical PSF is not established. Adding measured
jitter could double-count blur. This is a physical-model risk to resolve or
explicitly restrict before a native comparison, not a measured failure here.

Camera/spacecraft quaternion conventions, the detector Jacobian and sample
timing still need a physical contract. DVA and thermal deformation cannot
simply be equated with rigid pointing. Guide membership, target exclusion
and upstream target-pulse coupling remain unestablished. No thermal predictor
or empirical gain/sign/lag/profile adjustment is introduced.

There are **zero native response comparisons, zero detector decisions and zero
added observing days**. [Current continuation](../LS7M_CONTINUATION.md).
LS7J and historical negative results remain closed; unused TESS sectors and
M43 panels stay unopened.

## Reproducible files

- [Cases](cases.json), [per-pixel predictions](predictions.npz), [field weights](field_weights.json).
- [Coordinate sensitivity](coordinate_sensitivity.json), [phase checks](phase_checks.csv), [summary](summary.json).
- [Independent audit](audit.json), [benchmark log](benchmark.log), [audit log](audit.log), [provenance](provenance.json), [checksums](SHA256SUMS).
- [Original-model metadata](../results_ls7m_prf_inputs/inventory.json), [known-answer log](../results_ls7m_prf_inputs/known_answer_tests.log).

Execution used local Python 3.12.14 and pinned requirements_ls7g.txt. No GitHub
Actions run is claimed for this evaluation. The original 10,399,482 MATLAB
bytes remain a reproducible cache; hashes, URLs and full coordinate metadata
are retained. The auditor restores only those two files if absent. Reproduce
from the source freeze in an isolated checkout without this result directory.
