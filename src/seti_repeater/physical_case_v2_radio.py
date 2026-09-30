"""Versioned v2 engineering parent with strictly registered compressed evidence.

No renderer, source reader, RNG or scientific admission is supplied here.
Every flat checkpoint member is an ordinary charged journal artifact; its seal
binds the complete dynamic inventory. Interrupted cases cannot resume.
"""
import json
import math
import resource

from . import whole_cadence_journal_radio as j
from . import physical_evidence_v2_radio as e
from .empty_null_radio import canonical

SEAL='physical_inventory.json'
OUTCOME='case_outcome.json'
CLOSURE_RESERVES={SEAL:262144,OUTCOME:65536}
REASON_JSON_BYTES=4096


def bounded_reason(value):
    """Bound canonical journal bytes, including escaped Unicode/control text.

    The footer independently preserves the hash of the complete original text.
    This bound does not alter historical footers or journal revisions.
    """
    text=str(value)
    if len(canonical(text))<=REASON_JSON_BYTES:return text
    low,high=0,min(len(text),REASON_JSON_BYTES)
    while low<high:
        middle=(low+high+1)//2
        if len(canonical(text[:middle]))<=REASON_JSON_BYTES:low=middle
        else:high=middle-1
    return text[:low]


def policy(config, *, max_files=1024):
    return {'physical':{'prefix':'physical-','seal':SEAL,'max_files':max_files,
        'reserved_artifacts':dict(CLOSURE_RESERVES),'binding_sha256':e.sha(canonical(config)),
        'failure_finalization_milliseconds':5000}}


def multi_policy(configs, *, max_files=1024):
    """One cumulative parent ledger with a distinct immutable v2 pin per case."""
    configs=list(configs)
    if not configs:raise ValueError('At least one prospective physical configuration required')
    bindings={}
    for config in configs:
        e._config(config)
        identity=config['case_identity']
        if identity in bindings:raise ValueError('Duplicate prospective physical case identity')
        bindings[identity]=e.sha(canonical(config))
    result=policy(configs[0],max_files=max_files)
    result['physical']['binding_sha256']=bindings
    return result


def matches_policy(group, config):
    """Check fixed closure policy while retaining every manifest case pin."""
    expected=policy(config,max_files=group['max_files'])['physical']
    expected['binding_sha256']=group['binding_sha256']
    try:binding=j.group_binding(group,config['case_identity'])
    except (KeyError,TypeError):return False
    return group==expected and binding==e.sha(canonical(config))


def inspect_case(checkpoint,directory,*,case_index=-1):
    states=j.replay(checkpoint.document)['cases'];index=case_index%len(states)
    check=j.verify_archive(checkpoint,directory,case_index=index)
    case=states[index];g=checkpoint.document['manifest']['artifact_groups']['physical']
    files=e._inventory(directory)
    physical={e.nested_name(n):data for n,data in files.items() if n.startswith('physical-')}
    binding=j.group_binding(g,case['binding']['case_identity'])
    view=e.inspect_files(physical,expected_config_sha256=binding)
    conf=json.loads(view.config_bytes)
    if not matches_policy(g,conf):
        raise ValueError('Exact prospective physical closure policy required')
    if any(conf[key]!=case['binding'][key] for key in ('case_identity','plan_sha256')):
        raise ValueError('Physical case/plan differs from registered parent binding')
    if case['artifact_bytes']>e.MAX_BYTES:
        raise ValueError('Parent case exceeds fixed v2 18-MiB allocation')
    for name,pin in conf['existing_artifacts'].items():
        if name not in files or len(files[name])!=pin['bytes'] or e.sha(files[name])!=pin['sha256']:
            raise ValueError('Parent archive lost original base evidence')
    if conf['budget_bytes']!=case['artifact_bytes']-sum(g['reserved_artifacts'].values()):
        raise ValueError('Parent/physical cumulative budget differs')
    return view,{**check,'physical':view.summary(),'case_cap_bytes':case['artifact_bytes'],
        'registered_inventory_exact':True,'scientific_admission_authorized':False}


