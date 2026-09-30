"""Fresh native-v2 render, threshold, physical and evaluation stages.

The old native engineering namespace remains closed.  This module binds the
fresh v2 plans to their own receipts and to the compressed v2 physical writer.
It does not allocate a case, construct a lease or grant execution authority.
"""
from dataclasses import dataclass
import json
import numpy as np

from . import gaussian_engineering_radio as gaussian
from . import native_v2_parent_radio as parent
from . import whole_cadence_journal_radio as journal
from . import whole_cadence_physical_radio as physical
from . import physical_evidence_v2_radio as v2_evidence
from . import receiver_bank_radio as received
from .empty_null_radio import canonical,Maximum,maximum
from .whole_cadence_reference_radio import Family,CadenceMaximum,digest


START_SCHEMA='radio-native-v2-engineering-start-v1'
THRESHOLD_SCHEMA='radio-native-v2-four-reference-threshold-v1'
GATE_SCHEMA='radio-native-v2-engineering-gate-v1'


def family(context):
    return Family(context.identity,context.factor_contract.factors.identity,
        len(context.bank),context.grid)


def render(context,plan,*,lease,forbidden_cases,verify_freeze):
    """Enter the fresh renderer only after its durable start artifact."""
    parent.validate_plan(context,plan,forbidden_cases)
    if type(lease) is not journal.Lease:
        raise ValueError('Fresh native-v2 engineering lease required')
    if (lease.manifest['mode']!='engineering'
            or lease.manifest['namespace']!=parent.NAMESPACE
            or lease.case['binding']!=parent.case_binding(plan)
            or tuple(lease.manifest['required_artifacts'])!=parent.REQUIRED_ARTIFACTS):
        raise ValueError('Native-v2 lease domain or binding differs')
    lease.budget();verify_freeze(lease.manifest)
    marker={'schema':START_SCHEMA,'case_identity':plan['case']['identity'],
        'plan_sha256':plan['plan_sha256'],'manifest_sha256':lease.manifest_sha,
        'nonce':lease.case['nonce'],'consumption_event_sha256':lease.case['consumption_event_sha256'],
        'scientific_allocation_charged':False,'restart_authorized':False}
    lease.write_artifact('rng_start.json',canonical(marker))
    def factory(entropy):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
    return gaussian._rows(context,plan,factory,lease.budget,marker,
        receipt_schema='radio-native-v2-gaussian-receipt-v1')


def _threshold_record(context,records):
    f=family(context);expected=[parent.make_plan(context,i)['case']['identity'] for i in range(4)]
    if len(records)!=4:raise ValueError('Exactly four fresh v2 reference receipts required')
    checked=[]
    for raw,identity in zip(records,expected,strict=True):
        record=CadenceMaximum(canonical(raw)).record()
        hypotheses=len(context.bank)*len(f.record()['widths'])*len(f.record()['activity_subsets'])
        if (record['case_identity']!=identity or record['family']!=f.record()
                or record['family_sha256']!=digest(f.record())
                or record['noise_law_sha256']!=parent.LAW_SHA
                or record['domain']!='synthetic-native'
                or record['all_hypotheses_evaluated'] is not True
                or record['score_shift_resampling'] is not False
                or record['visited_hypotheses']!=hypotheses
                or record['scored_cells']!=hypotheses*context.grid.score_bin_count
                or not 0<=record['eligible_cells']<=record['scored_cells']
                or (record['maximum']['kind']=='empty')!=(record['eligible_cells']==0)):
            raise ValueError('Fresh v2 reference source/order/law/completeness differs')
        checked.append(record)
    maxima=[Maximum.from_record(record['maximum']) for record in checked]
    value={'schema':THRESHOLD_SCHEMA,'status':'UNCALIBRATED_ENGINEERING_ONLY',
        'reference_records':checked,
        'reference_bundle':{'ordered_maxima':[item.record() for item in maxima],
            'ordered_case_identities':expected,'reference_count':4},
        'destination_family':f.record(),'noise_law_sha256':parent.LAW_SHA,
        'operational_threshold':maximum((Maximum('finite',10.),*maxima)).value,
        'reference_denominator':5,'minimum_possible_rank_p':0.2,
        'rank_ceiling':[1,100],'calibrated_1_percent_test':False,
        'production_threshold':False,'scientific_candidate_selection_authorized':False,
        'telescope_admission_authorized':False}
    value['threshold_receipt_sha256']=digest(value)
    return value


@dataclass(frozen=True)
class EngineeringThreshold:
    payload:bytes
    context:object

    def record(self):
        value=json.loads(self.payload)
        if canonical(value)!=self.payload or value!=_threshold_record(self.context,value['reference_records']):
            raise ValueError('Fresh v2 threshold semantics changed')
        return value

    def validate(self,candidate_family,*,case_identity,noise_law_sha256,domain):
        value=self.record()
        expected={parent.make_plan(self.context,i)['case']['identity'] for i in range(4,8)}
        if (candidate_family.record()!=value['destination_family'] or case_identity not in expected
                or noise_law_sha256!=parent.LAW_SHA or domain!='synthetic-native'):
            raise ValueError('Fresh v2 observation family/law/domain/case differs')
        return value


