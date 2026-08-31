# Milestone 37 post-contact capacity census

Status: **DIAGNOSTIC COMPLETE — RUN 004 REMAINS INVALID; NO SIGNAL OR NULL
CLAIM**.

After Run 004 stopped at the frozen 10,000-record limit, a separate diagnostic
replayed every frozen ON and OFF hypothesis against the already sealed global
threshold. It counted score cells but retained no candidate records, applied no
veto, and did not modify the Run 004 controller or journal.

## Complete census

The restartable four-process replay evaluated all 2,976 hypotheses for each of
five windows and both scan kinds: 22,250,510,400 score cells in total. A second
invocation reopened and revalidated all ten immutable children in 2.4 seconds.

| Window | ON records | OFF records | 10,000 cap exceeded |
|---|---:|---:|---|
| `m37_1400p5` | 1,800 | 1,720 | no |
| `m37_1406p5` | 218 | 232 | no |
| `m37_1412p5` | 225 | 208 | no |
| `m37_1418p5` | 41,640 | 0 | ON only |
| `m37_1425p0` | 0 | 0 | no |
| **Total** | **43,883** | **2,160** | **46,043 combined** |

The four ON totals that completed during Run 004 reproduce exactly. The full
`m37_1418p5` ON total is 41,640, establishing that the original lower bound of
10,026 represented about one quarter of the complete retention demand.

## Overflow morphology

All 41,640 `m37_1418p5` ON records are produced by the 129-channel filter,
whose nominal width is about 365.78 Hz. No other spectral width contributes a
single record. The records occupy 42 contiguous motion-template line indices,
from -21 through 20, and two adjacent 10 kHz census buckets spanning
1,419,340,000–1,419,360,000 Hz.

| Threshold range | Records | Fraction |
|---|---:|---:|
| 1.00–1.05× | 9,971 | 23.946% |
| 1.05–1.10× | 16,379 | 39.335% |
| 1.10–1.25× | 15,290 | 36.720% |
| ≥1.25× | 0 | 0% |

The maximum is S/N 154.97610473632812, or 1.2280044 times the frozen threshold
126.20158386230469. Activity subsets `[0, 1]` and `[0, 1, 2]` account for
25,466 and 16,158 records; the two remaining pairs contribute eight each.

This is best described at this stage as one dense, broad, ON-only feature in
the detector score space, duplicated across nearby carrier cells, motion
templates and activity subsets. That is an engineering characterization, not
a count of independent events and not a physical RFI or technosignature
classification. Those interpretations require the complete frozen OFF,
adjacent-OFF, receiver-frame and significance stages in a new valid run.

## Capacity-only continuation

The recommended post-contact v0.6.1 amendment raises the per-window retention
and cluster cap to 50,000. This is 8,360 records, or 20.08%, above the exact
deterministic maximum while avoiding an unnecessary change to the threshold,
grid, templates, widths, activity subsets or veto logic.

Dependent resource envelopes must be raised at the same time rather than
waiting for a second mid-run failure:

| Resource | v0.6 | Proposed v0.6.1 |
|---|---:|---:|
| Records/clusters per window | 10,000 | 50,000 |
| Alias bucket entries | 30,000 | 150,000 |
| Adjacent/receiver queries | 30,000 | 150,000 |
| Alias identity/candidate visits | 5,000,000 | 125,000,000 |
| Evidence bytes per window | 96,000,000 | 480,000,000 |
| Evidence bytes for five windows | 480,000,000 | 2,400,000,000 |
| Live ndarray bytes | 536,870,912 | unchanged |

The quadratic alias allowance is scaled by 25 because the record envelope is
scaled by five. The derived worst-case retention evidence bound is 417,647,424
bytes per window, below the proposed 480,000,000-byte cap.

The amendment must be independently identified, tested on cap boundaries and
published before a new Run 005 is created. Run 004 stays permanently invalid;
its threshold must not be adapted and its over-cap records must not be
truncated. If Run 005 reaches another declared resource cap, it must also stop
fail-closed rather than being repaired in place.

Machine-readable results and all ten child ledgers are under
`results_m37_v0p6_capacity_census_001/`.
