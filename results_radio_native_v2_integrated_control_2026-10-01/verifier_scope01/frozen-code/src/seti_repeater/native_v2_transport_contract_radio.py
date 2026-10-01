"""Versioned shared caller/host transcript contract for native-v2 publication.

This module grants no execution or reservation authority.  It closes the
accounting gap between the portable caller (which sees start, polls, source
reads, connectors and deliveries) and the local host (which sees publication
and Git custody).  A later execution freeze must pin this code and must supply
independently durable receipts for every accepted case.
"""
import hashlib
import json
import math

from .empty_null_radio import canonical

SCHEMA='radio-native-v2-runner-shared-transport-v2'
CASE_SCHEMA='radio-native-v2-runner-shared-case-v2'
CLIENT_SCHEMA='radio-native-v2-single-exec-tool-courier-v1'
CONTROLLER_SCHEMA='radio-native-v2-local-tool-courier-v1'
PERSISTENCE_SCHEMA='radio-native-v2-caller-transcript-persistence-v2'
CASE_CALLS=64
TOTAL_CALLS=512
CASE_REQUEST_BYTES=48*1024**2
TOTAL_REQUEST_BYTES=384*1024**2
CASE_RESPONSE_BYTES=64*1024**2
TOTAL_RESPONSE_BYTES=512*1024**2
CASE_SECONDS=600
TOTAL_SECONDS=4800
RSS_BYTES=512*1024**2
GIT_PROCESSES=4
QUALIFIED_CLIENT_CAPS={'actual_calls':59,'request_bytes':40*1024**2,
    'response_bytes':64*1024**2-256*1024,'support_yield_time_ms':30000,
    'caller_tail_calls':1,'caller_tail_request_bytes':8*1024**2,
    'caller_tail_response_bytes':256*1024}
CONNECTOR_SEQUENCE=('mcp__codex_apps__github_fetch','mcp__codex_apps__github_create_tree',
    'mcp__codex_apps__github_create_commit','mcp__codex_apps__github_fetch',
    'mcp__codex_apps__github_update_ref','mcp__codex_apps__github_fetch')
CALL_KINDS={'actual_controller_start','actual_idle_poll','actual_source_read',
            'actual_connector','actual_delivery'}


def _sha(data):return hashlib.sha256(data).hexdigest()


def _integer(value,label):
    if type(value) is not int or value<0:raise ValueError('Nonnegative integer required: '+label)
    return value


def _validate_record(record,ordinal):
    if (not isinstance(record,dict) or record.get('ordinal')!=ordinal
            or record.get('kind') not in CALL_KINDS or record.get('response_unknown') is not False
            or record.get('automatic_retry') is not False):
        raise ValueError('Exact ordered complete caller record required')
    request=record.get('request_json');response=record.get('response_json')
    if (not isinstance(request,str) or not isinstance(response,str)
            or record.get('request_bytes')!=len(request.encode())
            or record.get('response_bytes')!=len(response.encode())
            or record.get('request_sha256')!=_sha(request.encode())
            or record.get('response_sha256')!=_sha(response.encode())):
        raise ValueError('Complete caller envelope bytes and hashes required')
    try:restored=json.loads(response)
    except (TypeError,json.JSONDecodeError) as error:
        raise ValueError('Retained caller response is not exact JSON') from error
    if restored!=record.get('raw_result'):
        raise ValueError('Untouched raw caller result differs from retained JSON')
    try:request_object=json.loads(request)
    except (TypeError,json.JSONDecodeError) as error:
        raise ValueError('Retained caller request is not exact JSON') from error
    if (not isinstance(request_object,dict) or set(request_object)!={'tool','arguments'}
            or request_object['tool']!=record.get('tool')
            or not isinstance(request_object['arguments'],dict)):
        raise ValueError('Caller record tool differs from its actual request')
    reserved=_integer(record.get('response_reserved_bytes'),'response_reserved_bytes')
    if reserved<record['response_bytes'] or record.get('response_charged_bytes')!=record['response_bytes']:
        raise ValueError('Complete caller response exceeded its prospective reservation')
    return record