def bind_threshold(context,units):
    return EngineeringThreshold(canonical(_threshold_record(context,[unit.record() for unit in units])),context)


def run_physical(run,store,threshold,plan,*,evidence):
    """Run physical decisions while v2 saves every stage boundary."""
    parent.validate_plan(run.context,plan,[])
    if type(threshold) is not EngineeringThreshold or plan['case']['spec']['reference']:
        raise ValueError('Distinct fresh v2 evaluation threshold required')
    if (type(evidence) is not v2_evidence.Writer
            or evidence.config!=parent.physical_config(parent.case_binding(plan))
            or evidence.closed or evidence.poisoned):
        raise ValueError('Exact fresh compressed physical evidence writer required')
    return physical.run_native(run,store,threshold,
        case_identity=plan['case']['identity'],noise_law_sha256=parent.LAW_SHA,
        evidence=evidence)


def evaluate(report,context,plan):
    """Associate truth only after immutable physical decisions; never a 1% gate."""
    parent.validate_plan(context,plan,[])
    if (plan['case']['spec']['reference'] or report.get('complete') is not True
            or report['result_sha256']!=digest({k:v for k,v in report.items() if k!='result_sha256'})
            or report['retention']['case_identity']!=plan['case']['identity']
            or report['family_sha256']!=digest(family(context).record())
            or report['factor_provider_receipt']['domain']!='synthetic-native'):
        raise ValueError('Complete matching fresh v2 physical report required')
    rows=report['retention']['retained']['on'];decisions=report['decisions']
    by_id={item['record_id']:item for item in decisions}
    if len(by_id)!=len(decisions) or set(by_id)!={row['record_id'] for row in rows}:
        raise ValueError('Complete unique fresh v2 decision inventory required')
    spec=plan['case']['spec'];q=context.grid.center_mhz*1e6
    center=json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock=received.clock(json.loads(context.factor_contract.source_contract_bytes))
    truth=np.array([q*(1+spec['rate_label_hz_s']*float(t[1])/center)
        for scan_index in (0,2,4) for t in clock[scan_index*16:(scan_index+1)*16]])
    factors=context.factor_contract.matrix_for_kind('on');association=[]
    for row in rows:
        if digest({k:v for k,v in row.items() if k!='record_id'})!=row['record_id']:
            raise ValueError('Fresh v2 retained member changed')
        decision=by_id[row['record_id']]
        if decision['diagnostic_final'] or decision['meets_diagnostic_rank_cut'] or decision['scientific_candidate']:
            raise ValueError('Four references cannot pass the unchanged 1/100 rank cut')
        indices=[epoch*16+i for epoch in row['active_epochs_zero_based'] for i in range(16)]
        error=abs(row['carrier_hz']*factors[row['template_index'],indices]-truth[indices])
        associated=bool(spec['on_epochs']
            and set(row['active_epochs_zero_based']).issubset(spec['on_epochs'])
            and np.all(error<=2*context.geometry.channel_width_hz))
        association.append({'record_id':row['record_id'],
            'engineering_survivor':decision['passes_evaluated_physical_vetoes'],
            'associated':associated,'maximum_truth_track_error_hz':float(error.max()),
            'width':row['spectral_width_channels']})
    survivors={item['record_id'] for item in association if item['engineering_survivor']}
    associated={item['record_id'] for item in association
        if item['engineering_survivor'] and item['associated']}
    members=[record_id for cluster in report['clusters'] for record_id in cluster['member_ids']]
    if len(members)!=len(set(members)) or set(members)!=set(by_id):
        raise ValueError('Complete fresh v2 physical cluster partition required')
    counts={'physical_survivors':len(survivors),
        'associated_physical_survivors':len(associated),
        'unassociated_physical_survivors':len(survivors-associated),
        'physical_survivor_clusters':sum(bool(survivors.intersection(cluster['member_ids']))
            for cluster in report['clusters'])}
    gate=bool(associated) if spec['kind']=='on_signal' else not survivors
    result={'schema':GATE_SCHEMA,'case_identity':plan['case']['identity'],
        'physical_report_sha256':report['result_sha256'],'kind':spec['kind'],
        'counts':counts,'association':association,'engineering_gate_pass':gate,
        'broad_unassociated_survivors':{str(width):sum(item['engineering_survivor']
            and not item['associated'] and item['width']==width for item in association)
            for width in (65,129)},
        'truth_used_only_after_decisions':True,'calibrated_rank_gate_pass':False,
        'production_recovery_rfi_null_qualification':False,'scientific_candidate':False}
    result['result_sha256']=digest(result)
    return result
