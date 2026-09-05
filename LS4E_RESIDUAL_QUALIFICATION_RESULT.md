# LS4E v1: residual-pulse synthetic qualification result

Status: **SYNTHETIC QUALIFICATION PASSED; REAL CANDIDATE NOT REANALYSED**.

LS4E implements a separately versioned residual-pulse diagnostic following
the LS4D specificity audit. The thresholds, ten case families and 24 seeds
were committed locally in `429f1a0` before the first qualification-grid run.
The freeze was local and had not been publicly registered before execution.
No parameters were retuned after the results were inspected.

## Results

| Synthetic case | Passes | Intended outcome |
|---|---:|---|
| White noise | 0 / 24 | Reject |
| Constant plateau | 0 / 24 | Reject |
| Smooth Gaussian envelope | 0 / 24 | Reject |
| Linear baseline | 0 / 24 | Reject |
| Single gain step | 0 / 24 | Reject |
| Isolated impulse | 0 / 24 | Reject |
| Pulse trains in ON and shifted OFF control | 0 / 24 | Reject |
| ON candidate pulses plus ON-reference pulses | 0 / 24 | Reject |
| Periodic ON-only pulse train | 24 / 24 | Recover |
| Irregular ON-only pulse train | 24 / 24 | Recover |

All **192 negative grid examples were rejected** and all **48 positive
examples recovered**. Seeds are reused across the case families, so these
totals should not be interpreted as independent trials from a common
population. No false-alarm probability or confidence interval is inferred.

The exact native-LS4C-geometry plateau counterexample from LS4D was also
rejected: 837,632 samples at 0.349525 ms, the same seed `114004`, and the
92.341797–156.766306 s interval. It produces zero residual pulse clusters
at every scale, whereas the old LS4C rule passed it. This is one additional
test beyond the 240-case grid, not a new radio observation.

All **28 LS4A–LS4E unit tests passed**. The LS4E freeze, LS4C freeze and
LS4D result manifest verify. Independent geometry checks select the intended
11 channel centers for the candidate's padded band, indices `[7354, 7365)`,
and exercise reversed axes, exact edges and invalid intervals. No measured
LS4C spectrum has yet been extracted with that corrected selection.

## What changed and what this supports

The new module removes a local robust linear baseline before measuring
short-scale power. It requires multiple separated pulse events with matching
times between scales and rejects residual pulses in the available ON-reference
or OFF regions. Thus a slow envelope alone does not satisfy this diagnostic
in the tested examples. The original detector remains unchanged and auditable.

This is an engineering qualification of a deliberately narrow, conservative
screen. The positive injections are strong 12 ms pulse trains above independent
Gaussian noise, not a model of diffraction. These examples do not establish
sensitivity to weak signals, other pulse widths, quantization, clipping,
nonstationary noise or the full spectrum-level selection procedure. An ON-only
terrestrial pulse train with identical morphology could pass. The 2 s guard
intervals are excluded, and background pulses may veto genuine transients.

**The origin and revised-test outcome of `LS4B-A1-9380` remain unknown.**
The synthetic result neither rehabilitates nor rejects the real event.

## Next step

A separately frozen LS4F runtime should apply the qualified diagnostic to
the original and corrected frequency selections, retain pulse timing and
cross-band/channel concentration diagnostics, and compare the selected ON
data with controls. It must bind exact input hashes, resource limits and
the derived-output schema before re-reading radio data. Reanalysis remains
retrospective, and another independent epoch is still needed for candidate
promotion. LS4E itself reads no new radio spectra.

## Reproduction

```bash
sha256sum -c LS4E_FREEZE.sha256
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'
PYTHONPATH=src:scripts python scripts/ls4e_residual_qualification.py
sha256sum -c RESULTS_MANIFEST_LS4E.sha256
```

Recorded runtime: Python 3.12.13, NumPy 2.3.5. Exact floating-point result hashes
can depend on runtime versions. The result is
`results_ls4e_qualification/qualification.json`, with canonical identity
`75a5f3576bfb1e279aa6908523102c7adb8ff8257e1e7f0b5c26e51727cd2682`.
The qualification grid executes only after its source/config freeze verifies.
