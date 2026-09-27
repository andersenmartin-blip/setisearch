"""One fresh local ancestry fixture; no scientific panel or codec replay."""
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from seti_repeater import factors_radio as direct
from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native
from seti_repeater.injection_m43r import ScoreStore

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def fixture():
    cfg = json.loads((ROOT / 'config/radio_score_handoff_20260927.json').read_text())
    design = cfg['fixture']
    retained = json.loads((ROOT / 'results_radio_codec_publication_2026-09-27/gzip_codec_direct.json').read_text())
    bank = direct.build(**retained['direct_bank']['record']['inputs'])
    if bank.identity != retained['direct_bank']['identity']:
        raise ValueError('published interface bank identity changed')
    geometry = core.NativeFrequencyGeometry(design['raw_zero_hz'],
        design['channel_width_hz'], design['native_channels'])
    grid = core.make_proxy_carrier_grid(
        (geometry.raw_zero_hz + 512 * geometry.channel_width_hz) / 1e6,
        geometry.channel_width_hz, design['score_half_bins'], design['support_guard_bins'])
    scans = [{'epoch': i // 2 + 1, 'kind': 'on' if i % 2 == 0 else 'off',
        'label': label, 'source_domain': 'synthetic',
        'expected_header': {'dataset_shape': [16, 1, geometry.channel_count]}}
        for i, label in enumerate(direct.LABELS)]
    context = pipeline.Context(scans=scans, factors=bank, grid=grid, window=design['window'])
    rng = np.random.default_rng(design['seed'])
    sources = {}
    for scan in scans:
        values = np.asarray(40 + rng.standard_normal((16, geometry.channel_count)), dtype='<f4')
        label = scan['label']
        sources[label] = native.normalize_synthetic_rows(lambda row, v=values: v[row],
            geometry, 16, input_orientation='ascending', scope={'kind': 'synthetic',
                'scan': label, 'direct_factor_bank_sha256': bank.identity,
                'purpose': 'score-handoff-integrity-only', 'fixture_seed': design['seed'],
                'window': context.window, 'scientific_evaluation': False})
    run = pipeline.NativeRun(context, sources)
    store = run.build_store()
    return run, store


def reconstructed_with_changed_cell(store):
    arrays = {key: value.copy() for key, value in store.arrays.items()}
    arrays['on', 0, 1][0, 0] += np.float32(1)
    return ScoreStore(arrays, json.loads(json.dumps(store.provenance)))
