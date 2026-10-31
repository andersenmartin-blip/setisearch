"""Prospective descriptive analysis of two published hit-count histograms.

No original telescope powers, detection thresholds or data-dependent masks.
Only the exact frozen CSV sizes/Git blobs are accepted in the production CLI.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import resource
import signal
import statistics
import sys
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def parse_counts(raw, labels, caps):
    """Strict UTF-8 CSV; retain every nonempty physical record, no imputation."""
    require(len(raw) <= caps['max_file_bytes'], 'CSV exceeds size cap')
    rows = csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True)
    header = next(rows, None)
    require(header == ['filename', *labels], 'Unexpected column schema')
    observations = {}
    empty_records = 0
    for row in rows:
        if not row:
            empty_records += 1
            continue
        require(len(row) == len(header), 'Inconsistent row width')
        name = row[0]
        require(0 < len(name) <= caps['max_filename_chars'] and '\0' not in name,
                'Invalid observation identifier')
        require(name not in observations, 'Duplicate observation identifier')
        values = []
        for cell in row[1:]:
            require(0 < len(cell) <= caps['max_numeric_cell_chars'], 'Invalid numeric cell length')
            try:
                value = Decimal(cell)
            except InvalidOperation as exc:
                raise ValueError('Nonnumeric count') from exc
            require(value.is_finite() and value >= 0 and value == value.to_integral_value(),
                    'Nonfinite, negative or noninteger count')
            require(value <= caps['max_count_integer'], 'Count exceeds fixed integer cap')
            values.append(int(value))
        observations[name] = values
        require(len(observations) <= caps['max_rows_per_file'], 'Too many rows')
    require(observations, 'No observation records')
    return observations, empty_records


def make_keys(observations, detector, canonical):
    result = {}
    for raw in observations:
        key = raw[:-4] if canonical and detector == 'turboSETI' and raw.endswith('.dat') else raw
        require(key and key not in result, 'Empty or duplicate canonical identifier')
        result[key] = raw
    return result


def identity_sets(turbo, energy):
    output = {}
    for name, canonical in [('raw', False), ('canonical', True)]:
        tk = make_keys(turbo, 'turboSETI', canonical)
        ek = make_keys(energy, 'energy_detection', canonical)
        common = sorted(tk.keys() & ek.keys())
        output[name] = {
            'intersection_count': len(common),
            'intersection': common,
            'pairs': [{'key': key, 'turboSETI_filename': tk[key],
                       'energy_detection_filename': ek[key]} for key in common],
            'turboSETI_unmatched': [{'key': key, 'filename': tk[key]}
                                   for key in sorted(tk.keys()-ek.keys())],
            'energy_detection_unmatched': [{'key': key, 'filename': ek[key]}
                                          for key in sorted(ek.keys()-tk.keys())],
        }
    return output


def dataset_bin(observations, index):
    values = [row[index] for row in observations.values()]
    count = len(values)
    nonzero = sum(value > 0 for value in values)
    return {'observations': count, 'nonzero_rows': nonzero,
            'nonzero_fraction': nonzero/count, 'median_hit_count': statistics.median(values),
            'total_hit_count': sum(values)}


def paired_bin(turbo, energy, pairs, index):
    states = [0, 0, 0, 0]
    for pair in pairs:
        t = turbo[pair['turboSETI_filename']][index] > 0
        e = energy[pair['energy_detection_filename']][index] > 0
        states[2*int(t)+int(e)] += 1
    neither, eonly, tonly, both = states
    n = sum(states)
    return {'paired_observations': n, 'turbo_nonzero_rows': tonly+both,
            'energy_nonzero_rows': eonly+both, 'both_nonzero_rows': both,
            'turbo_only_rows': tonly, 'energy_only_rows': eonly,
            'neither_nonzero_rows': neither,
            'turbo_nonzero_fraction': (tonly+both)/n if n else None,
            'energy_nonzero_fraction': (eonly+both)/n if n else None,
            'energy_minus_turbo_nonzero_fraction': (eonly-tonly)/n if n else None}


def calculate(turbo, energy, frequencies, analysis):
    identities = identity_sets(turbo, energy)
    rows = []
    for index, low in enumerate(frequencies):
        rows.append({
            'lower_edge_mhz': low, 'upper_edge_mhz': low+1,
            'source_notch_label_flag': analysis['notch_flag_label_lower_inclusive_mhz'] <= low <= analysis['notch_flag_label_upper_inclusive_mhz'],
            'fixed_neighborhood': analysis['fixed_neighborhood_lower_mhz'] <= low < analysis['fixed_neighborhood_upper_exclusive_mhz'],
            'turboSETI': dataset_bin(turbo, index),
            'energy_detection': dataset_bin(energy, index),
            'paired_raw': paired_bin(turbo, energy, identities['raw']['pairs'], index),
            'paired_canonical': paired_bin(turbo, energy, identities['canonical']['pairs'], index),
        })
    return identities, rows


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def expire(signum, frame):
    raise TimeoutError('Frozen wall-time limit exceeded')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    scope_raw = args.scope.read_bytes()
    scope = json.loads(scope_raw)
    require(scope['schema'] == 'SETI_BY_DERIVED_RFI_SCOPE_V1', 'Unexpected scope')
    caps = scope['limits']
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(caps['wall_seconds'])
    resource.setrlimit(resource.RLIMIT_AS, (caps['memory_bytes'], caps['memory_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (caps['output_file_size_bytes'], caps['output_file_size_bytes']))
    require(args.out.is_absolute() and str(args.out).startswith('/dev/shm/'), 'Output must be exclusive tmpfs directory')
    args.out.mkdir(parents=True, exist_ok=False)
    shape = scope['schema_expectation']
    frequencies = list(range(shape['frequency_label_first_mhz'], shape['frequency_label_last_mhz']+1,
                             shape['frequency_label_step_mhz']))
    require(len(frequencies) == shape['frequency_columns'] == 1001, 'Unexpected frequency count')
    labels = [f'{value:.1f}' for value in frequencies]
    observations, receipts, paths = {}, {}, {}
    for source in scope['inputs']:
        detector = source['detector']
        require(detector in ('turboSETI', 'energy_detection') and detector not in observations,
                'Duplicate or unknown detector')
        path = args.scope.parent/source['local_relative_path']
        require(not path.is_symlink() and path.resolve().is_relative_to(args.scope.parent.resolve()),
                'Input path escapes scope directory')
        raw = path.read_bytes()
        require(len(raw) == source['bytes'] and git_blob(raw) == source['git_blob_sha1'],
                'Input does not match frozen original Git blob')
        values, blank = parse_counts(raw, labels, caps)
        observations[detector] = values
        receipts[detector] = {'bytes': len(raw), 'git_blob_sha1': git_blob(raw), 'sha256': sha256(raw),
                              'published_rows': len(values), 'empty_physical_records': blank,
                              'all_counts_integer_finite_nonnegative': True}
        paths[detector] = path
    require(set(observations) == {'turboSETI', 'energy_detection'}, 'Both detectors required')
    identities, rows = calculate(observations['turboSETI'], observations['energy_detection'], frequencies, scope['analysis'])
    dataset_summaries = {}
    for detector, source in observations.items():
        total_cells = len(source)*len(frequencies)
        dataset_summaries[detector] = {
            **receipts[detector], 'frequency_bins': len(frequencies),
            'total_count_cells': total_cells,
            'total_hit_counts_all_bins': sum(row[detector]['total_hit_count'] for row in rows),
            'nonzero_count_cells': sum(row[detector]['nonzero_rows'] for row in rows),
            'all_zero_observation_rows': sum(not any(row) for row in source.values()),
            'all_zero_frequency_bins': sum(row[detector]['nonzero_rows'] == 0 for row in rows),
        }
    identities['all_raw_filenames'] = {d: sorted(v) for d, v in observations.items()}
    write_json(args.out/'OBSERVATION_IDS_RFI_BY.json', identities)
    write_json(args.out/'PER_BIN_RFI_BY.json', {'schema': 'SETI_BY_RFI_ALL_BINS_V1', 'bins': rows})
    flattened = []
    for row in rows:
        flat = {key: value for key, value in row.items() if not isinstance(value, dict)}
        for group in ('turboSETI', 'energy_detection', 'paired_raw', 'paired_canonical'):
            flat.update({group+'_'+key: value for key, value in row[group].items()})
        flattened.append(flat)
    with (args.out/'PER_BIN_RFI_BY.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flattened[0]))
        writer.writeheader()
        writer.writerows(flattened)
    for detector, path in paths.items():
        require(sha256(path.read_bytes()) == receipts[detector]['sha256'], 'Input changed during analysis')
    require(args.scope.read_bytes() == scope_raw, 'Scope changed during analysis')
    summary = {
        'schema': 'SETI_BY_DERIVED_RFI_RESULT_V1', 'status': 'PASS_DESCRIPTIVE_DERIVED_COUNTS',
        'scope_sha256': sha256(scope_raw), 'source_commit': scope['source_commit'],
        'source_repository': scope['source_repository'],
        'analyzer_sha256': sha256(Path(__file__).read_bytes()), 'python_version': sys.version,
        'datasets': dataset_summaries, 'frequency_label_range_mhz': [frequencies[0], frequencies[-1]],
        'raw_filename_intersection_count': identities['raw']['intersection_count'],
        'canonical_filename_intersection_count': identities['canonical']['intersection_count'],
        'identity_matching': scope['identity_matching'],
        'fixed_neighborhood': [row for row in rows if row['fixed_neighborhood']],
        'notch_flagged_label_bins': sum(row['source_notch_label_flag'] for row in rows),
        'all_inputs_unchanged': True, 'interpretation_limits': scope['interpretation_limits'],
        'new_raw_SETI_searches': 0, 'new_original_technical_MHz_visits': 0,
        'new_original_unique_archive_ids': 0,
        'output_sha256': {p.name: sha256(p.read_bytes()) for p in sorted(args.out.iterdir())},
        'wall_seconds': time.monotonic()-started,
    }
    write_json(args.out/'SUMMARY_RFI_BY.json', summary)
    signal.alarm(0)
    print(json.dumps({'status': summary['status'], 'rows': {k: v['published_rows'] for k,v in receipts.items()},
                      'raw_matches': identities['raw']['intersection_count'],
                      'canonical_matches': identities['canonical']['intersection_count'],
                      'new_raw_SETI_searches': 0}))


if __name__ == '__main__':
    main()
