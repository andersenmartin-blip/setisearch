# M43S weaker and fractional native-profile sensitivity results

The prospectively frozen pilot is complete: **96 new signal-injection runs**,
16 reused zero-level endpoints, and 112 total endpoints. It measures the effect
of weaker ideal signals and a defined harder profile on the unchanged M43R
detector. All tests use one observing sequence, 37 templates and the same small
11.6 kHz search interval. No astronomical candidate is authorized.

## Recovery versus injected strength

Each profile has eight truths per strength: two anchor/carrier groups crossed
with the four activity subsets. The table gives retained and fully recovered
truths separately. The 16 zero-level endpoints reuse one M43R background
execution; 0 were recovered. They are not independent noise trials.

| Nominal total strength | Ideal retained | Ideal recovered | Combined retained | Combined recovered |
|---:|---:|---:|---:|---:|
| 0 | 0/8 | 0/8 | 0/8 | 0/8 |
| 2 | 0/8 | 0/8 | 0/8 | 0/8 |
| 4 | 0/8 | 0/8 | 0/8 | 0/8 |
| 6 | 1/8 | 1/8 | 0/8 | 0/8 |
| 8 | 8/8 | 8/8 | 0/8 | 0/8 |
| 12 | 8/8 | 8/8 | 4/8 | 4/8 |
| 32 | 8/8 | 8/8 | 4/8 | 4/8 |

The total-strength scale equals M43R's nominal active-epoch width-1 SNR for ideal
bin-centered signals. For the combined profile it is the **total added power**
on that same scale, not the actual peak SNR. Power is spread across channels,
with fractional carrier placement, a supported off-template perturbation and a
one-channel linear sweep during each integration. The effects are combined and
cannot be assigned individually from this experiment.

There were 0 truth/strength endpoints retained but lost at the
physical-veto stage, and 0 that passed physical vetoes but failed rank.
These are truth-level losses, not counts of the correlated member records.

| Anchor / carrier index | Active epochs (1-based) | Profile | Recovered strengths | First recovered tested strength |
|---|---|---|---|---:|
| 0 / 1024 | 1, 2 | ideal | 8, 12, 32 | 8 |
| 0 / 1024 | 1, 2 | combined | none | none |
| 0 / 1024 | 1, 3 | ideal | 8, 12, 32 | 8 |
| 0 / 1024 | 1, 3 | combined | 32 | 32 |
| 0 / 1024 | 2, 3 | ideal | 8, 12, 32 | 8 |
| 0 / 1024 | 2, 3 | combined | none | none |
| 0 / 1024 | 1, 2, 3 | ideal | 6, 8, 12, 32 | 6 |
| 0 / 1024 | 1, 2, 3 | combined | 12, 32 | 12 |
| 1700 / 3072 | 1, 2 | ideal | 8, 12, 32 | 8 |
| 1700 / 3072 | 1, 2 | combined | 12 | 12 |
| 1700 / 3072 | 1, 3 | ideal | 8, 12, 32 | 8 |
| 1700 / 3072 | 1, 3 | combined | 32 | 32 |
| 1700 / 3072 | 2, 3 | ideal | 8, 12, 32 | 8 |
| 1700 / 3072 | 2, 3 | combined | 12 | 12 |
| 1700 / 3072 | 1, 2, 3 | ideal | 8, 12, 32 | 8 |
| 1700 / 3072 | 1, 2, 3 | combined | 12, 32 | 12 |

The first recovered tested strength is a bracket point on this finite grid,
not a continuous detection limit or a population completeness percentile.
There are 2 adjacent-strength reversals where a recovered signal
becomes a miss at higher injected strength. Those outcomes remain in the table
and need a rejection-stage explanation; recovery must not be assumed monotonic.

## Association and geometric scope

The new M43S primary endpoint requires the exact activity subset and a retained
member within 20 Hz of the true center track at **every active integration**,
passing physical vetoes and inclusive rank p <=0.01. Any searched template and
width may supply it. This differs from M43R's exact-template/exact-carrier
endpoint, which is preserved. In ideal-profile trials here, the secondary exact
criterion recovered 25/48 nonzero endpoints, versus 25/48 under the
new association criterion. The two must not be silently conflated.

Before publication or new signal evaluation, metadata showed that all eight
literal midpoint controls lacked a member within 20 Hz in this **37-template
sample**: their nearest residuals range from 43.465 to
2726.439 Hz. Those geometry-only controls remain in config, outside
the 112 injected endpoints. This finding says nothing by itself about coverage
of the full 1,701-template bank.

