# Distinct M43T experiments

On 7 September 2026, after publishing the saved `neighbor9` freeze and before
running its new calibration or injections, continuation discovered a completed
`neighbor2` experiment already linked from the main README. Both use M43T in
their historical names. Preserve both names, code, inputs and result histories;
identify the policy and branch explicitly whenever reporting either experiment.

| Scope | Saved mask comparison | Separate neighboring-support test |
|---|---|---|
| Branch | `m43-support-qualification` | `m43t-neighbor-mask` |
| Policy | `neighbor9` | `neighbor2` |
| Support radius | +/-9 proxy bins | +/-2 proxy bins |
| Final mask dilation | +/-9 bins | +/-9 bins |
| Nonzero strengths | 6, 8, 12, 32 | 12, 32 |
| Distinct nonzero input pairs | 64 | 32 |
| Legacy executions | Newly executed in both-arm comparison | Historical M43S executions, with rank-eligibility equivalence checked |
| Public freeze | `4f3c86de46a3920e595856fa7315560ff20723c3` | `0bfa205d3f0671de661b6555c42a4763dcba0165` |

The separate experiment reports four gains and no losses at its tested levels.
Its unchanged baseline masks contain no masked cells, so equal conditional
null outcomes do not qualify rejection of strong interference. The saved
`neighbor9` specification remains unchanged after reading that result. Neither
study is blind validation or a reason to select an optimal support radius.
The saved comparison uses scramble seed 430020; the separate test uses 430021.
Their 256-row shift inventories have zero overlapping rows. Both still reuse
the same observing sequence, so this does not make their evidence independent.

[Separate neighbor2 report](https://github.com/andersenmartin-blip/setisearch/blob/m43t-neighbor-mask/MILESTONE_43T_NEIGHBOR_MASK_RESULT.md).

The scratch runtime holding the original input arrays was unavailable on this
continuation. Operational helpers restore the same historical HTTP segments,
source receipts and full-support arrays against their published SHA-256 values.
Those downloads add no observing coverage. Any later experiment-level count of
zero telescope requests refers only to numerical evaluation after restoration,
not to the complete continuation session. Recovery logs retain transport errors
and interrupted attempts. No frozen scientific dependency is edited for recovery.
