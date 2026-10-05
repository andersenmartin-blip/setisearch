"""Finite pure preparation refusals; no actual root or package operations."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
B={"__name__":"_builder_tests","__file__":str(HERE/'build_bootstrap_b.py')}
exec(compile((HERE/'build_bootstrap_b.py').read_bytes(),B['__file__'],'exec'),B)


class PreparationSafetyTests(unittest.TestCase):
    def test_budget_refuses_before_oversized_read(self):
        guard=B['ReadGuard']()
        with self.assertRaises(B['PreparationRefusal']):
            guard.charge(B['READ_BYTES']+1)
        self.assertEqual(guard.charged,0)

    def test_budget_refuses_non_integer_and_negative(self):
        for size in (-1,True,1.5):
            guard=B['ReadGuard']()
            with self.assertRaises(B['PreparationRefusal']):
                guard.charge(size)
            self.assertEqual(guard.charged,0)

    def test_file_count_refuses_before_held_read(self):
        guard=B['ReadGuard']();guard.files=B['READ_FILES']
        called=[]
        gate={'held_file':lambda *args:called.append(args)}
        with self.assertRaises(B['PreparationRefusal']):
            guard.read(gate,'/explicit/path',1)
        self.assertEqual(called,[])

    def test_descriptor_selects_only_explicit_dynamic_proxy_and_trust(self):
        d=B['descriptor']({'TRANSPORT_SCHEMA':'radio-runtime-package-bootstrap-proxy-descriptor-v1'})
        self.assertEqual(d['proxy_selection'],{'environment_name':'PIP_PROXY','policy':'canonical-credential-free-loopback-http-v1'})
        self.assertEqual(d['trust_binding']['sha256'],B['TRUST_PIN']['sha256'])
        self.assertEqual(d['tunnel_destination'],{'host':'files.pythonhosted.org','port':443})

    def test_builder_cannot_write_actual_root_or_marker(self):
        for path in (B['FINAL_ROOT']/'spent.json',B['FINAL_ROOT']/'arbitrary',
                     B['FINAL_REPOSITORY']/'config/radio_runtime_bootstrap_20261005b.activate.json'):
            with self.assertRaises(B['PreparationRefusal']):
                B['write_exclusive'](path,b'unadmitted')

    def test_gate_wrong_hash_prevents_code_execution(self):
        with tempfile.TemporaryDirectory(prefix='bootstrap-b-preparation-pure-') as temp:
            path=Path(temp)/'gate.py'
            path.write_bytes(b"raise RuntimeError('must never execute')\n")
            with self.assertRaises(B['PreparationRefusal']):
                B['load_gate'](path,'0'*64)

    def test_exclusive_preparation_write_does_not_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='bootstrap-b-preparation-pure-') as temp:
            path=Path(temp)/'report.json'
            B['write_exclusive'](path,b'first')
            with self.assertRaises(FileExistsError):
                B['write_exclusive'](path,b'second')
            self.assertEqual(path.read_bytes(),b'first')
            self.assertEqual(os.stat(path).st_mode&0o7777,0o644)


if __name__=='__main__':
    unittest.main(verbosity=2)