To measure numerical sensitivity rather than known geometric absence, the frozen
rule selects the largest dyadic fraction toward the partner whose nearest
active-row residual is <= one native channel. Selected coefficient fractions
range from 0.00390625 to 0.015625; all selected truths have
residual <=2.483472 Hz. Every attempted metadata fraction is retained.
These are near-template perturbations, not a sample of the entire gaps between
templates. Carrier 1024 is paired with anchor 0 and carrier 3072 with anchor
1700, so carrier and anchor effects also cannot be separated.

## Retrospective diagnosis of strong-signal losses

After the frozen experiment completed, a separately labelled diagnostic replayed
only the 4 strongest-level misses. Every reproduced injected input
identity and ON mask hash matches the original trial, and masked above-threshold
associated-cell counts reproduce the retained-member audits exactly.

| Strongest-level missed truth | Associated cells >=10 without mask | With original mask | Best active-cut score before mask |
|---:|---:|---:|---:|
| 1 | 31 | 0 | 25.158772 |
| 5 | 31 | 0 | 24.799772 |
| 9 | 31 | 0 | 25.254629 |
| 13 | 31 | 0 | 26.089767 |

In 4/4 of these misses, the inherited isolation mask removes
all associated above-threshold cells before the later physical-veto stages.
The diagnostic retains the exact seed witnesses: filter width, epoch, neighboring
carrier, injected and background epoch scores. The rule flags a >=10 peak when
all other epochs at that carrier are below 3, combines flags across widths and
expands them by nine carriers. A displaced multi-epoch signal can therefore
trigger an isolated-epoch flag at a nearby carrier and lose its usable members.
This is a sensitivity limitation of the existing rule; arithmetic still matches
the frozen implementation.

Removing a mask in this explanation is **not a calibrated alternate detector**
and does not establish final recovery after other vetoes. No rule, threshold,
original endpoint or published result was changed. An actual mask revision needs
its own prospective null and injection calibration.

## Native model, calibration reuse and evidence

The combined profile uses a finite sinc-squared response, 17 midpoint time
samples across a one-native-channel sweep, and 16 tail channels beyond each
sweep endpoint. Each finite native packet is normalized to unit total mass;
unnormalized masses and packet hashes are retained. It is a defined sensitivity
model, not an instrument-channelizer measurement or inferred astrophysical drift.
Normalization remains fixed before addition. Complete affected native windows
and integrated columns are recomputed in float32; the same patches feed receiver
signatures. Original telescope receipts remain untouched.

- Public freeze: `95eeaa74eb0eb52f8c0a782dc9010175d269ba53`.
- Result seal: `e47ae9c30c32be355e5022c40ea7e50d8ee3cacf15b983d4bb21a869e2857645`.
- Config SHA-256: `e1976b727a1c79af5d75b2dc0fc2043cde28a900a3d1068627ecddb37250edd4`; 231 pinned dependencies.
- The M43R threshold certificate `9c8fe4dccaa4c38e564dd251158e044cbcbae72896dcb9ba6379c8080e9f2065` is reused
  unchanged at threshold 10. Its 128 calibration maxima and held-out diagnostics
  are reused; **zero new null calculations** are counted.
- Ten focused tests pass, including five new profile/association/rehydration
  tests and the five M43R injection tests. Earlier unchanged integration evidence
  remains applicable and is not relabelled as new testing.
- All 24 native cache/gather identities reproduce the M43R anchors exactly.
  Original 96 M43P arrays and the complete baseline identity are verified on load.
- All 112 endpoints and 1,069 compact member decisions validate; every
  trial uses the same threshold. There is no truncation.
- Runtime: 556.503 seconds; zero new telescope data requests.

The [audit directory](results_m43s_profile_sensitivity/) contains all 96 sealed
nonzero trial files, source/profile provenance, compact members, stage
certificates, complete endpoints, input-reuse evidence and logs. Compact audits
bind the full in-memory pipeline hash but are not full pipeline serializations.
The manifest covers these artifacts, report, plan, model and executable scripts.

## Interpretation and next step

This is a bounded sensitivity experiment on previously inspected background.
It locates recovery changes on the tested strength grid and exposes the limits
of interpreting sparse-template tests. It is not an independent search,
instrument-completeness measurement or statement that no artificial emission
exists. The immediate next step is a prospectively frozen isolation-mask
comparison, with fresh null calibration and paired injection trials, to test
a repair for the demonstrated losses. Broader template coverage and independently
varied profile effects and carriers remain necessary afterward. The fixed
detector and existing results remain reference points.

Reproduce in the pinned Python/NumPy environment with the retained M43H/M43P
inputs:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/m43s_profile_sensitivity.py \
  --freeze-commit 95eeaa74eb0eb52f8c0a782dc9010175d269ba53 \
  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
```
