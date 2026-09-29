#!/usr/bin/env python3
"""One metadata-only projection of the still-inactive 151-case storage design."""
import hashlib
import json
from pathlib import Path
import resource
import time
from radio_receiver_adapter_common import ROOT, context
from seti_repeater import whole_cadence_capacity_radio as capacity
from seti_repeater import whole_cadence_journal_radio as journal
from seti_repeater import whole_cadence_compact_radio as compact
from seti_repeater import whole_cadence_render_radio as renderer
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest


def main():
    start=time.monotonic()
    out=ROOT/'results_radio_journal_capacity_2026-09-29';out.mkdir(exist_ok=False)
    path='config/radio_whole_cadence_null_proposal_20260928.json'
    raw=(ROOT/path).read_bytes();proposal=json.loads(raw);budget=compact.phase_budget(raw)
    contexts={'calibration':context('calibration'),'evaluation':context('validation')}
    cases=[]
    for case in proposal['cases']:
        plan=renderer.prepare(contexts[case['role']],case,raw).record()
        cases.append({'case_identity':case['identity'],'plan_sha256':plan['plan_sha256'],
                      'context_sha256':case['context_sha256'],
                      'source_contract_sha256':case['source_contract_sha256'],
                      'noise_law_sha256':case['noise_law_sha256'],'role':case['role']})
    # Capacity-shape input only, not an execution manifest, allocation or ledger.
    manifest={'schema':journal.SCHEMA,'mode':'scientific','namespace':proposal['cases'][0]['namespace'].rsplit('/null/',1)[0],
              'execution_binding_sha256':digest('capacity-shape-only-no-executable-freeze'),
              'allocation_sha256':digest('capacity-shape-only-no-allocation'),
              'cases':cases,'caps':dict(journal.CAPS),'required_artifacts':list(compact.ARTIFACTS)}
    reservations=[{'case_identity':r['case_identity'],'milliseconds':r['reserved_milliseconds'],
                   'artifact_bytes':r['reserved_artifact_bytes']} for r in budget['cases']]
    projection=capacity.project(manifest,reservations)
    # Reconcile the previously published two-case archive using its actual
    # immutable files. This is byte accounting, not a new numerical run.
    base=ROOT/'results_radio_gaussian_engineering_2026-09-29/live01/journal'
    sizes=[p.stat().st_size for p in (base/'revisions').iterdir() if p.is_file()]
    snapshot=journal.DirectoryStore(base).read()
    actual_reservations=[{'case_identity':c['binding']['case_identity'],
                          'milliseconds':c['milliseconds'],'artifact_bytes':c['artifact_bytes']}
                         for c in journal.replay(snapshot.document)['cases']]
    observed_lower=capacity.project(snapshot.document['manifest'],actual_reservations)
    if sum(sizes)<observed_lower['all_revisions_lower_bound_bytes']:
        raise ValueError('Actual archive is below claimed lower bound')
    result={'schema':'radio-journal-history-capacity-study-v1',
            'status':'CURRENT_FULL_SNAPSHOT_DESIGN_EXCEEDS_8_MIB_LEDGER_ALLOCATION',
            'proposal_sha256':hashlib.sha256(raw).hexdigest(),
            'phase_budget_sha256':budget['budget_sha256'],'projection':projection,
            'scope':'lower bound for complete immutable canonical full-snapshot history',
            'minimum_artifact_names':list(compact.ARTIFACTS),
            'physical_gate_artifacts_omitted_for_lower_bound':True,
            'raw_artifact_byte_sizes_assumed_zero_in_receipts':True,
            'physical_artifact_reservations_unchanged':True,
            'total_reserved_bytes_with_history_lower_bound':projection['artifact_reservations_bytes']
                +projection['all_revisions_lower_bound_bytes']+compact.OVERHEAD['failure_and_summary_bytes'],
            'original_total_evidence_cap_bytes':1024**3,
            'actual_stage_a_history':{'revision_count':len(sizes),'all_revision_bytes':sum(sizes),
                                    'latest_revision_bytes':max(sizes),'lower_bound':observed_lower},
            'no_packed_git_storage_measurement':True,'future_delta_or_compression_design_not_qualified':True,
            'scientific_proposal_status':'PROPOSED_NOT_ACTIVATED','new_cases_consumed':0,
            'new_gaussian_values':0,'new_telescope_values':0,'old_ledgers_changed':False,
            'elapsed_seconds':time.monotonic()-start,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    if projection['status']!='BLOCKED_LOWER_BOUND_EXCEEDS_LEDGER_RESERVE':
        raise ValueError('Report claim must follow the actual projection')
    (out/'result.json').write_bytes(canonical(result))
    (out/'projection_inputs.json').write_bytes(canonical({'mode':'CAPACITY_SHAPES_ONLY_NOT_AN_EXECUTION_MANIFEST',
                    'manifest_shape':manifest,'reservation_shapes':reservations,
                    'scientific_allocation_charged':False,'execution_authorized':False}))
    print(json.dumps({k:v for k,v in result.items() if k not in ('projection','actual_stage_a_history')},indent=2))
    print(json.dumps({k:v for k,v in projection.items() if k!='cases'},indent=2))


if __name__=='__main__':main()
