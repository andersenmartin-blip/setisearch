# LS7I input preparation: both closed TESS sectors are ready

**Input restoration and independent checks pass. The new background model has not yet been evaluated.**

The first work block of the [two-week plan](../TWO_WEEK_PLAN_2026-09-14.md) is complete: sector 32 has been restored from its original identity-pinned TESS products; sector 29 reuses its sealed LS7G cutouts. The common input index accounts for all **6,720 historical trial rows**, with full spatial/temporal injection recipes and original archive links. These reuse **20 background contexts**, with **8,020 individual cadences** in their cutouts. They are not independent trials or new observing coverage.

| Closed TESS sector | Backgrounds × cadences | Aperture pixels | Historical trial rows | Models linked | Training vectors checked |
|---|---:|---:|---:|---:|---:|
| 29 | 10 × 401 | 21 | 3,540 | 80 | 150 |
| 32 | 10 × 401 | 18 | 3,180 | 94 | 150 |

## Trial suites and the remaining design gap

| Common suite | Sector 29 | Sector 32 |
|---|---:|---:|
| base | 1460 | 1460 |
| sparse_stress | 1040 | 1040 |
| known_extended | 360 | 360 |
| unmodeled_shapes | 360 | 0 |
| bounded_pointing | 320 | 320 |

Sector 32 has no historical cross/ring/triangle control suite corresponding to LS7G’s 360 omitted-shape rows. The upcoming model protocol must decide the corresponding fixed supplement before evaluating its outcomes. No supplement is generated here, and neither historical denominator changes.

## What was verified

- Both original sector-32 FITS product hashes and byte counts match. The original eligibility and all ten anchor indices reproduce.
- An independent FITS reader restores cosmic-ray correction records using cadence and detector coordinates. It checks all 4,010 full-stamp context samples and the ten original run-flux arrays against the export, exactly.
- Sector 29 remains byte-identical to its existing published cutout file. Its original FITS/eligibility audit is retained by hash; no second copy or download is required.
- All 6,720 injection recipes reproduce the saved event vectors and both injected/native temporal selections. The audit uses independent pulse integration and scalar window enumeration.
- All 300 archived training vectors reproduce from the individual cadences; every case has an original row, model and context link. Sector prefixes prevent historical trial-ID collisions.
- Residual stress remains in its parent’s window even when the altered trial selects another window. Physical pointing remains at its original unamplified multiplier.
- Three analytical tests cover parent-window stress, fixed-flux/null amplitudes and complete sector-qualified identity/order. Historical spatial fits and covariance audits are reused by hash; there is no new fitting or qualification pass.

| Sector | Maximum event-vector error (e⁻/s per pixel) | Maximum temporal-score error | Maximum normalized training-vector error |
|---|---:|---:|---:|
| 29 | 0 | 0 | 0 |
| 32 | 0 | 0 | 0 |

## Input contract for the next model

`datasets.json` identifies each context file and original ledger by SHA-256. Paths are relative to the repository root. Sector 29 points to `results_ls7g_transfer/backgrounds.npz`; sector 32 points to this package’s `sector32.npz`. Both use the same array names: `native`, `seconds`, `sigmas`, `aperture`, `anchors`, `anchor_btjd`, `context_cadence`, `context_quality`, and the per-anchor original run flux/bounds. 

`contexts.json` provides the chronology and global context IDs. `trial_recipes.jsonl.gz` and `patterns.json` reconstruct each historical injected cube, including its residual pixel. The original fit outcomes and event vectors remain in the linked, unchanged historical ledgers.

**The recipe files contain injection truth.** They belong in the evaluation harness. A new detector must receive only the observable input allowed by its frozen inference protocol, not the case kind, true native realization beneath a pulse, injection amplitude or clean target vector. This input-preparation freeze is not the upcoming model’s scientific freeze.

## Restored contexts

| Context | Native row index | Anchor BTJD | First cadence | Last cadence |
|---|---:|---:|---:|---:|
| s029/a00 | 718 | 2088.398592159 | 3719082 | 3719482 |
| s029/a01 | 9772 | 2090.494392798 | 3728136 | 3728536 |
| s029/a02 | 19839 | 2092.824680673 | 3738203 | 3738603 |
| s029/a03 | 30588 | 2095.312836648 | 3748952 | 3749352 |
| s029/a04 | 38439 | 2097.130169781 | 3756803 | 3757203 |
| s029/a05 | 47092 | 2099.133148078 | 3765456 | 3765856 |
| s029/a06 | 73622 | 2105.274269321 | 3791986 | 3792386 |
| s029/a07 | 83077 | 2107.462901764 | 3801441 | 3801841 |
| s029/a08 | 94709 | 2110.155464241 | 3813073 | 3813473 |
| s029/a09 | 107347 | 2113.080894855 | 3825711 | 3826111 |
| s032/a00 | 426 | 2174.315026061 | 4090242 | 4090642 |
| s032/a01 | 7912 | 2176.047921521 | 4097728 | 4098128 |
| s032/a02 | 17676 | 2178.308139876 | 4107492 | 4107892 |
| s032/a03 | 27442 | 2180.568821715 | 4117258 | 4117658 |
| s032/a04 | 39778 | 2183.424420307 | 4129594 | 4129994 |
| s032/a05 | 61335 | 2188.414546012 | 4151151 | 4151551 |
| s032/a06 | 73859 | 2191.313673942 | 4163675 | 4164075 |
| s032/a07 | 87822 | 2194.545910207 | 4177638 | 4178038 |
| s032/a08 | 97216 | 2196.720487929 | 4187032 | 4187432 |
| s032/a09 | 111190 | 2199.955269813 | 4201006 | 4201406 |

## Next action

Implement the one primary time-dependent background/residual model with a protected event interval and training exclusions. Test whether surrounding cadences predict the problematic component while preserving pulses, including an unpredictable-noise known-answer case. Fix the joint two-sector evaluation and any missing control supplement before running it. No new sector, threshold sweep or model adoption follows from successful input restoration.

All LS7G/LS7H detector failures remain unchanged. This stage produces no candidate, sensitivity limit or additional observing coverage. The dates in the two-week plan are work windows; input work started when the owner asked to start, without waiting for a calendar boundary.

Source freeze: `44040ac87de1fab261191dd19f7f3ebd2d04e073`. GitHub run: [restoration and independent audit](https://github.com/andersenmartin-blip/setisearch/actions/runs/34763103507).

- [Input protocol](../LS7I_INPUT_PROTOCOL.md), [configuration](../config/ls7i_inputs.json), [source hashes](../LS7I_INPUT_FREEZE.sha256)
- [Dataset identities](datasets.json), [context index](contexts.json), [sector-32 cutouts](sector32.npz), [original source identities](sector32_source.json)
- [Trial recipes](trial_recipes.jsonl.gz), [patterns](patterns.json), [summary](summary.json), [independent audit](AUDIT.json), [output hashes](SHA256SUMS)
- [Current status](../PROJECT_STATUS.md), [continuation](../LS7I_CONTINUATION.md)
