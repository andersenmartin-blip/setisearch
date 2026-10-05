"""Short offline launcher tests; dispatches TEMP synthetic programs only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LAUNCHER = Path(__file__).with_name("launch_scope.py")
FAKE = '''import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--freeze',required=True)
args,_=p.parse_known_args()
f=json.loads(Path(args.freeze).read_text())
root=Path(f['output_root'])
result={'status':('MATERIALIZED_SYNTHETIC_ONLY' if f['synthetic_exit_code']==0
                  else 'FAILED_SYNTHETIC_ONLY'),'children':[
    {'wait4_direct_child_ru_maxrss_bytes':f['synthetic_child_peak']}]}
(root/'result.json').write_text(json.dumps(result)+'\\n')
print('synthetic gate stdout')
print('synthetic gate stderr',file=sys.stderr)
raise SystemExit(f['synthetic_exit_code'])
'''


class LauncherTests(unittest.TestCase):
    def run_case(self, code, peak=1024):
        with tempfile.TemporaryDirectory(prefix="synthetic-launcher-test-") as d:
            directory=Path(d)
            scope=directory/"SYNTHETIC_ONLY";scope.mkdir()
            fake=directory/"synthetic_gate.py";fake.write_text(FAKE)
            freeze=dict(identity="SYNTHETIC_LAUNCHER_TEST_ONLY",output_root=str(scope),
                        python_executable=sys.executable,gate_source_path=str(fake),
                        preparation_root=str(directory),synthetic_exit_code=code,
                        synthetic_child_peak=peak)
            def pin(path):
                raw=Path(path).read_bytes()
                return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            freeze['source_pins']=[pin(fake)]
            freeze['runtime_pins']=[pin(sys.executable)]
            freeze_path=directory/"synthetic-freeze.json"
            raw=(json.dumps(freeze,sort_keys=True)+'\n').encode();freeze_path.write_bytes(raw)
            args=[sys.executable,'-I','-B','-S',str(LAUNCHER),
                  '--freeze',str(freeze_path),'--freeze-sha256',hashlib.sha256(raw).hexdigest(),
                  '--proof',str(directory/'SYNTHETIC_UNUSED_PROOF'), '--proof-sha256','0'*64,
                  '--marker',str(directory/'SYNTHETIC_UNUSED_MARKER'),'--marker-sha256','0'*64]
            completed=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     timeout=15,check=False)
            self.assertEqual(completed.stderr,b'')
            receipt=json.loads((scope/'caller-receipt.json').read_text())
            self.assertEqual(json.loads(completed.stdout),receipt)
            self.assertEqual(receipt['identity'],'SYNTHETIC_LAUNCHER_TEST_ONLY')
            self.assertEqual(receipt['dispatches'],1)
            self.assertTrue(receipt['child_reaped'])
            self.assertEqual(receipt['child_exit_code'],code)
            self.assertFalse(receipt['watchdog_killed'])
            self.assertGreater(receipt['elapsed_full_parent_lifetime_seconds'],0)
            self.assertLess(receipt['elapsed_full_parent_lifetime_seconds'],15)
            self.assertGreater(receipt['parent_wait4_lifetime_ru_maxrss_bytes'],0)
            self.assertGreaterEqual(receipt['parent_wait4_cpu_user_seconds'],0)
            self.assertGreaterEqual(receipt['parent_wait4_cpu_system_seconds'],0)
            if peak is None:
                self.assertIsNone(receipt['conservative_joined_rss_upper_bound_bytes'])
                self.assertFalse(receipt['child_peak_custody_complete'])
                self.assertFalse(receipt['success'])
            else:
                self.assertTrue(receipt['child_peak_custody_complete'])
                self.assertEqual(receipt['conservative_joined_rss_upper_bound_bytes'],
                                 receipt['parent_wait4_lifetime_ru_maxrss_bytes']+peak)
            self.assertEqual(receipt['successful_gate_status'],
                             'MATERIALIZED_SYNTHETIC_ONLY' if code==0 else 'FAILED_SYNTHETIC_ONLY')
            self.assertFalse(receipt['runtime_qualified'])
            self.assertFalse(receipt['scientific_authority'])
            self.assertEqual((directory/'SYNTHETIC_ONLY.caller-stdout').read_bytes(),b'synthetic gate stdout\n')
            self.assertEqual((directory/'SYNTHETIC_ONLY.caller-stderr').read_bytes(),b'synthetic gate stderr\n')
            self.assertEqual(receipt['storage_before_caller_receipt']['files'],1)
            # Only these expected TEMP objects were created; no real gate/source
            # marker was read or activated by this synthetic child.
            self.assertEqual({p.name for p in scope.iterdir()},{'result.json','caller-receipt.json'})
            return completed.returncode,receipt['success']

    def test_success_single_dispatch_wait4_reap_and_exact_streams(self):
        self.assertEqual(self.run_case(0),(0,True))

    def test_nonzero_child_still_reaped_and_failure_receipt_retained(self):
        self.assertEqual(self.run_case(3),(1,False))

    def test_missing_child_peak_retained_as_none_and_cannot_claim_success(self):
        # Even exit zero plus a success-shaped fake gate status must fail when
        # the child RSS observation is missing, while still retaining streams,
        # full direct-parent metrics and a reaped, parseable terminal receipt.
        self.assertEqual(self.run_case(0,peak=None),(1,False))


if __name__=='__main__':
    unittest.main()
