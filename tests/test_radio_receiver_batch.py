"""New deterministic software fixtures; no historical native case or RNG."""
from dataclasses import replace
import math
import unittest
from unittest.mock import patch
import numpy as np
from seti_repeater import pipeline_radio as radio
from seti_repeater import transfer_m43g as native
from seti_repeater import search_v0p6 as core


def fixture(channels=4096, templates=3, score_half=8):
    geometry = core.NativeFrequencyGeometry(1.4e9, 2.79, channels)
    grid = core.make_proxy_carrier_grid((geometry.raw_zero_hz + channels//2*2.79)/1e6,
                                      2.79, score_half, 9)
    def row(i):
        x = np.arange(channels, dtype='<f4')
        return (100 + ((x*7+i*11) % 127)/32).astype('<f4')
    source = native.normalize_synthetic_rows(row, geometry, 16,
        input_orientation='ascending',
        scope={'kind': 'synthetic', 'namespace': 'receiver-batch-software-20260929f'})
    factors = np.ones((templates, 16), dtype='<f8')
    for t in range(templates):
        factors[t] += ((t % 3)-1)*1e-9*np.arange(16)
    return source, grid, factors


class ReceiverBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.grid, cls.factors = fixture()

    def cache(self, width=1):
        return native.build_synthetic_cache(self.source, self.factors, self.grid,
                                             width, bank_sha256='a'*64)

    def test_all_widths_boundaries_duplicates_and_order_match_scalar_bytes(self):
        queries = ((2,16),(0,0),(1,8),(2,16),(0,8),(1,0))
        for width in core.M37_SPECTRAL_WIDTHS:
            cache = self.cache(width)
            expected = [radio.synthetic_signature(cache, *q) for q in queries]
            got = radio.synthetic_signatures_batch(cache, queries)
            self.assertEqual(core.canonical_json_bytes(got), core.canonical_json_bytes(expected))
            self.assertIsNot(got[0][0], got[3][0])
            self.assertIsNot(got[0][1], got[3][1])

    def test_independent_source_window_oracle_all_widths(self):
        queries = ((0,0),(1,8),(2,16))
        for width in core.M37_SPECTRAL_WIDTHS:
            cache = self.cache(width)
            for (t,q), (sig,receipt) in zip(queries, radio.synthetic_signatures_batch(cache, queries)):
                total = 0.
                for f in cache.factors[t]: total += float(self.grid.score_hz[q])*float(f)
                predicted = total/16/1e6
                frequency = (self.source.geometry.raw_zero_hz + np.arange(4096)*2.79)/1e6
                raw = np.flatnonzero(abs((frequency-predicted)*1e6) <= 100.)
                values = np.zeros(len(raw), dtype='<f4')
                for row in range(16):
                    windows = self.source.values[row, raw[:,None]+np.arange(-(width//2), width//2+1)]
                    values += (np.sum(windows,axis=-1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
                values /= np.float32(math.sqrt(16))
                winner = int(np.argmax(values))
                self.assertEqual(sig['predicted_mid_mhz'], predicted)
                self.assertEqual(sig['peak_snr'], float(values[winner]))
                self.assertEqual(sig['peak_frequency_mhz'], float(frequency[raw[winner]]))
                self.assertEqual(receipt['winning_raw_index'], int(raw[winner]))

    def test_tie_uses_lowest_native_frequency(self):
        # Zero payload with fully recomputed synthetic identities is a distinct
        # hand-built arithmetic fixture, not a noise realization.
        import json
        from dataclasses import asdict
        src = self.source
        values = native.immutable(np.zeros_like(src.values)); h = native.array_hash(values)
        identity = native.digest({'contract':native.CONTRACT_SHA256,'geometry':asdict(src.geometry),
            'rows':16,'scope':json.loads(src.scope_json),'raw_sha256':src.raw_sha256,'normalized_sha256':h})
        src = replace(src, values=values, normalized_sha256=h, identity=identity)
        cache = native.build_synthetic_cache(src, self.factors, self.grid, 1, bank_sha256='a'*64)
        for sig,receipt in radio.synthetic_signatures_batch(cache, ((0,0),(2,16))):
            self.assertEqual(sig['peak_snr'], 0.)
            self.assertEqual(receipt['winning_raw_index'], receipt['raw_start'])

    def test_two_payload_validations_for_repeated_queries(self):
        cache = self.cache()
        with patch.object(native, 'gather_bank_slice', wraps=native.gather_bank_slice) as validate:
            got = radio.synthetic_signatures_batch(cache, ((0,8),)*32)
        self.assertEqual(len(got),32); self.assertEqual(validate.call_count,2)

    def test_corrupt_source_cache_and_factors_are_rejected(self):
        cache = self.cache()
        for target in ('source','values','factors'):
            a = (cache.source.values if target=='source' else getattr(cache,target)).copy(); a.flat[0]+=1
            bad = replace(cache, source=replace(cache.source, values=native.immutable(a))) if target=='source' else replace(cache, **{target:native.immutable(a)})
            with self.assertRaises(ValueError): radio.synthetic_signatures_batch(bad, ((0,8),))

    def test_readonly_view_of_mutable_owner_rejected(self):
        cache = self.cache()
        for target in ('source','values','factors'):
            a = (cache.source.values if target=='source' else getattr(cache,target)).copy()
            view=a.view();view.flags.writeable=False
            bad = replace(cache, source=replace(cache.source,values=view)) if target=='source' else replace(cache,**{target:view})
            with self.assertRaisesRegex(ValueError,'byte-backed'):radio.synthetic_signatures_batch(bad,((0,8),))

    def test_bad_query_and_capacity_fail_before_arithmetic(self):
        cache=self.cache()
        for queries in ((), ((0,8),)*30001, [(0,8)], ((0,-1),), ((0,17),), ((-1,8),), ((3,8),), ((True,8),), ((0,8,9),)):
            with patch.object(radio,'_synthetic_signature_arithmetic',side_effect=AssertionError('reached')):
                with self.assertRaises(ValueError):radio.synthetic_signatures_batch(cache,queries)

    def test_postvalidation_failure_returns_no_batch(self):
        cache=self.cache(); original=native.gather_bank_slice; calls=[]
        def validate(*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise ValueError('changed at exit')
            return original(*args,**kwargs)
        with patch.object(native,'gather_bank_slice',side_effect=validate):
            with self.assertRaisesRegex(ValueError,'changed at exit'):
                radio.synthetic_signatures_batch(cache,((0,8),))

    def test_receiver_orchestration_preserves_all_epoch_receipts_and_order(self):
        from types import SimpleNamespace
        from collections import defaultdict
        from seti_repeater import pipeline_receiver_radio as receiver
        # Orchestration fixture: cache arithmetic is tested independently above.
        bank = [{'template_index':i,'fixture':True} for i in range(3)]
        context = SimpleNamespace(bank=bank,identity='b'*64,
                                  factor_contract=SimpleNamespace(identity='c'*64))
        run = SimpleNamespace(context=context,source_ids={'fixture':self.source.identity},
                              cache=lambda label,width:self.cache(width))
        records = [{'record_id':str(i),'template_index':t,'proxy_carrier_index':q,
                    'spectral_width_channels':w,'active_epochs_zero_based':epochs}
                   for i,(t,q,w,epochs) in enumerate(((2,16,129,[0,2]),(0,0,1,[1]),(2,16,129,[0,1,2])))]
        expected={r['record_id']:[] for r in records}; queries=defaultdict(list); receipts=[]
        for r in records:
            for e in r['active_epochs_zero_based']:queries[f'epoch{e+1}_on',r['spectral_width_channels']].append((r,e))
        for (label,width), entries in sorted(queries.items()):
            cache=run.cache(label,width)
            for r,e in entries:
                sig,receipt=radio.synthetic_signature(cache,r['template_index'],r['proxy_carrier_index'])
                expected[r['record_id']].append({'epoch_zero_based':e,**sig})
                receipts.append({'record_id':r['record_id'],'scan':label,**receipt})
        for values in expected.values():values.sort(key=lambda x:x['epoch_zero_based'])
        with patch.object(radio,'synthetic_signature',side_effect=AssertionError('scalar path reached')):
            got,receipt=receiver.NativeRun.receiver(run,records,bank)
        self.assertEqual(core.canonical_json_bytes(got),core.canonical_json_bytes(expected))
        self.assertEqual(core.canonical_json_bytes(receipt['queries']),core.canonical_json_bytes(receipts))
        self.assertEqual(receipt['signatures_sha256'],native.digest(expected))
        self.assertIsNone(run._cached);self.assertIsNone(run._cached_key)


if __name__=='__main__': unittest.main()
