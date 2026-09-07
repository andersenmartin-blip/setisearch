# M43W: prospective OFF-window and active-epoch confirmation

Completed **192 native inputs, 192 shared base detector executions and 768
paired policy endpoints**. One uninjected execution/four endpoints is separate.
The protocol, code, complete panel and gates were public before scoring.
No candidate or general adoption is claimed.

**All three alternatives fail the predeclared development gate.** Active-epoch
confirmation removes all 18 leaking-control cases and all 3 absent-truth
associations, but loses two of the reference's 80 signal-associated cases.
The same-width OFF-window addition changes no final member set in this panel.
It also leaves the three false associations, so it fails its own gate.

## Complete prospective comparison

| Endpoint | Signal cases associated /96 | Leaking controls /96 | ON-OFF leaks /32 | Interferer-only false associations /32 | Development gate |
|---|---:|---:|---:|---:|---|
| neighbor9 | 80 | 18 | 0 | 3 | reference |
| off_window | 80 | 18 | 0 | 3 | False |
| epoch_confirmation | 78 | 0 | 0 | 0 | False |
| combined | 78 | 0 | 0 | 0 | False |

Signal associations use the unchanged exact activity subset and <=20 Hz
maximum center-track residual. They are not proof of causal signal recovery;
the interferer-only controls explicitly measure absent-truth confusion.
Controls count cases with any final member; member multiplicity is reported
separately in the complete result. Nonincrease of control leakage is automatic
for these additive predicates, so that condition cannot establish success alone.

## Strength and morphology

Rows nearest/combined/mixed count signal associations. Interferer-only rows
count false associations with the absent combined truth. Supported-spike and
ON-OFF rows count cases with any final diagnostic survivor. Every entry has
16 inputs at the listed strength.

| Strength / input | Neighbor9 | OFF window | Epoch confirmation | Combined |
|---|---:|---:|---:|---:|
| 12 / nearest | 16/16 | 16/16 | 16/16 | 16/16 |
| 12 / combined | 8/16 | 8/16 | 7/16 | 7/16 |
| 12 / mixed | 8/16 | 8/16 | 7/16 | 7/16 |
| 12 / interferer-only | 0/16 | 0/16 | 0/16 | 0/16 |
| 12 / supported-spike | 0/16 | 0/16 | 0/16 | 0/16 |
| 12 / ON-OFF | 0/16 | 0/16 | 0/16 | 0/16 |
| 32 / nearest | 16/16 | 16/16 | 16/16 | 16/16 |
| 32 / combined | 16/16 | 16/16 | 16/16 | 16/16 |
| 32 / mixed | 16/16 | 16/16 | 16/16 | 16/16 |
| 32 / interferer-only | 3/16 | 3/16 | 0/16 | 0/16 |
| 32 / supported-spike | 3/16 | 3/16 | 0/16 | 0/16 |
| 32 / ON-OFF | 0/16 | 0/16 | 0/16 | 0/16 |

Each of the 16 strata crosses two new carrier centers 768/3328, all four activity
subsets and two anchor templates. Strengths 12/32 are nominal native injection
strengths, not measured output SNRs. Mixed inputs add a single-epoch component
with four times the signal strength, 12 proxy bins away. Signal-only and that
exact interferer-only input are both present. Supported spikes add strength S/8
six bins away in other active epochs; ON/OFF components have equal strength S.

## What changes and what is shared

All endpoints start from the unchanged neighbor9 mask and complete detector
path. OFF-window adds a >=5.5 veto over the same-width paired-OFF proxy-bin
neighborhood of radius `width//2`, using full support without clipping/wrapping.
Epoch confirmation requires >=5.5 in every declared active ON epoch. Combined
applies both. Predicates run after the existing retention and physical/alias
stages; upstream alias witness sets are shared, not recomputed after rejection.

No alternative lowers the score threshold or introduces new retained members.
The four endpoints are computed from one base execution per input and are
paired, not independent runs or noise realizations. Alternative final sets
are exact subsets of the reference. The stronger active requirement can reject
faint or uneven signals; its measured cost must remain visible.

## Frozen development conditions

### combined

Signal loss cases: [73, 74]. Removed leaking-control cases: [9, 21, 33, 45, 57, 81, 93, 105, 117, 129, 141, 142, 153, 165, 177, 178, 189, 190].

- no_increased_leaking_control_count: **True**.
- no_signal_case_loss: **False**.
- zero_ON_OFF_final_members: **True**.
- zero_interferer_only_false_associations: **True**.
- zero_shared_heldout_pre_veto_exceedances: **True**.
### epoch_confirmation

Signal loss cases: [73, 74]. Removed leaking-control cases: [9, 21, 33, 45, 57, 81, 93, 105, 117, 129, 141, 142, 153, 165, 177, 178, 189, 190].

