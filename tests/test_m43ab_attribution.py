from types import SimpleNamespace
import numpy as np
import pytest
from seti_repeater.attribution_m43ab import centered_signature, centered_agreement
from seti_repeater.search_v0p6 import V0P6CoverageError


def test_neighbor_cannot_replace_candidate_but_centered_rfi_is_measured():
    values = np.zeros((4, 201), dtype='<f4')
    values[:, 100] = 3
    values[:, 130] = 100
    cache = SimpleNamespace(width=1, values=values, source=SimpleNamespace(
        geometry=SimpleNamespace(raw_zero_hz=1e9, channel_width_hz=1., channel_count=201),
        integration_count=4))
    sig, raw = centered_signature(cache, np.ones(4), 1e9+100)
    assert raw == 100 and sig['peak_snr'] == 6.
    # Overlay must replace the background at the actual centered sample.
    sig, _ = centered_signature(cache, np.ones(4), 1e9+100,
                                [(100, np.array([8.], dtype='<f4'))]*4)
    assert sig['peak_snr'] == 16.
    # A real stationary interferer at the candidate center remains visible.
    values[:, 100] = 100
    assert centered_signature(cache, np.ones(4), 1e9+100)[0]['peak_snr'] == 200.


def test_response_agreement_requires_shape_and_off_strength():
    g = SimpleNamespace(score_bin_count=5, support_bin_count=9, score_slice=slice(2, 7))
    on = np.zeros((3, 9), dtype='<f4'); off = on.copy()
    on[:, 3:6] = [1, 8, 2]; off[:, 3:6] = [2, 16, 4]
    assert centered_agreement(on, off, g, 2, 3, [0, 1])['vetoed']
    off[:, 3:6] = [8, 1, 7]
    assert not centered_agreement(on, off, g, 2, 3, [0, 1])['vetoed']
    off[:, 3:6] = [.1, .8, .2]
    assert not centered_agreement(on, off, g, 2, 3, [0, 1])['vetoed']
    off[:] = 10
    result = centered_agreement(on, off, g, 2, 3, [0, 1])
    assert not result['vetoed'] and result['epochs'][0]['correlation'] is None


def test_native_boundary_is_rejected():
    cache = SimpleNamespace(width=3, values=np.zeros((4, 7), dtype='<f4'),
        source=SimpleNamespace(geometry=SimpleNamespace(raw_zero_hz=1e9,
            channel_width_hz=1., channel_count=9), integration_count=4))
    with pytest.raises(V0P6CoverageError):
        centered_signature(cache, np.ones(4), 1e9)
