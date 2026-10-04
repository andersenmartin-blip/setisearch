import copy
import tempfile
import unittest
import network_policy as n
import readback as h
import review as r
from test_fixture import setup,capture_stub


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.scope,self.source,self.publication,outputs=setup(self.tmp.name)
        capture,calls=capture_stub(self.scope,outputs)
        self.terminal=h.execute(self.scope,n.pin(n.canonical(self.scope))['sha256'],self.publication,capture=capture,source=self.source)

    def verify(self,terminal=None):
        a=n.canonical(self.scope);b=n.canonical(self.terminal if terminal is None else terminal)
        return r.review(a,r.pin(a),b,r.pin(b),expected_publication=self.publication)

    def test_exact_complete_synthetic_fixture_is_selected_evidence_only(self):
        result=self.verify();self.assertEqual(result['native_processes'],7)
        self.assertFalse(result['scientific_execution_authorized']);self.assertFalse(result['complete_hosted_runtime_qualified'])

    def test_endpoint_host_port_hash_and_unknown_fields_are_refused(self):
        for key,value in (('host','example.com'),('port',True),('port',80),('sha256','f'*64),('secret','SECRET')):
            t=copy.deepcopy(self.terminal);t['network_observation']['proxies']['HTTP_PROXY'][key]=value
            with self.assertRaises(ValueError):self.verify(t)

    def test_unrelated_inherited_name_and_wrong_policy_pin_are_refused(self):
        for change in ('name','policy'):
            t=copy.deepcopy(self.terminal)
            if change=='name':t['network_observation']['actual_environment_names'].append('PRIVATE_TOKEN')
            else:t['network_observation']['policy_pin']['sha256']='f'*64
            with self.assertRaises(ValueError):self.verify(t)

    def test_reordered_clock_regression_and_missing_capture_are_refused(self):
        for change in ('clock','order','missing'):
            t=copy.deepcopy(self.terminal)
            if change=='clock':t['operations'][1]['before_monotonic_ns']=0
            elif change=='order':t['operations'][0],t['operations'][1]=t['operations'][1],t['operations'][0]
            else:t['operations'].pop()
            with self.assertRaises(ValueError):self.verify(t)

    def test_arbitrary_destination_and_native_command_substitution_are_refused(self):
        for change in ('destination','argv'):
            t=copy.deepcopy(self.terminal);record=t['operations'][0]['capture']
            if change=='argv':record['argv']=['arbitrary-command']
            else:record['destination']['path']='/elsewhere'
            with self.assertRaises(ValueError):self.verify(t)

    def test_raw_prefix_eof_or_persistence_tampering_is_refused(self):
        for change in ('raw','eof','persistence','disposition'):
            t=copy.deepcopy(self.terminal);record=t['operations'][0]['capture']
            if change=='raw':record['streams']['stdout']['reconstruction']['data']='eA=='
            elif change=='eof':record['streams']['stdout']['eof_observed']=False
            elif change=='persistence':record['streams']['stdout']['file_write_complete']=False
            else:record['disposition_first_payload_sha256']='f'*64
            with self.assertRaises(ValueError):self.verify(t)

    def test_returned_git_parent_blob_or_changed_proxy_summary_cannot_replace_raw_evidence(self):
        for change in ('parent','blob','proxy'):
            t=copy.deepcopy(self.terminal)
            if change=='parent':t['public_git_proof']['parent']='f'*40
            elif change=='blob':next(iter(t['public_git_proof']['selected_files'].values()))['git_blob']='f'*40
            else:t['changed_prior_static_proxy_names'].pop()
            with self.assertRaises(ValueError):self.verify(t)

    def test_failed_terminal_scientific_promotion_and_false_child_completion_are_refused(self):
        for change in ('failed','authority','child'):
            t=copy.deepcopy(self.terminal)
            if change=='failed':t['status']='CLOSED_FAILED'
            elif change=='authority':t['scientific_execution_authorized']=True
            else:t['operations'][0]['capture']['returncode']=False
            with self.assertRaises(ValueError):self.verify(t)

    def test_external_raw_pin_and_duplicate_json_members_are_refused(self):
        a=n.canonical(self.scope);b=n.canonical(self.terminal)
        with self.assertRaises(ValueError):r.review(a,r.pin(a),b+b' ',r.pin(b),expected_publication=self.publication)
        bad=b'{"key":1,"key":2}\n'
        with self.assertRaises(ValueError):r.load(bad,r.pin(bad))


if __name__=='__main__':unittest.main()
