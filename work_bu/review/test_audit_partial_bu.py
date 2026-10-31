"""Tiny deterministic tests; no telescope powers or network use."""
from pathlib import Path
import importlib.util
import json
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('bu_independent_subject',Path(__file__).with_name('audit_partial_bu.py'))
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)


class IndependentAuditTests(unittest.TestCase):
    def test_direct_vector_and_fsum_known_tracks(self):
        y=np.arange(16*100,dtype=np.float32).reshape(16,100)
        offsets=np.arange(-8,8,dtype=np.int32)
        centers=np.array([20,50,70],dtype=np.int32)
        for width in (1,3,9,33):
            expected=np.array([subject.scalar_track(y,offsets,int(center),width) for center in centers])
            self.assertTrue(np.array_equal(subject.direct_vector(y,offsets,centers,width),expected))

    def test_all_four_partial_states(self):
        center=np.full((4,6),12.);center[:,(1,3)]=0;center[:,5]=np.nan
        maximum=center.copy();valid=np.ones((4,6),dtype=bool);valid[:,5]=False
        maximum[1,3]=5;center[2,0]=9.999;valid[3,1]=False
        supported,on3,off,status=subject.classifications(center,maximum,valid)
        self.assertEqual(status.tolist(),['INCOMPLETE_OFF_COVERAGE','REJECTED_AVAILABLE_OFF','THREE_ON_FAIL','UNSUPPORTED'])
        self.assertEqual(supported.tolist(),[True,True,True,False])
        self.assertEqual(on3.tolist(),[True,True,False,True])
        self.assertEqual(off.tolist(),[False,True,False,False])

    def test_fixed_bound_and_empty(self):
        self.assertEqual(subject.fixed_rows(0).tolist(),[])
        self.assertEqual(subject.fixed_rows(3).tolist(),[0,1,2])
        selected=subject.fixed_rows(100000)
        self.assertEqual((len(selected),selected[0],selected[-1]),(129,0,99999))

    def test_duplicate_json_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):json.loads('{"a":1,"a":2}',object_pairs_hook=subject._pairs)
        with self.assertRaises(ValueError):json.loads('{"a":NaN}',parse_constant=subject._bad)


if __name__=='__main__':unittest.main()
