"""Physical stages for distinct whole-cadence retention receipts.

Reuses pure alias/signature/partition arithmetic, never legacy certificate
validators. Wrappers compute their own upstream retention in the same call.
Fixtures and native sources remain separate; neither grants sky admission.
"""
from collections import defaultdict
import math
import json
import resource
import time
import numpy as np

from . import search_v0p6 as core
from . import alias_v0p6 as alias
from .adjacent_v0p6 import disposition_after_single_adjacent_off
from .detector_m43u import checked_vectors
from .empty_null_radio import canonical
from .receiver_v0p6 import _predicted_midpoint_hz
from .whole_cadence_reference_radio import Family, digest
from .whole_cadence_downstream_radio import execute_fixture, execute_native

RULES = {'off_tolerance_hz':20., 'adjacent_floor':5.5, 'receiver_half_width_hz':100.,
         'receiver_peak_floor':5.5, 'receiver_tolerance_hz':20., 'shared_epochs':2,
         'identity_tolerance_hz':20., 'neighbor9_unchanged':True}
CAPS = {'records':10000, 'alias_bucket_entries':10000, 'off_candidate_visits':5000000,
        'identity_track_comparisons':5000000, 'alias_candidate_visits':5000000,
        'canonical_bytes_per_stage':128000000}


class IncompletePhysical(ValueError):
    def __init__(self, reason, evidence):
        super().__init__(reason)
        # Preserve complete upstream retention and accumulated stage evidence.
        import json
        self.evidence = json.loads(canonical(evidence))


def stable(record):
    return (record['template_index'],record['spectral_width_index'],
        core.M37_ACTIVITY_SUBSETS.index(tuple(record['active_epochs_zero_based'])),
        record['proxy_carrier_index'],record['record_id'])


def numeric_view(record):
    """Aliases for pure numerical helpers; no certificate/ancestry relabelling."""
    return {**record, 'proxy_carrier_hz':record['carrier_hz'], 'snr':record['stack_snr']}


def exact_key(record):
    return (record['template_index'],record['proxy_carrier_index'],
        record['spectral_width_index'],tuple(record['active_epochs_zero_based']))