def validate_client(value,*,qualified=False):
    """Validate the complete visible caller transcript for one terminal case."""
    if (not isinstance(value,dict) or value.get('schema')!=CLIENT_SCHEMA
            or value.get('status')!='SINGLE_CASE_COMPONENT_COMPLETE' or value.get('reason') is not None
            or value.get('connector_requests')!=6 or value.get('pending_delivery_reservation') is not None
            or value.get('automatic_retry') is not False):
        raise ValueError('Complete successful single-case caller transcript required')
    for field in ('execution_authorized','reservation_authorized','scientific_execution_authorized'):
        if value.get(field) is not False:raise ValueError('Caller component cannot grant authority')
    if value.get('rng_draws')!=0 or value.get('telescope_reads')!=0:
        raise ValueError('Transport transcript cannot contain science activity')
    records=value.get('records')
    if not isinstance(records,list) or not records:raise ValueError('Nonempty caller records required')
    for ordinal,record in enumerate(records):_validate_record(record,ordinal)
    kinds=[r['kind'] for r in records]
    if (kinds.count('actual_controller_start')!=1 or kinds[0]!='actual_controller_start'
            or kinds.count('actual_connector')!=6 or kinds.count('actual_delivery')!=6):
        raise ValueError('Exact start/connector/delivery caller sequence required')
    connectors=tuple(r['tool'] for r in records if r['kind']=='actual_connector')
    if connectors!=CONNECTOR_SEQUENCE:raise ValueError('Exact connector sequence required')
    phase=0;awaiting_delivery=False
    for record in records[1:]:
        kind=record['kind']
        if kind=='actual_connector':
            if awaiting_delivery or phase>=6:raise ValueError('Sequential connector delivery required')
            awaiting_delivery=True
        elif kind=='actual_delivery':
            if not awaiting_delivery:raise ValueError('Sequential connector delivery required')
            awaiting_delivery=False;phase+=1
        elif kind=='actual_source_read':
            if awaiting_delivery or phase!=1:raise ValueError('Source reads require the single tree request')
        elif kind=='actual_idle_poll':
            if awaiting_delivery:raise ValueError('Poll must precede the next controller frame')
        else:raise ValueError('Only one initial startup is permitted')
    if awaiting_delivery or phase!=6:raise ValueError('Complete sequential connector deliveries required')
    usage=value.get('usage')
    if not isinstance(usage,dict):raise ValueError('Complete caller usage required')
    calls=_integer(usage.get('calls'),'calls')
    request_bytes=_integer(usage.get('request_bytes'),'request_bytes')
    response_bytes=_integer(usage.get('response_bytes'),'response_bytes')
    charged=_integer(usage.get('response_charged_bytes'),'response_charged_bytes')
    if (calls!=len(records) or request_bytes!=sum(r['request_bytes'] for r in records)
            or response_bytes!=sum(r['response_bytes'] for r in records) or charged!=response_bytes
            or usage.get('unknown_response_bytes')!=0 or usage.get('unknown_response_count')!=0
            or usage.get('conservatively_charged_local_git_processes')!=GIT_PROCESSES
            or usage.get('calls_including_declared_git_processes')!=calls+GIT_PROCESSES
            or usage.get('all_actual_start_poll_read_connector_delivery_calls_counted') is not True
            or usage.get('hidden_http_bytes_known') is not False):
        raise ValueError('Exact complete caller accounting required')
    elapsed=usage.get('elapsed_seconds')
    if (calls+GIT_PROCESSES>CASE_CALLS or request_bytes>CASE_REQUEST_BYTES
            or response_bytes>CASE_RESPONSE_BYTES or type(elapsed) not in (int,float)
            or not math.isfinite(elapsed) or not 0<=elapsed<=CASE_SECONDS):
        raise ValueError('Caller case allocation exceeded')
    terminal=value.get('controller_terminal')
    if (not isinstance(terminal,dict) or terminal.get('schema')!=CONTROLLER_SCHEMA
            or terminal.get('kind')!='terminal' or terminal.get('status')!='SINGLE_CASE_COMPONENT_ONLY'):
        raise ValueError('Exact controller terminal pointer required')
    supporting=[r for r in records if r['kind'] in ('actual_controller_start','actual_idle_poll','actual_delivery')]
    if any(not isinstance(r['raw_result'].get('output'),str) for r in supporting):
        raise ValueError('Complete supporting controller output required')
    try:
        frames=[json.loads(line) for line in ''.join(r['raw_result']['output'] for r in supporting).splitlines()
            if line.strip()]
    except json.JSONDecodeError as error:
        raise ValueError('Complete controller frame transcript required') from error
    observed=[frame for frame in frames if isinstance(frame,dict) and frame.get('kind')=='terminal']
    if observed!=[terminal]:raise ValueError('Controller terminal differs from its actual raw acknowledgement')
    # The controller cannot observe the acknowledgement of its own terminal
    # delivery.  Durable custody is therefore supplied separately below.
    if value.get('last_supporting_acknowledgement_durable') is not False:
        raise ValueError('Caller/controller boundary must not self-certify late custody')
    if qualified and value.get('prospective_caps')!=QUALIFIED_CLIENT_CAPS:
        raise ValueError('Tail capacity and 30-second wait must be reserved before caller start')
    if qualified and (calls>QUALIFIED_CLIENT_CAPS['actual_calls']
            or request_bytes>QUALIFIED_CLIENT_CAPS['request_bytes']
            or response_bytes>QUALIFIED_CLIENT_CAPS['response_bytes']
            or kinds.count('actual_idle_poll')>7):
        raise ValueError('Prospectively reduced caller allocation exceeded')
    return json.loads(canonical(value))


