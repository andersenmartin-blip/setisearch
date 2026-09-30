"""Inline terminal broker packing, exact tree/readback and stop conditions."""
import base64
import copy
import hashlib
import unittest
from dataclasses import replace
from unittest.mock import patch

from seti_repeater import native_v2_broker_radio as b
from seti_repeater import physical_evidence_v2_radio as physical
import test_radio_event_archive_remote as remote


class InlineGit(remote.FakeGit):
    def __init__(self):
        super().__init__();self.inline_requests=[];self.bad_grouped=False

    def invoke(self,operation,params):
        if operation=='create_tree' and any('content' in row for row in params['tree_elements']):
            self.inline_requests.append(copy.deepcopy(params['tree_elements']))
            changed={**params,'tree_elements':[{**{k:v for k,v in row.items() if k!='content'},
                'sha':self.blob(row['content'].encode())} for row in params['tree_elements']]}
            return super().invoke(operation,changed)
        if operation=='fetch_files':
            self.calls.append((operation,params));leaves=self.flatten(self.commits[params['ref']]['tree']['sha']);result={}
            for index,path in enumerate(params['paths']):
                data=self.blobs[leaves[path]]
                if self.bad_grouped and index==0:data=(bytes([data[0]^1])+data[1:]) if data else b'x'
                result[path]={'sha':leaves[path],'content':base64.b64encode(data).decode()}
            return result
        return super().invoke(operation,params)


