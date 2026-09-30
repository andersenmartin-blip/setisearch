"""One-shot fresh eight-case native-v2 engineering orchestration.

This module supplies no public reservation or transport credential. A caller
must first independently verify a COMPLETE_RUNNER_BROKER_RUNTIME freeze and a
separate irrevocable eight-case reservation. Injected callbacks are integration
boundaries, not execution authority. Historical preparation freezes cannot enter.
"""
from contextlib import contextmanager
import gc
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import threading
import time

from . import native_v2_parent_radio as parent
from . import native_v2_chain_radio as chain
from . import native_v2_broker_radio as broker
from . import gaussian_engineering_radio as gaussian
from . import whole_cadence_compact_radio as compact
from . import whole_cadence_event_store_radio as events
from . import whole_cadence_journal_radio as journal
from . import physical_case_v2_radio as cases
from . import physical_evidence_v2_radio as evidence
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import CadenceMaximum,digest

SCHEMA='radio-native-v2-eight-case-runner-v1'
AUTHORITY_SCHEMA='radio-native-v2-runner-authority-v1'
FREEZE_PROOF_SCHEMA='radio-native-v2-runner-freeze-verification-v1'
RESERVATION_PROOF_SCHEMA='radio-native-v2-runner-reservation-verification-v1'
CHECKPOINT_SCHEMA='radio-native-v2-runner-checkpoint-v1'
WRAPPER_FIELDS=('native_v2_runner_checkpoint','native_v2_engineering_gate',
                'native_v2_engineering_association')
WHOLE_SECONDS=broker.CumulativeLimits().seconds
OPERATION_SECONDS=30
_DEADLINE_DEPTH=0
HOST_SCHEMA='radio-native-v2-tool-host-accounting-v1'
HOST_COUNTERS=('calls','request_bytes','response_bytes','response_charged_bytes',
    'unknown_response_bytes','unknown_response_count','tool_argument_bytes',
    'receipt_bytes','receipt_charged_bytes','unknown_receipt_bytes',
    'git_spool_bytes','git_spool_charged_bytes','unknown_git_spool_bytes')
HOST_CAPS={'calls':512,'request_bytes':384*1024**2,'response_charged_bytes':512*1024**2,
    'receipt_charged_bytes':1536*1024**2,'git_spool_charged_bytes':320*1024**2}
HOST_CASE_CAPS={'calls':64,'request_bytes':48*1024**2,'response_charged_bytes':64*1024**2,
    'receipt_charged_bytes':192*1024**2,'git_spool_charged_bytes':40*1024**2}


class RunnerStopped(RuntimeError):
    """Terminal failure with retained forensic state; never a retry token."""
    def __init__(self,message,result):
        super().__init__(message);self.result=result


def prepare_manifest(context,*,execution_sha256,allocation_sha256,forbidden_cases):
    """Metadata only: reconstruct exact plans/configs without reserving or RNG."""
    plans=[parent.make_plan(context,i) for i in range(parent.CASE_COUNT)]
    for plan in plans:parent.validate_plan(context,plan,forbidden_cases)
    if (len({p['case']['identity'] for p in plans})!=parent.CASE_COUNT
            or len({p['case']['seed'] for p in plans})!=parent.CASE_COUNT):
        raise ValueError('Distinct fresh eight-case identities and seeds required')
    manifest,configs=parent.manifest(execution_sha256,allocation_sha256,
                                    [parent.case_binding(p) for p in plans])
    return {'plans':plans,'manifest':manifest,'configs':configs}