def client_binding_payload(client):
    """Bind exact envelopes through a small, cross-runtime integer projection.

    SHA256 pins bind every retained request and response without copying large
    source envelopes into the tail. Status, authority, sequence and counter
    consistency are independently checked by validate_client.
    """
    fields=('calls','request_bytes','response_bytes','response_charged_bytes',
        'unknown_response_bytes','unknown_response_count',
        'conservatively_charged_local_git_processes','calls_including_declared_git_processes')
    usage={key:_integer(client['usage'][key],key) for key in fields}
    usage['elapsed_milliseconds']=math.ceil(client['usage']['elapsed_seconds']*1000)
    records=[{key:record[key] for key in ('ordinal','kind','tool','request_bytes',
        'request_sha256','response_bytes','response_sha256')} for record in client['records']]
    return canonical({'schema':'radio-native-v2-caller-binding-v1',
        'prospective_caps':client['prospective_caps'],'records':records,'usage':usage})


def client_binding_sha256(client):return _sha(client_binding_payload(client))


def caller_tail_payload(client):
    """Return only raw caller envelopes that the successful host cannot own.

    Connector, source-read, startup and all but the final delivery envelopes
    are already retained/reconstructed by the controller/host.  Idle polls and
    the acknowledgement returned by the final delivery exist only in the
    outer caller and therefore need one separate, small durable tail artifact.
    """
    records=client['records'];deliveries=[r['ordinal'] for r in records if r['kind']=='actual_delivery']
    if not deliveries:raise ValueError('Final delivery acknowledgement required')
    selected=[r for r in records if r['kind']=='actual_idle_poll' or r['ordinal']==deliveries[-1]]
    return canonical({'schema':'radio-native-v2-caller-only-tail-v2',
        'client_sha256':client_binding_sha256(client),
        'records':[{'ordinal':r['ordinal'],'response_json':r['response_json']} for r in selected]})


def validate_persistence(value,client):
    """Validate one independently durable caller-only tail and its tool cost."""
    payload=caller_tail_payload(client)
    selected=json.loads(payload)['records'];ordinals=[r['ordinal'] for r in selected]
    if not isinstance(value,dict):raise ValueError('Independent caller tail persistence required')
    expected={'schema':PERSISTENCE_SCHEMA,'client_sha256':client_binding_sha256(client),
        'stored_record_ordinals':ordinals,'payload_bytes':len(payload),'payload_sha256':_sha(payload),
        'durable':True,'single_authoritative_file':True,'exact_readback_verified':True,
        'includes_terminal_delivery_acknowledgement':True,'automatic_retry':False,
        'calls':1,'unknown_response_bytes':0,'unknown_response_count':0}
    if any(value.get(k)!=v for k,v in expected.items()):
        raise ValueError('Independent exact caller tail persistence required')
    request=_integer(value.get('request_bytes'),'tail_request_bytes')
    response=_integer(value.get('response_bytes'),'tail_response_bytes')
    if request<len(payload) or request>QUALIFIED_CLIENT_CAPS['caller_tail_request_bytes'] or response>256*1024:
        raise ValueError('Caller tail persistence envelope exceeded')
    request_json=value.get('request_json');response_json=value.get('response_json')
    if (not isinstance(request_json,str) or not isinstance(response_json,str)
            or len(request_json.encode())!=request or len(response_json.encode())!=response
            or value.get('request_sha256')!=_sha(request_json.encode())
            or value.get('response_sha256')!=_sha(response_json.encode())):
        raise ValueError('Complete actual caller tail envelopes required')
    try:
        dispatched=json.loads(request_json);raw=json.loads(response_json)
        helper=json.loads(raw['output'])
    except (TypeError,KeyError,json.JSONDecodeError) as error:
        raise ValueError('Complete actual caller tail readback response required') from error
    if (not isinstance(dispatched,dict) or set(dispatched)!={'tool','arguments'}
            or dispatched['tool']!='exec_command' or not isinstance(dispatched['arguments'],dict)
            or raw!=value.get('raw_result') or raw.get('exit_code')!=0 or 'session_id' in raw
            or helper.get('schema')!='radio-native-v2-caller-tail-readback-v1'):
        raise ValueError('Actual terminal caller tail tool reply required')
    helper_expected={key:expected[key] for key in ('client_sha256','stored_record_ordinals',
        'payload_bytes','payload_sha256','durable','single_authoritative_file',
        'exact_readback_verified','includes_terminal_delivery_acknowledgement','automatic_retry')}
    helper_expected.update(directory_entry_fsynced=True,independent_reopen=True,
        reopened_bytes=len(payload),reopened_sha256=_sha(payload))
    if any(helper.get(key)!=wanted for key,wanted in helper_expected.items()):
        raise ValueError('Independent reopened caller tail bytes differ')
    start=_integer(value.get('dispatch_at_epoch_ms'),'tail_dispatch_at_epoch_ms')
    end=_integer(value.get('returned_at_epoch_ms'),'tail_returned_at_epoch_ms')
    elapsed=value.get('elapsed_seconds')
    if (end<start or type(elapsed) not in (int,float) or not math.isfinite(elapsed)
            or elapsed<0 or abs(elapsed-(end-start)/1000)>0.001):
        raise ValueError('Actual caller tail elapsed time differs')
    shared_start=_integer(value.get('shared_case_started_at_epoch_ms'),'shared_case_started_at_epoch_ms')
    shared_end=_integer(value.get('shared_case_finished_at_epoch_ms'),'shared_case_finished_at_epoch_ms')
    shared_elapsed=value.get('shared_case_elapsed_seconds')
    if (shared_start>start or shared_end<end or type(shared_elapsed) not in (int,float)
            or not math.isfinite(shared_elapsed) or shared_elapsed<0
            or abs(shared_elapsed-(shared_end-shared_start)/1000)>0.001
            or shared_elapsed+0.001<client['usage']['elapsed_seconds']+elapsed):
        raise ValueError('Complete shared caller preparation/custody/observer time required')
    return json.loads(canonical(value))


