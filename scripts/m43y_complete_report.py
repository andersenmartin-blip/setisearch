"""Build the M43Y report and reproducible package manifest from sealed evidence."""
import json
from pathlib import Path
from m43y_response_diagnostic import ROOT,OUT,sha
from m43e_economical_bank import read_sealed

def main():
    r=read_sealed(OUT/'result.json');a=read_sealed(OUT/'artifact_validation.json')
    e=read_sealed(OUT/'survivor_response_evidence.json')
    assert a['passed'] and e['source_result_sha256']==r['result_sha256']
    assert sum(s['members'] for s in e['summary'])==34
    table='\n'.join(f"| {s['case_index']} | {s['members']} | {s['exact_OFF_max_range'][0]:.6f}–{s['exact_OFF_max_range'][1]:.6f} | {s['neighborhood_OFF_max_range'][0]:.6f}–{s['neighborhood_OFF_max_range'][1]:.6f} | {s['members_with_neighborhood_OFF_at_least_5p5']} |" for s in e['summary'])
    counts='\n'.join(f"| {s['name']} | {s['final_counts']['neighbor9']} | {s['final_counts']['epoch_confirmation']} | {s['final_counts']['remaining_aggregate']} |" for s in r['summary'])
    text=f'''# M43Y result: broad OFF response and background-supported interference

M43Y explains two distinct failure mechanisms in the exposed M43X controls.
All seven surviving ON-OFF members have same-width neighboring OFF responses
above 5.5 while their queried active-epoch OFF centers remain below 5.5.
The other 27 labeled outcomes are nine members repeated under three input labels:
a strong single-epoch injection combines with pre-existing broad ON structure
in another epoch. Their neighboring OFF responses stay below 5.5.
No detector is changed or adopted; the M43X qualification failures remain.

## Scope and exact reproduction

The [public freeze](https://github.com/andersenmartin-blip/setisearch/commit/{r['freeze_commit']})
preceded evaluation. The run completed 13 base executions and 39 paired post-cut
endpoints: six historical control inputs, one separate baseline, and six new
ON-only/OFF-only counterparts. All seven historical executions exactly reproduce
X audits, confirmation evidence and policy decisions. There are 11 distinct native
patch inventories including the empty baseline; 13/45/109 share one intervention.
The 34 labeled surviving-member outcomes represent 15 distinct hypothesis
coordinates. These are selected, correlated development diagnostics on one existing
observing sequence, not new independent signal realizations.

## Where the OFF checks fail

Each maximum below is over a member's actual active epochs. The neighborhood
uses its own width and includes both endpoints q +/- floor(width/2); the table
shows the range across members, not a confidence interval.

| Original case | Surviving members | Exact-coordinate OFF maximum | Neighborhood OFF maximum | Members with neighborhood OFF ≥5.5 |
|---|---:|---:|---:|---:|
{table}

All seven ON-OFF members survive in their ON-only counterparts and disappear
in OFF-only and uninjected inputs. The frozen component comparisons verify
identical ON responses with/without OFF, identical OFF responses with/without ON,
and exact background responses in the uninjected kind. This establishes the
stage behavior without confusing changed ON arithmetic with an OFF veto.

For case 47, template 2, q1290–1294, width129 and active epochs [0,2], the injected
point lies within all 16 ON row windows in each active epoch. In the second
active OFF epoch it lies within only 8,7,7,6,5 of 16 windows, respectively.
At q1290, ON scores are [5.792226,8.500895], paired OFF scores [4.810463,5.133028].
The independently reconstructed additions are approximately 3.521804 in both ON
epochs but only 1.760902 in that second OFF epoch: part of the native response
falls outside the displaced template's filter windows. The nearby OFF maximum
is 6.634779. This is actual partial filter overlap, not a native-cache error.

For cases 79/111, the common surviving hypothesis is template0, q1249, width65,
active epochs [1,2]. The q1280 injection is included in every ON and OFF row window.
It adds approximately 40/sqrt(65)=4.961389 in each active epoch. Background ON
scores [1.103099,3.134699] yield [6.064487,8.096088]; background OFF scores
[-0.419949,0.331663] yield [4.541440,5.293052]. Thus even complete response overlap
can leave the exact-coordinate OFF score below the floor because backgrounds
differ. The neighboring OFF maximum is 7.187113. Case111 additionally has an
OFF score of 6.334426 in epoch0, but that epoch is outside this member's active
subset and is correctly excluded by the existing rule.

The retained-OFF track checks also executed and found no match. Recomputed
nearest retained-OFF distances, using the existing maximum over all 48 OFF
integration positions, are 161.233–172.575 Hz for case47, 53.878 Hz for case79,
and 39.699 Hz for case111, all above the fixed 20 Hz tolerance. These distances
include OFF records of every retained width/activity/template; the local-track
matcher is not simply a same-width restriction. Exact-coordinate single-OFF
queries are unmasked, so mask suppression is not the reason those queries pass.
Receiver-alias evaluation ran for all 34 outcomes and found no rejecting match.
The inherited pending disposition is an evaluated no-match outcome, not evidence
that the alias calculation was omitted or that a celestial candidate exists.

## Why the remaining interference is different

Cases13/45/109 insert the same strength160 point at q1292 only in ON epoch0.
Their nine width129 members have active epochs [0,2]. The injected response adds
about 160/sqrt(129)=14.087215 to epoch0; epoch2 is unchanged from background and
already scores 5.530963–5.896018. Both confirmation rules therefore pass.
All these active masks are clear. No OFF component was inserted, no OFF member
was retained, and the maximum in every measured same-width OFF neighborhood is
below 3.874. Increasing the OFF search neighborhood to the already specified
width radius does not provide above-floor OFF evidence for these members.
This diagnoses background-supported single-epoch interference; it does not
identify the physical origin of that background structure or establish a
Gaussian-noise probability. The absent intended truth remains unassociated.

## Complete endpoint counts

These are final diagnostic member counts, not recovered astronomical signals.

| Input | Neighbor9 | Hard epoch confirmation | Remaining aggregate |
|---|---:|---:|---:|
{counts}

## Verification and reproducibility

All 96 original arrays and 48 native gathers match. The complete X calibration
summary, all 128 training maxima, threshold10 and binding replay exactly.
There are zero fresh null rows or new heldout claims. The 1,536 prior used shift
rows remain excluded from future fresh calibration. No new telescope requests
or observing coverage. Runtime: {r['wall_seconds']:.3f} seconds.

Three focused tests pass. The separate artifact audit verifies 285 frozen files,
13 sealed records, 12 component response invariants and 11,232 direct native
score comparisons across 18 fixed probes/input and all eight widths, six scans.
The comparison count includes repeated coordinates under different frozen
activity labels; it is an arithmetic check count, not independent evidence.
Full neighborhood arrays, masks/seeds, row indices/filter scores, retained-OFF
ledger, paired-OFF, receiver and rank evidence are preserved. Postprocessing
initially stopped on blank JSONL separator lines; that failure log is retained,
and the report reader now skips blank lines. No experiment, pinned runner or
scientific result changed, and no numerical run was repeated for this report fix.

Result seal: `{r['result_sha256']}`.
[Plan](MILESTONE_43Y_RESPONSE_DIAGNOSTIC_PLAN.md),
[result](results_m43y_response_diagnostic/result.json),
[full ledger](results_m43y_response_diagnostic/case_audits.jsonl.gz),
[member response evidence](results_m43y_response_diagnostic/survivor_response_evidence.json),
[audit](results_m43y_response_diagnostic/artifact_validation.json),
[run log](results_m43y_response_diagnostic/live_run.log),
[checksums](RESULTS_MANIFEST_M43Y_RESPONSE_DIAGNOSTIC.sha256).

## Next useful experiment

The measured OFF neighborhood is exactly the existing M43W width-window
geometry, which was not an M43X endpoint. Reuse that implementation and its
arithmetic evidence rather than inventing an equivalent new rule. A prospective
joint comparison should evaluate reference, OFF-window alone, remaining-aggregate
alone and their combination on additional carrier/template/activity/strength
combinations with pure interference and signal-present counterparts. Include
ON-only signals with unrelated OFF structure to measure the added false-veto
cost; declare matching tolerances and no-signal-loss gates before scoring.
Selected Y successes cannot qualify that rule or quantify completeness.

An OFF extension alone leaves the demonstrated background-supported interference
mechanism unresolved. Preserve this as a separate gate rather than presenting
seven OFF responses as a complete repair. Likewise the remaining-aggregate rule
still loses the three exposed two-epoch signal cases in X. Its two-epoch identity
with the hard rule is mathematical; do not lower 5.5 to fit those losses.
A broader panel is useful only if it tests these unresolved mechanisms and
sensitivity costs together. No astronomical candidate or general adoption follows.
'''
    (ROOT/'MILESTONE_43Y_RESPONSE_DIAGNOSTIC_RESULT.md').write_text(text)
    paths=['MILESTONE_43Y_RESPONSE_DIAGNOSTIC_PLAN.md','MILESTONE_43Y_RESPONSE_DIAGNOSTIC_RESULT.md',
        'M43Y_CONTINUATION.md','config/m43y_response_diagnostic.json','tests/test_m43y_response_diagnostic.py']
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts').glob('m43y_*.py'))]
    paths += [str(p.relative_to(ROOT)) for p in sorted(OUT.iterdir()) if p.is_file()]
    (ROOT/'RESULTS_MANIFEST_M43Y_RESPONSE_DIAGNOSTIC.sha256').write_text(''.join(sha(ROOT/p)+'  '+p+'\n' for p in sorted(paths)))
    print(json.dumps(dict(report_created=True,manifest_files=len(paths))))
if __name__=='__main__':main()
