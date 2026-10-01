import base64
import copy
import json
import unittest

from seti_repeater import native_v2_transport_contract_radio as c
from test_radio_native_v2_transport_contract import client,raw_record


def streaming_proof(value):
    payload=c.caller_tail_payload(value);selected=json.loads(payload)
    wire=json.dumps(selected,ensure_ascii=False,separators=(',',':')).encode()
    ordinals=[r['ordinal'] for r in selected['records']]
    authority={'execution_authorized':False,'reservation_authorized':False,
        'scientific_execution_authorized':False,'automatic_retry':False,'rng_draws':0,'telescope_reads':0}
    pins={'client_sha256':c.client_binding_sha256(value),'payload_bytes':len(payload),
        'payload_sha256':c._sha(payload),'wire_bytes':len(wire),'wire_sha256':c._sha(wire),
        'destination':'/tmp/fresh-streaming-fixture/tail.json'}
    maximum=((2*7*256*1024+2048+2)//3)*4
    ready={'schema':'radio-native-v2-streaming-caller-tail-ready-v1','kind':'ready',
        **pins,**authority,
        'terminal_ordinal':[r['ordinal'] for r in value['records'] if r['kind']=='actual_delivery'][-1],
        'input_encoding':'base64_utf8_json',
        'maximum_base64_bytes':maximum,'max_stdin_bytes':maximum+1,'stdin_raw_noecho_ready':True,
        'stdin_is_tty':True,'stdin_mode':'tty_raw_noecho'}
    receipt={'schema':'radio-native-v2-streaming-caller-tail-readback-v1',**pins,**authority,
        'stored_record_ordinals':ordinals,'durable':True,'single_authoritative_file':True,
        'exact_readback_verified':True,'includes_terminal_delivery_acknowledgement':True,
        'directory_entry_fsynced':True,'independent_reopen':True,'reopened_bytes':len(payload),
        'reopened_sha256':c._sha(payload)}
    args=[{'cmd':'pinned-python pinned-tail-helper','tty':True,'max_output_tokens':4096,'yield_time_ms':1000},
        {'session_id':31,'chars':base64.b64encode(wire).decode()+'\n',
            'max_output_tokens':4096,'yield_time_ms':30000}]
    raws=[{'session_id':31,'output':json.dumps(ready)+'\n'},
        {'exit_code':0,'output':json.dumps(receipt)+'\n'}]
    rows=[]
    for n in range(2):
        tool=('exec_command','write_stdin')[n]
        request=json.dumps({'tool':tool,'arguments':args[n]},separators=(',',':'))
        response=json.dumps(raws[n],separators=(',',':'))
        rows.append({'ordinal':n,'tool':tool,'kind':('actual_caller_tail_start','actual_caller_tail_transfer')[n],
            'request_json':request,'request_bytes':len(request.encode()),'request_sha256':c._sha(request.encode()),
            'response_json':response,'response_bytes':len(response.encode()),'response_sha256':c._sha(response.encode()),
            'raw_result':raws[n],'response_reserved_bytes':(4096,252*1024)[n],
            'response_charged_bytes':len(response.encode()),'response_unknown':False,'automatic_retry':False,
            'dispatch_at_epoch_ms':13000+2*n,'returned_at_epoch_ms':13001+2*n,'elapsed_seconds':0.001})
    return {'schema':c.STREAMING_PERSISTENCE_SCHEMA,**pins,'stored_record_ordinals':ordinals,
        'durable':True,'single_authoritative_file':True,'exact_readback_verified':True,
        'includes_terminal_delivery_acknowledgement':True,'automatic_retry':False,'calls':2,
        'request_bytes':sum(r['request_bytes'] for r in rows),'response_bytes':sum(r['response_bytes'] for r in rows),
        'unknown_response_bytes':0,'unknown_response_count':0,'records':rows,
        'dispatch_at_epoch_ms':13000,'returned_at_epoch_ms':13003,'elapsed_seconds':0.003,
        'shared_case_started_at_epoch_ms':0,'shared_case_finished_at_epoch_ms':13003,
        'shared_case_elapsed_seconds':13.003,'stored_bytes':len(payload),'stored_items':1,
        'stored_bytes_reserved':6*7*256*1024+2048,'storage_kind':'host_receipt'}


def streaming_client(polls=6,large=False):
    value=client(polls=polls,source_reads=39)
    value['prospective_caps']=copy.deepcopy(c.QUALIFIED_STREAMING_CLIENT_CAPS)
    if large:
        for row in value['records']:
            if row['kind']=='actual_idle_poll':
                row['raw_result']['padding']='\x7f'*30000
                response=json.dumps(row['raw_result'],ensure_ascii=False,separators=(',',':'))
                row.update(response_json=response,response_bytes=len(response.encode()),
                    response_sha256=c._sha(response.encode()),response_reserved_bytes=256*1024,
                    response_charged_bytes=len(response.encode()))
        value['usage']['response_bytes']=sum(r['response_bytes'] for r in value['records'])
        value['usage']['response_charged_bytes']=value['usage']['response_bytes']
    return value


class StreamingContractTests(unittest.TestCase):
    def test_full_call_bound_and_large_escaped_tail_are_charged_exactly(self):
        value=streaming_client(large=True);proof=streaming_proof(value)
        self.assertGreater(proof['payload_bytes'],1024**2)
        self.assertLess(proof['wire_bytes'],proof['payload_bytes'])
        ledger=c.RunTranscript();case=ledger.append(0,value,proof,client_peak_rss_bytes=64*1024**2)
        self.assertEqual(case['calls'],64)
        self.assertEqual(case['elapsed_seconds'],13.003)
        self.assertEqual(case['persistence']['stored_bytes'],proof['payload_bytes'])
        self.assertEqual(ledger.receipt()['status'],'INCOMPLETE')

    def test_seventh_poll_cannot_borrow_second_tail_call(self):
        value=streaming_client(polls=7)
        with self.assertRaisesRegex(ValueError,'allocation exceeded'):
            c.RunTranscript().append(0,value,streaming_proof(value),client_peak_rss_bytes=1)

    def test_terminal_frame_may_arrive_in_a_poll_after_last_delivery(self):
        value=streaming_client(polls=5)
        delivery=value['records'][-1];delivery['raw_result']['output']=''
        response=json.dumps(delivery['raw_result'],separators=(',',':'))
        delivery.update(response_json=response,response_bytes=len(response.encode()),
            response_charged_bytes=len(response.encode()),response_sha256=c._sha(response.encode()))
        poll=raw_record(len(value['records']),'actual_idle_poll','write_stdin',terminal=True)
        value['records'].append(poll)
        usage=value['usage'];usage['calls']+=1;usage['calls_including_declared_git_processes']+=1
        usage['request_bytes']=sum(r['request_bytes'] for r in value['records'])
        usage['response_bytes']=sum(r['response_bytes'] for r in value['records'])
        usage['response_charged_bytes']=usage['response_bytes']
        result=c.RunTranscript().append(0,value,streaming_proof(value),client_peak_rss_bytes=1)
        self.assertEqual(result['calls'],64)

    def test_raw_mode_lost_terminal_and_session_change_are_refused(self):
        value=streaming_client()
        for mutation in ('raw_mode','running','session','reserved','missing'):
            proof=streaming_proof(value)
            if mutation=='missing':proof['records'].pop()
            else:
                n=0 if mutation=='raw_mode' else 1;row=proof['records'][n]
                if mutation=='raw_mode':
                    ready=json.loads(row['raw_result']['output']);ready['stdin_raw_noecho_ready']=False
                    row['raw_result']['output']=json.dumps(ready)+'\n'
                elif mutation=='running':row['raw_result']['session_id']=31
                elif mutation=='session':
                    dispatched=json.loads(row['request_json']);dispatched['arguments']['session_id']=32
                    row['request_json']=json.dumps(dispatched,separators=(',',':'))
                    row['request_bytes']=len(row['request_json'].encode())
                    row['request_sha256']=c._sha(row['request_json'].encode())
                else:row['response_reserved_bytes']+=1
                response=json.dumps(row['raw_result'],separators=(',',':'))
                row.update(response_json=response,response_bytes=len(response.encode()),
                    response_sha256=c._sha(response.encode()),response_charged_bytes=len(response.encode()))
                proof['request_bytes']=sum(r['request_bytes'] for r in proof['records'])
                proof['response_bytes']=sum(r['response_bytes'] for r in proof['records'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                c.validate_persistence(proof,value)

    def test_changed_wire_cannot_be_accepted_using_unchanged_readback_claim(self):
        value=streaming_client();proof=streaming_proof(value);row=proof['records'][1]
        dispatched=json.loads(row['request_json']);wire=json.loads(base64.b64decode(dispatched['arguments']['chars']))
        wire['records'][0]['response_json']='{}'
        dispatched['arguments']['chars']=base64.b64encode(json.dumps(wire).encode()).decode()+'\n'
        row['request_json']=json.dumps(dispatched,separators=(',',':'))
        row['request_bytes']=len(row['request_json'].encode());row['request_sha256']=c._sha(row['request_json'].encode())
        proof['request_bytes']=sum(r['request_bytes'] for r in proof['records'])
        with self.assertRaisesRegex(ValueError,'differs from complete caller'):
            c.validate_persistence(proof,value)

    def test_one_call_allocation_cannot_accept_two_call_persistence(self):
        value=streaming_client();proof=streaming_proof(value)
        value['prospective_caps']=copy.deepcopy(c.QUALIFIED_CLIENT_CAPS)
        with self.assertRaises(ValueError):c.validate_persistence(proof,value)

    def test_canonical_storage_bytes_cannot_be_charged_as_smaller_wire_bytes(self):
        value=streaming_client(large=True);proof=streaming_proof(value)
        proof['stored_bytes']=proof['wire_bytes']
        with self.assertRaisesRegex(ValueError,'two-call tail persistence'):
            c.validate_persistence(proof,value)


if __name__=='__main__':unittest.main()
