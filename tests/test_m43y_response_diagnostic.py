import unittest
from types import SimpleNamespace
import numpy as np
from m43y_response_diagnostic import neighborhood,direct_point_score

class ResponseDiagnosticTests(unittest.TestCase):
    def test_inclusive_edges_and_ties(self):
        v=np.zeros((3,9),dtype='<f4');v[0,2]=6;v[0,6]=6;v[1,7]=99
        n=neighborhood(v,4,5,3)
        self.assertEqual(n['first_proxy_index'],-1);self.assertEqual(n['last_proxy_index'],3)
        self.assertEqual(n['maximum'],[6,0,0]);self.assertEqual(n['first_maximum_proxy_index'][0],-1)
        self.assertEqual(n['center'],[0,0,0])
    def test_no_clipped_coverage(self):
        with self.assertRaises(ValueError):neighborhood(np.zeros((3,7)),1,5,0)
    def test_native_point_additions_and_row_normalization(self):
        src=SimpleNamespace(values=np.zeros((4,11),dtype='<f4'),integration_count=4)
        overlay=SimpleNamespace(receiver=SimpleNamespace(cache=lambda label,w:SimpleNamespace(source=src)),
            joint_indices={('off',1):np.full((1,4,1),5)},
            overlay_receipt={'sources':[dict(scan='epoch2_off',profiles=[{'start':4}]*4,per_row_total_strength=2.),
                dict(scan='epoch2_off',profiles=[{'start':6}]*4,per_row_total_strength=3.),
                dict(scan='epoch2_off',profiles=[{'start':7}]*4,per_row_total_strength=99.)]})
        d=direct_point_score(overlay,'off',1,0,0,3)
        expected=np.float32(np.float32(5/np.sqrt(3))*4/2)
        self.assertEqual(d['score'],float(expected))
        self.assertEqual(direct_point_score(overlay,'off',1,0,0,1)['score'],0.)
if __name__=='__main__':unittest.main()