def validate_authority(authority,manifest,plans):
    """Require an independently produced immutable public-verification receipt.

    The production caller is responsible for obtaining these fields by exact
    immutable public readback, including every code/input/runtime pin. This
    check deliberately refuses the PREPARED_NOT_EXECUTABLE receipt format.
    """
    if not isinstance(authority,dict):raise ValueError('Verified public execution authority required')
    for field in ('freeze_commit','reservation_commit'):
        broker.archive.git_sha(authority.get(field))
    for field in ('freeze_sha256','reservation_sha256','allocation_sha256',
                  'code_inventory_sha256','input_inventory_sha256','runtime_inventory_sha256'):
        journal._sha(authority.get(field),field)
    expected={'schema':AUTHORITY_SCHEMA,'namespace':parent.NAMESPACE,
        'freeze_kind':'COMPLETE_RUNNER_BROKER_RUNTIME',
        'freeze_sha256':manifest['execution_binding_sha256'],
        'allocation_sha256':manifest['allocation_sha256'],
        'ordered_case_identities':[p['case']['identity'] for p in plans],
        'all_eight_irrevocably_reserved':True,'exact_public_readback_verified':True,
        'runtime_files_verified':True,'restart_authorized':False,
        'execution_authorized':True,'transport_integration_qualified':True,
        'scientific_execution_authorized':False}
    if (any(canonical(authority.get(k))!=canonical(v) for k,v in expected.items())
            or authority['freeze_commit']==authority['reservation_commit']):
        raise ValueError('Complete fresh public freeze and separate exact eight-case reservation required')
    return json.loads(canonical(authority))


@contextmanager
def deadline(seconds):
    """Bound synchronous operations in the POSIX main-thread runner.

    Host cancellation and untouched external envelopes remain the transport's
    duty. A timed-out mutation is ambiguous and is never dispatched again.
    """
    if (not math.isfinite(seconds) or seconds<=0 or
            threading.current_thread() is not threading.main_thread() or
            not hasattr(signal,'setitimer')):
        raise ValueError('Positive POSIX main-thread operation deadline required')
    global _DEADLINE_DEPTH
    previous_handler=signal.getsignal(signal.SIGALRM)
    previous_timer=signal.getitimer(signal.ITIMER_REAL)
    if previous_timer!=(0.0,0.0) and _DEADLINE_DEPTH==0:
        raise ValueError('Runner cannot replace an active external deadline')
    # Runner stages compose: a nested operation can shorten, never extend, the
    # enclosing deadline. Independently installed external timers stay intact.
    started=time.monotonic()
    allowance=min(seconds,previous_timer[0]) if previous_timer[0] else seconds
    def expired(signum,frame):raise TimeoutError('Frozen native-v2 operation deadline exhausted')
    _DEADLINE_DEPTH+=1
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,allowance)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous_handler)
        _DEADLINE_DEPTH-=1
        if previous_timer[0]:
            signal.setitimer(signal.ITIMER_REAL,max(1e-9,previous_timer[0]-(time.monotonic()-started)),previous_timer[1])


def terminal_maps(store,lease,config):
    """Extract only an exact registered terminal case and complete journal."""
    checkpoint=store.read();state=journal.replay(checkpoint.document)
    if not state['cases'] or state['cases'][-1]['binding']!=lease.case['binding']:
        raise ValueError('Latest exact case binding required for terminal extraction')
    if state['cases'][-1]['status'] not in ('completed','failed'):
        raise ValueError('Terminal case required before publication')
    journal.verify_archive(checkpoint,lease.directory,case_index=len(state['cases'])-1)
    files={n:(lease.directory/n).read_bytes() for n in state['cases'][-1]['artifacts']}
    physical={evidence.nested_name(n):data for n,data in files.items() if n.startswith('physical-')}
    base={n:data for n,data in files.items() if not n.startswith('physical-')}
    journal_files=events.inventory(store.path)
    genesis_sha=store.genesis_sha256
    pointer_sha=journal_files['HEAD'][:-1].decode('ascii')
    view=evidence.inspect_files(physical,expected_config_sha256=digest(config))
    pins={'config_sha256':digest(config),
          'last_checkpoint_sha256':view.summary()['latest_checkpoint_sha256'],
          'genesis_sha256':genesis_sha,'pointer_sha256':pointer_sha}
    # Validate every registered byte, the physical seal, terminal state, and
    # every cumulative event/pointer version before broker preparation.
    broker.archive._validated_maps(physical,journal_files,base,pins)
    return physical,journal_files,base,pins


def original_snapshot(wrapper):
    """Restore exact original report fields from the fresh measured wrapper."""
    receipt=wrapper['native_v2_runner_checkpoint']
    if receipt.get('schema')!=CHECKPOINT_SCHEMA:raise ValueError('Fresh runner checkpoint wrapper required')
    original={k:v for k,v in wrapper.items() if k not in WRAPPER_FIELDS}
    if evidence.sha(canonical(original))!=receipt['original_snapshot_sha256']:
        raise ValueError('Original report bytes differ from wrapper receipt')
    return original


