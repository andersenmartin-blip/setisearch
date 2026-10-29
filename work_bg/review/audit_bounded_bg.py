"""Finite independent scalar QA for a bounded local-calibration radio search.

Uses synthetic arrays only. Does not load telescope data, grant execution, or
qualify sensitivity, false-alarm probabilities, discovery, or original models.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work_be/runtime'))
import numpy as np


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def scalar_track(y, offsets, center, width):
    half = width // 2
    return math.fsum(float(y[t, center + int(offsets[t]) + j])
                     for t in range(len(y)) for j in range(-half, half + 1))


def scalar_anchor(row):
    center = np.float32(statistics.median(float(x) for x in row))
    deviations = [float(np.abs(np.float32(x - center))) for x in row]
    scale = np.float32(np.float32(statistics.median(deviations)) * np.float32(1.4826))
    return center, scale


def scalar_interpolate(channel, centers, coefficients):
    if channel <= centers[0]:
        return float(coefficients[0])
    if channel >= centers[-1]:
        return float(coefficients[-1])
    for lo in range(len(centers) - 1):
        if centers[lo] <= channel <= centers[lo + 1]:
            weight = (channel - centers[lo]) / (centers[lo + 1] - centers[lo])
            return float(coefficients[lo]) + weight * (float(coefficients[lo + 1]) - float(coefficients[lo]))
    raise ValueError('Scalar interpolation support missing')


def run_checks(detector_dir):
    detector_dir = Path(detector_dir)
    kernel_path, normalization_path = detector_dir / 'kernel_v.py', detector_dir / 'continuous_normalization_ac.py'
    kernel = load('bg_qa_unchanged_kernel', kernel_path)
    norm = load('bg_qa_unchanged_normalizer', normalization_path)
    nr, nc, block = 16, 12288, 4096
    rng = np.random.default_rng(20261029)
    gradient = np.linspace(0, 25, nc, dtype=np.float64)
    raw = (100 + gradient[None, :] + rng.normal(0, 5, (nr, nc))).astype('<f4')
    raw_sha = hashlib.sha256(raw.tobytes()).hexdigest()
    y, audit = norm.normalize(raw, block)
    require(hashlib.sha256(raw.tobytes()).hexdigest() == raw_sha, 'Normalization modified native inputs')
    checks = []
    maximum_normalization_error = 0.0
    for row in (0, 7, 15):
        medians, scales = [], []
        for lo in range(0, nc, block):
            median, scale = scalar_anchor(raw[row, lo:lo + block])
            medians.append(median); scales.append(scale)
        require(np.array_equal(np.asarray(medians, dtype=np.float32), audit['block_median'][:, row]),
                'Independent float32 block medians differ')
        require(np.array_equal(np.asarray(scales, dtype=np.float32), audit['block_MAD_scale'][:, row]),
                'Independent float32 block MAD scales differ')
        for channel in (0, 2047, 2048, 4095, 4096, 6143, 6144, 8191, 8192, 10240, 12287):
            center = scalar_interpolate(channel, audit['anchor_channel'], medians)
            scale = scalar_interpolate(channel, audit['anchor_channel'], scales)
            expected = np.float32((float(raw[row, channel]) - center) / scale)
            error = abs(float(expected) - float(y[row, channel]))
            maximum_normalization_error = max(maximum_normalization_error, error)
            require(error <= 2 * np.finfo(np.float32).eps * max(abs(float(expected)), 1),
                    'Independent continuous normalized value differs')
        checks.append({'name': 'scalar_float32_anchors_and_interpolation', 'row': row, 'status': 'PASS'})

    dt, df, maxdrift = 18.253611008, -2.7939677238464355, 4.0
    nside = math.ceil(maxdrift * nr * dt / abs(df))
    rates = np.linspace(-maxdrift, maxdrift, 2 * nside + 1, dtype=np.float64)
    times = (np.arange(nr) - (nr - 1) / 2) * dt
    offsets = np.rint(rates[:, None] * times[None, :] / df).astype(np.int32)
    require(len(rates) == 839 and rates[0] == -4 and rates[-1] == 4, 'Original drift-grid geometry differs')
    for ri in (0, 419, 838):
        scalar_offsets = [round(float(rates[ri]) * ((t - 7.5) * dt) / df) for t in range(nr)]
        require(scalar_offsets == offsets[ri].tolist(), 'Independent rounded drift offsets differ')
    count, maximum_track_error, maximum_score_error = 0, 0.0, 0.0
    for width, stride in zip((1, 3, 9, 33), (1, 1, 2, 8)):
        prepared = kernel.boxcars(y, width)
        centers = np.arange(4096, 8192, stride, dtype=np.int32)
        count += len(centers) * len(rates)
        for ri in (0, 419, 838):
            got, fallbacks, _ = kernel.tracks_grid(y, prepared, offsets[ri], 4096, 8192, stride, width)
            expected = np.asarray([scalar_track(y, offsets[ri], int(c), width) for c in centers], dtype=np.float64)
            error = float(np.max(np.abs(got - expected)))
            maximum_track_error = max(maximum_track_error, error)
            require(error < 5e-5, 'Explicit scalar track sum tolerance failed')
            center = statistics.median(float(x) for x in expected)
            scale = 1.4826 * statistics.median(abs(float(x) - center) for x in expected)
            require(math.isfinite(scale) and scale > 0, 'Independent local calibration scale invalid')
            got_center = float(np.median(got))
            got_scale = float(1.4826 * np.median(np.abs(got - got_center)))
            actual_ess, scalar_ess = (got - got_center) / got_scale, (expected - center) / scale
            score_error = float(np.max(np.abs(actual_ess - scalar_ess)))
            maximum_score_error = max(maximum_score_error, score_error)
            require(score_error < 1e-9, 'Independent local-domain ESS differs')
            checks.append({'name': 'full_bounded_vector_scalar_sum_and_local_calibration', 'width': width,
                           'drift_index': ri, 'centers_checked': len(centers), 'fallbacks': fallbacks,
                           'maximum_sum_error': error, 'maximum_ess_error': score_error, 'status': 'PASS'})
        sample = centers[[0, len(centers) // 2, -1]]
        selected, _, _ = kernel.tracks_selected(y, prepared, offsets[0], sample, width)
        expected_selected = [scalar_track(y, offsets[0], int(c), width) for c in sample]
        require(np.max(np.abs(selected - expected_selected)) < 5e-5, 'Forced selected-track oracle differs')

    require(count == 9020928, 'Bounded per-scan hypothesis count differs')
    for name, action in [
        ('float64_normalized_input', lambda: kernel.boxcars(y.astype(np.float64), 1)),
        ('unsupported_width', lambda: kernel.boxcars(y, 2)),
        ('unsupported_track', lambda: kernel.tracks_selected(y, kernel.boxcars(y, 33), offsets[0], np.array([0]), 33)),
        ('zero_spectral_MAD', lambda: norm.normalize(np.ones((16, 12288), dtype='<f4'), 4096)),
        ('nonfinite_native_power', lambda: norm.normalize(np.full((16, 12288), np.nan, dtype='<f4'), 4096)),
    ]:
        try:
            action()
        except (ValueError, TypeError):
            checks.append({'name': name, 'expected_rejection': True, 'status': 'PASS'})
        else:
            raise ValueError('Required invalid-input rejection missing: ' + name)

    return {
        'schema': 'SETI_BG_BOUNDED_SCALAR_SYNTHETIC_QA_V1', 'status': 'PASS_SYNTHETIC_SCALAR_ONLY',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
        'test_matrix_shape': [nr, nc], 'drift_trials': len(rates),
        'hypotheses_per_scan': count, 'hypotheses_six_scans': count * 6,
        'maximum_normalization_error': maximum_normalization_error,
        'maximum_track_sum_error': maximum_track_error, 'maximum_local_ess_error': maximum_score_error,
        'kernel_sha256': sha(kernel_path), 'normalizer_sha256': sha(normalization_path),
        'qa_source_sha256': sha(__file__), 'archive_requests': 0, 'telescope_rows_read': 0,
        'qualification': 'Finite synthetic scalar QA only, with local bounded-domain median/MAD calibration.',
        'limits': ['Does not validate original codec/TREE model, observational origin, sensitivity or globalFAP.',
                   'Local q1 ESS calibration is a distinct family from whole-native calibration.',
                   'Does not establish any real-data search result or authorize a blind discovery claim.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--detector-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run_checks(args.detector_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'checks': len(result['checks']),
                      'maximum_track_sum_error': result['maximum_track_sum_error']}))


if __name__ == '__main__':
    main()
