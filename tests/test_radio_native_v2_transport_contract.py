import copy
import json
import unittest

from seti_repeater.empty_null_radio import canonical
from seti_repeater import native_v2_transport_contract_radio as c


def raw_record(ordinal,kind,tool):
    request=json.dumps({'tool':tool,'arguments':{'ordinal':ordinal}},separators=(',',':'))
    result={'ordinal':ordinal,'ok':True};response=json.dumps(result,separators=(',',':'))
    return {'ordinal':ordinal,'tool':tool,'kind':kind,'request_json':request,
        'request_bytes':len(request.encode()),'request_sha256':c._sha(request.encode()),
        'response_reserved_bytes':len(response.encode())+10,'response_unknown':False,
        'response_charged_bytes':len(response.encode()),'automatic_retry':False,
        'raw_result':result,'response_json':response,'response_bytes':len(response.encode()),
        'response_sha256':c._sha(response.encode())}


def client(polls=1,source_reads=1):
    records=[raw_record(0,'actual_controller_start','exec_command')]
    ordinal=1
    for n,tool in enumerate(c.CONNECTOR_SEQUENCE):
        if n==1:
            for _ in range(source_reads):
                records.append(raw_record(ordinal,'actual_source_read','exec_command'));ordinal+=1
        records.append(raw_record(ordinal,'actual_connector',tool));ordinal+=1
        records.append(raw_record(ordinal,'actual_delivery','write_stdin'));ordinal+=1
    for _ in range(polls):records.append(raw_record(ordinal,'actual_idle_poll','write_stdin'));ordinal+=1
    request=sum(r['request_bytes'] for r in records);response=sum(r['response_bytes'] for r in records)
    return {'schema':c.CLIENT_SCHEMA,'status':'SINGLE_CASE_COMPONENT_COMPLETE','reason':None,
        'usage':{'calls':len(records),'request_bytes':request,'response_bytes':response,
            'response_charged_bytes':response,'unknown_response_bytes':0,'unknown_response_count':0,
            'conservatively_charged_local_git_processes':4,
            'calls_including_declared_git_processes':len(records)+4,'elapsed_seconds':12.5,
            'hidden_http_bytes_known':False,'all_actual_start_poll_read_connector_delivery_calls_counted':True},
        'controller_terminal':{'schema':c.CONTROLLER_SCHEMA,'kind':'terminal',
            'status':'SINGLE_CASE_COMPONENT_ONLY'},'connector_requests':6,'records':records,'events':[],
        'pending_delivery_reservation':None,'last_supporting_acknowledgement_durable':False,
        'controller_poll_receipts_joined_into_host_ledger':False,'actual_client_runtime_rss_known':False,
        'prospective_caps':copy.deepcopy(c.QUALIFIED_CLIENT_CAPS),
        'execution_authorized':False,'reservation_authorized':False,'scientific_execution_authorized':False,
        'rng_draws':0,'telescope_reads':0,'automatic_retry':False}


def persistence(value):
    raw=c.caller_tail_payload(value);rows=json.loads(raw)['records']
    return {'schema':c.PERSISTENCE_SCHEMA,'client_sha256':c._sha(canonical(value)),
        'stored_record_ordinals':[r['ordinal'] for r in rows],
        'payload_bytes':len(raw),'payload_sha256':c._sha(raw),'durable':True,
        'single_authoritative_file':True,'exact_readback_verified':True,
        'includes_terminal_delivery_acknowledgement':True,'automatic_retry':False,
        'calls':1,'request_bytes':len(raw)+512,'response_bytes':128,
        'unknown_response_bytes':0,'unknown_response_count':0}


class ContractTests(unittest.TestCase):
    def test_exact_eight_case_transcript_closes_inside_all_caps(self):
        ledger=c.RunTranscript()
        for ordinal in range(8):
            value=client(polls=0,source_reads=39)
            case=ledger.append(ordinal,value,persistence(value),client_peak_rss_bytes=64*1024**2)
            self.assertEqual(case['calls'],57)
        receipt=ledger.receipt();self.assertEqual(receipt['status'],'COMPLETE')
        self.assertEqual(receipt['case_count'],8);self.assertEqual(receipt['calls'],456)

    def test_every_poll_is_charged_and_excess_stops_without_retry(self):
        value=client(polls=48);ledger=c.RunTranscript()
        with self.assertRaisesRegex(ValueError,'allocation exceeded'):
            ledger.append(0,value,persistence(value),client_peak_rss_bytes=1)
        self.assertTrue(ledger.stopped)
        with self.assertRaisesRegex(RuntimeError,'no retry'):
            ledger.append(0,client(),persistence(client()),client_peak_rss_bytes=1)

    def test_lost_or_changed_envelope_and_fake_late_custody_are_refused(self):
        for mutate in ('unknown','raw','persistence'):
            with self.subTest(mutate=mutate):
                value=client();proof=persistence(value)
                if mutate=='unknown':value['records'][0]['response_unknown']=True
                elif mutate=='raw':value['records'][0]['raw_result']['ok']=False
                else:proof['includes_terminal_delivery_acknowledgement']=False
                with self.assertRaises(ValueError):c.RunTranscript().append(0,value,proof,client_peak_rss_bytes=1)

    def test_client_rss_must_be_measured_and_bounded(self):
        value=client();proof=persistence(value)
        for rss in (0,c.RSS_BYTES+1):
            with self.assertRaisesRegex(ValueError,'RSS'):
                c.RunTranscript().append(0,value,proof,client_peak_rss_bytes=rss)

    def test_sequence_and_cumulative_case_identity_are_append_only(self):
        value=client();ledger=c.RunTranscript()
        with self.assertRaisesRegex(ValueError,'ordinal'):
            ledger.append(1,value,persistence(value),client_peak_rss_bytes=1)


if __name__=='__main__':unittest.main()
