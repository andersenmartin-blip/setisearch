import unittest
import numpy as np
from seti_repeater.tess_reference_motion import affine_reference_motion


class ReferenceMotionTests(unittest.TestCase):
    def setUp(self):
        self.x=np.array([[1,-1,-1],[1,1,-1],[1,-1,1],[1,1,1],[1,.2,-.7],[1,-.3,.6]])
        self.side=np.r_[140:195,207:262]
        self.selected=np.r_[self.side,200:202]
        self.c=np.broadcast_to(np.arange(12).reshape(6,1,2)+100.,(6,401,2)).copy()
        self.e=np.broadcast_to(np.linspace(.002,.004,6).reshape(6,1,1),(6,401,2)).copy()
        self.q=np.zeros((6,401),int)

    def run_model(self):
        return affine_reference_motion(self.c,self.e,self.q,self.x,self.side,self.selected)

    def test_known_affine_translation_rotation_scale(self):
        # Sidebands have zero displacement, event a known spatial affine field.
        b=np.array([[.013,-.018],[.003,.005],[-.006,.002]])
        self.c[:,200:202]+= (self.x@b)[:,None,:]
        r=self.run_model()
        np.testing.assert_allclose(r['positions_xy'][200:202],np.tile(b[0],(2,1)),atol=2e-14)
        np.testing.assert_allclose(r['affine_coefficients_xy'][-2:],np.tile(b,(2,1,1)),atol=2e-14)
        np.testing.assert_allclose(r['positions_xy'][self.side],0,atol=2e-14)

    def test_formal_noise_propagation(self):
        r=self.run_model()
        for axis in range(2):
            cov=np.linalg.inv(self.x.T@np.diag(1/self.e[:,0,axis]**2)@self.x)
            np.testing.assert_allclose(r['formal_sigma_xy'][self.selected,axis],np.sqrt(cov[0,0]),rtol=1e-12)

    def test_event_errors_do_not_change_centers_or_weights(self):
        a=self.run_model()
        self.e[:,200:202]*=20
        self.c[:,200:202]+=.03
        b=self.run_model()
        for k in ['centers_xy','sideband_median_error_xy','operators_xy']:
            np.testing.assert_array_equal(a[k],b[k])
        np.testing.assert_allclose(b['formal_sigma_xy'][200:202],a['formal_sigma_xy'][200:202]*20)

    def test_unselected_data_cannot_change_result(self):
        a=self.run_model()
        unused=np.setdiff1d(np.arange(401),self.selected)
        self.c[:,unused]=np.nan
        self.e[:,unused]=np.nan
        self.q[:,unused]=999
        b=self.run_model()
        for k in a:np.testing.assert_equal(a[k],b[k])

    def test_invalid_reference_is_not_silently_dropped(self):
        self.q[0,200]=1
        with self.assertRaises(ValueError):self.run_model()
        self.q[0,200]=0
        self.e[0,200,0]=0
        with self.assertRaises(ValueError):self.run_model()

    def test_bad_geometry_and_excessive_motion_fail(self):
        original=self.x.copy()
        self.x[:,2]=self.x[:,1]
        with self.assertRaises(ValueError):self.run_model()
        self.x=original
        self.c[:,200:202]+=.3
        with self.assertRaises(ValueError):self.run_model()


if __name__=='__main__':unittest.main()