def validate_transport_usage(value,*,case=False):
    """Check actual visible envelopes and separately charged durable local bytes."""
    if not isinstance(value,dict):raise ValueError('Measured host transport usage required')
    for name in HOST_COUNTERS:
        if type(value.get(name)) is not int or value[name]<0:
            raise ValueError('Finite nonnegative measured host counter required: '+name)
    for charged,known,unknown in (('response_charged_bytes','response_bytes','unknown_response_bytes'),
            ('receipt_charged_bytes','receipt_bytes','unknown_receipt_bytes'),
            ('git_spool_charged_bytes','git_spool_bytes','unknown_git_spool_bytes')):
        if value[charged]!=value[known]+value[unknown]:
            raise ValueError('Actual host charge differs from known and unknown bytes')
    for name,cap in (HOST_CASE_CAPS if case else HOST_CAPS).items():
        if value[name]>cap:raise ValueError('Measured host transport capacity exceeded: '+name)
    if not case:
        elapsed=value.get('elapsed_seconds')
        if (value.get('schema')!=HOST_SCHEMA or type(value.get('cases')) is not int
                or not 0<=value['cases']<=8 or type(elapsed) not in (int,float)
                or not math.isfinite(elapsed) or not 0<=elapsed<=WHOLE_SECONDS
                or value.get('automatic_retry') is not False
                or value.get('visible_tool_objects_only') is not True
                or value.get('hidden_http_bytes_known') is not False):
            raise ValueError('Measured bounded host accounting receipt required')
    return json.loads(canonical(value))


