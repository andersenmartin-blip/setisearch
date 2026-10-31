"""Tiny deterministic tests; no telescope powers or network use."""
from pathlib import Path
import importlib.util
import json
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('bv_independent_subject',Path(__file__).with_name('audit_partial_bv.py'))
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)


class IndependentAuditTests(unittest.TestCase):
    def test_complete_continuation_and_short_final_batch(self):
        self.assertEqual(len(subject.BATCHES),28)
        self.assertEqual(subject.BATCHES[0],list(range(33,41)))
        self.assertEqual(subject.BATCHES[-1],list(range(249,254)))
        self.assertEqual([q for batch in subject.BATCHES for q in batch],list(range(33,254)))
        self.assertEqual(len(subject.BATCHES[-1])*45104640,225523200)
        self.assertEqual((len(subject.BATCHES[-1])+2)*4096,28672)

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

    def test_nonempty_production_associations_against_direct_scalar_replay(self):
        # Test-only production import: the standalone reviewer still imports none.
        production_path=Path(__file__).resolve().parents[1]/'partial_search.py'
        spec=importlib.util.spec_from_file_location('bv_artificial_association',production_path)
        production=importlib.util.module_from_spec(spec);spec.loader.exec_module(production)
        kernel,_,_=production.load_numerics()
        df=-2.7939677238464355; fch=2301.85546875
        scopes=[dict(scan=i,tref_midpoint_mjd=57660.+i*10/86400,fch1_mhz=fch,df_hz=df) for i in range(5)]
        records=[dict(support_start=0) for i in range(5)]
        supports=[np.zeros((16,128),dtype=np.float32) for i in range(5)]
        for i in (0,2,4):supports[i][:,64]=1
        supports[1][:,65]=.4
        rates=np.linspace(-4,4,839);offsets=np.zeros((839,16),dtype=np.int32)
        grids=[dict(drift_hz_s=rates,offsets=offsets,**{f'calibration_width_{w}':np.tile([0.,1.],(839,1)) for w in subject.WIDTHS}) for i in range(5)]
        catalogs=[]
        for i in range(5):
            n=int(i%2==0)
            catalogs.append(dict(channel_at_midpoint=np.full(n,64,dtype=np.int32),drift_index=np.full(n,419,dtype=np.int32),width_channels=np.full(n,1,dtype=np.int16),ess=np.full(n,16.),drift_hz_s=np.zeros(n),frequency_at_midpoint_mhz=np.full(n,fch+64*df/1e6)))
        arrays,summary=production.associate_partial(dict(scans=scopes),records,grids,catalogs,kernel,supports)
        source_scans=np.array([0,2,4]);center=arrays['forced_center_local_ess'];maximum=arrays['forced_neighborhood_max_local_ess'];valid=arrays['forced_valid']
        for row,src in enumerate(source_scans):
            for scan in range(5):
                gap=(scopes[scan]['tref_midpoint_mjd']-scopes[src]['tref_midpoint_mjd'])*86400
                radius=int(np.ceil(1+.5*(rates[1]-rates[0])*abs(gap)/abs(df)))
                direct=np.array([subject.scalar_track(supports[scan],offsets[419],64+d,1) for d in range(-radius,radius+1)])
                self.assertEqual(center[row,scan],direct[radius]);self.assertEqual(maximum[row,scan],direct.max())
        classified=subject.classifications(center,maximum,valid)
        self.assertEqual(classified[3].tolist(),['REJECTED_AVAILABLE_OFF']*3)
        self.assertTrue(np.isnan(center[:,5]).all());self.assertFalse(valid[:,5].any())

    def test_duplicate_json_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):json.loads('{"a":1,"a":2}',object_pairs_hook=subject._pairs)
        with self.assertRaises(ValueError):json.loads('{"a":NaN}',parse_constant=subject._bad)


if __name__=='__main__':unittest.main()
