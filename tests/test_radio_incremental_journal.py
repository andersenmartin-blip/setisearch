"""Named new risks in incremental durable storage, not a new science evaluation."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from seti_repeater import whole_cadence_incremental_radio as r
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_remote import GitDouble

NONCE = '00000000-0000-4000-8000-000000000091'
PAYLOAD = b'{"engineering":"new incremental fixture"}'


def genesis(prefix=r.PREFIXES[0]):
    label = lambda k: digest(['incremental-offline-unit-only', prefix, k])
    return canonical(j.genesis({'schema': j.SCHEMA, 'mode': 'engineering', 'namespace': prefix,
        'execution_binding_sha256': label('freeze'), 'allocation_sha256': label('allocation'),
        'cases': [{k:label(k) for k in j.BINDING_KEYS if k != 'role'} | {'role':'engineering'}],
        'caps': {**j.CAPS, 'active_milliseconds':120000, 'evidence_bytes':131072,
                 'ledger_reserve_bytes':r.LEDGER_CAP}, 'required_artifacts':['witness.json']}))


def events(raw):
    binding = json.loads(raw)['manifest']['cases'][0]
    return [{'kind':'consume', 'binding':binding, 'milliseconds':120000,
             'artifact_bytes':r.ARTIFACT_CAP, 'nonce':NONCE},
            {'kind':'artifact', 'nonce':NONCE, 'name':'witness.json',
             'size':len(PAYLOAD), 'sha256':r.sha(PAYLOAD)},
            {'kind':'finish', 'nonce':NONCE, 'outcome':'completed',
             'elapsed_milliseconds':1, 'reason':'fixed engineering unit'}]


class IncrementalDouble(GitDouble):
    def __init__(self, raw):
        self.blobs={}; self.trees={}; self.flat={}; self.commits={}; self.calls=[]; self.hook=None
        self.raw = raw; self.prefix = json.loads(raw)['manifest']['namespace']
        history = r.initial(raw)
        self.head = self.commit(None, self.tree({self.prefix+'/genesis.json':self.blob(raw),
            self.prefix+'/head.json':self.blob(history.head), 'unrelated.txt':self.blob(b'keep')}))
        self.freeze = self.head

    def invoke(self, method, params):
        if method == 'create_tree':
            params = copy.deepcopy(params)
            for e in params['tree_elements']:
                e['sha'] = self.blob(e.pop('content').encode('ascii'))
        return super().invoke(method, params)


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.raw=genesis(); self.git=IncrementalDouble(self.raw); self.tick=0.
        self.meter=r.Meter(clock=lambda:self.tick)
        self.client=r.Client(self.git.invoke,meter=self.meter)
        self.session=self.fresh(); self.ev=events(self.raw)

    def fresh(self, client=None):
        return r.Session(client or self.client,r.PREFIXES[0],self.raw,
                         freeze_commit=self.git.freeze,execution_verifier=lambda:None)

    def complete(self):
        self.session.begin()
        for e in self.ev:
            self.session.append(e,artifact=PAYLOAD if e['kind']=='artifact' else None)
        return self.session.history

    def reader(self, client=None):
        return r.Reader(client or self.client.readonly_recovery(),r.PREFIXES[0],r.sha(self.raw))

    def test_all_original_revisions_restore_and_untouched_git_bytes_preserved(self):
        h=self.complete(); got=self.reader().read(self.git.head,expected_pointer_sha256=r.sha(h.head))
        original=[self.raw]; doc=json.loads(self.raw)
        for e in self.ev:
            doc=j.append(doc,e); original.append(canonical(doc))
        self.assertEqual(list(got.revisions),original)
        self.assertEqual(got.summary()['states'],['completed'])
        self.assertEqual(list(self.reader().verify_artifacts(self.git.head,got).values()),[PAYLOAD])
        flat=self.git.flat[self.git.commits[self.git.head]['tree']['sha']]
        self.assertEqual(self.git.blobs[flat['unrelated.txt']],b'keep')
        self.assertFalse(any('/ledger.json' in p for p in flat))

    def test_exact_cumulative_accounting_includes_every_historical_pointer(self):
        h=self.complete(); files={}; seen_pointer=[]
        head=self.git.head
        while True:
            rec=self.git.commits[head];flat=self.git.flat[rec['tree']['sha']]
            for name,blob in flat.items():
                if name.startswith(r.PREFIXES[0]+'/') and '/artifacts/' not in name:
                    if name.endswith('/head.json'):seen_pointer.append(blob)
                    else:files[name]=blob
            if not rec['parents']:break
            head=rec['parents'][0]['sha']
        expected=sum(len(self.git.blobs[x]) for x in files.values())
        expected+=sum(len(self.git.blobs[x]) for x in set(seen_pointer))
        self.assertEqual(expected,h.ledger_bytes)
        self.assertEqual(len(seen_pointer),4)

    def test_missing_reordered_and_corrupt_chunks_cannot_form_a_prefix(self):
        h=self.complete()
        for chunks in (h.chunks[:-1],tuple(reversed(h.chunks)),(h.chunks[0]+b' ',)+h.chunks[1:]):
            with self.assertRaises(ValueError):
                r.restore(h.genesis,chunks,h.head,expected_genesis_sha256=r.sha(h.genesis),
                          expected_head_sha256=r.sha(h.head))

    def test_independently_pinned_latest_head_rejects_valid_old_prefix(self):
        h=self.complete(); old=r.initial(self.raw)
        with self.assertRaisesRegex(ValueError,'external pin'):
            r.restore(old.genesis,old.chunks,old.head,expected_genesis_sha256=r.sha(self.raw),
                      expected_head_sha256=r.sha(h.head))

    def test_rehashed_checkpoint_tampering_is_rejected(self):
        h=self.complete(); chunk=json.loads(h.chunks[-1]);chunk['after_bytes']-=1
        chunks=h.chunks[:-1]+(canonical(chunk),)
        with self.assertRaisesRegex(ValueError,'checkpoint'):
            r.restore(h.genesis,chunks,h.head,expected_genesis_sha256=r.sha(h.genesis),
                      expected_head_sha256=r.sha(h.head))

    def test_genesis_and_authority_cannot_be_self_asserted(self):
        h=r.initial(self.raw);head=json.loads(h.head);head['execution_restart_authorized']=True
        changed=canonical(head)
        with self.assertRaisesRegex(ValueError,'authority'):
            r.restore(h.genesis,(),changed,expected_genesis_sha256=r.sha(h.genesis),
                      expected_head_sha256=r.sha(changed))
        with self.assertRaisesRegex(ValueError,'independent freeze'):
            r.restore(h.genesis,(),h.head,expected_genesis_sha256='f'*64,
                      expected_head_sha256=r.sha(h.head))

    def test_ledger_cap_counts_history_before_any_remote_mutation(self):
        self.session.begin(); old=self.git.head
        original=r.extend
        def capped(history,event):return original(history,event,ledger_cap=history.ledger_bytes)
        with patch.object(r,'extend',capped), self.assertRaisesRegex(ValueError,'Cumulative'):
            self.session.append(self.ev[0])
        self.assertEqual(self.git.head,old)
        self.assertFalse(any(m=='create_tree' for m,p in self.git.calls))
        self.assertTrue(self.session.stopped)

    def test_lost_response_after_actual_mutation_consumes_once_and_recovers_readonly(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='update_ref':raise OSError('lost after durable ref update')
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(r.Stopped,'lost after'):self.session.append(self.ev[0])
        self.git.hook=None;n=len(self.git.calls)
        with self.assertRaises(r.Stopped):self.session.append(self.ev[0])
        self.assertEqual(n,len(self.git.calls))
        recovery=self.client.readonly_recovery();got=self.reader(recovery).read(self.git.head)
        self.assertEqual(got.summary()['states'],['consumed'])
        self.assertIs(recovery.meter,self.meter)
        with self.assertRaisesRegex(ValueError,'authority'):
            recovery.call('update_ref',repository_full_name=r.git.REPO,
                          branch_name=r.git.BRANCH,sha=self.git.head,force=False)
        with self.assertRaisesRegex(ValueError,'no resume'):self.fresh(r.Client(self.git.invoke)).begin()
        self.assertEqual([m for m,p in self.git.calls].count('update_ref'),1)

    def test_explicit_session_boundary_ack_loss_has_same_stop_and_consumed_state(self):
        self.session.begin()
        with self.assertRaisesRegex(OSError,'Injected loss'):
            self.session.append(self.ev[0],lose_acknowledgement=True)
        self.assertTrue(self.session.stopped)
        self.assertEqual(self.reader().read(self.git.head).summary()['states'],['consumed'])

    def test_failure_before_ref_mutation_never_reports_consumption(self):
        self.session.begin();head=self.git.head
        def invoke(m,p):
            if m=='update_ref':raise OSError('disconnect before update')
            return self.git.invoke(m,p)
        self.client.invoke=invoke
        with self.assertRaises(r.Stopped):self.session.append(self.ev[0])
        self.assertEqual(self.git.head,head)
        self.assertEqual(self.reader().read(head).summary()['states'],[])
        self.assertTrue(self.session.stopped)

    def test_concurrent_branch_change_never_rebases_or_updates(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='create_commit':
                self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'Concurrent'):self.session.append(self.ev[0])
        self.assertNotIn('update_ref',[m for m,p in self.git.calls])
        self.assertTrue(self.session.stopped)

    def test_conflict_at_ref_update_is_not_retried(self):
        self.session.begin();original=self.git.invoke
        def invoke(m,p):
            if m=='update_ref':
                self.git.head=self.git.commit(self.git.head,self.git.commits[self.git.head]['tree']['sha'])
            return original(m,p)
        self.client.invoke=invoke
        with self.assertRaisesRegex(r.Stopped,'Non fast-forward'):self.session.append(self.ev[0])
        self.assertEqual([m for m,p in self.git.calls].count('update_ref'),1)

    def test_corrupt_immutable_readback_stops_after_durable_consumption(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='fetch_file' and '/events/' in p['path']:
                result['content']=base64.b64encode(b'corrupt').decode()
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'content hash'):self.session.append(self.ev[0])
        self.assertTrue(self.session.stopped)
        self.git.hook=None
        self.assertEqual(self.reader().read(self.git.head).summary()['states'],['consumed'])

    def test_crash_during_postwrite_validation_does_not_restore_authority(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='fetch_file' and '/events/' in p['path']:raise SystemExit('simulated process exit boundary')
            return result
        self.git.hook=hook
        with self.assertRaises(r.Stopped):self.session.append(self.ev[0])
        self.git.hook=None
        self.assertEqual(self.reader().read(self.git.head).summary()['states'],['consumed'])
        with self.assertRaisesRegex(ValueError,'no resume'):self.fresh(r.Client(self.git.invoke)).begin()

    def test_actual_subprocess_exit_leaves_recovery_bytes_and_no_lease(self):
        self.session.begin();h=self.session.append(self.ev[0])
        with tempfile.TemporaryDirectory() as d:
            payload=canonical({'genesis':h.genesis.decode(),'chunks':[x.decode() for x in h.chunks],'head':h.head.decode()})
            path=Path(d)/'crash.json'
            script='import os,sys; from pathlib import Path; p=Path(sys.argv[1]); f=p.open("xb"); f.write(sys.stdin.buffer.read()); f.flush(); os.fsync(f.fileno()); os._exit(73)'
            run=subprocess.run(['python','-c',script,str(path)],input=payload)
            self.assertEqual(run.returncode,73)
            rec=json.loads(path.read_bytes());restored=r.restore(rec['genesis'].encode(),
                tuple(x.encode() for x in rec['chunks']),rec['head'].encode(),
                expected_genesis_sha256=r.sha(h.genesis),expected_head_sha256=r.sha(h.head))
            self.assertEqual(restored.summary()['states'],['consumed'])
            self.assertFalse(hasattr(restored,'begin_gaussian'));self.assertFalse(hasattr(restored,'append'))

    def test_artifact_receipt_and_bytes_are_atomic_and_wrong_bytes_never_mutate(self):
        self.session.begin();self.session.append(self.ev[0]);head=self.git.head
        with self.assertRaisesRegex(ValueError,'Exact ASCII'):self.session.append(self.ev[1],artifact=b'wrong')
        self.assertEqual(self.git.head,head)
        self.assertEqual(self.reader().read(head).summary()['states'],['consumed'])

    def test_cumulative_artifact_limit_precedes_remote_mutation(self):
        self.session.begin();self.session.append(self.ev[0]);head=self.git.head
        self.session.artifact_bytes=r.ARTIFACT_CAP
        with self.assertRaisesRegex(ValueError,'artifact capacity'):self.session.append(self.ev[1],artifact=PAYLOAD)
        self.assertEqual(self.git.head,head)

    def test_missing_artifact_prevents_completion(self):
        self.session.begin();self.session.append(self.ev[0]);head=self.git.head
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.session.append(self.ev[2])
        self.assertEqual(self.git.head,head)

    def test_finished_session_and_fresh_reader_cannot_reopen(self):
        self.complete();count=len(self.git.calls)
        with self.assertRaises(r.Stopped):self.session.append(self.ev[0])
        with self.assertRaises(r.Stopped):self.session.begin()
        self.assertEqual(len(self.git.calls),count)
        with self.assertRaisesRegex(ValueError,'no resume'):self.fresh().begin()
        self.assertFalse(hasattr(self.reader(),'append'))

    def test_external_artifact_corruption_is_independently_detected(self):
        h=self.complete()
        def hook(m,p,result):
            if m=='fetch_file' and '/artifacts/' in p['path']:
                result['content']=base64.b64encode(b'wrong').decode()
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'content hash'):self.reader().verify_artifacts(self.git.head,h)

    def test_server_tree_change_outside_namespace_stops_before_commit(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='create_tree':
                flat=dict(self.git.flat[result['sha']]);flat['unrelated.txt']=self.git.blob(b'wrong')
                return {'sha':self.git.tree(flat)}
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'preserved parent'):self.session.append(self.ev[0])
        self.assertNotIn('create_commit',[m for m,p in self.git.calls])

    def test_time_after_publication_is_charged_and_cannot_complete(self):
        self.session.begin()
        def hook(m,p,result):
            if m=='update_ref':self.tick=121.
            return result
        self.git.hook=hook
        with self.assertRaisesRegex(ValueError,'session time'):self.session.append(self.ev[0])
        self.assertTrue(self.session.stopped)

    def test_call_request_reply_reservations_are_shared_with_recovery(self):
        for key in ('calls','request_bytes','response_bytes'):
            meter=r.Meter(clock=lambda:0.);setattr(meter,key,r.LIMITS[key])
            client=r.Client(self.git.invoke,meter=meter);n=len(self.git.calls)
            with self.assertRaises(r.Stopped):
                client.call('fetch',url='https://api.github.com/repos/'+r.git.REPO+'/git/ref/heads/'+r.git.BRANCH)
            self.assertEqual(n,len(self.git.calls));self.assertIs(client.readonly_recovery().meter,meter)

    def test_uncertain_reply_is_charged_full_reserved_bytes(self):
        def fail(m,p):raise OSError('lost reply')
        c=r.Client(fail,meter=self.meter)
        with self.assertRaises(r.Stopped):c.call('fetch',url='https://api.github.com/repos/'+r.git.REPO+'/git/ref/heads/'+r.git.BRANCH)
        self.assertEqual(self.meter.response_bytes,1048576)
        self.assertEqual(self.meter.calls,1)

    def test_oversized_reply_is_charged_in_full_and_stops(self):
        c=r.Client(lambda m,p:{'too_large':'x'*1048576},meter=self.meter)
        with self.assertRaisesRegex(r.Stopped,'Reply cap'):
            c.call('fetch',url='https://api.github.com/repos/'+r.git.REPO+'/git/ref/heads/'+r.git.BRANCH)
        self.assertGreater(self.meter.response_bytes,1048576)

    def test_namespace_science_rng_and_noninteger_prefix_are_rejected(self):
        m=json.loads(self.raw);m['manifest']['mode']='scientific';m['manifest_sha256']=digest(m['manifest'])
        with self.assertRaises(ValueError):r.initial(canonical(m))
        with self.assertRaises(ValueError):r.Reader(self.client,'unfrozen',r.sha(self.raw))
        h=r.initial(self.raw);head=json.loads(h.head);head['event_count']=False;raw=canonical(head)
        with self.assertRaises(ValueError):
            r.restore(h.genesis,(),raw,expected_genesis_sha256=r.sha(h.genesis),expected_head_sha256=r.sha(raw))
        self.session.begin();self.session.append(self.ev[0])
        with self.assertRaisesRegex(ValueError,'Engineering cannot'):
            self.session.append({'kind':'rng_start','nonce':NONCE,'plan_sha256':self.ev[0]['binding']['plan_sha256']})

    def test_historical_pointer_retention_wins_over_latest_only_accounting(self):
        h=self.complete()
        latest=len(h.genesis)+sum(map(len,h.chunks))+len(h.head)
        self.assertGreater(h.ledger_bytes,latest)
        with self.assertRaisesRegex(ValueError,'all pointer versions'):
            r.restore(h.genesis,h.chunks,h.head,expected_genesis_sha256=r.sha(h.genesis),
                      expected_head_sha256=r.sha(h.head),ledger_cap=latest)

    def test_current_tree_with_stale_pointer_cannot_hide_a_consumed_event(self):
        self.session.begin();self.session.append(self.ev[0])
        flat=dict(self.git.flat[self.git.commits[self.git.head]['tree']['sha']])
        flat[r.PREFIXES[0]+'/head.json']=self.git.blob(r.initial(self.raw).head)
        bad=self.git.commit(self.git.head,self.git.tree(flat))
        with self.assertRaisesRegex(ValueError,'omits retained'):
            self.reader().read(bad)

    def test_orphan_artifact_is_not_silently_left_out_of_capacity(self):
        h=self.complete();flat=dict(self.git.flat[self.git.commits[self.git.head]['tree']['sha']])
        flat[r.PREFIXES[0]+'/artifacts/orphan.txt']=self.git.blob(b'extra')
        bad=self.git.commit(self.git.head,self.git.tree(flat))
        with self.assertRaisesRegex(ValueError,'omits retained'):
            self.reader().read(bad,expected_pointer_sha256=r.sha(h.head))


if __name__=='__main__':unittest.main()