- no_increased_leaking_control_count: **True**.
- no_signal_case_loss: **False**.
- zero_ON_OFF_final_members: **True**.
- zero_interferer_only_false_associations: **True**.
- zero_shared_heldout_pre_veto_exceedances: **True**.
### off_window

Signal loss cases: []. Removed leaking-control cases: [].

- no_increased_leaking_control_count: **True**.
- no_signal_case_loss: **True**.
- zero_ON_OFF_final_members: **True**.
- zero_interferer_only_false_associations: **False**.
- zero_shared_heldout_pre_veto_exceedances: **True**.

A failed condition is not relaxed after evaluation. A passing development
panel would still require broader and independent validation. Earlier M43U/V
counts and failures remain unchanged; exposed V cases 35/44/61/69 are not part
of this panel.

Every lost signal case has a [member-level rejection record](results_m43w_confirmation/signal_loss_evidence.json),
including its per-epoch scores, OFF-window measurements and exact new reasons.
This preserves the distinction between total signal strength and the weakest
declared active epoch. No threshold is adjusted to remove these failures.

Cases 73 and 74 represent the SAME strength 12 combined-profile truth, with and
without its stronger neighboring component: carrier 768, anchor 0, all three
epochs active. They are two paired input cases, not two independent signal
realizations. Both have two associated width 3 members at carriers 768/769,
with combined scores 10.694390/11.062478. Their minimum active-epoch scores are
5.393839/5.422268, below 5.5. The loss is therefore caused by the new absolute
per-epoch floor despite adequate total score; the OFF addition is not its cause.

The final member sets of OFF-window and reference are identical, as are those
of combined and epoch-confirmation. All 32 ON-OFF cases already have zero final
members under the reference, so this panel provides no comparative repair
evidence for the old ON-OFF failure. Its absence at the new locations does not
erase the exposed M43V failure or establish that OFF rejection is generally sound.

## Next step

The next useful candidate is confirmation from the aggregate of the remaining
active epochs after removing the strongest epoch, rather than an absolute
floor on each one. That targets domination by one observation while potentially
retaining distributed weak evidence. This is a proposed endpoint, not a tested
repair. It must be explicitly defined and publicly frozen before evaluation,
including its threshold, fresh null rows and complete decision conditions.

Use new carrier/activity combinations and unequal active-epoch strengths,
with matched signal-only, interferer-only and mixed inputs. Retain false truth
associations and signal-case losses as separate gates. Keep cases 73/74 and the
earlier V failures as exposed development examples. Any further OFF proposal
must address width/response information explicitly and preserve its false-veto
cost; merely reducing the 5.5 floor to fit these exposed values is not qualified.

## Calibration, validation and scope

The 128 new training shifts have maximum 8.407228; the
shared operational threshold is 10.000000. The separate 128 held-out shifts have
maximum 8.335863, with 0/128
at or above threshold. All 256 new rows exclude 1,024 prior R/T/U rows.

This certificate uses the conservative >=3 pre-veto global maxima for all
four endpoints. Because the added cuts only reject, no lower threshold is
claimed. Masks are estimated on baseline full support, cropped and co-rolled;
they are not regenerated after scrambling. Shared pre-veto held-out evidence
does not measure OFF false-rejection rates or an independent physical FAP.

All 96 original arrays and 48 native ON/OFF gathers reproduce. Before calibration,
4,440 new OFF-window maxima at fixed real-data positions across all 37 templates,
eight widths and three epochs match scalar references, including score edges.
Four focused tests pass. Unchanged detector numerical evidence is reused.
Artifact validation verifies 263 pinned files, 192 sealed
inputs, 768 endpoints, 11,267 reference members and 45,068
policy decisions, recomputed associations and every development condition.
Runtime: 1216.4 seconds; new telescope requests: 0.

This is the same 37-template, 4,097-carrier pilot in one observing sequence.
It adds injection combinations, not observing coverage, full-bank completeness,
arbitrary variability sensitivity or population constraints. The two signal
profiles and two strengths do not qualify all astrophysical signal classes.

- Public freeze: `8c27879ff6fac0e78812bb9b0bb79a98f5cf376f`.
- Result seal: `5436338277dff4130ec878330289d4e67afee76ddb5b9d61627bffc06d4aece5`.
- Ledger SHA-256: `ce6d892addccf9fbc87b40dc496aa8acc8696f3ca3d2bd6be875834dda7cf2b4`.
- [Plan](MILESTONE_43W_CONFIRMATION_PLAN.md), [complete result](results_m43w_confirmation/result.json),
  [ledger](results_m43w_confirmation/case_audits.jsonl.gz),
  [validation](results_m43w_confirmation/artifact_validation.json),
  [run log](results_m43w_confirmation/live_run.log), and
  [manifest](RESULTS_MANIFEST_M43W_CONFIRMATION.sha256).
