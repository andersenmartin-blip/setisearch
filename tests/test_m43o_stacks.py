import unittest
from unittest.mock import patch
import numpy as np
from m43o_stack_reference import reference_stack,qualify_stacks,validate_vectors,SUBSETS
from seti_repeater import search_v0p6 as core
from seti_repeater.transfer_m43i import array_hash

class RealStackTests(unittest.TestCase):
    def fixture(self):
        low=np.nextafter(np.float32(3),np.float32(-np.inf))
        high=np.nextafter(np.float32(3),np.float32(np.inf))
        return [np.array([[3,low,high,5,-2,4],[6,2,3,4,1,7]],dtype='<f4'),
                np.array([[3,3,3,-1,6,8],[2,5,3,6,9,1]],dtype='<f4'),
                np.array([[3,4,2,7,8,-1],[9,7,3,5,2,6]],dtype='<f4')]

    def test_raw_and_active_boundary_against_scalar_accumulation(self):
        vectors=self.fixture();cube=np.stack(vectors)
        for mode in ('raw','active3'):
            for subset in SUBSETS:
                expected=np.empty((2,6),dtype='<f4')
                for t in range(2):
                    for q in range(6):
                        value=np.float32(0);admit=True
                        for epoch in subset:
                            value=np.float32(value+cube[epoch,t,q]);admit &= cube[epoch,t,q]>=3
                        expected[t,q]=value/np.float32(np.sqrt(len(subset))) if mode=='raw' or admit else -np.inf
                np.testing.assert_array_equal(reference_stack(cube,subset,mode),expected)
                actual=core.stack_hypothesis(cube.reshape(3,-1),subset,minimum_active_epoch_snr=None if mode=='raw' else 3.,stack_statistic='sum')
                np.testing.assert_array_equal(actual.reshape(2,6),expected)
        self.assertTrue(np.isfinite(reference_stack(cube,(0,1),'active3')[0,0]))
        self.assertFalse(np.isfinite(reference_stack(cube,(0,1),'active3')[0,1]))

    def test_chunked_all_rules_include_raw_and_masked_cells(self):
        vectors=self.fixture();labels=['epoch1_on','epoch2_on','epoch3_on'];hashes=[array_hash(v) for v in vectors]
        for chunk in (1,5,6):
            checks=qualify_stacks(vectors,labels,'on',hashes,chunk_bins=chunk)
            self.assertEqual(len(checks),8)
            self.assertEqual(sum(x['cells_compared'] for x in checks),96)
            self.assertEqual(sum(x['finite_cells'] for x in checks if x['mode']=='raw'),48)
            self.assertTrue(all(x['finite_cells']<12 for x in checks if x['mode']=='active3'))
        with patch('m43o_stack_reference.core.stack_hypothesis',return_value=np.zeros(2,dtype='<f4')):
            with self.assertRaises(RuntimeError):qualify_stacks(vectors,labels,'on',hashes,chunk_bins=1)

    def test_swapped_epochs_mixed_kind_and_changed_payload_rejected(self):
        vectors=self.fixture();labels=['epoch1_on','epoch2_on','epoch3_on'];hashes=[array_hash(v) for v in vectors]
        for names in (labels[::-1],['epoch1_on','epoch2_off','epoch3_on'],[labels[0]]*3):
            with self.assertRaises(ValueError):validate_vectors(vectors,names,'on',hashes)
        for bad in ([vectors[1],vectors[0],vectors[2]],[vectors[0].astype('<f8'),*vectors[1:]],
                    [vectors[0].copy()+1,*vectors[1:]]):
            with self.assertRaises(ValueError):validate_vectors(bad,labels,'on',hashes)

    def test_rule_inventory_and_invalid_chunk_rejected(self):
        cube=np.stack(self.fixture())
        for subset,mode in (((0,), 'raw'),((0,1),'unknown'),((1,0),'raw')):
            with self.assertRaises(ValueError):reference_stack(cube,subset,mode)
        vectors=self.fixture()
        for chunk in (0,-1,True,1.5):
            with self.assertRaises(ValueError):qualify_stacks(vectors,['epoch1_on','epoch2_on','epoch3_on'],'on',[array_hash(v) for v in vectors],chunk_bins=chunk)
