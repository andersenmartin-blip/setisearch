"""Fixed truth association and recovery/RFI/null counting after all decisions.

Truth never enters retention, ranking or physical vetoes. Receipt integrity is
reproducibility evidence, not independent experimental or telescope authority.
"""
import numpy as np
from . import receiver_bank_radio as received
from .whole_cadence_reference_radio import Family, digest
from .pipeline_receiver_radio import Context
import json
import math


def evaluate(report, context, recipe, *, expected_case_identity, case_definition):
    if not isinstance(context,Context):raise ValueError('Actual receiver context required')
    context.validate()
    if (case_definition.get('identity')!=expected_case_identity
            or digest({k:v for k,v in case_definition.items() if k!='identity'})!=expected_case_identity
            or case_definition.get('recipe')!=recipe or case_definition.get('context_sha256')!=context.identity
            or case_definition.get('role')!='evaluation'):
        raise ValueError('Truth recipe/case binding differs')
    if (report.get('schema')!='radio-whole-cadence-physical-v1' or report.get('complete') is not True
            or report.get('result_sha256')!=digest({k:v for k,v in report.items() if k!='result_sha256'})):
        raise ValueError('Complete physical report with intact receipt required')
    family=Family(context.identity,context.factor_contract.factors.identity,len(context.bank),context.grid)
    if report['family_sha256']!=digest(family.record()):raise ValueError('Evaluation/physical context differs')
    retention=report['retention']
    if retention['case_identity']!=expected_case_identity:raise ValueError('Evaluation case differs')
    if (retention.get('complete') is not True or retention.get('result_sha256')!=digest({k:v for k,v in retention.items() if k!='result_sha256'})):
        raise ValueError('Retention receipt changed')
    kind=recipe['kind']
    if kind not in ('on_signal','matched_on_off','single_adjacent_off','noise_null'):raise ValueError('Fixed evaluation kind required')
    active=[] if kind=='noise_null' else recipe['activity_patterns'][kind]['on_epochs_zero_based']
    if any(type(e) is not int or e not in (0,1,2) for e in active) or len(set(active))!=len(active):
        raise ValueError('Invalid injected ON epochs')
    q=context.grid.center_mhz*1e6;rate=recipe['rate_label_hz_s']
    if isinstance(rate,bool) or not isinstance(rate,(int,float)) or not math.isfinite(rate):
        raise ValueError('Finite truth drift required')
    center=json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock=received.clock(json.loads(context.factor_contract.source_contract_bytes))
    truth=np.array([q*(1+rate*float(row[1])/center) for si in (0,2,4) for row in clock[si*16:(si+1)*16]])
    if not np.isfinite(truth).all():raise ValueError('Nonfinite truth track')
    factors=context.factor_contract.matrix_for_kind('on')
    rows=retention['retained']['on'];ids=[r['record_id'] for r in rows]
    decisions={d['record_id']:d for d in report['decisions']}
    if len(ids)!=len(set(ids)) or len(decisions)!=len(report['decisions']) or set(decisions)!=set(ids):
        raise ValueError('Decision inventory missing or duplicated')
    association=[]
    for row in rows:
        if row.get('record_id')!=digest({k:v for k,v in row.items() if k!='record_id'}):raise ValueError('Retained member changed')
        t=row['template_index'];wi=row['spectral_width_index'];qi=row['proxy_carrier_index'];epochs=row['active_epochs_zero_based']
        from . import search_v0p6 as core
        if (type(t) is not int or not 0<=t<len(context.bank) or type(qi) is not int or not 0<=qi<context.grid.score_bin_count
                or tuple(epochs) not in core.M37_ACTIVITY_SUBSETS or type(wi) is not int or not 0<=wi<len(core.M37_SPECTRAL_WIDTHS)
                or row['spectral_width_channels']!=core.M37_SPECTRAL_WIDTHS[wi]
                or row['carrier_hz']!=float(context.grid.score_hz[qi])):
            raise ValueError('Retained member geometry differs')
        decision=decisions[row['record_id']]
        final=decision['passes_evaluated_physical_vetoes'] and decision['meets_diagnostic_rank_cut']
        if decision['diagnostic_final']!=final or decision['scientific_candidate'] is not False:
            raise ValueError('Decision final/authority flag differs')
        indices=[e*16+i for e in epochs for i in range(16)]
        error=abs(row['carrier_hz']*factors[t,indices]-truth[indices])
        associated=bool(active and set(epochs).issubset(active) and np.all(error<=2*context.geometry.channel_width_hz))
        association.append({'record_id':row['record_id'],'final':bool(final),'associated':associated,
            'maximum_truth_track_error_hz':float(error.max()),'width':row['spectral_width_channels']})
    clusters=report['clusters'];members=[rid for c in clusters for rid in c['member_ids']]
    if len(members)!=len(set(members)) or set(members)!=set(ids):raise ValueError('Full cluster partition differs')
    finals=[x for x in association if x['final']];final_ids={x['record_id'] for x in finals}
    associated_ids={x['record_id'] for x in finals if x['associated']}
    clustered_final=[]
    for c in clusters:
        if c['member_count']!=len(c['member_ids']) or set(c['diagnostic_final_ids'])!={rid for rid in c['member_ids'] if decisions[rid]['diagnostic_final']}:
            raise ValueError('Cluster final partition differs')
        clustered_final.extend(c['diagnostic_final_ids'])
    if len(clustered_final)!=len(set(clustered_final)) or set(clustered_final)!=final_ids:raise ValueError('Final partition differs')
    final_clusters=[c for c in clusters if c['diagnostic_final_ids']]
    counts={'final_members':len(finals),'associated_final_members':len(associated_ids),
        'unassociated_final_members':len(final_ids-associated_ids),'final_clusters':len(final_clusters),
        'associated_final_clusters':sum(bool(set(c['diagnostic_final_ids'])&associated_ids) for c in final_clusters),
        'unassociated_final_clusters':sum(bool(set(c['diagnostic_final_ids'])&(final_ids-associated_ids)) for c in final_clusters)}
    broad={}
    for w in (65,129):
        bad={x['record_id'] for x in finals if not x['associated'] and x['width']==w}
        broad[str(w)]={'unassociated_final_members':len(bad),
            'unassociated_final_clusters':sum(bool(set(c['diagnostic_final_ids'])&bad) for c in final_clusters)}
    primary=counts['associated_final_members']>=1 and counts['associated_final_clusters']>=1 if kind=='on_signal' else not finals
    broad_pass=kind=='on_signal' or all(x['unassociated_final_members']==0 for x in broad.values())
    result={'schema':'radio-whole-cadence-evaluation-gates-v1','case_identity':expected_case_identity,
        'physical_report_sha256':report['result_sha256'],'context_sha256':context.identity,
        'recipe_sha256':digest(recipe),'kind':kind,'counts':counts,'association':association,
        'broad_width_counts':broad,'mixed_cluster_counts_can_overlap':True,'complete_partition':True,
        'recovery_or_zero_control_gate_pass':bool(primary),'broad_width_gate_pass':broad_pass,
        'gate_pass':bool(primary and broad_pass),'truth_used_only_after_decisions':True,
        'scientific_experiment_or_telescope_admission_authorized':False}
    result['result_sha256']=digest(result);return result
