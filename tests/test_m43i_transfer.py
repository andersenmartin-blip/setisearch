"""M43I boundary/adversarial tests; tiny inputs mock M43H, not telescope data."""
from dataclasses import replace, asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from seti_repeater import transfer_m43i as new
from seti_repeater import transfer_m43g as synthetic
from seti_repeater import source_m43h as sources
from seti_repeater import search_v0p6 as core
from m43g_reference import direct_reference, sorted_reference


class TelescopeTransferTests(unittest.TestCase):
    def fixture(self):
        geometry=core.NativeFrequencyGeometry(100.,1.,8201)
        raw=((np.arange(3*8201).reshape(3,8201)*17%127)-63).astype('<f4')
        values=sorted_reference(raw)
        # The only mocked operation is the already tested M43H attestation gate.
        receipt=sources.seal({'complete':True,'scope':{'kind':'telescope-remote',
            'geometry':asdict(geometry)},'rows':[{'row':i,'normalized_sha256':new.array_hash(v)}
                                               for i,v in enumerate(values)]})
        with tempfile.TemporaryDirectory() as d:
            for i,v in enumerate(values):np.save(Path(d)/f'row{i:02d}.normalized.npy',v)
            with patch.object(sources,'rehydrate',return_value=receipt) as gate:
                src=new.load_telescope_source(d,trusted_receipt_sha256=receipt['receipt_sha256'])
                gate.assert_called_once_with(d,receipt['receipt_sha256'],required_kind='telescope-remote')
        grid=core.make_proxy_carrier_grid(.004,1.,30,4)
        factors=np.array([[.8,1.,1.2],[1.01,1.02,1.03]])
        return src,grid,factors

    def test_all_widths_direct_oracle_chunks_and_repeats(self):
        src,grid,f=self.fixture()
        self.assertTrue(np.any(np.diff(core.nearest_native_indices(src.geometry,f[0,0]*grid.support_hz))==0))
        for width in core.M37_SPECTRAL_WIDTHS:
            c=new.build_telescope_cache(src,f,grid,width,bank_sha256='1'*64)
            expected=direct_reference(src.values,src.geometry,f,grid,width,0,grid.support_bin_count)
            for chunk in (1,7,100):
                np.testing.assert_array_equal(new.gather_bank_slice(c,0,grid.support_bin_count,chunk_bins=chunk),expected)
            np.testing.assert_array_equal(new.gather_bank_slice(c,3,11,template_indices=[1]),expected[1:2,3:11])

    def test_synthetic_and_telescope_boundaries_are_separate(self):
        s,g,f=self.fixture()
        syn=synthetic.normalize_synthetic_rows(lambda i:np.array(s.values[i]),s.geometry,3,
                    input_orientation='ascending',scope={'kind':'synthetic'})
        with self.assertRaises(ValueError):new.build_telescope_cache(syn,f,g,1,bank_sha256='1'*64)
        with self.assertRaises(ValueError):synthetic.build_synthetic_cache(s,f,g,1,bank_sha256='1'*64)
        c=new.build_telescope_cache(s,f,g,1,bank_sha256='1'*64)
        with self.assertRaises(ValueError):synthetic.gather_bank_slice(c,0,5)

    def test_fixture_receipt_is_rejected_even_if_self_sealed(self):
        s,g,f=self.fixture()
        r=json.loads(s.receipt_json);r.pop('receipt_sha256');r['scope']['kind']='fixture'
        r=sources.seal(r)
        bad=replace(s,receipt_json=json.dumps(r),trusted_receipt_sha256=r['receipt_sha256'],
             identity=new.source_identity(s.geometry,3,r['receipt_sha256'],s.normalized_sha256))
        with self.assertRaises(ValueError):new.validate_source(bad)

    def test_wrong_trust_anchor_and_changed_receipt_rejected(self):
        s,g,f=self.fixture()
        for bad in (replace(s,trusted_receipt_sha256='0'*64),replace(s,receipt_json=s.receipt_json.replace('telescope-remote','fixture'))):
            with self.assertRaises(ValueError):new.validate_source(bad)

    def test_row_swap_resealed_payload_still_rejected_by_receipt(self):
        s,g,f=self.fixture();v=new.immutable(s.values[::-1]);h=new.array_hash(v)
        bad=replace(s,values=v,normalized_sha256=h,
                    identity=new.source_identity(s.geometry,3,s.trusted_receipt_sha256,h))
        with self.assertRaises(ValueError):new.validate_source(bad)

    def test_same_bytes_dtype_shape_and_mutability_rejected(self):
        s,g,f=self.fixture();c=new.build_telescope_cache(s,f,g,3,bank_sha256='1'*64)
        for bad in (replace(c,values=c.values.view('<u4')),replace(c,values=c.values.reshape(1,-1)),
                    replace(c,values=c.values.copy()),replace(c,factors=c.factors.view('<u8')),
                    replace(c,source=replace(s,values=s.values.view('<u4')))):
            with self.assertRaises(ValueError):new.gather_bank_slice(bad,0,5)
        with self.assertRaises(ValueError):s.values.setflags(write=True)
        with self.assertRaises(ValueError):c.values.setflags(write=True)

    def test_cache_identity_binds_bank_factors_grid_and_width(self):
        s,g,f=self.fixture();c=new.build_telescope_cache(s,f,g,3,bank_sha256='1'*64)
        for bad in (replace(c,bank_sha256='2'*64),replace(c,factors=new.immutable(f+.001)),
                    replace(c,grid=core.make_proxy_carrier_grid(.004001,1.,30,4)),replace(c,width=5),
                    replace(c,values=new.immutable(np.zeros_like(c.values)))):
            with self.assertRaises(ValueError):new.gather_bank_slice(bad,0,5)

    def test_loading_rechecks_row_after_gate(self):
        s,g,f=self.fixture();r=json.loads(s.receipt_json)
        with tempfile.TemporaryDirectory() as d:
            np.save(Path(d)/'row00.normalized.npy',np.zeros(s.geometry.channel_count,dtype='<f4'))
            with patch.object(sources,'rehydrate',return_value=r):
                with self.assertRaises(ValueError):new.load_telescope_source(d,trusted_receipt_sha256=s.trusted_receipt_sha256)

    def test_coverage_bad_factors_and_selection_rejected(self):
        s,g,f=self.fixture()
        for bad in (f*0,f*np.nan,f*3):
            with self.assertRaises(ValueError):new.build_telescope_cache(s,bad,g,1,bank_sha256='1'*64)
        with self.assertRaises(core.V0P6CoverageError):new.build_telescope_cache(s,f,core.make_proxy_carrier_grid(.02,1.,30,4),129,bank_sha256='1'*64)
        c=new.build_telescope_cache(s,f,g,1,bank_sha256='1'*64)
        for selection in ([0,0],[-1],[3],[.5],[]):
            with self.assertRaises(ValueError):new.gather_bank_slice(c,0,5,template_indices=selection)
        for bounds in ((-1,5),(5,5),(0,g.support_bin_count+1)):
            with self.assertRaises(ValueError):new.gather_bank_slice(c,*bounds)


if __name__=='__main__':unittest.main()