def _execute(family, store, retention, on_factors, off_factors, receiver_factory,
             provider_receipt, *, caps=None):
    caps={**CAPS, **(caps or {})}
    if set(caps)!=set(CAPS) or any(type(v) is not int or not 1<=v<=CAPS[k] for k,v in caps.items()):
        raise ValueError('Physical caps must be positive and cannot be enlarged')
    if retention.get('complete') is not True or digest({k:v for k,v in retention.items() if k!='result_sha256'})!=retention.get('result_sha256'):
        raise ValueError('Complete verified whole-cadence retention required')
    # Preserve the original receipt even if a callback mutates store provenance.
    retention=json.loads(canonical(retention))
    factors={}
    for kind, supplied in (('on',on_factors),('off',off_factors)):
        a=np.asarray(supplied)
        if a.dtype!=np.dtype('<f8') or a.shape!=(family.template_count,48) or not np.isfinite(a).all() or np.any(a<=0) or np.any(a>=2):
            raise ValueError('Explicit finite 48-midpoint factor matrix required')
        factors[kind]=np.frombuffer(a.tobytes(order='C'),dtype='<f8').reshape(a.shape)
    rows={k:[numeric_view(r) for r in retention['retained'][k]] for k in ('on','off')}
    result={'schema':'radio-whole-cadence-physical-v1','complete':False,
        'family_sha256':digest(family.record()),'rules':RULES,'caps':caps,
        'retention':retention,'factor_provider_receipt':provider_receipt,
        'factor_matrix_sha256s':{k:core.factor_table_sha256(v) for k,v in factors.items()},
        'matched_off':[], 'adjacent_off':[], 'receiver_alias':[], 'decisions':[], 'clusters':[],
        'legacy_certificates_issued':False,'scientific_candidate_selection_authorized':False,
        'telescope_admission_authorized':False}
    upstream_sha=retention['result_sha256']; expected_ids=dict(store.expected_ids)
    expected_provenance=digest(store.provenance)
    def validate_upstream():
        if (digest({k:v for k,v in retention.items() if k!='result_sha256'})!=upstream_sha
                or digest(store.provenance)!=expected_provenance or store.expected_ids!=expected_ids
                or set(store.arrays)!=set(expected_ids)):
            raise ValueError('Physical upstream identity changed during stage')
        for (kind,t,w),identity in expected_ids.items():
            checked_vectors(store,kind,t,w,family.grid,identity)
    stage='admission'; started=time.monotonic(); stage_bytes=defaultdict(lambda:2)
    def budget():
        if time.monotonic()-started>600: raise ValueError('Physical active-time capacity exceeded')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:
            raise ValueError('Physical RSS capacity exceeded')
    def append_stage(name, item):
        size=len(canonical(item))+(1 if result[name] else 0)
        if stage_bytes[name]+size>caps['canonical_bytes_per_stage']:
            result['first_capacity_crossing_evidence']={'stage':name,'item':item}
            raise ValueError('Canonical physical-stage byte capacity exceeded: '+name)
        result[name].append(item);stage_bytes[name]+=size;budget()
    def bounded(name, value):
        size=len(canonical(value))
        if size>caps['canonical_bytes_per_stage']:
            raise ValueError('Canonical physical-stage byte capacity exceeded: '+name)
        return size
    try:
        if any(len(rows[k])>caps['records'] for k in rows):raise ValueError('Physical record capacity exceeded')
        for kind in rows:
            if len({exact_key(r) for r in rows[kind]})!=len(rows[kind]):raise ValueError('Duplicate retained hypothesis')
        stage='matched_off'
        off_tracks={r['record_id']:np.float64(r['carrier_hz'])*factors['off'][r['template_index']] for r in rows['off']}
        exact={exact_key(r):r for r in rows['off']}
        ordered=sorted(rows['off'],key=lambda r:(float(off_tracks[r['record_id']][0]),stable(r)))
        anchors=np.array([off_tracks[r['record_id']][0] for r in ordered],dtype='<f8')
        visits=0;off_by_id={}
        for on in rows['on']:
            track=np.float64(on['carrier_hz'])*factors['off'][on['template_index']]
            scale=max(abs(float(track[0])),20.,1.);guard=4*float(np.spacing(np.float64(scale)))
            low=np.nextafter(track[0]-np.float64(20.)-guard,-np.inf)
            high=np.nextafter(track[0]+np.float64(20.)+guard,np.inf)
            matches=[]
            for off in ordered[int(np.searchsorted(anchors,low,'left')):int(np.searchsorted(anchors,high,'right'))]:
                visits+=1;result['off_candidate_visits']=visits
                result['current_off_query']={'record_id':on['record_id'],'partial_matches':matches}
                if visits>caps['off_candidate_visits']:raise ValueError('OFF candidate-visit capacity exceeded')
                distance=float(np.max(np.abs(track-off_tracks[off['record_id']])))
                if not math.isfinite(distance):raise ValueError('Nonfinite OFF track distance')
                if distance<=20.:matches.append({'record_id':off['record_id'],'maximum_track_distance_hz':distance})
            by_id={r['record_id']:r for r in rows['off']}
            matches.sort(key=lambda m:(-by_id[m['record_id']]['snr'],stable(by_id[m['record_id']])))
            same=exact.get(exact_key(on))
            disposition=('rfi_veto_matched_off_same_hypothesis' if same else
                'rfi_veto_local_off_track' if matches else 'pending_receiver_alias_evaluation')
            evidence={'record_id':on['record_id'],'same_hypothesis_witness_id':None if same is None else same['record_id'],
                'local_matches':matches,'matched_local_count':len(matches),
                'best_local_witness':matches[0] if matches else None,'disposition':disposition}
            append_stage('matched_off',evidence);off_by_id[on['record_id']]=evidence
        result.pop('current_off_query',None)
        result['off_candidate_visits']=visits;bounded(stage,result['matched_off'])
        stage='adjacent_off';adjacent_by_id={}
        for on in rows['on']:
            t=on['template_index'];w=on['spectral_width_channels'];q=on['proxy_carrier_index']
            values=checked_vectors(store,'off',t,w,family.grid)[:,family.grid.score_slice]
            measured=[{'epoch_zero_based':e,'snr':float(values[e,q]),'meets_floor':bool(values[e,q]>=5.5)}
                      for e in on['active_epochs_zero_based']]
            vetoed=any(m['meets_floor'] for m in measured)
            disposition=disposition_after_single_adjacent_off(off_by_id[on['record_id']]['disposition'],vetoed)
            evidence={'record_id':on['record_id'],'measurements':measured,'vetoed':vetoed,
                'exclusion_mask_applied':False,'same_template_carrier_width':True,'disposition':disposition}
            append_stage('adjacent_off',evidence);adjacent_by_id[on['record_id']]=evidence
        bounded(stage,result['adjacent_off'])
        stage='receiver_signatures'
        signatures,receipt=receiver_factory(json.loads(canonical(retention['retained']['on'])))
        if receipt.get('signatures_sha256')!=digest(signatures):raise ValueError('Receiver signature receipt changed')
        normalized,signature_sha=alias._validate_signatures(rows['on'],signatures,local_half_width_hz=100.)
        # This check is separate from the signature's own self-consistency:
        # every stated midpoint must come from this context's actual factors.
        for row in rows['on']:
            for sig in normalized[row['record_id']]:
                e=sig['epoch_zero_based']
                wanted=_predicted_midpoint_hz(row['carrier_hz'],factors['on'][row['template_index'],e*16:(e+1)*16])/1e6
                if sig['predicted_mid_mhz']!=wanted:raise ValueError('Receiver midpoint differs from bound factors')
        result['receiver_signatures']=signatures;result['receiver_receipt']=receipt
        result['normalized_signature_sha256']=signature_sha;bounded(stage,{'signatures':signatures,'receipt':receipt})
        stage='identity_partition'
        components,partition=alias._build_alias_identity_partition(rows['on'],factors['on'],20.,caps['identity_track_comparisons'])
        result['identity_partition']=partition;bounded(stage,partition)
        stage='receiver_alias'
        qualified={r['record_id']:{s['epoch_zero_based']:s for s in normalized[r['record_id']] if s['peak_snr']>=5.5} for r in rows['on']}
        buckets=defaultdict(list);entries=0
        ordered_on=sorted(rows['on'],key=stable);by_id={r['record_id']:r for r in ordered_on}
        for row in ordered_on:
            signature=qualified[row['record_id']];epochs=sorted(signature)
            for i,a in enumerate(epochs):
                for b in epochs[i+1:]:
                    cells=(math.floor(signature[a]['peak_frequency_mhz']*1e6/20.),math.floor(signature[b]['peak_frequency_mhz']*1e6/20.))
                    buckets[a,b,*cells].append(row['record_id']);entries+=1
                    if entries>caps['alias_bucket_entries']:raise ValueError('Alias bucket-entry capacity exceeded')
        result['alias_bucket_entries']=entries;visits=0
        for row in ordered_on:
            rid=row['record_id'];signature=qualified[rid];epochs=sorted(signature);candidates=set()
            for i,a in enumerate(epochs):
                for b in epochs[i+1:]:
                    x=math.floor(signature[a]['peak_frequency_mhz']*1e6/20.);y=math.floor(signature[b]['peak_frequency_mhz']*1e6/20.)
                    # Same two-cell floating-boundary guard as legacy matcher.
                    for dx in range(-2,3):
                        for dy in range(-2,3):candidates.update(buckets.get((a,b,x+dx,y+dy),()))
            candidates.discard(rid);visits+=len(candidates)
            if visits>caps['alias_candidate_visits']:raise ValueError('Alias candidate-visit capacity exceeded')
            component=components[row['template_index'],row['proxy_carrier_index']];matches=[]
            for candidate_id in sorted(candidates,key=lambda x:stable(by_id[x])):
                candidate=by_id[candidate_id];other=components[candidate['template_index'],candidate['proxy_carrier_index']]
                if component==other:continue
                shared=alias._literal_alias_matches(signature,qualified[candidate_id],tolerance_hz=20.)
                if len(shared)>=2:matches.append({'record_id':candidate_id,'component_sha256':other,'shared_epochs':shared})
            matches.sort(key=lambda m:(-by_id[m['record_id']]['snr'],stable(by_id[m['record_id']])))
            prior=adjacent_by_id[rid]['disposition']
            final='rfi_veto_receiver_frame_alias' if prior=='pending_receiver_alias_evaluation' and matches else prior
            evidence={'record_id':rid,'component_sha256':component,'matches':matches,
                'best_alias_witness':matches[0] if matches else None,'candidate_visits':len(candidates),
                'qualified_epochs':sorted(signature),'disposition':final}
            append_stage('receiver_alias',evidence)
            rank=row['rank'];physical=final=='pending_receiver_alias_evaluation'
            append_stage('decisions',{'record_id':rid,'physical_disposition':final,
                'passes_evaluated_physical_vetoes':physical,'inclusive_rank_p':rank['inclusive_p'],
                'meets_diagnostic_rank_cut':rank['meets_rank_cut'],
                'diagnostic_final':physical and rank['meets_rank_cut'],'scientific_candidate':False})
        result['alias_candidate_visits']=visits;bounded(stage,result['receiver_alias']);bounded('decisions',result['decisions'])
        stage='clusters';groups=defaultdict(list);decisions={r['record_id']:r for r in result['decisions']}
        for row in ordered_on:groups[components[row['template_index'],row['proxy_carrier_index']]].append(row['record_id'])
        for component,ids in sorted(groups.items()):
            append_stage('clusters',{'cluster_sha256':component,'member_ids':sorted(ids),'member_count':len(ids),
                'physical_survivor_ids':sorted(r for r in ids if decisions[r]['passes_evaluated_physical_vetoes']),
                'diagnostic_final_ids':sorted(r for r in ids if decisions[r]['diagnostic_final'])})
        member_ids=[rid for c in result['clusters'] for rid in c['member_ids']]
        expected={r['record_id'] for r in rows['on']}
        if len(member_ids)!=len(set(member_ids)) or set(member_ids)!=expected or set(decisions)!=expected:
            raise ValueError('Cluster/decision partition lost or duplicated retained members')
        bounded(stage,result['clusters'])
        validate_upstream();budget();result['stage_canonical_bytes']=dict(stage_bytes)
        result['complete']=True;result['result_sha256']=digest(result);return result
    except (ValueError,core.V0P6ContractError,core.V0P6CapacityError,core.V0P6IncompleteError) as error:
        result['failure']={'stage':stage,'reason':str(error)}
        raise IncompletePhysical(str(error),result) from error


