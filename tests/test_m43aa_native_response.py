import unittest
from types import SimpleNamespace
import numpy as np
from m43aa_native_response import shape, similarity, raw_window_score

class NativeResponseTests(unittest.TestCase):
    def test_lobe_ties_and_censoring(self):
        r=shape([0,2,4,2,0,4,0],10)
        self.assertEqual(r['peak_index'],12)
        self.assertEqual(r['half_height_width_bins'],3)
        self.assertFalse(r['boundary_censored'])
        self.assertTrue(shape([4,2,0],0)['boundary_censored'])
        self.assertIsNone(shape([-1,-2],0)['half_height_width_bins'])

    def test_shape_similarity(self):
        self.assertAlmostEqual(similarity([0,1,4],[3,5,11]),1)
        self.assertAlmostEqual(similarity([0,1,4],[4,3,0]),-1)
        self.assertIsNone(similarity([1,1,1],[1,2,3]))

    def test_overlapping_profiles_and_clipped_mass(self):
        src=SimpleNamespace(values=np.zeros((4,11),dtype='<f4'),integration_count=4)
        parts=[([(4,np.array([.25,.5,.25]))]*4,4.),
               ([(6,np.array([.5,.5]))]*4,2.),
               ([(8,np.array([1.]))]*4,100.)]
        r=raw_window_score(src,np.array([5]*4),parts,3)
        self.assertEqual(r['component_mass_in_window'],[[1.,.5,0.]]*4)
        expected=np.float32(np.float32(5/np.sqrt(3))*4/2)
        self.assertEqual(r['score'],float(expected))
        self.assertEqual(raw_window_score(src,np.array([5]*4),parts,1)['score'],4.)
        with self.assertRaises(ValueError):raw_window_score(src,np.array([0]*4),parts,3)

if __name__=='__main__':unittest.main()
