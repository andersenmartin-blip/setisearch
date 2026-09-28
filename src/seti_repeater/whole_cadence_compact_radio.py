"""Compact score/receipt audit, explicitly without reconstructing native data.

Independent artifact hashes and actual metadata contexts are required. Native
source and cache identities remain historical provenance; only retained score
bytes and their score-derived statistics are revalidated here. No RNG, cache
construction, NativeRun or detector-performance experiment is performed.
"""
from dataclasses import asdict
import hashlib
import json
import numpy as np
from . import transfer_m43g as native
from . import search_v0p6 as core
from .empty_null_radio import canonical
from .injection_m43r import ScoreStore
from .whole_cadence_reference_radio import Family,CadenceMaximum,digest,_reduce,_sha
from .whole_cadence_archive_radio import decode_npz
from .whole_cadence_render_radio import PROPOSAL_SHA256

ARTIFACTS=('sources.json','scores.json','scores.npz','maximum.json','renderer.json')
MIB=1024**2
PHASES={'calibration':{'count':127,'milliseconds_per_case':40000,'bytes_per_case':4*MIB},
        'evaluation':{'count':24,'milliseconds_per_case':80000,'bytes_per_case':18*MIB}}
OVERHEAD={'milliseconds':200000,'ledger_bytes':8*MIB,'failure_and_summary_bytes':76*MIB}


def phase_budget(proposal_bytes):
    if hashlib.sha256(proposal_bytes).hexdigest()!=PROPOSAL_SHA256:raise ValueError('Exact immutable proposal required')
    p=json.loads(proposal_bytes)
    entries=[]
    if [c['role'] for c in p['cases']]!=['calibration']*127+['evaluation']*24:
        raise ValueError('Ordered 127/24 proposal required')
    for c in p['cases']:
        phase=PHASES[c['role']]
        entries.append({'case_identity':c['identity'],'role':c['role'],
            'reserved_milliseconds':phase['milliseconds_per_case'],'reserved_artifact_bytes':phase['bytes_per_case']})
    r={'schema':'radio-whole-cadence-phase-budget-v1','status':'PROPOSED_NOT_ACTIVATED',
        'proposal_sha256':PROPOSAL_SHA256,'cases':entries,
        'phases':json.loads(canonical(PHASES)),'overhead':json.loads(canonical(OVERHEAD)),
        'total_milliseconds':sum(e['reserved_milliseconds'] for e in entries)+OVERHEAD['milliseconds'],
        'total_evidence_bytes':sum(e['reserved_artifact_bytes'] for e in entries)+OVERHEAD['ledger_bytes']+OVERHEAD['failure_and_summary_bytes'],
        'new_scientific_allocation_charged':False,'refund_or_retry_allowed':False,
        'integration_with_external_scientific_adapter_qualified':False}
    if r['total_milliseconds']!=7200000 or r['total_evidence_bytes']!=1024**3:
        raise ValueError('Prospective phase ceilings changed')
    r['budget_sha256']=digest(r);return r


def reservation(proposal_bytes,budget,case_identity):
    if budget!=phase_budget(proposal_bytes):raise ValueError('Published phase budget differs')
    rows=[x for x in budget['cases'] if x['case_identity']==case_identity]
    if len(rows)!=1:raise ValueError('Case absent from bounded phase inventory')
    return dict(rows[0])