class RunTranscript:
    """Append-only eight-case outer accounting; any ambiguity permanently stops."""
    def __init__(self):
        self.cases=[];self.stopped=False

    def append(self,ordinal,client,persistence,*,client_peak_rss_bytes):
        if self.stopped:raise RuntimeError('Shared transport transcript stopped; no retry')
        try:
            if ordinal!=len(self.cases) or not 0<=ordinal<8:
                raise ValueError('Exact next case ordinal required')
            client=validate_client(client,qualified=True);persistence=validate_persistence(persistence,client)
            rss=_integer(client_peak_rss_bytes,'client_peak_rss_bytes')
            if rss<=0 or rss>RSS_BYTES:raise ValueError('Measured caller process RSS cap exceeded')
            usage=client['usage']
            case={'schema':CASE_SCHEMA,'ordinal':ordinal,'client':client,'persistence':persistence,
                'client_peak_rss_bytes':rss,'calls':usage['calls_including_declared_git_processes'],
                'request_bytes':usage['request_bytes'],'response_bytes':usage['response_bytes'],
                'elapsed_seconds':usage['elapsed_seconds'],'automatic_retry':False,
                'execution_authorized':False,'scientific_execution_authorized':False}
            case['calls']+=persistence['calls'];case['request_bytes']+=persistence['request_bytes']
            case['response_bytes']+=persistence['response_bytes']
            tail_seconds=persistence.get('elapsed_seconds')
            if type(tail_seconds) not in (int,float) or not math.isfinite(tail_seconds) or tail_seconds<0:
                raise ValueError('Measured caller tail elapsed time required')
            case['elapsed_seconds']=persistence['shared_case_elapsed_seconds']
            if (case['calls']>CASE_CALLS or case['request_bytes']>CASE_REQUEST_BYTES
                    or case['response_bytes']>CASE_RESPONSE_BYTES or case['elapsed_seconds']>CASE_SECONDS):
                raise ValueError('Combined caller case allocation exceeded')
            trial=self.cases+[case]
            if (sum(c['calls'] for c in trial)>TOTAL_CALLS
                    or sum(c['request_bytes'] for c in trial)>TOTAL_REQUEST_BYTES
                    or sum(c['response_bytes'] for c in trial)>TOTAL_RESPONSE_BYTES
                    or sum(c['elapsed_seconds'] for c in trial)>TOTAL_SECONDS):
                raise ValueError('Cumulative eight-case caller allocation exceeded')
            self.cases.append(case);return json.loads(canonical(case))
        except BaseException:
            self.stopped=True;raise

    def receipt(self):
        return {'schema':SCHEMA,'status':'COMPLETE' if len(self.cases)==8 and not self.stopped else 'INCOMPLETE',
            'cases':json.loads(canonical(self.cases)),'case_count':len(self.cases),
            'calls':sum(c['calls'] for c in self.cases),
            'request_bytes':sum(c['request_bytes'] for c in self.cases),
            'response_bytes':sum(c['response_bytes'] for c in self.cases),
            'elapsed_seconds':sum(c['elapsed_seconds'] for c in self.cases),
            'all_visible_polls_and_deliveries_counted':True,'hidden_http_bytes_known':False,
            'automatic_retry':False,'execution_authorized':False,
            'scientific_execution_authorized':False}
