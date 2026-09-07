# M43X: strongest-epoch-excluded aggregate confirmation

M43W rejected the tested false associations but lost two paired signal cases
under an absolute per-active-epoch floor. M43X tests one specified alternative
with uneven signal strengths. This development study does not adopt a detector.
All prior scientific decisions and the exposed W73/74 and V failures remain.

## Fixed statistic and paired endpoints

For a retained member with canonical active subset A (two or three epochs),
exclude the active epoch with the largest ON score at that member's template,
width and carrier. Ties exclude the earliest active epoch. Compute
`R = sum(scores in remaining active epochs) / sqrt(len(A)-1)` using float64
accumulation. Require R >= 5.5, inclusive. Nonfinite/incomplete evidence aborts.
The 5.5 confirmation floor is inherited, not fitted to exposed losses. R is a
specified diagnostic; it is not assigned an independent normal-tail p-value.
For two epochs this is exactly the old minimum-active-epoch rule. With three,
it pools the two weaker epochs. The unchanged upstream >=3 support floor
still applies to every declared active epoch; arbitrary variability is not
qualified by this test. The statistic deliberately has no new OFF treatment.

Three endpoints share each native input and one M43U neighbor9 base execution:
`neighbor9` reference; `epoch_confirmation` (M43W >=5.5 in every active epoch);
and `remaining_aggregate` (R >=5.5). Both additions operate after unchanged
retention, OFF, receiver, alias and rank stages. Do not rebuild alias witnesses
or recover previously vetoed members. Both final sets must be reference subsets;
the epoch-confirmation set must also be an aggregate-confirmation subset.
Record exact per-member scores, excluded epoch, statistic and rejection reasons.

## Verification and calibration

Reverify all 96 original native arrays and all 48 ON/OFF gathers. Before
calibration, compare R against a separate sorted-score scalar sum at five
preselected positions 0/1/2048/4095/4096, all 37 templates, eight widths and
four activity subsets: 5,920 comparisons, including both carrier-grid edges.
Verify every retained ON vector against its source. Focused tests cover scalar
permutations, subset semantics, ties, boundaries, prior vetoes and corruption.
Unchanged detector numerical evidence is reused.

Seed 430024 fixes 128 training and 128 held-out shift rows, excluding all 1,280
unique R/T/U/W prior rows (V reused U). Preserve baseline mask estimation,
cropping and co-rolling, and the conservative >=3 pre-veto global null maxima.
Seal the shared threshold max(10, training maximum) before held-out and native
panel execution. Added cuts cannot lower the threshold or increase retention.
Held-out evidence is correlated within one observing sequence; it measures
neither independent physical FAP nor an OFF false-veto probability.

## Complete panel and component pairing

Carrier centers 1280/2816 cross all four activity subsets and anchor templates
local 0/36: 16 strata. Both nominal strengths 16/40 cross eight input types:
nearest-profile unequal signal; combined-profile equal signal; combined-profile
unequal signal; equal combined signal plus interference; unequal combined signal
plus interference; matched interferer alone; displaced supported spike; ON-OFF.
This is 256 declared native input cases / 256 base detector executions / 768 paired
endpoints, with 160 signal-present and 96 pure-control inputs. A separate
uninjected execution has three endpoints. There are 32 inputs per type.

Equal active amplitudes are S. Unequal amplitudes use ratios [1,1/2] for two
active epochs and [1,3/4,1/2] for three, rotated left by stratum modulo active
count. Nominal S is not an output SNR. Each signal epoch is an explicit separate
component; all additions use existing native float32 component/filter semantics.
Combined profiles preserve U's coefficient offset, half-proxy-bin displacement,
one-native-channel smear and finite sinc-squared profile. Geometry <=20 Hz is
verified without scores before freeze; abort unsupported prescribed cases.

Interference has strength 4S in active[stratum modulo active count], displaced
12 proxy bins. The identical interference-only component and both exact
signal-only counterparts occur in the panel. The supported spike has S at
truth in that epoch and S/8 displaced six bins in the other active epochs.
ON-OFF uses equal nearest-bin strengths S in all declared active ON and OFF
epochs. Interference-only associations with the absent combined truth are
explicit false associations, never recoveries. Inputs are paired and correlated;
none adds independent telescope observations or full-bank coverage. Some pure-control
inputs can be numerically identical across activity labels. Report duplicate
native patch-payload inventories explicitly; do not call case counts independent
realizations.

## Predeclared development decision

Each alternative must satisfy every condition versus neighbor9 over the entire
panel: no lost signal-associated case; no increase in leaking-control count;
a strict reduction in leaking-control count; zero final members in every
ON-OFF and every supported-spike input; zero absent-truth associations in every
interferer-only input; and zero shared held-out pre-veto threshold exceedances.
The strict-reduction condition prevents a vacuous control success when the
reference has no leakage. Signal association retains exact activity and <=20 Hz
maximum center-track residual. Association is not proof of causal recovery.

Report all gains/losses, counts by morphology/strength/activity, exact loss
members, two- versus three-epoch outcomes, and conditional matched signal-only,
interferer-only and mixed outcomes. Do not tune the statistic or relax a failed
gate. Even a pass permits broader validation only, not general adoption.

Publish plan, implementation, tests and complete configuration before scoring.
Checkpoints bind public freeze, config, calibration and exact components;
restart only matching sealed cases. No partial panel gives a final verdict.
Publish all failures, logs and checksums. No new telescope requests are planned.
