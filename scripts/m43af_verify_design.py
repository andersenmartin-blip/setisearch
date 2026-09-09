"""Check the published M43AF draft using metadata only; never read spectra."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'config/m43af_prospective_design_draft.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def generate_shifts(excluded):
    state = 430032

    def word():
        nonlocal state
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        state &= 0xffffffff
        return state

    def draw():
        while True:
            value = word()
            if value < (2**32//3841)*3841:
                return 128+value % 3841

    rows, seen = [], set()
    while len(rows) < 256:
        a, b = draw(), draw()
        row = (0, a, b)
        if min(abs(a-b), 4097-abs(a-b)) < 128 or row in excluded or row in seen:
            continue
        rows.append(list(row))
        seen.add(row)
    return rows


def verify():
    cfg = json.loads(CONFIG.read_text())
    sources = {}
    assert set(cfg['source_configs']) == set(cfg['source_sha256_from_m43ae'])
    for path in cfg['source_configs']:
        raw = (ROOT/path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == cfg['source_sha256_from_m43ae'][path], path
        sources[path] = json.loads(raw)
    excluded = set()
    for path, c in sources.items():
        if path in ('config/m43ab_attribution.json', 'config/m43ad_geometry.json',
                    'config/m43ae_joint_response.json'):
            continue
        rows = c.get('calibration_shifts', c.get('training_shifts'))+c['heldout_shifts']
        assert len(rows) == 256, path
        excluded.update(tuple(row) for row in rows)
    assert len(excluded) == 1792
    assert cfg['excluded_prior_shifts'] == [list(row) for row in sorted(excluded)]
    rows = generate_shifts(excluded)
    assert rows == cfg['training_shifts']+cfg['heldout_shifts']
    assert len(cfg['training_shifts']) == len(cfg['heldout_shifts']) == 128
    ad = sources['config/m43ad_geometry.json']
    previous = {canonical(c['components']) for s in sources.values() for c in s.get('cases', [])}
    components = {}
    counts = {}
    for panel, targets in (('training', {1280:1024, 2816:3072}),
                           ('validation', {1280:1152, 2816:2944})):
        expected = []
        for old in ad['cases']:
            if old['panel'] != 'fresh':
                continue
            c = copy.deepcopy(old)
            delta = targets[c['score_index']]-c['score_index']
            c['score_index'] += delta
            c['reference_truth']['score_index'] += delta
            for part in c['components']:
                part['truth']['score_index'] += delta
            i = len(expected)
            c.update(case_index=i, source_name=old['name'], panel=panel, name=f'{panel}{i:03d}')
            expected.append(c)
        assert cfg['cases'][panel] == expected
        assert len(expected) == 112 and sum(c['signal_present'] for c in expected) == 64
        components[panel] = {canonical(c['components']) for c in expected}
        assert not components[panel].intersection(previous)
        counts[panel] = dict(cases=112, signals=64, controls=48,
                             distinct_component_specifications=len(components[panel]))
    assert not components['training'].intersection(components['validation'])
    return dict(passed=True, metadata_only=True, prior_unique_shift_rows=1792,
                new_unique_shift_rows=256, panels=counts,
                native_payload_novelty_verified=False, scientific_measurements_evaluated=0)


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
