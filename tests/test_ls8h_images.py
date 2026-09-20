import unittest
import numpy as np
from seti_repeater.cheops_image_pair import temporal_map, analyze, classify
from ls8h_images_audit import rebuild


class PairedImageAnswers(unittest.TestCase):
    def setUp(self):
        self.t=np.arange(30,dtype=float)-14
        self.side=np.r_[np.arange(12),np.arange(18,30)]
        self.event=np.array([14,15])
        y,x=np.indices((101,101))
        self.p=1e5*np.exp(-((x-50)**2+(y-50)**2)/80.)
        self.base=100+self.p

    def cubes(self):return np.repeat(self.base[None,:,:],30,axis=0)

    def test_tiny_signed_pulse_on_large_sloped_background(self):
        for value in (1e-6,-1e-6,19.,-19.):
            cube=np.broadcast_to((4e8+2*self.t)[:,None,None],(30,2,2)).copy()
            cube[self.event]+=value
            got=temporal_map(self.t,cube,self.side,self.event)
            expected=2*(cube[14,0,0]-4e8)
            np.testing.assert_allclose(got,expected,rtol=0,atol=1e-12)

    def test_guards_and_missing_pixels(self):
        a=self.cubes();a[12:14]+=1e8;a[16:18]-=1e8
        a[12,0,0]=np.nan;a[0,1,1]=np.nan;a[self.event,50,50]+=3
        out=temporal_map(self.t,a,self.side,self.event)
        self.assertEqual(out[50,50],6)
        self.assertTrue(np.isnan(out[1,1]))
        self.assertEqual(out[0,0],0)

    def test_pure_brightness_model(self):
        a=self.cubes();a[self.event]+=.01*self.p
        result,_=analyze(self.t,a,a,np.zeros((30,101)),self.side,self.event,[50.,50.],'positive')
        for c in result['conventions'].values():
            self.assertAlmostEqual(c['fits']['COR']['brightness']['explained'],1.,places=10)
        self.assertEqual(result['classification'],'UNRESOLVED_WITHIN_FIXED_SCOPE')

    def test_pure_displacement_model(self):
        dx=np.zeros_like(self.p);dx[:,1:-1]=(self.p[:,2:]-self.p[:,:-2])/2
        a=self.cubes();a[self.event]+=.05*dx
        result,_=analyze(self.t,a,a,np.zeros((30,101)),self.side,self.event,[50.,50.],'positive')
        for c in result['conventions'].values():
            self.assertAlmostEqual(c['fits']['COR']['displacement']['explained'],1.,places=10)
            self.assertLess(c['fits']['COR']['brightness']['explained'],.01)

    def test_correction_both_signs(self):
        for sign,value in [('positive',20.),('negative',-20.)]:
            cal=self.cubes();cor=cal.copy();cor[self.event]+=value
            smear=np.zeros((30,101));smear[self.event]+=value
            result,_=analyze(self.t,cal,cor,smear,self.side,self.event,[50.,50.],sign)
            self.assertEqual(result['classification'],'CORRECTION_LINKED')
            for c in result['conventions'].values():self.assertAlmostEqual(c['delta_over_cor'],1.)

    def test_both_coordinate_gates_and_sign_required(self):
        models={'COR':{'brightness':{'available':True,'explained':0.},'displacement':{'available':True,'explained':.9}}}
        c={'aperture_complete':True,'delta_over_cor':.5,'column_delta_over_cor':0.,'sign_matches_l2':True,'fits':models}
        both={'C0':dict(c),'C1':dict(c)}
        self.assertEqual(classify(both,'positive'),'CORRECTION_LINKED')
        both['C1']['delta_over_cor']=.49
        self.assertEqual(classify(both,'positive'),'SPATIALLY_STRUCTURED')
        both['C1']['sign_matches_l2']=False
        self.assertEqual(classify(both,'positive'),'UNRESOLVED_WITHIN_FIXED_SCOPE')

    def test_independent_correction_reference(self):
        x=np.arange(101,dtype=float)
        line=10*np.exp(-(x-50)**2/50.)
        for sign,multiplier in [('positive',1.),('negative',-1.)]:
            cal=self.cubes();cor=cal.copy();cor[self.event]+=multiplier*line[None,None,:]
            smear=np.zeros((30,101));smear[self.event]+=multiplier*line
            result,maps=rebuild(self.t,cal,cor,smear,self.side.tolist(),self.event.tolist(),[50.,50.],sign)
            self.assertEqual(result['classification'],'CORRECTION_LINKED')
            np.testing.assert_allclose(maps['DELTA'],np.broadcast_to(2*multiplier*line,(101,101)),rtol=0,atol=1e-9)
            for c in result['conventions'].values():
                self.assertAlmostEqual(c['smearing_delta_fit']['coefficients'][1],1.,places=10)


if __name__=='__main__':unittest.main()
