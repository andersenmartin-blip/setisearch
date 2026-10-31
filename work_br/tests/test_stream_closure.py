"""Deterministic engineering fixtures only; no BP/BQ saved inputs opened."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('br_closure_tests',ROOT/'work_br/stream_closure.py')
c=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
SPEC2=importlib.util.spec_from_file_location('br_closed_tests',ROOT/'work_br/closed_association.py')
a=importlib.util.module_from_spec(SPEC2)
SPEC2.loader.exec_module(a)


def receipt(path,records):
    data=path.read_bytes()
    return {'path':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'records':records,'complete':True}


def fixtures(directory):
    out=Path(directory)
    result={'status':'PASS','method_results':{}}
    for method in ('current','legacy'):
        writer=c.AtomicJSONLPublisher(out,method+'.jsonl')
        writer.append({'status':'OFF_VETO','x':1})
        writer.append({'status':'THREE_ON_FAIL','x':2})
        r=writer.close()
        result['method_results'][method]={
            'association_stream':r,'source_ON_hits':2,'flags':0,
            'association_counts':{'PASS':0,'UNSUPPORTED':0,'THREE_ON_FAIL':1,'OFF_VETO':1}}
    return result


def change(path,data):
    path.chmod(0o644)
    path.write_bytes(data)


class ClosureTests(unittest.TestCase):
    def test_valid_child_and_parent_fences(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d)
            check=c.verify_manifest_streams(d,r)
            self.assertEqual(check['total_records'],4)
            child=c.evaluate_closure(d,r,'child_end')
            parent=c.evaluate_closure(d,r,'parent_end',previous_check=child)
            self.assertEqual(parent['effective_status'],'PASS')
            self.assertEqual(child['verification'],parent['verification'])

    def test_truncated_tail_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl'
            change(p,p.read_bytes()[:-5])
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'BYTE_COUNT')

    def test_changed_same_length_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl'
            change(p,p.read_bytes().replace(b'"x":1',b'"x":9'))
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'SHA256')

    def test_missing_complete_line_rejected_even_with_new_size_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl'
            change(p,p.read_bytes().splitlines(keepends=True)[0])
            r['method_results']['current']['association_stream']=receipt(p,2)
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'RECORD_COUNT')

    def test_same_bytes_wrong_declared_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d)
            r['method_results']['current']['association_stream']['sha256']='0'*64
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'SHA256')

    def test_final_newline_is_required_independently_of_hash(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl'
            change(p,p.read_bytes()[:-1])
            r['method_results']['current']['association_stream']=receipt(p,2)
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'MISSING_NEWLINE')

    def test_post_child_mutation_forces_effective_fail(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);child=c.evaluate_closure(d,r,'child_end')
            p=Path(d)/'current.jsonl'
            change(p,p.read_bytes().replace(b'"x":1',b'"x":9'))
            parent=c.evaluate_closure(d,r,'parent_end',previous_check=child)
            self.assertEqual(child['effective_status'],'PASS')
            self.assertEqual(r['status'],'PASS')
            self.assertEqual(parent['computation_status_preserved'],'PASS')
            self.assertEqual(parent['status'],'FAIL')
            self.assertEqual(parent['effective_status'],'FAIL')

    def test_changed_identity_metadata_between_fences_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);child=c.evaluate_closure(d,r,'child_end')
            p=Path(d)/'current.jsonl';s=p.stat()
            os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1))
            parent=c.evaluate_closure(d,r,'parent_end',previous_check=child)
            self.assertEqual(parent['effective_status'],'FAIL')
            self.assertEqual(parent['error_code'],'CROSS_FENCE_MUTATION')

    def test_path_escape_and_absolute_paths_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=fixtures(d)
            for name in ('../current.jsonl','/tmp/current.jsonl','x/y.jsonl','x\\y.jsonl','..'):
                r=copy.deepcopy(base)
                r['method_results']['current']['association_stream']['path']=name
                with self.subTest(name=name),self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
                self.assertEqual(cm.exception.code,'UNSAFE_PATH')

    def test_symlink_stream_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl';p.unlink();p.symlink_to(Path(d)/'legacy.jsonl')
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'OPEN_FAILED')

    def test_nonregular_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);p=Path(d)/'current.jsonl';p.unlink();os.mkfifo(p)
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'NONREGULAR_STREAM')

    def test_status_manifest_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d)
            r['method_results']['current']['association_counts']['OFF_VETO']=2
            with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
            self.assertEqual(cm.exception.code,'STATUS_COUNTS')

    def test_invalid_json_duplicate_keys_and_nonfinite_rejected(self):
        cases=[(b'{bad}\n','INVALID_JSON'),
               (b'{"status":"PASS","status":"OFF_VETO"}\n','DUPLICATE_JSON_KEY'),
               (b'{"status":"OFF_VETO","v":NaN}\n','NONFINITE_JSON'),
               (b'{"status":"OFF_VETO","v":1e999}\n','NONFINITE_JSON')]
        for data,code in cases:
            with self.subTest(code=code),tempfile.TemporaryDirectory() as d:
                r=fixtures(d);p=Path(d)/'current.jsonl';change(p,data)
                r['method_results']['current']['association_stream']=receipt(p,1)
                with self.assertRaises(c.ClosureError) as cm:c.verify_manifest_streams(d,r)
                self.assertEqual(cm.exception.code,code)

    def test_failed_computation_never_promoted_by_valid_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            r=fixtures(d);r['status']='FAIL'
            check=c.evaluate_closure(d,r,'child_end')
            self.assertEqual(check['status'],'PASS')
            self.assertEqual(check['effective_status'],'FAIL')


class PublicationTests(unittest.TestCase):
    def test_final_name_only_exists_after_close_and_is_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            w=c.AtomicJSONLPublisher(d,'new.jsonl')
            w.append({'status':'OFF_VETO','x':1})
            self.assertFalse((Path(d)/'new.jsonl').exists())
            self.assertTrue((Path(d)/'.new.jsonl.pending').exists())
            r=w.close()
            self.assertTrue((Path(d)/'new.jsonl').exists())
            self.assertFalse((Path(d)/'.new.jsonl.pending').exists())
            self.assertEqual((Path(d)/'new.jsonl').stat().st_mode&0o777,0o444)
            self.assertEqual(r,receipt(Path(d)/'new.jsonl',1))

    def test_existing_final_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'new.jsonl';p.write_bytes(b'old evidence')
            with self.assertRaises(FileExistsError):c.AtomicJSONLPublisher(d,'new.jsonl')
            self.assertEqual(p.read_bytes(),b'old evidence')

    def test_publication_race_preserves_pending_and_existing_final(self):
        with tempfile.TemporaryDirectory() as d:
            w=c.AtomicJSONLPublisher(d,'new.jsonl');w.append({'status':'OFF_VETO'})
            p=Path(d)/'new.jsonl';p.write_bytes(b'concurrent evidence')
            with self.assertRaises(FileExistsError):w.close()
            self.assertEqual(p.read_bytes(),b'concurrent evidence')
            self.assertTrue((Path(d)/'.new.jsonl.pending').exists())

    def test_partial_pending_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            w=c.AtomicJSONLPublisher(d,'new.jsonl');w.append({'status':'OFF_VETO'})
            w.close_partial()
            self.assertTrue((Path(d)/'.new.jsonl.pending').exists())
            self.assertFalse((Path(d)/'new.jsonl').exists())

    def test_bad_record_prevents_publication_and_preserves_pending(self):
        with tempfile.TemporaryDirectory() as d:
            w=c.AtomicJSONLPublisher(d,'new.jsonl');w.append({'status':'UNKNOWN'})
            with self.assertRaises(c.ClosureError):w.close()
            self.assertTrue((Path(d)/'.new.jsonl.pending').exists())
            self.assertFalse((Path(d)/'new.jsonl').exists())


class UnchangedEndpointTests(unittest.TestCase):
    def test_frozen_bq_endpoint_comparisons_pass_with_atomic_writer(self):
        path=ROOT/'work_bq/tests/test_stream_association.py'
        spec=importlib.util.spec_from_file_location('br_reused_bq_tests',path)
        tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
        checker=tests.ExactComparatorTests()
        factories=[lambda:tests.MockStore(),lambda:tests.MockStore(off=4),
                   lambda:tests.MockStore(on=(12,3,3),off=0),lambda:tests.MockStore(unsupported=1),
                   lambda:tests.MockStore(off=8,legacy_off=4),lambda:tests.MockStore(on=(1,1,1),off=0)]
        with patch.object(tests.bq,'AssociationWriter',a.ClosedWriter):
            for index,factory in enumerate(factories):
                with self.subTest(case=index):checker.compare(factory())

    def test_wrapper_marks_child_closure_failure_effective_fail(self):
        class FakeBQ:
            AssociationWriter=None
            def run_stream_assessment(self,scan_dirs,case_spec,output_dir,base_scan_dirs,input_pins):
                Path(output_dir).mkdir()
                r=fixtures(output_dir)
                p=Path(output_dir)/'current.jsonl'
                change(p,p.read_bytes()[:-1])
                return r
        with tempfile.TemporaryDirectory() as d,patch.object(a,'load_bq',return_value=FakeBQ()):
            r=a.run_closed_assessment([],{},Path(d)/'payload',[],[])
            self.assertEqual(r['original_computation_status_preserved'],'PASS')
            self.assertEqual(r['status'],'FAIL')
            self.assertFalse(r['output_bindings_verified'])
            self.assertEqual(r['child_stream_closure']['effective_status'],'FAIL')


if __name__=='__main__':unittest.main()
