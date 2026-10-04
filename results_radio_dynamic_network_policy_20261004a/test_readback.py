from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import network_policy as n
import readback as h
from test_fixture import setup,capture_stub


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.scope,self.source,self.publication,self.outputs=setup(self.tmp.name)

    def execute(self,**extra):
        capture,calls=capture_stub(self.scope,self.outputs,**extra)
        result=h.execute(self.scope,n.pin(n.canonical(self.scope))['sha256'],self.publication,
                         capture=capture,source=self.source)
        return result,calls

    def test_exact_metadata_read_with_changed_static_ports_passes_no_authority(self):
        result,calls=self.execute()
        self.assertEqual(result['status'],'OBSERVED_DYNAMIC_LOOPBACK_GIT_METADATA',result.get('error'))
        self.assertEqual(len(calls),7);self.assertEqual(result['changed_prior_static_proxy_names'],list(n.PROXIES))
        self.assertFalse(result['scientific_execution_authorized']);self.assertFalse(result['qualified_atomic_expected_revision_cas'])
        for call in calls:
            self.assertNotIn('GIT_ASKPASS',call['kwargs']['env'])
            self.assertIn('http.sslVerify=true',call['argv']);self.assertIn('http.followRedirects=false',call['argv'])

    def test_same_original_root_refuses_replay_without_another_process(self):
        self.execute();capture,calls=capture_stub(self.scope,self.outputs)
        with self.assertRaises(ValueError):h.execute(self.scope,n.pin(n.canonical(self.scope))['sha256'],self.publication,capture=capture,source=self.source)
        self.assertEqual(calls,[])

    def test_nonzero_raw_3000_byte_stderr_is_preserved_on_new_wrapper_failure(self):
        result,calls=self.execute(failure='nonzero')
        self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(calls),1)
        raw=(Path(self.scope['artifact_root']['path'])/'op0-init/stderr.raw').read_bytes()
        self.assertEqual(raw,b'\x00\xff'+b'E'*2998)
        self.assertTrue((Path(self.scope['artifact_root']['path'])/'terminal.json').exists())

    def test_timeout_keeps_original_binary_prefix_and_does_not_continue(self):
        result,calls=self.execute(failure='timeout')
        self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(calls),1)
        self.assertEqual((Path(self.scope['artifact_root']['path'])/'op0-init/stderr.raw').read_bytes(),b'partial\0\xff')

    def test_hostile_network_refuses_after_spend_before_any_process(self):
        self.source['HTTPS_PROXY']='http://secret:SECRET@example.com:23456'
        result,calls=self.execute();self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(calls,[])
        self.assertTrue((Path(self.scope['artifact_root']['path'])/'attempt-started.json').exists())
        self.assertNotIn('SECRET',result['error'])

    def test_changed_head_member_commit_or_blob_cannot_be_qualified(self):
        for failure in ('head','member','commit','blob'):
            with tempfile.TemporaryDirectory() as root:
                scope,source,publication,outputs=setup(root);capture,calls=capture_stub(scope,outputs,failure=failure)
                result=h.execute(scope,n.pin(n.canonical(scope))['sha256'],publication,capture=capture,source=source)
                self.assertEqual(result['status'],'CLOSED_FAILED',failure)

    def test_certificate_mutated_during_capture_is_refused_at_final_recheck(self):
        def change(i,label,record):
            if i==0:Path(self.source['SSL_CERT_FILE']).write_bytes(b'changed after admission')
        result,calls=self.execute(on_call=change)
        self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(calls),7)

    def test_output_persistence_failure_cannot_promote_zero_child_exit(self):
        def change(i,label,record):
            if i==0:record['streams']['stderr']['file_fsync_complete']=False
        result,calls=self.execute(on_call=change)
        self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(calls),1)

    def test_extra_telescope_path_is_refused_before_marker_or_process(self):
        self.scope['selected_files']['telescope.h5']={'raw_pin':n.pin(b'not-read'),'git_blob':'0'*40}
        capture,calls=capture_stub(self.scope,self.outputs)
        with self.assertRaises(ValueError):h.execute(self.scope,n.pin(n.canonical(self.scope))['sha256'],self.publication,capture=capture,source=self.source)
        self.assertEqual(calls,[]);self.assertEqual(list(Path(self.scope['artifact_root']['path']).iterdir()),[])

    def test_original_symlink_and_identity_substitution_are_refused(self):
        art=Path(self.scope['artifact_root']['path']);art.rmdir();replacement=art.parent/'replacement';replacement.mkdir();art.symlink_to(replacement,target_is_directory=True)
        capture,calls=capture_stub(self.scope,self.outputs)
        with self.assertRaises(OSError):h.execute(self.scope,n.pin(n.canonical(self.scope))['sha256'],self.publication,capture=capture,source=self.source)
        self.assertEqual(calls,[])

    def test_storage_limit_preserves_first_capture_and_closes(self):
        self.scope['retained_original_evidence_ceiling_bytes']=self.scope['terminal_reserve_bytes']+4096
        result,calls=self.execute();self.assertEqual(result['status'],'CLOSED_FAILED');self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
