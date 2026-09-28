"""Exact inactive 127/24 phase quotas and separately reserved overhead.

Metadata validation only. The caller must durably publish transitions through a
qualified allocation store. No helper here creates a scientific execution lease.
"""
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest,_sha
from .whole_cadence_compact_radio import phase_budget,reservation,OVERHEAD
from .whole_cadence_journal_radio import replay,clone,CAPS
import json


def validate_cases(document,proposal_bytes,budget):
    if budget!=phase_budget(proposal_bytes):raise ValueError('Exact pinned phase budget required')
    state=replay(document);m=document['manifest'];proposal=json.loads(proposal_bytes)
    if m['mode']!='scientific' or m['caps']!=CAPS:raise ValueError('Exact scientific aggregate caps required')
    if len(m['cases'])!=151:raise ValueError('Complete 127/24 case inventory required')
    for binding,case in zip(m['cases'],proposal['cases'],strict=True):
        expected={k:case[k] for k in ('role','context_sha256','source_contract_sha256','noise_law_sha256')}
        expected.update(case_identity=case['identity'],plan_sha256=binding['plan_sha256'])
        if binding!=expected:raise ValueError('Phase source/context/law/role/case binding differs')
    for case in state['cases']:
        quota=reservation(proposal_bytes,budget,case['binding']['case_identity'])
        if (case['milliseconds']!=quota['reserved_milliseconds'] or case['artifact_bytes']!=quota['reserved_artifact_bytes']):
            raise ValueError('Exact per-case quota required; overhead cannot be spent as case quota')
    if (state['reserved_milliseconds']>7000000 or state['reserved_artifact_bytes']>940*1024**2):
        raise ValueError('Case allocation invades the protected overhead reserve')
    return {'case_milliseconds':state['reserved_milliseconds'],'case_artifact_bytes':state['reserved_artifact_bytes'],
        'protected_overhead':clone(budget['overhead']),'scientific_execution_authorized':False,
        'plan_hash_requires_separate_executable_binding':True}


def overhead_genesis(proposal_bytes,budget):
    if budget!=phase_budget(proposal_bytes):raise ValueError('Exact pinned phase budget required')
    return {'schema':'radio-whole-cadence-overhead-v1','budget_sha256':budget['budget_sha256'],
        'reserved':clone(budget['overhead']),'entries':[],'refundable':False}


def validate_overhead(document,proposal_bytes,budget):
    expected=overhead_genesis(proposal_bytes,budget)
    if {**document,'entries':[]}!=expected:raise ValueError('Overhead reservation changed')
    milliseconds=0;used=0;ids=set()
    for i,e in enumerate(document['entries']):
        if set(e)!={'ordinal','identity','kind','milliseconds','bytes','artifact_sha256'} or e['ordinal']!=i or type(e['ordinal']) is not int:
            raise ValueError('Overhead event schema/order differs')
        if e['kind'] not in ('setup','failure','summary','finalization') or e['identity'] in ids:
            raise ValueError('Overhead kind/identity differs; no retry or EMPTY disposition')
        for k in ('identity','artifact_sha256'):_sha(e[k],k)
        for k in ('milliseconds','bytes'):
            if type(e[k]) is not int or e[k]<0:raise ValueError('Nonnegative measured overhead required')
        milliseconds+=e['milliseconds'];used+=e['bytes'];ids.add(e['identity'])
        if milliseconds>OVERHEAD['milliseconds'] or used>OVERHEAD['failure_and_summary_bytes']:
            raise ValueError('Protected overhead capacity exhausted')
    return {'used_milliseconds':milliseconds,'used_failure_summary_bytes':used,
        'remaining_milliseconds':OVERHEAD['milliseconds']-milliseconds,
        'remaining_failure_summary_bytes':OVERHEAD['failure_and_summary_bytes']-used,
        'full_reservation_stays_charged':True,'scientific_execution_authorized':False}


def append_overhead(document,event,*,expected_sha256,proposal_bytes,budget):
    if digest(document)!=expected_sha256:raise ValueError('Independent overhead checkpoint differs')
    validate_overhead(document,proposal_bytes,budget)
    result=clone(document);result['entries'].append(clone(event));validate_overhead(result,proposal_bytes,budget)
    return result
