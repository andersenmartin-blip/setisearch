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
PERSISTENCE_SCHEMA='radio-native-v2-caller-transcript-persistence-v1'
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
    # The controller cannot observe the acknowledgement of its own terminal
    # delivery.  Durable custody is therefore supplied separately below.
    if value.get('last_supporting_acknowledgement_durable') is not False:
        raise ValueError('Caller/controller boundary must not self-certify late custody')
    if qualified and value.get('prospective_caps')!=QUALIFIED_CLIENT_CAPS:
        raise ValueError('Tail capacity and 30-second wait must be reserved before caller start')
    return json.loads(canonical(value))


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
    return canonical({'schema':'radio-native-v2-caller-only-tail-v1',
        'client_sha256':_sha(canonical(client)),
        'records':[{'ordinal':r['ordinal'],'response_json':r['response_json']} for r in selected]})


def validate_persistence(value,client):
    """Validate one independently durable caller-only tail and its tool cost."""
    payload=caller_tail_payload(client)
    selected=json.loads(payload)['records'];ordinals=[r['ordinal'] for r in selected]
    if not isinstance(value,dict):raise ValueError('Independent caller tail persistence required')
    expected={'schema':PERSISTENCE_SCHEMA,'client_sha256':_sha(canonical(client)),
        'stored_record_ordinals':ordinals,'payload_bytes':len(payload),'payload_sha256':_sha(payload),
        'durable':True,'single_authoritative_file':True,'exact_readback_verified':True,
        'includes_terminal_delivery_acknowledgement':True,'automatic_retry':False,
        'calls':1,'unknown_response_bytes':0,'unknown_response_count':0}
    if any(value.get(k)!=v for k,v in expected.items()):
        raise ValueError('Independent exact caller tail persistence required')
    request=_integer(value.get('request_bytes'),'tail_request_bytes')
    response=_integer(value.get('response_bytes'),'tail_response_bytes')
    if request<len(payload) or request>CASE_REQUEST_BYTES or response>256*1024:
        raise ValueError('Caller tail persistence envelope exceeded')
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
            if (case['calls']>CASE_CALLS or case['request_bytes']>CASE_REQUEST_BYTES
                    or case['response_bytes']>CASE_RESPONSE_BYTES):
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
