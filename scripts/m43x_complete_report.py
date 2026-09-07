"""Add readable, explicitly retrospective interpretation after verified M43X audit."""
import json
from pathlib import Path
from m43e_economical_bank import read_sealed
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43x_confirmation'

def main():
    r=read_sealed(OUT/'result.json');d=read_sealed(OUT/'interpretation.json')
    assert d['source_result']==r['result_sha256']
    cfg=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    a,b=(cfg['cases'][i] for i in (226,228))
    assert a['reference_truth']==b['reference_truth'] and b['components'][:-1]==a['components']
    assert d['aggregate_restored_signal_cases_vs_hard']==[226,228]
    report=ROOT/'MILESTONE_43X_CONFIRMATION_RESULT.md';s=report.read_text()
    summary='''**The aggregate rule improves on the hard per-epoch rule but fails qualification.**
It preserves 134/160 signal associations versus 132/160 for the hard rule and
137/160 for neighbor9. Both additions reduce leaking pure-control cases from
28/96 to 6/96, but all three ON-OFF leakage cases remain. Neither alternative
passes the unchanged no-signal-loss and zero-ON-OFF-leak requirements.

'''
    needle='The new rule excludes';s=s.replace(needle,summary+needle,1)
    sections='''## What the improvement and remaining failures mean

The gain is confined to the three-active-epoch signal cases. The new rule
preserves all 35 of the reference's associations in those 40 cases, compared
with 33 for the hard rule. For two-active-epoch signals both alternatives
retain 99/120, down from 102/120 for neighbor9. This split follows injection
truth activity; unrelated retained hypotheses can have other activity subsets.

The two restored cases, 226/228, are the same strength-16 unequal combined
signal at carrier 2816, anchor 0, without/with its matched interfering component.
They are two paired cases, not two independent successful signal realizations.
For example, their width-3 member at carrier 2816 has active scores
4.751085, 9.539946 and 7.864453. Excluding the largest leaves aggregate score
8.920533, above 5.5, although the weakest epoch fails the hard 5.5 floor.
All five previously lost associated members in each case pass the aggregate rule.

The aggregate rule still loses cases 2, 132 and 180, all with two active truth
epochs and unequal strength-16 signals. Cases 132/180 are mixed-input associations
that their matched signal-only inputs do not reproduce. Their loss remains a
predeclared gate failure; association alone does not prove causal signal recovery.
No criterion is relaxed to discount these cases after seeing their outcomes.

The six leaking pure-control cases under both additions are interferer-only
13/45/109 and ON-OFF 47/79/111. The first three share the same native patch
inventory; the denominator remains declared input cases, not independent
realizations. Their retained members use width 129. ON-OFF case 47 has five
width-129 members; cases 79/111 each have the same width-65 hypothesis. All these
surviving members use two active epochs. The observations of broad filters
justify examining width/response handling next, but this extraction did not
reconstruct their OFF scores and does not establish the exact OFF-veto cause.

The interferer-only survivors are not associated with the absent reference
truth, so zero false truth associations does not mean zero interference leakage.
Moreover the reference already has zero such associations in this panel;
this is not evidence of a comparative false-association repair here.
All three methods retain the same original physical and receiver/alias stages.
The inherited label `pending_receiver_alias_evaluation` can persist after no
rejecting alias is found; it does not mean that evaluation was skipped.

See [the full interpretation](results_m43x_confirmation/interpretation.json),
[matched component outcomes](results_m43x_confirmation/matched_components.json),
and [surviving control member evidence](results_m43x_confirmation/control_survivor_evidence.json).

## Audit correction and publication history

The prospective v1 audit failed its overly broad whole-case activity assertion;
[its actual failure log is preserved](results_m43x_confirmation/artifact_validation_v1.log).
The [public audit amendment](MILESTONE_43X_AUDIT_AMENDMENT.md) corrects the check
to each member's actual activity subset. The v2 audit passes, including all
273 original pins, every seal and association, all 73,227 policy decisions,
subset relations and the unmodified development gates. The original four
focused tests and one new audit regression test pass. No detector, threshold,
input or scientific decision was changed, and no trial was rerun under altered
rules. The initial prepublication approval block was resolved by the user's
explicit ongoing approval in this conversation; the historical pending note
and intermediate 96-case checkpoint remain available.

## Next useful work

M43Y should first reconstruct the surviving broad-filter control cases with
exact baseline and single-component counterparts, and inspect native ON/OFF
response across coordinate and width. Any replay of exposed cases is a
retrospective diagnostic, not independent validation. Preserve the M43X failure.
The two-epoch sensitivity cost also needs an explicit operating decision or
a separately named endpoint; an epoch-aggregation rule cannot change the
mathematical two-epoch identity. Do not lower 5.5 simply to recover these losses.

Before evaluating any new response-aware OFF rule, publish its complete
semantics and prospective controls, including its false-veto cost on distributed
and unequal signals. Exclude all 1,536 earlier R/T/U/W/X shift rows from future
fresh null inventories. No general adoption, new observing coverage, independent
physical false-alarm probability, or astronomical candidate follows from M43X.

'''
    s=s.replace('## Calibration and verification',sections+'## Calibration and verification',1)
    report.write_text(s)

if __name__=='__main__':main()
