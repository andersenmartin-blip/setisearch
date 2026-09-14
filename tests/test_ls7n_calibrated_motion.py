import unittest
import numpy as np
from seti_repeater.tess_calibrated_motion import plane_basis,source_fit,protected_plane,corrections,side_state


class KnownAnswers(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((11,11));self.p=np.exp(-((x-6.2)**2+(y-5.1)**2)/2)/6.3
        self.ap=(abs(x-6)<2)&(abs(y-5)<2);self.support=x>=1;self.outside=self.support&~self.ap
        self.plane=plane_basis((11,11));self.noise=np.ones((11,11))

    def test_source_amplitude_and_plane(self):
        image=4321*self.p+self.plane@np.array([4.,2.,-3.])
        fit=source_fit(image,self.p,self.plane,self.noise,self.support)
        self.assertTrue(fit['valid']);np.testing.assert_allclose(fit['beta'],[4321,4,2,-3],atol=2e-12,rtol=1e-12)

    def test_protected_source_annihilation_and_plane_recovery(self):
        model=protected_plane(np.array([self.p]),self.plane,self.noise,self.outside)
        self.assertTrue(model['valid']);op=model['operator']
        np.testing.assert_allclose(op@self.p[self.outside],0,atol=1e-15)
        np.testing.assert_allclose(op@(self.plane@np.array([4,2,-3]))[self.outside],[4,2,-3],atol=3e-14)

    def test_downstream_pulse_protection_and_joint_correction(self):
        op=protected_plane(np.array([self.p]),self.plane,self.noise,self.outside)['operator']
        motion=np.roll(self.p,1,axis=1)-self.p;back=self.plane@np.array([1.,-.2,.3]);delta=motion+back
        a=corrections(delta,motion,self.plane,self.outside,op)
        b=corrections(delta+20*self.p,motion,self.plane,self.outside,op)
        np.testing.assert_allclose(a['combined'],delta,atol=2e-15)
        np.testing.assert_allclose(b['combined']-a['combined'],0,atol=2e-15)

    def test_event_exclusion_from_state_and_amplitude(self):
        rng=np.random.default_rng(1749);cube=1000*self.p+rng.normal(size=(401,11,11));changed=cube.copy()
        changed[175:190]+=1e6
        a,b=side_state(cube,self.ap,180,185),side_state(changed,self.ap,180,185)
        for key in a:np.testing.assert_array_equal(a[key],b[key])
        fa=source_fit(a['reference'],self.p,self.plane,a['pixel_noise'],self.support)
        fb=source_fit(b['reference'],self.p,self.plane,b['pixel_noise'],self.support)
        np.testing.assert_array_equal(fa['beta'],fb['beta'])

    def test_invalid_source_model_is_unavailable(self):
        self.assertFalse(source_fit(-100*self.p,self.p,self.plane,self.noise,self.support)['valid'])
        flat=np.ones((11,11));self.assertFalse(source_fit(flat,flat,self.plane,self.noise,self.support)['valid'])


if __name__=='__main__':unittest.main()
