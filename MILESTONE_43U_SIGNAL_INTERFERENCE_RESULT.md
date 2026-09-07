# M43U: native signals and interference at additional carriers

The completed three-policy experiment has **72 shared native inputs and 216 detector executions**. It recovers 29/48 signal-present cases with legacy, 47/48 with neighbor2, and 48/48 with neighbor9. Signal recovery and interference leakage are reported separately. No astronomical candidate is claimed.

- **neighbor2**: 18 signal gains, 0 signal losses; 0 added and 0 removed leaking control cases. Development gate: **failed**.
- **neighbor9**: 19 signal gains, 0 signal losses; 1 added and 0 removed leaking control cases. Development gate: **failed**.

## Signal recovery

Every row has eight cases per policy. Counts show retained truth, truth passing physical vetoes, and final rank-qualified recovery. All true signals have nominal strength 32; these are not measured output SNRs. The mixed cases also include a stronger nearby component.

| Signal case | Legacy retained / physical / recovered | Neighbor2 retained / physical / recovered | Neighbor9 retained / physical / recovered |
|---|---:|---:|---:|
| nearest | 8 / 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 |
| fractional-only | 8 / 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 |
| template-offset-only | 0 / 0 / 0 | 8 / 8 / 8 | 8 / 8 / 8 |
| smear-only | 8 / 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 |
| combined | 3 / 3 / 3 | 8 / 8 / 8 | 8 / 8 / 8 |
| mixed | 2 / 2 / 2 | 7 / 7 / 7 | 8 / 8 / 8 |

## Constructed interference controls

Every row has eight cases per policy. The first count is the number of cases with at least one final diagnostic survivor; the second counts all such members, which can be many correlated representations of the same input. These fractions are not physical false-alarm probabilities.

| Constructed control | Legacy leaking cases / final members | Neighbor2 leaking cases / final members | Neighbor9 leaking cases / final members |
|---|---:|---:|---:|
| single-epoch | 0 / 0 | 0 / 0 | 0 / 0 |
| supported-spike | 0 / 0 | 0 / 0 | 1 / 1 |
| ON-OFF | 1 / 3 | 1 / 3 | 1 / 3 |

Single-epoch controls add strength 32 in one active epoch only. Supported-spike controls also add strength 4 six proxy bins away in the other active epochs. ON-OFF controls add strength 32 along the same anchor hypothesis in active ON and corresponding OFF scans. These are constructed negative controls with known origin, not measurements of the terrestrial interference population. Mixed cases add a strength-128 component twelve bins from a combined true signal, in the first active epoch.

The shared ON-OFF failure is case 61: injection center 3584, anchor template 0, all three epochs active. Its three surviving members are identical across policies, at carriers 3610–3612 with width 65 and SNR 10.115–10.334. The extra neighbor9 failure is supported-spike case 69: one width-9 member at carrier 3588, template 36, activity subset [0, 2], SNR 10.208. All these records retain `pending_receiver_alias_evaluation` and `scientific_candidate=false`. Here “final” means passing the evaluated physical vetoes and diagnostic rank cut; it does not mean complete receiver-alias clearance. These ledger facts localize the failures but do not establish their causal mechanism. A subsequent diagnostic must trace the paired-OFF and receiver decisions before modifying any veto.

Maximum cropped ON mask occupancy across cases is {"legacy": 3430, "neighbor2": 3354, "neighbor9": 3079} cells. All per-case ON/OFF counts and physical dispositions are in the ledger. Mask counts obey neighbor9 <= neighbor2 <= legacy throughout. Equal final recovery alone does not prove that masks or earlier rejection stages behave identically.

## Mixed-input member multiplicity

| Policy | Mixed truths recovered | Final members | Associated final members | Other final members |
|---|---:|---:|---:|---:|
| legacy | 2/8 | 1759 | 67 | 1692 |
| neighbor2 | 7/8 | 2202 | 239 | 1963 |
| neighbor9 | 8/8 | 2710 | 369 | 2341 |

Association here requires the defined truth's exact activity subset and <=20 Hz center-track agreement at every active integration. Other members can include correlated template/width copies, different activity subsets, displaced responses or interference-induced outputs. This accounting does not identify their physical origin. The predeclared development gate constrains true-signal losses and the 24 pure-control case outcomes; it does not constrain total member multiplicity in mixed cases. Extra members must therefore remain visible even if that gate passes. Matched signal-only/interference-only component ablations at the same strength and location would be needed for causal assignment.

## Complete paired changes and declared decision conditions

The direct descriptive neighbor9-versus-neighbor2 comparison has signal-gain cases [44], signal-loss cases [], additional leaking controls [69], and removed leaking controls []. This does not add a new decision gate.

Case indices below refer to the frozen `cases` inventory in the configuration, which gives the carrier, activity subset, anchor and all native components.

### neighbor2

- additional control leakage cases: [].
- development gate passed: False.
- removed control leakage cases: [].
- signal gain cases: [2, 4, 8, 11, 13, 17, 20, 22, 26, 29, 31, 35, 38, 47, 49, 53, 56, 65].
- signal loss cases: [].

- no ON OFF survivors: **False**.
- no additional heldout exceedances: **True**.
- no increase in control leakage cases: **True**.
- no signal recovery loss: **True**.
### neighbor9

