import unittest
import numpy as np
from seti_repeater.cheops_l2 import score_window, cluster_positive

class CheopsL2Answers(unittest.TestCase):
    def base(self,n=80):
        c=30.8; t=2459000.+np.arange(n)*c/86400.; f=1e6+2.*np.arange(n)
        return c,t,f,np.ones(n)*10.,np.zeros(n,dtype=int),np.zeros(n,dtype=int)
    def test_linear_zero(self):
        c,t,f,e,s,v=self.base(); r=score_window(t,f,e,s,v,35,1,c)
        self.assertIsNotNone(r); self.assertAlmostEqual(r['score'],0.,places=5)
    def test_positive_and_negative(self):
        c,t,f,e,s,v=self.base(); f=f.copy(); f[35]+=120.
        self.assertGreater(score_window(t,f,e,s,v,35,1,c)['score'],8.5)
        f[35]-=240.; self.assertLess(score_window(t,f,e,s,v,35,1,c)['score'],-8.5)
    def test_status_blocks_context(self):
        c,t,f,e,s,v=self.base(); s=s.copy(); s[25]=1
        self.assertIsNone(score_window(t,f,e,s,v,35,1,c))
    def test_gap_blocks_context(self):
        c,t,f,e,s,v=self.base(); t=t.copy(); t[30:]+=120./86400.
        self.assertIsNone(score_window(t,f,e,s,v,35,1,c))
    def test_event_is_diagnostic(self):
        c,t,f,e,s,v=self.base(); v=v.copy(); v[35]=8
        self.assertEqual(score_window(t,f,e,s,v,35,1,c)['event_or'],8)
    def test_cluster_rule(self):
        rows=[{'start':10,'duration':1,'score':9.},{'start':11,'duration':2,'score':10.},{'start':20,'duration':1,'score':9.5}]
        c=cluster_positive(rows); self.assertEqual(len(c),2)
        self.assertEqual(c[0]['representative']['start'],11); self.assertEqual(c[1]['representative']['start'],20)

if __name__=='__main__': unittest.main()
