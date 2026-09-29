"""One engineering outer case with strictly registered physical checkpoints.

No renderer, source reader, RNG or scientific admission is supplied here.
Every flat checkpoint member is an ordinary charged journal artifact; its seal
binds the complete dynamic inventory. Interrupted cases cannot resume.
"""
import json
import resource

from . import whole_cadence_journal_radio as j
from . import physical_evidence_radio as e
from .empty_null_radio import canonical

SEAL='physical_inventory.json'
OUTCOME='case_outcome.json'
CLOSURE_RESERVES={SEAL:262144,OUTCOME:65536}


def policy(config, *, max_files=1024):
    return {'physical':{'prefix':'physical-','seal':SEAL,'max_files':max_files,
        'reserved_artifacts':dict(CLOSURE_RESERVES),'binding_sha256':e.sha(canonical(config)),
        'failure_finalization_milliseconds':5000}}


def inspect_case(checkpoint,directory,*,case_index=-1):
    states=j.replay(checkpoint.document)['cases'];index=case_index%len(states)
    check=j.verify_archive(checkpoint,directory,case_index=index)
    case=states[index];g=checkpoint.document['manifest']['artifact_groups']['physical']
    files=e._inventory(directory)
    physical={e.nested_name(n):data for n,data in files.items() if n.startswith('physical-')}
    view=e.inspect_files(physical,expected_config_sha256=g['binding_sha256'])
    conf=json.loads(view.config_bytes)
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
            'physical_evidence_reference':self.writer.receipt(),'reason':str(reason)[:4096],
            'reason_sha256':e.sha(str(reason).encode()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'elapsed_milliseconds':(self.lease.clock()-self.lease.started)*1000,
            'scientific_admission_authorized':False,'execution_restart_authorized':False}
        self.lease.write_artifact(OUTCOME,canonical(result))
        inspect_case(self.lease.checkpoint,self.lease.directory)
        cp=self.lease.finish('completed' if success else 'failed',str(reason)[:4096])
        self.closed=True
        return cp

    def fail(self,error):
        """Bounded closure after timeout or interrupted writes; never large dumps."""
        if self.closed:raise ValueError('Case already closed')
        reference=self.writer.receipt();closure_error=None
        if not self.writer.closed:
            try:reference=self.writer.close('failed','outer_failure',repr(error))
            except BaseException as nested:closure_error=repr(nested)[:2048]
        result={'schema':'radio-engineering-case-outcome-v1','outcome':'failed',
            'physical_evidence_reference':reference,'error':repr(error)[:4096],
            'error_sha256':e.sha(repr(error).encode()),'physical_closure_error':closure_error,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'elapsed_milliseconds':(self.lease.clock()-self.lease.started)*1000,
            'scientific_admission_authorized':False,'execution_restart_authorized':False}
        if self.lease.broken:
            self.closed=True
            return {**result,'parent_status':'uncertain','outer_footer_written':False}
        # A timeout closes normal work permanently. Only the already-reserved
        # small footer may be written in the separate fixed five-second window.
        self.lease.write_failure_artifact(OUTCOME,canonical(result))
        cp=self.lease.finish('failed',repr(error)[:4096]);self.closed=True
        return {'parent_status':j.replay(cp.document)['cases'][-1]['status'],
                'outer_footer_written':True,**result}