- additional control leakage cases: [69].
- development gate passed: False.
- removed control leakage cases: [].
- signal gain cases: [2, 4, 8, 11, 13, 17, 20, 22, 26, 29, 31, 35, 38, 44, 47, 49, 53, 56, 65].
- signal loss cases: [].

- no ON OFF survivors: **False**.
- no additional heldout exceedances: **True**.
- no increase in control leakage cases: **False**.
- no signal recovery loss: **True**.

At least one alternative fails the predeclared development gate. Preserve the complete failures and identify whether masking, ON/OFF rejection or receiver-alias logic controls them before proposing a new rule. Freeze any subsequent change and evaluate it on additional combinations or observations; do not tune this completed panel. General adoption remains unqualified even when a development gate passes.

## Conditional calibration and baseline

| Policy | Training maximum | Threshold | Held-out maximum | Held-out >= threshold |
|---|---:|---:|---:|---:|
| legacy | 8.214153 | 10.000000 | 8.102346 | 0/128 |
| neighbor2 | 8.214153 | 10.000000 | 8.102346 | 0/128 |
| neighbor9 | 8.214153 | 10.000000 | 8.102346 | 0/128 |

There are 128 training and 128 held-out shifts shared by all policies: 256 unique new rows and 768 policy-specific maxima. All 768 prior M43R/M43T rows were excluded. Masks are estimated on the original full-support baseline, cropped, then co-rolled with scores; masks are not re-estimated after scrambling. All thresholds were sealed before held-out and injection evaluation. These correlated within-sequence pre-veto maxima do not calibrate the constructed interference population and do not establish an independent physical FAP.

| Baseline policy | ON retained | OFF retained | Final diagnostic survivors | Cropped masked cells, ON+OFF |
|---|---:|---:|---:|---:|
| legacy | 0 | 0 | 0 | 0 |
| neighbor2 | 0 | 0 | 0 | 0 |
| neighbor9 | 0 | 0 | 0 | 0 |

The three baseline executions are reported separately and are not included in the 216 injection endpoints or counted as independent noise realizations.

## Scope and reproducibility

Four new injection centers, score indices 512, 1536, 2560 and 3584, are crossed with two anchor templates. Each center uses one predeclared activity subset, so carrier and activity remain confounded. This is 37 templates and 4,097 central score carriers in the same three ON/OFF pairs as M43T; it adds injection locations, not observing coverage. It is not a full-bank survey or a blind completeness estimate. Native rounding, fractional placement, template offset and one-channel smearing have separate cases plus a combined profile, but only one true-signal strength is tested.

All additions occur after fixed normalization and before complete native filtering/gathering. Overlapping components are summed in declared float32 order before filtering. ON additions enter receiver signatures; OFF additions enter OFF retention and paired-OFF measurements. All 96 original arrays and 48 native ON/OFF cache/gather identities match. The finite sinc-squared/smearing prescription is a defined model, not a measured channelizer response.

The initial startup stopped on a misspelled NumPy version attribute, before any data preparation or score evaluation. [The published startup amendment](MILESTONE_43U_STARTUP_AMENDMENT.md) fixes only this guard and retains the [original failure log](results_m43u_signal_interference/startup_failure_initial.log). All scientific configuration values are unchanged. Six focused numerical tests and the additional startup guard test pass; unchanged older evidence is reused.

Artifact validation verifies all 254 pinned files, 72 full sealed case records, 216 endpoints, identical three-policy inputs/overlays, recomputed summaries and decision gates, and 19,054 compact member decisions. No cap was exhausted in the completed result. The numerical run took **1409.4 seconds**. It used retained inputs and made no telescope requests.

- Original prospective freeze: `6091ff8907e4e882e7227ee6e9ec97c98dfe5331`.
- Corrected public execution freeze: `318cd93b0f550854bef7d25bef6ec75d14d07bc0`.
- Configuration SHA-256: `297482a20f3e721447acb2113f10e4df1aa614263d895681c40653b02c8e9cd1`.
- Result seal: `fc3d41d70bc5fa3606197084efd9dba44453e9a6e32ca5034d6caf06448f76d9`.
- Compressed ledger SHA-256: `5d17fa1be79f174366be81cd81f8f06164c2ee9b7d3f7c9ebfa6296de7f843b2`.
- Uncompressed ledger SHA-256: `e1bfb3880a9ebc6b132232acf87fdd9f5768d247577294379caf4b37e22ccbc2`.
- [Plan](MILESTONE_43U_SIGNAL_INTERFERENCE_PLAN.md), [complete result](results_m43u_signal_interference/result.json), [case ledger](results_m43u_signal_interference/case_audits.jsonl.gz), [artifact validation](results_m43u_signal_interference/artifact_validation.json), [run log](results_m43u_signal_interference/live_run.log), and [checksum manifest](RESULTS_MANIFEST_M43U_SIGNAL_INTERFERENCE.sha256).

With retained verified inputs and no completed result already present:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43u_signal_interference.py \
  --freeze-commit 318cd93b0f550854bef7d25bef6ec75d14d07bc0 \
  --anchor-root /path/to/anchors --source-root /path/to/sources \
  --checkpoint-root /path/to/m43u-case-checkpoints
```

Restart checkpoints must match the freeze, configuration, complete case and all three calibration bindings. Previous M43S/M43T results remain intact.
