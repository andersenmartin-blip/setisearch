# M43Q — the integrated diagnostic detector passes

M43 now has one connected diagnostic entry point from verified epoch scores
through masks, a global threshold handoff, exhaustive ON/OFF retention,
OFF-track matching, paired single-OFF rejection, native receiver signatures,
receiver-alias classification and inclusive rank-p evidence. All declared
integration checks pass after the documented reference/serialization amendment.

**165 tests pass.** The complete 1,701-template catalogue preserves every
one of its 163,296 physical factor values bit for bit. The real diagnostic
run reuses **37 templates, six scans, eight widths and 96 full-support ancestor
arrays**, covering the same 1,328,080,368 per-epoch cells already replayed by
M43P. This reuse is not new independent arithmetic evidence. **144 fixed real
native receiver signatures** match independently summed windows and winner
selection exactly. The synthetic whole-pipeline fixture produces all six
predeclared member outcomes, including a survivor of the physical controls.

## What changed

The Cartesian bank lacked fields required by the old retention record schema.
The new catalogue retains exact original x/y coefficients and explicit parent
identifiers. Radius, phase and legacy line fields are compatibility metadata;
they do not turn the disk bank into a physical line. All tracking uses the
original Cartesian coordinates. The 37-template catalogue has its own identity,
factor-table identity and threshold/retention receipts. Old identities are not
reused under a different catalogue.

At each score handoff, copied template bytes are checked against the inventory
derived from independently retained M43P batch hashes. Expected identities are
snapshotted before execution. The generic legacy numerical/physical algorithms
are unchanged; no M37 cache or epoch-product attestation is forged. Their M37-
specific provenance flags stay false, while the outer M43 inventory explicitly
binds the source/score inputs.

Paired OFF uses the exact values in the already verified native-gather score
vectors. Each width/epoch cache has an explicit M43Q vector plan and an actual
template-major payload hash. This is equivalent to querying those same scores,
not a relabelled M37 native cache. Stationary receiver peaks are newly measured
from receipt-bound M43I native-filter caches using the inherited ±100-Hz window
and ascending-channel tie break. All 144 fixed receiver anchors are evaluated
regardless of how many real diagnostic members pass retention.

## End-to-end diagnostic outcome

| Quantity | Result |
| --- | --- |
| Diagnostic template sample | 37 / 1,701 |
| Reused scramble rows | 4 |
| Diagnostic operational threshold | 276.775757 |
| Retained ON members | 0 |
| Retained OFF members | 0 |
| Final ON member decisions | 0 |
| Members passing evaluated physical vetoes | 0 |
| Scientific candidates selected | 0; selection is disabled |

| Inherited physical disposition | Diagnostic members |
| --- | --- |
| No diagnostic ON members retained | 0 |

The four global null maxima exactly equal the maxima of the independently
retained M43P per-template values for the same scramble rows. The threshold
is the frozen engineering rule max(50, maximum of those four global values),
with inclusive retention. It is not a newly established science threshold.
Four null values imply a minimum inclusive rank p of 0.2, so none can meet
the 0.01 scientific cutoff. The retained member counts are pipeline diagnostics,
not a search result, false-alarm measurement or candidate count. An empty real
member inventory, if present, does not by itself exercise nonempty rejection;
the known-answer synthetic fixture explicitly supplies that coverage.

The inherited `pending_receiver_alias_evaluation` label is preserved for
compatibility. After the alias stage, a separate `passes_evaluated_physical_vetoes`
Boolean explains whether a member survived these physical controls. Exact
record IDs join physical dispositions to rank evidence; none is promoted to
a scientific candidate in this qualification.

## Preserved initial failure and amendment

The initial public freeze was
`e9ceca61e8db7c0dca0076e1a8b0c3e1f8e9b17c`. It stopped at the first native
receiver anchor. The reference used Python 3.12's built-in sum instead of
the inherited sequential binary64 reduction, giving a one-ULP midpoint
difference. A second defect affected the synthetic artifact's outer seal:
integer dictionary keys changed canonical ordering after JSON conversion.

Only the reference reduction, pre-seal key normalization and explicit Python
version pin changed. Production scoring, receiver measurement, comparison
strictness, masks, the diagnostic threshold and physical rules did not.
Two regression tests cover the defects. The initial configuration, logs,
failure record and invalid synthetic outer seal are preserved, not replaced.
See MILESTONE_43Q_AMENDMENT.md. The successful rerun used the publicly verified
amended freeze **`90c3da4e3a987843398affddb49409f9784b8dbe`** before any rerun evaluation.

## Evidence and reproduction

The successful combined run took **218.344 seconds** wall time
in one process, including source/cache validation and the receiver anchors.
There were **zero new telescope requests/downloads**. NumPy 2.3.5,
Python 3.12.13; the configuration pins 210 files.

- Result: `fe2e4f6ef142d37acc904fade555058f8c374f6729d5030d2838acc7b1255fae`.
- Configuration: `70ec193275d7b8108466b97c526339803f0d9316992284d7e3321448b49f6f56`.
- Integrated pipeline: `17b59301c0e0294e83a345e5efb9594e489d131ffdb1a8c30b95e08af2eeea19`.
- Diagnostic catalogue: `1d0dc9c9adf4d88feb50fc9af53366108002f99be3f1f12eb5e471fa7ae49ae7`.
- Parent catalogue: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.

`pipeline.json` retains the complete connected outputs and input ancestry;
`receiver_anchors.json` contains every fixed native comparison. `synthetic.json`
contains the nonempty known-answer pipeline and expected outcomes. The full
run log, tests and initial failed attempt are included in the manifest.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43q_integrated_detector.py --freeze-commit 90c3da4e3a987843398affddb49409f9784b8dbe --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
PYTHONPATH=src:scripts .venv/bin/python scripts/m43q_result_report.py
sha256sum -c RESULTS_MANIFEST_M43Q_INTEGRATED_DETECTOR.sha256
```

The anchor directory contains disposable M43P arrays. If absent, reproduce
M43P from its published protocol first; M43Q refuses missing or changed arrays.
Elapsed time and enclosing run seals may differ on reproduction. The manifest
checks exact published bytes, including the intentionally invalid initial
synthetic artifact as historical evidence.

## Next work and scientific limits

The integration gap is now exercised through every connected stage. This
does not establish a full-bank spectral search, a fresh null distribution,
a native injection/recovery curve or a scientific nondetection. The real
template sample and one frequency window remain the declared scope; the three
epochs are scans in one observing sequence. The synthetic additions were
score-level fixtures, not native telescope injections.

Next: freeze a joint fresh null/native-injection programme using this integrated
path, with explicit search scope, source ancestry, resource caps and recovery
denominators. Reuse the established arithmetic and focus on measured false
alarms and recovery. Earlier scientific endpoints and denominators remain intact.
