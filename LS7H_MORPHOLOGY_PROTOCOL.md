# LS7H: background and morphology diagnosis of the closed LS7G transfer

Declared 13 September 2026 after LS7G and before computing any LS7H result.
This is an explicitly retrospective development study, not unseen validation.

## Question and fixed scope

LS7G passes all six signal-recovery cells but fails four control cells:
2x2 at score 8.5 (4/40), cross at 8.5 (8/40), triangle at 8.5 (9/40), and
triangle at 12 (3/40). Each permits only 2/40. A 2x2 template was already
present. Determine how native background changes these spatial comparisons,
and whether one explicit shape-bank extension repairs them at an acceptable
cost to genuine injected signals. Do not select another threshold.

Use **all 3,540** archived LS7G rows, all five suites, all 80 saved models and
the same ten sector-29 cutouts. Read the saved patterns, covariance matrices,
event vectors, original fit outcomes and full summary. No FITS acquisition,
new injection trials, temporal reselection, covariance retraining, new sector
or M43 held-out access is included. Earlier results and denominators stay fixed.
Source inputs are pinned to the current public science branch and its hashes.

## One fully specified model comparison

Keep LS7G's covariance-sparse stellar bank, all original broad nuisances, its
optional free pixel with penalty 9, source amplitude score >=5, reduced
stellar chi-square <=2, temporal score >=8 and margin **>=-1** unchanged.
Append the following binary 3x3 templates:

- Cross: center plus the four axial neighbors (5 pixels).
- Ring: all pixels except the center (8 pixels).
- Triangle: upper triangular including the diagonal (6 pixels), at each of
  four 90-degree rotations.

Enumerate these families in that order, rotations in order 0, 1, 2, 3, and
every fully in-stamp 3x3 placement in row-major order. Keep placements whose
projection intersects the existing 21-pixel optimal aperture, including
duplicate projected vectors. Do not center only on accepted failures.
Use the unchanged exact LS7E FitBank arithmetic. Minimize over the existing
and added nuisance banks; a tie retains the existing winner. Keep the saved
stellar fit exactly. This extension can only remove acceptances.

Compare the old and augmented rule on every archived trial and all inherited
joint gates. Also tabulate the already archived covariance-plain broad-bank
ablation at the same margin -1, with its full signal cost. No other threshold
or extra bank is evaluated. The named omitted shapes cease to be omitted in
this development comparison; their outcomes cannot establish generalization.

## Same-window component diagnosis

Reconstruct the injected cube from each saved pattern, amplitude, integrated
20-second exposure pulse and residual pixel. At the **recorded selected
window**, compute the signed event mean minus the 110-sample sideband median
for the injected cube (y), native cube (b), and injected addition by itself
(p). Define the background-removed increment **s = y - b**. Save b, s and p,
check y against the old vector, and measure s-p to retain any median
nonadditivity. Do not assume component medians add. This operation uses known
injection truth and is not available as a native-event detector feature.

Refit s using the saved stellar bank, existing broad nuisance bank and the
single new bank, at the same covariance and reference templates. Save full
winning fits and old/augmented clean margins. Do not assign a new temporal
detection to these counterfactual vectors. For each original accepted focus
control, record whether its clean old-bank margin falls below -1, whether
the actual added bank rejects it, and whether the original stellar winner
used the sparse pixel. Count all cases, without selecting favorable anchors.

For the **observed** winning star and broad nuisance, fix the selected
template, pixel and nonnegative source active set (include the template only
if its fitted amplitude is positive). Let D be nuisance minus stellar
residual precision after projecting out those active designs. Record the
exact conditional decomposition

`margin = s' D s + b' D b + 2 b' D s + nuisance_penalty - star_penalty`.

The terms are injected shape, native background, interaction and the penalty
difference. Check their sum against the archived margin. Component
projections within this identity are linear and unconstrained; the separate
clean-bank refits above handle alternative winners and nonnegative bounds.
This attribution does not measure a causal noise distribution, compensate
for selection, or calibrate a probability.

## Signal safeguards, denominators and reporting

Publish all original and augmented decisions, every newly lost recovered
stellar ID, all newly rejected nonstellar IDs, all 36 core cells, all group
counts and all 360 background/cell counts. Retain unmatched or confounded
rows. Counts use recovered for stellar rows and accepted for controls.
Count disjoint stellar recovery paths in the order temporal, source score,
residual, nuisance margin, confounding, recovered. Also retain acceptance
when a nuisance fits better. Reuse the exact LS7G joint descriptive gates.

For every accepted control in the four declared focus cells, link all five
nominal/displaced base stellar trials sharing anchor, phase, shape and
target score. Record both decisions for every pair, retaining actual model
IDs if numerical temporal ties select different windows. These are shared
background comparisons, not independent paired samples.

Publish a complete report, one scientific figure, machine-readable features,
bank, summary, pairs, audit, logs and checksums. State all signal costs even
if a control improvement looks favorable. No detector adoption, candidate
promotion, physical sensitivity estimate or additional observing coverage
follows from a closed-data pass. The maintained continuation must follow
the actual joint result, with no silent LS7G/LS7H repair.

## Verification and execution boundary

Five analytical tests cover geometry/rotations, signed partial-window
residuals, nonlinear medians, fixed sparse-design attribution and fixed
cut/confounding semantics. The independent auditor reconstructs templates
using coordinate sets and rotations, uses the frozen LS7G pulse integrator,
reconstructs all component vectors and checks the decomposition using
whitened least squares rather than residual precision matrices.

Audit every new winning fit directly and every new-bank/clean-bank minimum
with the frozen LS7F independent whitened QR enumeration. Check every group,
decision, loss, pair and gate independently. Relative/absolute fit tolerances
are 1e-7 / 2e-7, as in the prior audited work. Original LS7G temporal and
covariance computations reuse their completed, hash-verified audit instead
of rerunning a closed challenge. Verify all preserved manifests before and
after execution. Refuse to overwrite an existing LS7H result directory.

Publish this protocol, configuration, analysis, tests, audit and report
source with `LS7H_FREEZE.sha256` **before** the numerical evaluation. Run:

```sh
sha256sum -c LS7H_FREEZE.sha256
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_ls7h_morphology.py' -v
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python -u scripts/ls7h_morphology.py
OPENBLAS_NUM_THREADS=1 python -u scripts/ls7h_review.py
python scripts/ls7h_report.py
```

Any demonstrated implementation error must be documented explicitly before
repair. Do not alter preserved inputs, thresholds or denominators to obtain
a desired scientific outcome.