class NativeV2BrokerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=remote.RemoteArchiveTests('test_all_exact_bytes_single_commit_tree_and_immutable_readback')
        self.fixture.setUp();self.git=InlineGit()

    def tearDown(self):self.fixture.tearDown()

    def bundle(self,ordinal=0,**changes):
        args={'ordinal':ordinal,'expected_config_sha256':self.fixture.writer.config_sha,
            'expected_last_checkpoint_sha256':self.fixture.writer.previous,
            'expected_genesis_sha256':self.fixture.store.genesis_sha256,
            'expected_pointer_sha256':self.fixture.journal['HEAD'][:-1].decode(),
            'expected_parent_sha':self.git.head,
            'expected_parent_tree_sha':self.git.commits[self.git.head]['tree']['sha']}
        args.update(changes)
        return b.prepare_bundle(self.fixture.physical,self.fixture.journal,self.fixture.base,**args)

    def test_exact_sources_pack_into_bounded_inline_chunks_and_restore(self):
        bundle=self.bundle();freeze=__import__('json').loads(bundle.freeze_bytes)
        self.assertLessEqual(len(bundle.files),28);self.assertTrue(all(path.startswith(bundle.prefix+'/') for path in bundle.files))
        restored=b.restore(bundle.files,expected_manifest_sha256=freeze['manifest_sha256'],expected_prefix=bundle.prefix)
        expected={group+'/'+name:data for group,values in [('base',self.fixture.base),
            ('journal',self.fixture.journal),('physical',self.fixture.physical)] for name,data in sorted(values.items())}
        self.assertEqual(restored,expected);self.assertTrue(freeze['single_inline_tree_request'])
        self.assertTrue(freeze['single_grouped_readback'])

    def test_worst_case_inline_and_cumulative_envelopes_fit(self):
        record=b.capacity_record()
        self.assertEqual((record['source_bytes'],record['chunks'],record['remote_files']),
            (26*1024**2,26,28))
        self.assertLessEqual(record['stored_bytes_including_head_and_manifest_reserve'],36*1024**2)
        self.assertLessEqual(record['create_tree_request_bytes_including_framing_reserve'],48*1024**2)
        self.assertLessEqual(record['grouped_response_bytes_including_framing_reserve'],64*1024**2)

    def test_durable_invoker_persists_raw_result_before_caller_parses_it(self):
        order=[];saved=[]
        def transport(operation,params):
            order.append(('transport',operation));return {'value':params['value']}
        def persist(ordinal,operation,request,result):
            order.append(('persist',operation));saved.append((ordinal,request,result))
            raw=b.canonical(result)
            return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        adapter=b.DurableInvoker(transport,persist)
        result=adapter.invoke('probe',{'value':7});order.append(('caller','probe'))
        self.assertEqual(result,{'value':7})
        self.assertEqual(order,[('transport','probe'),('persist','probe'),('caller','probe')])
        self.assertEqual(saved[0][1],b'{"value":7}')
        self.assertEqual(adapter.records[0]['response_sha256'],hashlib.sha256(b'{"value":7}').hexdigest())

    def test_durable_invoker_preflight_and_bad_receipt_stop_without_retry(self):
        calls=[]
        adapter=b.DurableInvoker(lambda operation,params:calls.append(operation),lambda *args:None)
        with self.assertRaises(b.Stopped):adapter.invoke('bad',{'value':object()})
        self.assertEqual(calls,[])
        with self.assertRaises(b.Stopped):adapter.invoke('again',{})
        transport_calls=[]
        adapter=b.DurableInvoker(lambda operation,params:(transport_calls.append(operation) or {'ok':True}),
            lambda *args:{'bytes':0,'sha256':'0'*64})
        with self.assertRaises(b.Stopped):adapter.invoke('one',{})
        with self.assertRaises(b.Stopped):adapter.invoke('two',{})
        self.assertEqual(transport_calls,['one'])

    def test_publisher_uses_one_durable_receipt_for_every_transport_call(self):
        stored=[]
        def persist(ordinal,operation,request,result):
            stored.append((ordinal,operation,result))
            raw=b.canonical(result)
            return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        adapter=b.DurableInvoker(self.git.invoke,persist)
        bundle=self.bundle();publisher=b.Publisher(bundle,adapter.invoke,
            expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        receipt=publisher.publish()
        self.assertEqual(len(stored),receipt['usage']['calls'])
        self.assertEqual([row[0] for row in stored],list(range(len(stored))))
        self.assertEqual([row['operation'] for row in adapter.records],
            [operation for _,operation,_ in stored])

    def test_rss_is_checked_before_first_transport_call(self):
        bundle=self.bundle();publisher=b.Publisher(bundle,self.git.invoke,
            expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        class Usage:ru_maxrss=1024**3
        with patch.object(b.resource,'getrusage',return_value=Usage()):
            with self.assertRaises(b.Stopped):publisher.publish()
        self.assertEqual(self.git.calls,[]);self.assertTrue(publisher.stopped)

    def test_one_inline_tree_one_commit_update_and_one_grouped_readback(self):
        bundle=self.bundle();publisher=b.Publisher(bundle,self.git.invoke,expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        result=publisher.publish();methods=[name for name,_ in self.git.calls]
        self.assertEqual(methods.count('create_tree'),1);self.assertEqual(methods.count('create_commit'),1)
        self.assertEqual(methods.count('update_ref'),1);self.assertEqual(methods.count('fetch_files'),1)
        self.assertNotIn('create_blob',methods);self.assertNotIn('fetch_file',methods)
        self.assertEqual(len(self.git.inline_requests),1);self.assertTrue(result['exact_tree_delta_verified'])
        self.assertTrue(result['single_grouped_readback']);self.assertFalse(result['scientific_admission_authorized'])
        before=len(self.git.calls)
        with self.assertRaisesRegex(b.Stopped,'One broker'):publisher.publish()
        self.assertEqual(len(self.git.calls),before)

    def test_conflict_lost_update_and_bad_grouped_readback_stop_without_retry(self):
        for fault in ('conflict','lost_update','bad_readback'):
            with self.subTest(fault=fault):
                self.git=InlineGit();bundle=self.bundle();publisher=b.Publisher(bundle,self.git.invoke,
                    expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
                if fault=='conflict':self.git.move_before_update=True
                elif fault=='lost_update':self.git.lost_update=True
                else:self.git.bad_grouped=True
                with self.assertRaises(b.Stopped):publisher.publish()
                before=len(self.git.calls)
                with self.assertRaises(b.Stopped):publisher.publish()
                self.assertEqual(len(self.git.calls),before);self.assertFalse(publisher.receipt['scientific_admission_authorized'])
                if fault in ('lost_update','bad_readback'):self.assertTrue(publisher.receipt['update_may_have_landed'])

    def test_bundle_pin_prefix_manifest_and_chunk_corruption_are_refused(self):
        bundle=self.bundle();files=dict(bundle.files);path=next(p for p in files if p.endswith('.b64'))
        files[path]=files[path][:-1]+(b'A' if files[path][-1:]!=b'A' else b'B')
        freeze=__import__('json').loads(bundle.freeze_bytes)
        with self.assertRaises(ValueError):b.restore(files,expected_manifest_sha256=freeze['manifest_sha256'],expected_prefix=bundle.prefix)
        with self.assertRaises(ValueError):b.Publisher(bundle,self.git.invoke,expected_bundle_sha256='0'*64)
        with self.assertRaises(ValueError):b.prefix(8,freeze['files'][next(iter(freeze['files']))]['sha256'])

    def test_cumulative_broker_enforces_order_and_stops_after_failure(self):
        cumulative=b.CumulativeBroker(self.git.invoke,clock=lambda:0.)
        with self.assertRaisesRegex(ValueError,'fixed order'):cumulative.publish(self.bundle(1))
        first=self.bundle(0);receipt=cumulative.publish(first);self.assertEqual(receipt['ordinal'],0)
        second=self.bundle(1);self.git.bad_grouped=True
        with self.assertRaises(b.Stopped):cumulative.publish(second)
        self.assertTrue(cumulative.stopped)
        with self.assertRaises(b.Stopped):cumulative.publish(second)

    def test_reply_capacity_is_reserved_before_any_transport_call(self):
        bundle=self.bundle(limits=replace(b.Limits(),response_bytes=1024))
        publisher=b.Publisher(bundle,self.git.invoke,expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        with self.assertRaisesRegex(b.Stopped,'reserve operation reply'):publisher.publish()
        self.assertEqual(self.git.calls,[])
        self.assertEqual(publisher.usage()['calls'],0)

    def test_lost_update_retains_unknown_reply_charge_and_never_retries(self):
        bundle=self.bundle();self.git.lost_update=True
        publisher=b.Publisher(bundle,self.git.invoke,expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        with self.assertRaises(b.Stopped):publisher.publish()
        usage=publisher.usage()
        self.assertEqual(usage['unknown_response_count'],1)
        self.assertEqual(usage['unknown_response_bytes'],b.RESPONSE_RESERVATIONS['update_ref'])
        self.assertEqual(usage['response_charged_bytes'],usage['response_bytes']+usage['unknown_response_bytes'])
        self.assertTrue(publisher.receipt['update_may_have_landed'])
        self.assertTrue(publisher.events[-1]['response_unknown'])
        before=len(self.git.calls)
        with self.assertRaises(b.Stopped):publisher.publish()
        self.assertEqual(len(self.git.calls),before)

    def test_cumulative_failure_keeps_all_spent_calls_bytes_and_ambiguity(self):
        cumulative=b.CumulativeBroker(self.git.invoke,clock=lambda:0.)
        first=cumulative.publish(self.bundle(0));self.git.lost_update=True
        with self.assertRaises(b.Stopped):cumulative.publish(self.bundle(1))
        failed=cumulative.failed_attempt;usage=cumulative.usage()
        self.assertEqual(usage['cases'],2)
        self.assertEqual(usage['calls'],first['usage']['calls']+failed['usage']['calls'])
        self.assertEqual(usage['stored_bytes'],first['stored_bytes']+failed['stored_bytes'])
        self.assertEqual(usage['response_charged_bytes'],
            first['usage']['response_charged_bytes']+failed['usage']['response_charged_bytes'])
        self.assertEqual(usage['unknown_response_count'],1)
        self.assertTrue(failed['stored_bytes_conservative'])
        self.assertTrue(failed['update_may_have_landed'])

    def test_oversized_known_reply_is_charged_exactly_before_stopping(self):
        bundle=self.bundle();reply={'padding':'x'*b.RESPONSE_RESERVATIONS['fetch']}
        publisher=b.Publisher(bundle,lambda *args:reply,
            expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        with self.assertRaises(b.Stopped):publisher.publish()
        usage=publisher.usage();actual=len(b.canonical(reply))
        self.assertEqual(usage['calls'],1)
        self.assertEqual(usage['response_charged_bytes'],actual)
        self.assertEqual(usage['unknown_response_count'],0)
        self.assertFalse(publisher.update_attempted)

    def test_rss_growth_during_a_call_is_detected_before_next_operation(self):
        bundle=self.bundle();entered=False
        class Usage:
            @property
            def ru_maxrss(self):return 1024**3 if entered else 0
        def invoke(method,params):
            nonlocal entered
            result=self.git.invoke(method,params);entered=True;return result
        publisher=b.Publisher(bundle,invoke,expected_bundle_sha256=bundle.sha256,clock=lambda:0.)
        with patch.object(b.resource,'getrusage',return_value=Usage()):
            with self.assertRaises(b.Stopped):publisher.publish()
        self.assertEqual(len(self.git.calls),1)
        self.assertEqual(publisher.usage()['calls'],1)
        self.assertGreater(publisher.usage()['response_bytes'],0)


if __name__=='__main__':unittest.main()
