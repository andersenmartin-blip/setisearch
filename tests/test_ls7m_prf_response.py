"""Known answers for the LS7M forward operator; no native science arrays."""
import unittest
import numpy as np

from seti_repeater.tess_prf_response import LocalPRF, PRFCatalog, integrate, live_intervals


class TestPRFResponse(unittest.TestCase):
    def setUp(self):
        self.axis = np.linspace(-3, 3, 13)
        y, x = np.meshgrid(self.axis, self.axis, indexing='ij')
        self.model = LocalPRF(self.axis, self.axis, 100+3*x-4*y+x*y, np.full_like(x, .2))
        self.pixels = np.array([[0., 0.], [1., 0.], [0., 1.]])

    def test_bilinear_axis_order_and_subpixel_sign(self):
        source = np.array([.27, -.19])
        x, y = (self.pixels-source).T
        got = self.model.sample(self.pixels, source)
        np.testing.assert_allclose(got.flux, 100+3*x-4*y+x*y, rtol=0, atol=3e-14)
        self.assertLess(self.model.sample([0,0], [.1,0]).flux, 100)

    def test_integer_translation_covariance(self):
        a = self.model.sample(self.pixels, [.1,.2])
        b = self.model.sample(self.pixels+[2,-1], [2.1,-.8])
        np.testing.assert_allclose(a.flux,b.flux,rtol=0,atol=3e-14)

    def test_amplitude_and_no_phase_renormalization(self):
        other = LocalPRF(self.axis,self.axis,7*self.model.values,7*self.model.uncertainties)
        a,b = self.model.sample(self.pixels,[.1,.2]),other.sample(self.pixels,[.1,.2])
        np.testing.assert_allclose(b.flux,7*a.flux,rtol=3e-16)
        np.testing.assert_allclose(b.uncertainty_envelope,7*a.uncertainty_envelope,rtol=3e-16)
        self.assertGreater(float(a.flux.sum()),290)

    def test_edges_and_unsupported_pixels(self):
        got=self.model.sample([[3,3],[3.01,0],[-3,-3]],[0,0])
        np.testing.assert_array_equal(got.covered,[True,False,True])
        self.assertTrue(np.isnan(got.flux[1]))
        self.assertTrue(np.isnan(got.uncertainty_envelope[1]))

    def test_stationary_exposure(self):
        live=live_intervals(readout_phase_seconds=.01)
        self.assertAlmostEqual(float(np.diff(live).sum()),19.8,places=12)
        got,pieces=integrate(self.model,self.pixels,[-10,10],[[.1,.2],[.1,.2]],live)
        np.testing.assert_allclose(got.flux,self.model.sample(self.pixels,[.1,.2]).flux,rtol=5e-16)
        np.testing.assert_allclose(got.uncertainty_envelope,.2,rtol=5e-16)
        self.assertEqual(pieces,10)

    def test_readout_only_and_empty_pulses(self):
        live=live_intervals(readout_phase_seconds=0)
        for pulses in [[[-.02,0]],[]]:
            got,_=integrate(self.model,self.pixels,[-10,10],[[0,0],[0,0]],live,pulse_intervals=pulses)
            np.testing.assert_allclose(got.flux,0,atol=1e-14)

    def test_thirty_millisecond_pulse_live_fraction(self):
        for phase,duration in [(0,.015),(.01,.01),(.02,.015)]:
            got,_=integrate(self.model,self.pixels,[-10,10],[[0,0],[0,0]],
                            live_intervals(readout_phase_seconds=phase),pulse_intervals=[[-.015,.015]])
            np.testing.assert_allclose(got.flux,self.model.sample(self.pixels,[0,0]).flux*duration/19.8,atol=2e-14,rtol=0)

    def test_quadratic_path_integral_with_cell_crossings(self):
        # source=(.1+.06*t, -.2-.05*t): bilinear surface becomes quadratic.
        t=np.array([-10.,-2.,10.]); xy=np.column_stack([.1+.06*t,-.2-.05*t])
        live=live_intervals(readout_phase_seconds=.01)
        got,pieces=integrate(self.model,self.pixels,t,xy,live)
        wanted=[]
        for px,py in self.pixels:
            x,y=np.polynomial.Polynomial([px-.1,-.06]),np.polynomial.Polynomial([py+.2,.05])
            primitive=(100+3*x-4*y+x*y).integ()
            wanted.append(sum(primitive(b)-primitive(a) for a,b in live)/19.8)
        np.testing.assert_allclose(got.flux,wanted,rtol=0,atol=8e-14)
        self.assertGreater(pieces,10)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError): LocalPRF([1,0],[0,1],np.ones((2,2)),np.ones((2,2)))
        for bad in [np.nan,-.001,.021]:
            with self.assertRaises(ValueError):live_intervals(readout_phase_seconds=bad)
        with self.assertRaises(ValueError):self.model.sample(4,[0,0])
        with self.assertRaises(ValueError):integrate(self.model,[[np.nan,0]],[-10,10],[[0,0],[0,0]],[[-1,1]],pulse_intervals=[])
        with self.assertRaises(ValueError):integrate(self.model,self.pixels,[-1,1],[[0,0],[0,0]],[[-2,2]])
        with self.assertRaises(ValueError):integrate(self.model,self.pixels,[-10,10],[[0,0],[0,0]],[[-1,1],[0,2]])

    def test_field_weights_and_shift_annotation_guard(self):
        catalog=object.__new__(PRFCatalog)
        catalog.entries={(3,r,c):{'model':LocalPRF(self.axis,self.axis,(1+r+c)*self.model.values,self.model.uncertainties),
                                 'file':f'{r}_{c}','row_shift':0,'column_shift':0}
                         for r in [0,1] for c in [0,1]}
        model,weights=catalog.local(3,[.2,.3],calibration_column_offset=0)
        np.testing.assert_allclose(model.values,1.5*self.model.values,rtol=3e-16)
        self.assertAlmostEqual(sum(w['weight'] for w in weights),1)
        with self.assertRaises(ValueError):catalog.local(3,[.2,.3],calibration_column_offset=-44)
        catalog.entries[(3,1,1)]['row_shift']=1
        with self.assertRaises(ValueError):catalog.local(3,[.2,.3],calibration_column_offset=0)
        catalog.local(3,[0,0],calibration_column_offset=0)  # unused annotation is harmless


if __name__=='__main__': unittest.main()
