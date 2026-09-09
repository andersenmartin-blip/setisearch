from types import SimpleNamespace

import numpy as np
import pytest

from seti_repeater import search_v0p6 as core
from seti_repeater.native_null_m43af import TranslatedReceiver, NativeShiftOverlay
from seti_repeater.attribution_m43ab import centered_signature
from m43aa_native_response import raw_window_score


class NativeFixture:
    def __init__(self):
        data = np.random.default_rng(20260909).normal(size=(4, 1024)).astype('<f4')
        data.flags.writeable = False
        self.source = SimpleNamespace(geometry=core.NativeFrequencyGeometry(
            raw_zero_hz=1000., channel_width_hz=1., channel_count=1024),
            integration_count=4, values=data, identity='synthetic-source')

    def cache(self, label, w):
        windows = np.lib.stride_tricks.sliding_window_view(self.source.values, w, axis=1)
        values = (np.sum(windows, axis=-1, dtype=np.float32)/np.sqrt(w)).astype('<f4')
        values.flags.writeable = False
        return SimpleNamespace(source=self.source, width=w, values=values,
                               identity=f'synthetic-{label}-{w}')


@pytest.mark.parametrize('width', core.M37_SPECTRAL_WIDTHS)
def test_translation_matches_explicit_native_windows_and_receiver(width):
    original = NativeFixture()
    receiver = TranslatedReceiver(original, [0, 137, 239])
    cache = receiver.cache('epoch2_on', width)
    assert cache.source.source_family == 'derived-normalized-native-translation'
    centers = np.array([300, 302, 301, 303])
    direct = raw_window_score(original.source, centers+137, [], width)['score']
    translated = raw_window_score(cache.source, centers, [], width)['score']
    assert np.float32(direct).view('<u4') == np.float32(translated).view('<u4')
    total = np.float32(0.)
    for row, q in enumerate(centers):
        total += cache.values[row, q-width//2]
    total /= np.float32(2.)
    assert total.view('<u4') == np.float32(direct).view('<u4')
    sig, center = centered_signature(cache, np.ones(4), 1301.)
    stationary = raw_window_score(original.source, np.full(4, center+137), [], width)['score']
    assert np.float32(sig['peak_snr']).view('<u4') == np.float32(stationary).view('<u4')
    assert receiver.cache('epoch2_off', width).source.provenance['native_shift'] == 137


def test_translation_identity_boundary_and_parent_immutability():
    original = NativeFixture()
    before = original.source.values.copy()
    receiver = TranslatedReceiver(original, [0, 137, 239])
    source = receiver.cache('epoch2_on', 1).source
    assert source.geometry.channel_count == 1024-137
    assert source.identity != original.source.identity
    np.testing.assert_array_equal(source.values, before[:, 137:])
    np.testing.assert_array_equal(original.source.values, before)
    with pytest.raises(core.V0P6CoverageError):
        TranslatedReceiver(original, [0, 1000, 0]).cache('epoch2_on', 129)
    with pytest.raises(ValueError):
        TranslatedReceiver(original, [0, -1, 0])


def test_overlay_gather_and_receiver_share_the_derived_source(monkeypatch):
    original = NativeFixture()
    factors = np.array([[1., 1.001, 1.002, 1.003]])
    monkeypatch.setattr(core, 'factor_table_for_scan', lambda *args:factors)
    monkeypatch.setattr(core, 'proxy_carrier_grid_sha256', lambda grid:'fixture-grid')
    grid = SimpleNamespace(support_hz=np.arange(1300., 1501.), support_bin_count=201,
        score_hz=np.arange(1364., 1437.), score_slice=slice(64, 137), channel_width_hz=1.)
    table = SimpleNamespace(template_bank_sha256='fixture-bank', factor_table_sha256='fixture-factors')
    bank = [dict(template_index=0)]
    shifted = NativeShiftOverlay(original, [0, 137, 239], bank, table, None, grid)
    store = shifted.trial([])
    for e, delta in enumerate((0, 137, 239)):
        for w in core.M37_SPECTRAL_WIDTHS:
            a = store.get('on', 0, w)[0][e]
            for pos in (0, 100, 200):
                idx = core.nearest_native_indices(original.source.geometry, factors[0]*grid.support_hz[pos])
                score = raw_window_score(original.source, idx+delta, [], w)['score']
                assert a[pos].view('<u4') == np.float32(score).view('<u4')
    signatures, receipt = shifted([dict(record_id='r', template_index=0,
        proxy_carrier_index=20, spectral_width_channels=3, active_epochs_zero_based=[0, 1])], bank, table)
    assert receipt['source_family'] == 'm43af-normalized-native-positive-translation-v1'
    assert len(signatures['r']) == 2
    with pytest.raises(ValueError):
        shifted.trial([dict(kind='on')])