class Runner:
    """Exactly one invocation; terminal publication/readback precedes next case.

    ``invoke`` is the qualified host bridge. ``persist`` durably saves untouched
    raw results for DurableInvoker. ``prepare_transport`` pins each bundle in
    that host before publication; ``finish_transport`` closes the same exact
    immutable readback barrier before the next case. ``transport_usage`` supplies actual envelope
    and Git accounting, while ``persist_state`` retains each runner receipt.
    Tests may replace numerical functions, but production defaults always use
    the fresh v2 chain and original numerical arithmetic.
    """
    def __init__(self,context,plans,manifest,*,authority,verify_freeze,verify_reservation,target,
                 forbidden_cases,invoke,persist,parent_sha,parent_tree_sha,
                 transport_usage,prepare_transport,finish_transport,persist_state,
                 clock=time.monotonic):
        self.context=context;self.plans=json.loads(canonical(plans));self.manifest=json.loads(canonical(manifest))
        self.forbidden_cases=json.loads(canonical(forbidden_cases))
        prepared=prepare_manifest(context,
            execution_sha256=self.manifest['execution_binding_sha256'],
            allocation_sha256=self.manifest['allocation_sha256'],forbidden_cases=self.forbidden_cases)
        if prepared['plans']!=self.plans or prepared['manifest']!=self.manifest:
            raise ValueError('Exact fresh ordered parent plans and manifest required')
        self.configs=prepared['configs'];self.authority=validate_authority(authority,self.manifest,self.plans)
        for callback in (verify_freeze,verify_reservation,invoke,persist,transport_usage,prepare_transport,finish_transport,persist_state):
            if not callable(callback):raise ValueError('Complete verified runner integration callbacks required')
        self.verify_freeze=verify_freeze;self.verify_reservation=verify_reservation
        self.target=Path(target);self.clock=clock
        self.parent_sha=broker.archive.git_sha(parent_sha);self.parent_tree_sha=broker.archive.git_sha(parent_tree_sha)
        self.transport_usage=transport_usage;self.prepare_transport=prepare_transport
        self.finish_transport=finish_transport;self.persist_state=persist_state
        self.raw_invoker=broker.DurableInvoker(invoke,persist)
        self.publisher=None;self.store=None;self.lease=None;self.physical_case=None
        self.started=None;self.attempted=False;self.stopped=False;self.rows=[];self.resources=[]
        self.current_resources=[];self.gate=None;self.units=[];self.threshold=None
        self.raw_transport_started=False
        self.transport_receipts=[];self.previous_transport=None

    def _transport_snapshot(self,*,validate=True):
        allowance=5
        if validate:
            allowance=min(OPERATION_SECONDS,WHOLE_SECONDS-(self.clock()-self.started))
        with deadline(allowance):value=self.transport_usage()
        if validate:
            value=validate_transport_usage(value)
            if self.previous_transport is not None and any(value[k]<self.previous_transport[k]
                    for k in (*HOST_COUNTERS,'cases','elapsed_seconds')):
                raise ValueError('Measured cumulative transport usage regressed')
            self.previous_transport=value
        return json.loads(canonical(value))

    def _verify_freeze(self,manifest):
        expected={'schema':FREEZE_PROOF_SCHEMA,
            **{k:self.authority[k] for k in ('namespace','freeze_kind','freeze_commit','freeze_sha256',
                'code_inventory_sha256','input_inventory_sha256','runtime_inventory_sha256')},
            'code_files_verified':True,'input_files_verified':True,'runtime_files_verified':True,
            'exact_public_readback_verified':True,'execution_authorized':True,
            'transport_integration_qualified':True,'restart_authorized':False,
            'scientific_execution_authorized':False}
        receipt=self.verify_freeze(json.loads(canonical(manifest)))
        if canonical(receipt)!=canonical(expected):
            raise ValueError('Qualified complete immutable freeze verification receipt required')
        return receipt

    def _verify_reservation(self):
        expected={'schema':RESERVATION_PROOF_SCHEMA,
            **{k:self.authority[k] for k in ('namespace','freeze_commit','freeze_sha256',
                'reservation_commit','reservation_sha256','allocation_sha256','ordered_case_identities')},
            'all_eight_irrevocably_reserved':True,'all_eight_allocation_remains_spent':True,
            'exact_public_readback_verified':True,'restart_authorized':False,
            'scientific_execution_authorized':False}
        receipt=self.verify_reservation(json.loads(canonical(self.authority)))
        if canonical(receipt)!=canonical(expected):
            raise ValueError('Separate immutable irrevocable eight-case reservation verification receipt required')
        return receipt

    def _budget(self):
        elapsed=self.clock()-self.started
        if not math.isfinite(elapsed) or not 0<=elapsed<=WHOLE_SECONDS:
            raise ValueError('Whole interleaved native/publication wall-time cap exceeded')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>parent.caps()['rss_bytes']:
            raise ValueError('Whole native-v2 RSS cap exceeded')
        self._transport_snapshot()
        if self.store is not None:
            files=events.inventory(self.store.path)
            if sum(map(len,files.values()))>parent.JOURNAL_BYTES:
                raise ValueError('Cumulative journal capacity exceeded')
        if self.target.exists():
            size=0
            for p in self.target.rglob('*'):
                if p.is_symlink():raise ValueError('Symlink in runner evidence')
                if p.is_file():size+=p.stat().st_size
            if size>parent.bounds().cumulative_evidence_bytes:
                raise ValueError('Whole runner evidence byte cap exceeded')
        elapsed=self.clock()-self.started
        if not math.isfinite(elapsed) or not 0<=elapsed<=WHOLE_SECONDS:
            raise ValueError('Whole interleaved native/publication wall-time cap exceeded')
        return elapsed

    def _stage(self,label,action,*,case_budget=True,seconds=None):
        before=self.clock();self._budget()
        now=self.clock();allowance=WHOLE_SECONDS-(now-self.started)
        if case_budget and self.lease is not None:
            self.lease.budget()
            allowance=min(allowance,parent.CASE_MILLISECONDS/1000-(self.clock()-self.lease.started))
        if seconds is not None:allowance=min(allowance,seconds)
        ok=False
        try:
            with deadline(allowance):value=action()
            ok=True;return value
        finally:
            after=self.clock();row={'stage':label,'seconds':after-before,'completed':ok,
                'timing_scope':'inclusive_nested_stages',
                'boundary_budget_verified':False,
                'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
            if self.lease is not None:
                state=journal.replay(self.lease.checkpoint.document)['cases'][-1]
                row['registered_case_bytes']=sum(r['size'] for r in state['artifacts'].values())
            self.current_resources.append(row);self.resources.append(row)
            if ok:self._budget()
            if ok and case_budget and self.lease is not None and not self.lease.closed:
                self.lease.budget()
            if ok:row['boundary_budget_verified']=True

    def _invoke(self,operation,params):
        # Deadline is inside DurableInvoker: a timed-out external call poisons
        # the adapter and reserves the broker's unknown reply charge.
        with deadline(min(OPERATION_SECONDS,WHOLE_SECONDS-self._budget())):
            self.raw_transport_started=True
            return self.raw_invoker.invoke(operation,params)

    def _instrument(self,plan):
        writer=self.physical_case.writer
        checkpoint=writer.checkpoint;close=writer.close
        boundary=self.clock()
        def measured_checkpoint(label,document):
            nonlocal boundary
            now=self.clock()
            row={'stage':'physical_until_'+label,
                'seconds':now-boundary,'completed':True,
                'timing_scope':'inclusive_nested_stages',
                'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
            self.current_resources.append(row);self.resources.append(row)
            if any(k in document for k in WRAPPER_FIELDS):raise ValueError('Original physical report overlaps runner wrapper')
            wrapper={**document,'native_v2_runner_checkpoint':{
                'schema':CHECKPOINT_SCHEMA,'original_snapshot_sha256':digest(document),
                'stage':label,'stage_resources':list(self.current_resources),
                'scientific_execution_authorized':False}}
            if self.gate is not None:
                wrapper['native_v2_engineering_gate']={k:v for k,v in self.gate.items() if k!='association'}
                wrapper['native_v2_engineering_association']=self.gate.get('association',[])
            result=checkpoint(label,wrapper)
            after=self.clock()
            row={'stage':'checkpoint_write_'+label,
                'seconds':after-now,'completed':True,
                'timing_scope':'inclusive_nested_stages',
                'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
            self.current_resources.append(row);self.resources.append(row)
            boundary=after
            return result
        def measured_close(status,stage,reason='',*,snapshot=None):
            if status=='completed' and not plan['case']['spec']['reference']:
                # _execute has completed/hash-bound every physical decision.
                # Associate truth now, before this same terminal checkpoint.
                self.gate=self._stage('evaluate',lambda:chain.evaluate(snapshot,self.context,plan))
            return close(status,stage,reason,snapshot=snapshot)
        writer.checkpoint=measured_checkpoint;writer.close=measured_close

    def _save_state(self,record,*,failure=False):
        raw=canonical(record)
        # Failure receipts have a separate bounded forensic write allowance;
        # this never grants execution or publication time after the main cap.
        allowance=5 if failure else min(OPERATION_SECONDS,WHOLE_SECONDS-self._budget())
        with deadline(allowance):saved=self.persist_state(json.loads(raw))
        if saved!={'bytes':len(raw),'sha256':evidence.sha(raw)}:
            raise ValueError('Durable runner state receipt differs')
        if not failure:self._budget()

    def _result(self,status,error=None,*,failure=False):
        transport_error=None
        try:
            transport=self._transport_snapshot(validate=not failure)
        except BaseException as nested:
            if not failure:raise
            transport=None;transport_error=repr(nested)[:4096]
        result={'schema':SCHEMA,'status':status,'namespace':parent.NAMESPACE,
            'authority':self.authority,'cases':list(self.rows),'stage_resources':list(self.resources),
            'elapsed_seconds':0 if self.started is None else self.clock()-self.started,
            'whole_interleaved_wall_time_cap_seconds':WHOLE_SECONDS,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'broker_usage':None if self.publisher is None else self.publisher.usage(),
            'broker_receipts':[] if self.publisher is None else list(self.publisher.receipts),
            'broker_failed_attempt':None if self.publisher is None else self.publisher.failed_attempt,
            'raw_transport_receipts':list(self.raw_invoker.records),
            'transport_terminal_receipts':list(self.transport_receipts),
            'transport_usage':transport,
            'all_eight_allocation_remains_spent':True,'restart_authorized':False,
            'scientific_allocation_charged':False,'production_127_24_activated':False,
            'telescope_values_opened':False,'scientific_candidate':False}
        if error is not None:result['failure']={'error':repr(error)[:4096],'error_sha256':evidence.sha(repr(error).encode())}
        if transport_error is not None:result['transport_usage_error']=transport_error
        return result

    def _publish_terminal(self,ordinal,config):
        maps=self._stage('terminal_map_extraction',lambda:terminal_maps(self.store,self.lease,config),case_budget=False)
        physical,journal_files,base,pins=maps
        bundle=self._stage('broker_bundle',lambda:broker.prepare_bundle(physical,journal_files,base,
            ordinal=ordinal,expected_config_sha256=pins['config_sha256'],
            expected_last_checkpoint_sha256=pins['last_checkpoint_sha256'],
            expected_genesis_sha256=pins['genesis_sha256'],expected_pointer_sha256=pins['pointer_sha256'],
            expected_parent_sha=self.parent_sha,expected_parent_tree_sha=self.parent_tree_sha),case_budget=False)
        self._stage('prepare_transport',lambda:self.prepare_transport(bundle.freeze_bytes.decode('ascii'),bundle.sha256),
                    case_budget=False,seconds=OPERATION_SECONDS)
        receipt=self._stage('publication_and_readback',lambda:self.publisher.publish(bundle),case_budget=False)
        def finish():
            host=self.finish_transport()
            if (not isinstance(host,dict) or any(host.get(k)!=v for k,v in {
                    'ordinal':ordinal,'parent':self.parent_sha,'commit':receipt['commit'],
                    'tree':receipt['tree'],'bundle_sha256':bundle.sha256,'automatic_retry':False}.items())):
                raise ValueError('Host terminal receipt differs from exact Python publication/readback')
            usage=validate_transport_usage(host.get('actual_tool_usage'),case=True)
            if any(usage[k] for k in ('unknown_response_count','unknown_response_bytes',
                    'unknown_receipt_bytes','unknown_git_spool_bytes')):
                raise ValueError('Unknown host outcome cannot complete publication barrier')
            self.transport_receipts.append(json.loads(canonical(host)))
            return host
        self._stage('finish_transport',finish,case_budget=False,seconds=OPERATION_SECONDS)
        self.parent_sha=receipt['commit'];self.parent_tree_sha=receipt['tree']
        return receipt

    def run(self):
        if self.attempted or self.stopped:raise RunnerStopped('One runner invocation only; no retry',self._result('STOPPED',failure=True))
        self.attempted=True;self.started=self.clock()
        try:
            # Public proof and local runtime verification precede even local
            # event-store creation and every numerical constructor.
            self._stage('preflight_freeze',lambda:self._verify_freeze(self.manifest),case_budget=False,seconds=OPERATION_SECONDS)
            self._stage('preflight_reservation',self._verify_reservation,case_budget=False,seconds=OPERATION_SECONDS)
            self.target.mkdir(parents=True,exist_ok=False)
            self.store=self._stage('journal_create',lambda:events.EventDirectoryStore.create(self.target/'journal',self.manifest),case_budget=False)
            self.publisher=broker.CumulativeBroker(self._invoke,clock=self.clock)
            for ordinal,plan in enumerate(self.plans):
                self._budget();self.current_resources=[];self.gate=None
                self._stage('case_freeze',lambda:self._verify_freeze(self.manifest),case_budget=False,seconds=OPERATION_SECONDS)
                before=self.store.read()
                self.lease=self._stage('case_consume',lambda:journal.consume(self.store,expected_revision=before.revision,
                    expected_manifest_sha256=digest(self.manifest),binding=parent.case_binding(plan),
                    milliseconds=parent.CASE_MILLISECONDS,artifact_bytes=parent.CASE_BYTES,
                    directory=self.target/f'case{ordinal:02d}',clock=self.clock),case_budget=False)
                config=self.configs[ordinal]
                # Prospectively frozen configs have empty base pins. Create
                # their physical reservation before start/compact artifacts.
                self.physical_case=self._stage('physical_reservation',lambda:cases.PhysicalCase(self.lease,config,existing_artifacts={}))
                run,renderer=self._stage('render',lambda:chain.render(self.context,plan,
                    lease=self.lease,forbidden_cases=self.forbidden_cases,verify_freeze=self._verify_freeze))
                def scores():
                    store=run.build_store();run.validate_store(store);self.lease.budget(run.modelled_bytes);return store
                score_store=self._stage('score',scores)
                def compact_archive():
                    parts=gaussian.compact_parts(run,score_store,plan,renderer)
                    for name,data in parts.items():self.lease.write_artifact(name,data)
                    audit=compact.audit(self.context,
                        {k:v for k,v in parent.case_binding(plan).items() if k!='role'},parts,
                        expected_sha256s={k:evidence.sha(v) for k,v in parts.items()},byte_cap=parent.CASE_BYTES)
                    self.lease.write_artifact('compact_audit.json',canonical(audit))
                    return CadenceMaximum(parts['maximum.json'])
                unit=self._stage('compact_archive_and_audit',compact_archive)
                self._instrument(plan)
                if plan['case']['spec']['reference']:
                    report={'schema':'radio-native-v2-reference-only-physical-closure-v1',
                        'complete':True,'retention':{'case_identity':plan['case']['identity']},
                        'maximum_receipt':unit.record(),'physical_decisions_evaluated':False,
                        'reference_only':True,'scientific_admission_authorized':False}
                    self.gate={'schema':'radio-native-v2-reference-only-gate-v1',
                        'reference_only':True,'engineering_gate_pass':None,'scientific_candidate':False}
                    self._stage('reference_physical_closure',lambda:self.physical_case.writer.close(
                        'completed','reference_only',snapshot=report))
                else:
                    if self.threshold is None:raise ValueError('Four published fresh references required before evaluation')
                    self._stage('physical',lambda:chain.run_physical(run,score_store,self.threshold,plan,
                                                               evidence=self.physical_case.writer))
                    if self.gate is None:raise ValueError('Complete terminal postdecision gate missing')
                self._stage('case_closure',lambda:self.physical_case.finish(
                    reason=canonical({'stage_resources':self.current_resources}).decode()))
                receipt=self._publish_terminal(ordinal,config)
                state=journal.replay(self.store.read().document)['cases'][-1]
                self.rows.append({'ordinal':ordinal,'case_identity':plan['case']['identity'],
                    'status':state['status'],'engineering_gate_pass':self.gate.get('engineering_gate_pass'),
                    'gate_sha256':digest(self.gate),'publication':receipt,
                    'stage_resources':list(self.current_resources)})
                if ordinal<4:self.units.append(unit)
                if ordinal==3:
                    self.threshold=self._stage('threshold',lambda:chain.bind_threshold(self.context,self.units),case_budget=False)
                self._save_state(self._result('IN_PROGRESS'))
                # A physical engineering gate failure is terminal even though
                # its complete report/storage successfully closed and published.
                if self.gate.get('engineering_gate_pass') is False:
                    raise ValueError('Engineering physical gate failed; no next case')
                self.lease=None;self.physical_case=None
                del run,renderer,score_store,unit
                gc.collect()
            self._stage('final_freeze',lambda:self._verify_freeze(self.manifest),case_budget=False,seconds=OPERATION_SECONDS)
            result=self._result('CLOSED_ENGINEERING_PASS');self._save_state(result)
            self.stopped=True;return result
        except BaseException as error:
            self.stopped=True;closure=None;failure_publication=None
            # Broken/uncertain leases cannot be retried or papered over. The
            # original prefix/raw transport receipts stay available read-only.
            if self.lease is not None and not self.lease.closed and self.physical_case is not None:
                try:
                    with deadline(5):closure=self.physical_case.fail(error)
                except BaseException as nested:closure={'error':repr(nested)[:4096],'uncertain':True}
                if (self.lease.closed and self.publisher is not None and not self.publisher.stopped):
                    try:failure_publication=self._publish_terminal(len(self.rows),self.configs[len(self.rows)])
                    except BaseException as nested:failure_publication={'error':repr(nested)[:4096],'uncertain':True}
            result=self._result('CLOSED_FAILED',error,failure=True)
            result['failure_closure']=closure;result['failure_publication']=failure_publication
            try:self._save_state(result,failure=True)
            except BaseException as nested:result['runner_state_persistence_error']=repr(nested)[:4096]
            raise RunnerStopped('Fresh native-v2 runner stopped; no retry',result) from error
