"""Prospective bounds for the fresh eight-case native v2 engineering parent.

This module allocates no case and exposes no RNG.  Physical configurations are
frozen before generated base artifacts exist; the outer parent charges those
later artifacts while the v2 writer is restricted to the ``physical-`` group.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import uuid

from . import gaussian_engineering_radio as gaussian
from . import physical_case_v2_radio as physical_case
from . import physical_evidence_v2_radio as physical
from . import whole_cadence_event_store_radio as event_store
from . import whole_cadence_journal_radio as journal
from . import whole_cadence_physical_radio as stages
from .empty_null_radio import canonical
from .native_chain_engineering_radio import SPECS
from .pipeline_receiver_radio import Context
from .whole_cadence_reference_radio import digest

NAMESPACE='radio-native-v2-engineering-20260930a'
CASE_COUNT=8
CASE_MILLISECONDS=600000
CASE_BYTES=18*1024**2
JOURNAL_BYTES=8*1024**2
CHECKPOINT_LIMIT=stages.EVIDENCE_STAGE_CEILING
PHYSICAL_MAX_FILES=48
BASE_ARTIFACTS=tuple(gaussian.ARTIFACTS)
REQUIRED_ARTIFACTS=(*BASE_ARTIFACTS,physical_case.SEAL,physical_case.OUTCOME)
LAW={**gaussian.LAW,'namespace':NAMESPACE,
    'purpose':'fresh-native-v2-parent-qualification','same_window_only':True}
LAW_SHA=digest(LAW)


def make_plan(context,ordinal):
    """Build one of eight fresh plans without constructing a generator."""
    if not isinstance(context,Context):raise ValueError('Actual metadata receiver context required')
    context.validate()
    if context.native_window['role']!='validation':raise ValueError('Same validation window required')
    if type(ordinal) is not int or not 0<=ordinal<CASE_COUNT:raise ValueError('Eight fixed cases only')
    name=NAMESPACE+'/'+SPECS[ordinal]['name']
    seed=int.from_bytes(hashlib.sha256((name+'/seed-v1').encode()).digest()[:8],'big')
    case={'namespace':NAMESPACE,'ordinal':ordinal,'spec':SPECS[ordinal],
        'context_sha256':context.identity,'seed':seed,
        'source_contract_sha256':hashlib.sha256(context.factor_contract.source_contract_bytes).hexdigest(),
        'receiver_bank_sha256':context.factor_contract.factors.identity,
        'noise_law_sha256':LAW_SHA,'scientific_allocation_charged':False}
    case['identity']=digest(case)
    plan={'schema':'radio-native-v2-engineering-plan-v1','case':case,'law':LAW,
        'window':context.native_window,
        'streams':[{'scan_index':i,'scan':scan['label'],'entropy':[seed,i],
            'normal_calls':16,'arguments':[100.,1.,65536]}
            for i,scan in enumerate(context.scans)]}
    plan['plan_sha256']=digest(plan)
    return json.loads(canonical(plan))


def case_binding(plan):
    return gaussian.binding(plan)


def validate_plan(context,plan,forbidden_cases):
    if plan!=make_plan(context,plan['case']['ordinal']):
        raise ValueError('Exact fresh native v2 plan required')
    if any(plan['case']['identity']==case['identity'] or plan['case']['seed']==case['seed']
           for case in forbidden_cases):
        raise ValueError('Historical/reserved identity or seed collision')
    return plan


@dataclass(frozen=True)
class Bounds:
    case_count:int
    checkpoint_limit:int
    physical_files_per_case:int
    artifact_batch_events_per_case:int
    journal_events:int
    journal_files:int
    case_bytes:int
    cumulative_case_bytes:int
    journal_bytes:int
    cumulative_evidence_bytes:int


def bounds():
    # Reservation and physical outcome are single physical files.  Every one of
    # the remaining files belongs to one of the fixed checkpoint stages.  With
    # 48 total files no checkpoint can cross the 128-member event batch limit.
    checkpoint_files=PHYSICAL_MAX_FILES-2
    if checkpoint_files<CHECKPOINT_LIMIT:
        raise ValueError('Every checkpoint needs its own immutable commit record')
    batch_events=CHECKPOINT_LIMIT+(checkpoint_files-CHECKPOINT_LIMIT)//journal.GROUP_ARTIFACT_BATCH_MAX
    per_case=(1+len(BASE_ARTIFACTS)+1+batch_events+1+2+1)
    events=CASE_COUNT*per_case
    files=3+events+(events+1) # genesis/LOCK/HEAD, events, pointer versions
    result=Bounds(CASE_COUNT,CHECKPOINT_LIMIT,PHYSICAL_MAX_FILES,batch_events,
        events,files,CASE_BYTES,CASE_COUNT*CASE_BYTES,JOURNAL_BYTES,
        CASE_COUNT*CASE_BYTES+JOURNAL_BYTES)
    if (result.checkpoint_limit>51 or result.journal_events>event_store.MAX_EVENTS
            or result.journal_files>event_store.MAX_FILES
            or result.cumulative_evidence_bytes>journal.CAPS['evidence_bytes']):
        raise ValueError('Prospective native v2 parent exceeds a hard bound')
    return result


def physical_config(case_binding):
    """Freeze a case/plan pin without pretending future RNG artifacts exist."""
    if set(case_binding)!=journal.BINDING_KEYS or case_binding['role']!='engineering':
        raise ValueError('Exact engineering case binding required')
    return physical.configuration(NAMESPACE,case_binding['case_identity'],
        case_binding['plan_sha256'],{},
        budget_bytes=CASE_BYTES-sum(physical_case.CLOSURE_RESERVES.values()),
        checkpoint_limit=CHECKPOINT_LIMIT)


def caps():
    result={**journal.CAPS,'active_milliseconds':CASE_COUNT*CASE_MILLISECONDS,
        'evidence_bytes':bounds().cumulative_evidence_bytes,
        'ledger_reserve_bytes':JOURNAL_BYTES}
    return result


def manifest(execution_binding_sha256,allocation_sha256,cases):
    cases=list(cases)
    configs=[physical_config(case) for case in cases]
    value={'schema':journal.SCHEMA,'mode':'engineering','namespace':NAMESPACE,
        'execution_binding_sha256':execution_binding_sha256,
        'allocation_sha256':allocation_sha256,'cases':cases,'caps':caps(),
        'required_artifacts':list(REQUIRED_ARTIFACTS),
        'artifact_groups':physical_case.multi_policy(configs,max_files=PHYSICAL_MAX_FILES)}
    journal.validate_manifest(value)
    if len(cases)!=CASE_COUNT:raise ValueError('Exact fresh eight-case inventory required')
    return value,configs


def record():
    return {'schema':'radio-native-v2-parent-bounds-v1','namespace':NAMESPACE,
        **asdict(bounds()),'base_artifacts':list(BASE_ARTIFACTS),
        'group_artifact_batch_max':journal.GROUP_ARTIFACT_BATCH_MAX,
        'event_store_max_events':event_store.MAX_EVENTS,
        'event_store_max_files':event_store.MAX_FILES,
        'journal_snapshot_bytes':journal.GROUP_MAX_LEDGER_SNAPSHOT,
        'rng_opened':False,'reservation_authorized':False,
        'scientific_admission_authorized':False}


def worst_case_journal_model(*,terminal_failure=False):
    """Exact canonical/event-pointer accounting at all frozen count ceilings.

    Each ordinary artifact is assigned 300,000 bytes so byte-count fields use
    six digits while the 18-MiB case cap and both outer reserves still hold.
    The payload bytes are not allocated; only their immutable receipts exist.
    """
    h=lambda label:hashlib.sha256(label.encode()).hexdigest()
    cases=[{'case_identity':h(f'{NAMESPACE}/model/case/{i}'),
        'plan_sha256':h(f'{NAMESPACE}/model/plan/{i}'),'context_sha256':h('context'),
        'source_contract_sha256':h('source'),'noise_law_sha256':h('law'),'role':'engineering'}
        for i in range(CASE_COUNT)]
    m,_=manifest(h('freeze'),h('allocation'),cases);document=journal.genesis(m)
    genesis=canonical(document);genesis_sha=digest(document);last_event=journal.ZERO
    pointer=event_store.pointer(genesis_sha,document,last_event,journal.ZERO)
    previous_pointer=hashlib.sha256(pointer).hexdigest()
    stored=len(genesis)+len(pointer)+65 # LOCK is zero bytes; HEAD is 65.
    peak_stored_with_reserves=stored+journal.GROUP_LEDGER_FINALIZATION_RESERVE
    peak_revision=len(genesis);events=0

    def append(event):
        nonlocal document,last_event,previous_pointer,stored
        nonlocal peak_stored_with_reserves,peak_revision,events
        before=digest(document);following=journal.append(document,event);raw=canonical(following)
        record_bytes=canonical({'schema':event_store.SCHEMA,'index':events,
            'before_revision_sha256':before,'after_revision_sha256':digest(following),
            'after_revision_bytes':len(raw),'previous_event_sha256':last_event,
            'record':following['events'][-1]})
        last_event=hashlib.sha256(record_bytes).hexdigest()
        pointer_bytes=event_store.pointer(genesis_sha,following,last_event,previous_pointer)
        previous_pointer=hashlib.sha256(pointer_bytes).hexdigest()
        stored+=len(record_bytes)+len(pointer_bytes);events+=1;document=following
        reserved={name for group in m['artifact_groups'].values()
                  for name in group['reserved_artifacts']}
        closing=event['kind']=='finish' or event['kind']=='artifact' and event.get('name') in reserved
        held=0 if closing else journal.GROUP_LEDGER_FINALIZATION_RESERVE
        peak_stored_with_reserves=max(peak_stored_with_reserves,stored+65+held)
        peak_revision=max(peak_revision,len(raw))

    size=300000
    for case_index,case in enumerate(cases):
        nonce=str(uuid.UUID(int=case_index+1))
        append({'kind':'consume','binding':case,'milliseconds':CASE_MILLISECONDS,
            'artifact_bytes':CASE_BYTES,'nonce':nonce})
        for name in BASE_ARTIFACTS:
            append({'kind':'artifact','nonce':nonce,'name':name,'size':size,
                'sha256':h(f'{case_index}/{name}')})
        append({'kind':'artifact','nonce':nonce,'name':'physical-reservation.json',
            'size':size,'sha256':h(f'{case_index}/physical-reservation')})
        part_index=0;remaining=PHYSICAL_MAX_FILES-2-CHECKPOINT_LIMIT
        for checkpoint in range(CHECKPOINT_LIMIT):
            count=(remaining+CHECKPOINT_LIMIT-1-checkpoint)//(CHECKPOINT_LIMIT-checkpoint)
            rows=[]
            for _ in range(count):
                rows.append({'name':'physical-part-'+h(f'{case_index}/{part_index}'),
                    'size':size,'sha256':h(f'{case_index}/part-bytes/{part_index}')})
                part_index+=1
            rows.append({'name':f'physical-checkpoint-{checkpoint:04d}.json',
                'size':size,'sha256':h(f'{case_index}/checkpoint/{checkpoint}')})
            append({'kind':'artifact_batch','nonce':nonce,
                'artifacts':sorted(rows,key=lambda row:row['name'])})
            remaining-=count
        append({'kind':'artifact','nonce':nonce,'name':'physical-outcome.json',
            'size':size,'sha256':h(f'{case_index}/physical-outcome')})
        append({'kind':'artifact','nonce':nonce,'name':physical_case.SEAL,
            'size':physical_case.CLOSURE_RESERVES[physical_case.SEAL],
            'sha256':h(f'{case_index}/seal')})
        append({'kind':'artifact','nonce':nonce,'name':physical_case.OUTCOME,
            'size':physical_case.CLOSURE_RESERVES[physical_case.OUTCOME],
            'sha256':h(f'{case_index}/outcome')})
        failed=terminal_failure and case_index==CASE_COUNT-1
        append({'kind':'finish','nonce':nonce,'outcome':'failed' if failed else 'completed',
            'elapsed_milliseconds':CASE_MILLISECONDS+(5000 if failed else 0),
            'reason':'x'*(physical_case.REASON_JSON_BYTES-2) if failed else ''})
    result={'events':events,'files':2*events+4,'peak_revision_bytes':peak_revision,
        'terminal_stored_bytes':stored,'peak_stored_bytes_with_head_and_closure_reserve':peak_stored_with_reserves,
        'journal_budget_bytes':JOURNAL_BYTES,'journal_snapshot_limit_bytes':journal.GROUP_MAX_LEDGER_SNAPSHOT}
    if (events!=bounds().journal_events or result['files']!=bounds().journal_files
            or peak_revision>journal.GROUP_MAX_LEDGER_SNAPSHOT
            or peak_stored_with_reserves>JOURNAL_BYTES):
        raise ValueError('Exact prospective journal model exceeds its frozen bounds')
    return result