def audit(context,binding,parts,*,expected_sha256s,byte_cap):
    context.validate()
    if set(parts)!=set(ARTIFACTS) or set(expected_sha256s)!=set(ARTIFACTS):
        raise ValueError('Exact compact artifact inventory required')
    if type(byte_cap) is not int or not 0<byte_cap<=18*MIB:raise ValueError('Explicit bounded artifact cap required')
    sizes={}
    for name in ARTIFACTS:
        _sha(expected_sha256s[name],'independent artifact hash')
        data=parts[name]
        if not isinstance(data,bytes) or hashlib.sha256(data).hexdigest()!=expected_sha256s[name]:
            raise ValueError('Compact artifact differs from independent pin: '+name)
        sizes[name]=len(data)
    if sum(sizes.values())>byte_cap:raise ValueError('Compact evidence capacity exceeded')
    if set(binding)!={'case_identity','plan_sha256','context_sha256','source_contract_sha256','noise_law_sha256'}:
        raise ValueError('Exact compact case binding required')
    for k,v in binding.items():_sha(v,k)
    if (binding['context_sha256']!=context.identity
            or binding['source_contract_sha256']!=hashlib.sha256(context.factor_contract.source_contract_bytes).hexdigest()):
        raise ValueError('Compact context/source binding differs')
    sources=json.loads(parts['sources.json']);scoremeta=json.loads(parts['scores.json']);renderer=json.loads(parts['renderer.json'])
    unit=CadenceMaximum(parts['maximum.json']);old=unit.record()
    if (sources.get('schema')!='radio-whole-cadence-native-source-archive-v1'
            or scoremeta.get('schema')!='radio-whole-cadence-score-archive-v1'
            or sources['case_identity']!=binding['case_identity'] or sources['context_sha256']!=context.identity
            or sources['noise_law_sha256']!=binding['noise_law_sha256']):
        raise ValueError('Compact source metadata differs')
    if (renderer.get('receipt_sha256')!=digest({k:v for k,v in renderer.items() if k!='receipt_sha256'})
            or renderer.get('schema') not in ('radio-whole-cadence-renderer-mock-receipt-v1','radio-whole-cadence-gaussian-receipt-v1')
            or renderer['case_identity']!=binding['case_identity'] or renderer['draw_plan_sha256']!=binding['plan_sha256']
            or renderer['noise_law_sha256']!=binding['noise_law_sha256'] or digest(renderer['noise_law'])!=binding['noise_law_sha256']
            or renderer['normal_calls']!=96):
        raise ValueError('Renderer case/plan/law/receipt differs')
    expected_labels=[s['label'] for s in context.scans]
    if set(sources['sources'])!=set(expected_labels) or [s['scan'] for s in renderer['row_receipts']]!=expected_labels:
        raise ValueError('Complete ordered source/row receipt inventory required')
    sourceids={};rows_checked=0
    for label,receipt in zip(expected_labels,renderer['row_receipts'],strict=True):
        m=sources['sources'][label];scope=m['scope']
        if (m['geometry']!=asdict(context.geometry) or m['integration_count']!=16
                or scope.get('kind')!='synthetic' or scope.get('scan')!=label
                or scope.get('context_sha256')!=context.identity
                or scope.get('case_identity')!=binding['case_identity']
                or scope.get('noise_law_sha256')!=binding['noise_law_sha256']
                or scope.get('draw_plan_sha256')!=binding['plan_sha256']
                or scope.get('receiver_factor_bank_sha256')!=context.factor_contract.factors.identity):
            raise ValueError('Archived native source metadata binding differs')
        for key in ('raw_sha256','normalized_sha256','identity'):_sha(m[key],key)
        identity=native.digest({'contract':native.CONTRACT_SHA256,'geometry':m['geometry'],'rows':16,
            'scope':scope,'raw_sha256':m['raw_sha256'],'normalized_sha256':m['normalized_sha256']})
        if identity!=m['identity'] or identity!=receipt['source_identity']:
            raise ValueError('Archived source identity changed')
        sourceids[label]=identity
        if len(receipt['rows'])!=16 or [r['row'] for r in receipt['rows']]!=list(range(16)):
            raise ValueError('Complete ascending 16-row receipts required')
        for row in receipt['rows']:
            if row['generator_call_arguments']!=[100.,1.,65536]:raise ValueError('Archived row schedule differs')
            for key in ('background_sha256','raw_sha256','normalized_sha256'):_sha(row[key],key)
            rows_checked+=1
    if renderer['source_ids']!=sourceids:raise ValueError('Renderer source inventory changed')
    expected={(kind,t,w) for kind in ('on','off') for t in range(len(context.bank)) for w in core.M37_SPECTRAL_WIDTHS}
    vectors=scoremeta['vectors'];keys=[v['npz_key'] for v in vectors]
    if (len(vectors)!=len(expected) or {tuple(v['key']) for v in vectors}!=expected or len(set(keys))!=len(keys)
            or any(v['npz_key']!=f"{v['key'][0]}_{v['key'][1]:03d}_{v['key'][2]:03d}" for v in vectors)):
        raise ValueError('Complete compact vector inventory required')
    values=decode_npz(parts['scores.npz'],expected_keys=keys,expected_shape=(3,99),maximum_decoded_bytes=len(expected)*3*99*4)
    store=ScoreStore({tuple(v['key']):values[v['npz_key']] for v in vectors},scoremeta['provenance'])
    if any(store.expected_ids[tuple(v['key'])]!=v['identity'] for v in vectors):raise ValueError('Compact vector identity differs')
    provenance=store.provenance
    if (provenance.get('context_sha256')!=context.identity or provenance.get('source_ids')!=sourceids
            or provenance.get('receiver_factor_contract_sha256')!=context.factor_contract.identity
            or provenance.get('source_domain')!='synthetic'):
        raise ValueError('Compact score/source provenance differs')
    entries=provenance.get('native_caches',[])
    expected_entries=[(s,w) for s in context.scans for w in core.M37_SPECTRAL_WIDTHS]
    if len(entries)!=48:raise ValueError('Complete cache ancestry required')
    for entry,(scan,width) in zip(entries,expected_entries,strict=True):
        if entry['scan']!=scan['label'] or entry['width']!=width or entry['source_identity']!=sourceids[scan['label']]:
            raise ValueError('Cache source ancestry differs')
        _sha(entry['cache_identity'],'historical cache identity')
        table=np.stack([store.get(scan['kind'],t,width)[0][scan['epoch']-1] for t in range(len(context.bank))])
        if native.array_hash(table)!=entry['full_support_score_sha256']:raise ValueError('Cache score payload differs')
    family=Family(context.identity,context.factor_contract.factors.identity,len(context.bank),context.grid)
    if (old['domain']!='synthetic-native' or old['case_identity']!=binding['case_identity']
            or old['noise_law_sha256']!=binding['noise_law_sha256'] or old['source_ancestry']['source_ids']!=sourceids
            or old['family']!=family.record()):raise ValueError('Original native maximum binding differs')
    # This new audit has a distinct, unsupported-as-reference domain and does
    # not claim it just validated source values or recomputed native caches.
    derived=_reduce(family,store,binding['case_identity'],binding['noise_law_sha256'],'compact-score-audit',
        {'original_native_receipt_sha256':old['receipt_sha256'],'native_values_present':False}).record()
    fields=('family','family_sha256','input_vector_count','input_inventory_sha256','source_provenance_sha256',
        'visited_hypotheses','hypothesis_inventory_sha256','scored_cells','eligible_cells','mask_receipts','maximum',
        'all_hypotheses_evaluated','score_shift_resampling')
    if any(derived[k]!=old[k] for k in fields):raise ValueError('Archived score-derived maximum/masks differ')
    result={'schema':'radio-whole-cadence-compact-audit-v1','status':'COMPLETE_SCORE_RECEIPT_ARCHIVE_VERIFIED',
        'binding':binding,'artifact_sha256s':expected_sha256s,'artifact_bytes':sizes,'total_bytes':sum(sizes.values()),
        'byte_cap':byte_cap,'source_ids':sourceids,'row_receipts_bound':rows_checked,'cache_ancestry_bound':48,
        'score_vectors':len(store.arrays),'score_values':sum(x.size for x in store.arrays.values()),
        'original_native_maximum_sha256':old['receipt_sha256'],'score_only_reduction':derived,
        'source_values_present':False,'native_source_reconstruction_possible':False,
        'raw_or_normalized_values_revalidated_here':False,'native_cache_identities_recomputed_here':False,
        'scientific_allocation_charged':False,'scientific_or_telescope_admission_authorized':False}
    result['audit_sha256']=digest(result);return result
