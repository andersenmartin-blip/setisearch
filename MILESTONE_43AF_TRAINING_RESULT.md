# M43AF training result: no feasible joint boundary

**Training completed on 10 September 2026. See the current continuation for publication status.**
The frozen two-coordinate rule fails its training gate. No boundary is selected
and no new detector is adopted. The 112 validation inputs and 128 held-out
native nulls remain unopened. M43AF's historical diagnostic phase and final
whole-study audit remain pending; this is not a claim that all of M43AF is done.

## Frozen comparison and result

The executable freeze remains
`75b271b4b92819783692375687586d6df4f40c57`, with configuration SHA256
`a2c39320fd4e7a4972d989108282a2ac1f5887069c990dcb8df079e5eff7a9a3`.
All 940 pinned scientific files remain unchanged. The rule accepts a
geometry/rank-eligible member when its remaining-epoch ON projection coordinate
is at least the ON bound and its maximum OFF projection coordinate is below
the OFF bound. Coordinates, signs, both response mappings, scaling, the
quantile grid and tie ordering remain exactly as publicly specified.

The complete training stage records **241 inputs**: 128 native translations,
112 injection/control cases (64 signal-present and 48 controls), and one
separate baseline with reused upstream evidence. This comprises 240 new
upstream executions and one reused baseline, not 241 independent observations.
The seven injection/control types each have 16 cases.

The required recovery set is the union of the two frozen reference sets:
**57 signal cases**. The independent array-based auditor checks all **1,156
grid points against all 241 inputs**. It confirms **zero feasible grid points**.

| Frozen-grid condition | Grid points | Best attainable competing cost |
|---|---:|---|
| No control, baseline or native-null member survives | 406 | At least 4 of the 57 required signal cases are lost |
| All 57 required signal cases are recovered | 24 | At least 8 of the 48 control cases retain members |
| Both requirements jointly | 0 | No qualifying boundary |

These are descriptive extrema of the already frozen grid. No alternative
boundary has been adopted or tuned from them. The result does not prove that
every conceivable continuous boundary or different classifier must fail.
In particular, absence of a selected model is not counted as successful
rejection of every control or as zero-valued detector performance.

## Reference endpoints on the same 112 training inputs

| Unchanged reference | Recovered signals /64 | Leaking control cases /48 |
|---|---:|---:|
| Neighbor9 | 57 | 13 |
| Centered receiver + ON/OFF agreement + aggregation | 54 | 4 |
| Geometry + original OFF + aggregation | 48 | 4 |
| Geometry + aligned OFF + aggregation | 54 | 5 |

The centered reference's recovery set is contained in the 57-case required
union. A new rule must preserve the case identities in that union, not merely
match a total by exchanging lost cases for different gains.

## Evidence and limits

- 4,969 retained member records; 3,497 eligible member measurements; 12,560
  complete response profiles. These counts span related inputs and are not
  counts of independent astronomical events.
- Zero incomplete profiles and zero undefined member measurements.
- 5,646 direct native profile comparisons, plus 55,296 native-null probes
  (432 for each of 128 native translations). The scalar/coordinate oracle ran
  on every acquired record at the frozen relative/absolute tolerance of 1e-11.
- All 128 native-null records and the baseline have zero eligible members.
  Therefore they supply **no conditional profile-tail observations**. Zero
  surviving members here is not a measured physical false-alarm probability.
- The 112 training specifications contain **104 distinct native payloads**,
  with zero overlap with the pinned previous native-payload inventory. The
  within-panel duplicates and the shared observing sequence remain explicit.
- The original six sources and 96 anchor arrays were restored exactly. The
  unchanged native preflight reproduces all **7,503,600 score values bit for
  bit**, its 432 direct probes and the inherited 48 native gathers.
- The original 55 focused tests and six separate bounded-recovery tests pass.

All inputs reuse one original observing sequence. No additional observing
coverage, production qualification, physical false-alarm estimate or
astronomical candidate is claimed. Historical M43AE endpoints and earlier failed
gates remain unchanged. The separate full-study auditor has not yet run because
the historical phase is still gated on public model-decision verification.

## Seals and restoration

Model decision: `results_m43af_response/model_decision.json`

`e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`

Full training-grid seal:

`1e4d4e215ebff496620d888ffb8c9810062c169b1af4d664a0302c21e4ec0a2a`

Independent training-audit seal:

`fffcede84d651778480cf58e568207653483fc70107e3dfd1b4f7c86bd0d557e`

The lossless training archive preserves 241 original records, the grid, model
decision and training audit: 244 original files. Its manifest records all file
and transport-part SHA256 values. Byte-identical reconstruction is checked by:

```bash
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage training
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage training
```

## Next authorized scientific step

Publish and remotely verify the immutable failed model decision and its
evidence before any historical acquisition. Then acquire the remaining 261
historical response records, reusing their original detector endpoints and
exact native overlays. This completes the prospectively specified 502-record
no-model branch after its full independent audit. Leave both validation panels
unopened. Do not rerun training, change the grid, relax the gates, or credit
descriptive historical projections as restored detections.

See `M43AF_CURRENT_CONTINUATION.md` for the concrete publication and restart
status, and `M43AF_RUNTIME_RECOVERY.md` for the bounded storage repair.