class PhysicalCase:
    def __init__(self,lease,config,*,existing_artifacts):
        self.lease=lease;self.closed=False
        self.writer=e.Writer.create_for_lease(lease,config,existing_artifacts=existing_artifacts)

    def finish(self,*,reason=''):
        if self.closed or not self.writer.closed or self.writer.poisoned:
            raise ValueError('Only an intact terminal physical store can be sealed')
        view,check=inspect_case(self.lease.checkpoint,self.lease.directory)
        success=view.summary()['status']=='completed'
        self.lease.write_artifact(SEAL,canonical(j.group_seal(self.lease.checkpoint,'physical',complete=success)))
        result={'schema':'radio-engineering-case-outcome-v1','outcome':'completed' if success else 'failed',
            'physical_evidence_reference':self.writer.receipt(),'reason':bounded_reason(reason),
            'reason_sha256':e.sha(str(reason).encode()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'elapsed_milliseconds':(self.lease.clock()-self.lease.started)*1000,
            'scientific_admission_authorized':False,'execution_restart_authorized':False}
        self.lease.write_artifact(OUTCOME,canonical(result))
        inspect_case(self.lease.checkpoint,self.lease.directory)
        # Successful descriptions are retained in the hashed footer. Keeping
        # their journal reasons empty leaves the reserved last-failure margin.
        cp=self.lease.finish('completed' if success else 'failed',
            '' if success else bounded_reason(reason))
        self.closed=True
        return cp

    def fail(self,error):
        """Bounded closure after timeout or interrupted writes; never large dumps."""
        if self.closed:raise ValueError('Case already closed')
        closure_started=self.lease.clock()
        reference=self.writer.receipt();closure_error=None
        if not self.writer.closed:
            try:reference=self.writer.close('failed','outer_failure',repr(error))
            except BaseException as nested:
                closure_error=repr(nested)[:2048];reference=self.writer.receipt()
        result={'schema':'radio-engineering-case-outcome-v1','outcome':'failed',
            'physical_evidence_reference':reference,'error':repr(error)[:4096],
            'error_sha256':e.sha(repr(error).encode()),'physical_closure_error':closure_error,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'elapsed_milliseconds':(self.lease.clock()-self.lease.started)*1000,
            'scientific_admission_authorized':False,'execution_restart_authorized':False}
        if self.lease.broken:
            self.closed=True
            return {**result,'parent_status':'uncertain','outer_footer_written':False}
        if self.lease.failure_finalization_started is None:
            self.lease.failure_finalization_started=closure_started
        def closure_budget():
            elapsed=(self.lease.clock()-self.lease.failure_finalization_started)*1000
            group=self.lease.manifest['artifact_groups']['physical']
            if not math.isfinite(elapsed) or elapsed<0 or elapsed>group['failure_finalization_milliseconds']:
                self.closed=True
                raise ValueError('Whole failure finalization window exhausted; no retry')
        closure_budget()
        # Verify the exact charged prefix before sealing it incomplete. A lost
        # acknowledgement or orphaned filesystem write cannot enter this path.
        inspect_case(self.lease.checkpoint,self.lease.directory)
        closure_budget()
        state=j.replay(self.lease.checkpoint.document)['cases'][-1]
        if SEAL not in state['artifacts']:
            self.lease.write_failure_artifact(SEAL,
                canonical(j.group_seal(self.lease.checkpoint,'physical',complete=False)))
        # A timeout closes normal work permanently. Only the already-reserved
        # seal/footer can enter the same fixed five-second closure window.
        retained_footer=OUTCOME in state['artifacts']
        if not retained_footer:
            self.lease.write_failure_artifact(OUTCOME,canonical(result))
        closure_budget()
        reason=repr(error)
        if retained_footer:reason='failure-error-sha256:'+e.sha(reason.encode())+' '+reason
        cp=self.lease.finish('failed',bounded_reason(reason));self.closed=True
        closure_budget()
        return {'parent_status':j.replay(cp.document)['cases'][-1]['status'],
                'outer_footer_written':not retained_footer,'outer_footer_retained':retained_footer,
                'failure_closure_within_limit':True,**result}