def run_fixture(family,store,threshold,*,case_identity,noise_law_sha256,
                on_factors,off_factors,receiver_factory,caps=None):
    retention=execute_fixture(family,store,threshold,case_identity=case_identity,noise_law_sha256=noise_law_sha256)
    return _execute(family,store,retention,on_factors,off_factors,receiver_factory,
        {'domain':'deterministic-score-and-signature-fixtures','native_receiver_measured':False},caps=caps)


def run_native(run,store,threshold,*,case_identity,noise_law_sha256,caps=None):
    retention=execute_native(run,store,threshold,case_identity=case_identity,noise_law_sha256=noise_law_sha256)
    c=run.context;f=c.factor_contract
    family=Family(c.identity,f.factors.identity,len(c.bank),c.grid)
    def receiver(records):
        signatures,receipt=run.receiver(records,c.bank)
        if receipt['context_sha256']!=c.identity or receipt['source_ids']!=run.source_ids:
            raise ValueError('Native receiver source binding differs')
        return signatures,receipt
    return _execute(family,store,retention,f.matrix_for_kind('on'),f.matrix_for_kind('off'),receiver,
        {'domain':'synthetic-native','context_sha256':c.identity,'factor_contract_sha256':f.identity,
         'source_ids':run.source_ids,'native_receiver_measured':True},caps=caps)
