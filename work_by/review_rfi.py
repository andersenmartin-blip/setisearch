"""Independent, all-row validation of BY's derived RFI histogram results.

CSV decoding and Python arithmetic are shared runtime primitives. No production
analysis function is imported. Median selection, identity joins, occupancy
sets, aggregate counts and every published bin are reconstructed independently.
"""
from pathlib import Path
from fractions import Fraction
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import json
import re
import signal
import sys

EXPECTED = {
    'turboSETI': (708936, 'cbbf8b0e3bf5a672ce644fe09eeb035bc191a5f0'),
    'energy_detection': (700244, 'c8eb396c7bf21bb648fabd83ee8230ea5273b9b4'),
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_integer(text, maximum, max_chars):
    """Exact decimal string to integer, independently of Decimal parsing."""
    check(isinstance(text, str) and 0 < len(text) <= max_chars, 'Bad count cell')
    match = re.fullmatch(r'([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?', text.strip())
    check(match is not None, 'Count is not a finite decimal')
    sign, whole, tail, fraction, exponent = match.groups()
    digits = (whole or '') + (tail if tail is not None else (fraction or ''))
    mantissa = int(digits)
    if mantissa == 0:
        return 0
    check(sign != '-', 'Negative count')
    exponent = int(exponent or 0)
    decimal_places = len(tail if tail is not None else (fraction or ''))
    shift = exponent - decimal_places
    # A valid nonzero bounded integer cannot need a huge power of ten.
    check(-len(digits) <= shift <= len(str(maximum)), 'Decimal exponent incompatible with integer cap')
    rational = Fraction(mantissa * 10 ** max(shift, 0), 10 ** max(-shift, 0))
    check(rational.denominator == 1 and rational.numerator <= maximum, 'Noninteger or oversized count')
    return rational.numerator


def read_table(raw, labels, caps):
    check(len(raw) <= caps['max_file_bytes'], 'File cap')
    records = list(csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True))
    check(records and records[0] == ['filename'] + labels, 'CSV header differs')
    result = {}
    blank = 0
    for record in records[1:]:
        if not record:
            blank += 1
            continue
        check(len(record) == 1 + len(labels), 'CSV record width differs')
        name = record[0]
        check(name and len(name) <= caps['max_filename_chars'] and '\0' not in name, 'Bad filename')
        check(name not in result, 'Duplicate raw filename')
        result[name] = tuple(parse_integer(x, caps['max_count_integer'], caps['max_numeric_cell_chars']) for x in record[1:])
        check(len(result) <= caps['max_rows_per_file'], 'Row cap')
    check(result, 'Empty observation table')
    return result, blank


def independent_identities(tables):
    output = {}
    for mode in ('raw', 'canonical'):
        mapping = {}
        for detector in ('turboSETI', 'energy_detection'):
            names = {}
            for raw in tables[detector]:
                key = raw
                if mode == 'canonical' and detector == 'turboSETI' and key[-4:] == '.dat':
                    key = key[:-4]
                check(key and key not in names, 'Canonical collision')
                names[key] = raw
            mapping[detector] = names
        common = sorted(set(mapping['turboSETI']).intersection(mapping['energy_detection']))
        output[mode] = {
            'intersection_count': len(common), 'intersection': common,
            'pairs': [{'key': key, 'turboSETI_filename': mapping['turboSETI'][key],
                       'energy_detection_filename': mapping['energy_detection'][key]} for key in common],
            'turboSETI_unmatched': [{'key': key, 'filename': mapping['turboSETI'][key]}
                                    for key in sorted(set(mapping['turboSETI']).difference(mapping['energy_detection']))],
            'energy_detection_unmatched': [{'key': key, 'filename': mapping['energy_detection'][key]}
                                           for key in sorted(set(mapping['energy_detection']).difference(mapping['turboSETI']))],
        }
    output['all_raw_filenames'] = {detector: sorted(table) for detector, table in tables.items()}
    return output


def independent_bins(tables, identities, frequencies):
    result = []
    columns = {detector: list(zip(*table.values())) for detector, table in tables.items()}
    for index, frequency in enumerate(frequencies):
        row = {'lower_edge_mhz': frequency, 'upper_edge_mhz': frequency+1,
               'source_notch_label_flag': 2300 <= frequency <= 2360,
               'fixed_neighborhood': 2298 <= frequency < 2302}
        for detector in ('turboSETI', 'energy_detection'):
            values = sorted(columns[detector][index])
            n = len(values)
            total = 0
            zero = 0
            for value in values:
                total += value
                zero += value == 0
            median = values[n//2] if n % 2 else float(Fraction(values[n//2-1] + values[n//2], 2))
            row[detector] = {'observations': n, 'nonzero_rows': n-zero,
                             'nonzero_fraction': (n-zero)/n, 'median_hit_count': median,
                             'total_hit_count': total}
        for mode in ('raw', 'canonical'):
            pairs = identities[mode]['pairs']
            tset = {pair['key'] for pair in pairs if tables['turboSETI'][pair['turboSETI_filename']][index] != 0}
            eset = {pair['key'] for pair in pairs if tables['energy_detection'][pair['energy_detection_filename']][index] != 0}
            n = len(pairs)
            row['paired_'+mode] = {
                'paired_observations': n, 'turbo_nonzero_rows': len(tset),
                'energy_nonzero_rows': len(eset), 'both_nonzero_rows': len(tset & eset),
                'turbo_only_rows': len(tset - eset), 'energy_only_rows': len(eset - tset),
                'neither_nonzero_rows': n-len(tset | eset),
                'turbo_nonzero_fraction': len(tset)/n if n else None,
                'energy_nonzero_fraction': len(eset)/n if n else None,
                'energy_minus_turbo_nonzero_fraction': (len(eset)-len(tset))/n if n else None,
            }
        result.append(row)
    return result


def verify_csv(raw, bins):
    parsed = list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True))
    check(len(parsed) == len(bins), 'Published CSV bin count differs')
    for observed, expected in zip(parsed, bins):
        flattened = {}
        for field, value in expected.items():
            if isinstance(value, dict):
                flattened.update({field+'_'+key: '' if item is None else str(item) for key, item in value.items()})
            else:
                flattened[field] = str(value)
        check(observed == flattened, 'Published CSV differs from independently reconstructed bins')


def run(scope_path, production, out):
    scope_raw = scope_path.read_bytes()
    scope = json.loads(scope_raw)
    check(scope['schema'] == 'SETI_BY_DERIVED_RFI_SCOPE_V1', 'Scope schema')
    check(scope['source_repository'] == 'dbautista98/Breakthrough_Listen' and
          scope['source_commit'] == 'de774a274fd2dfe44e31ba88178c9dd8305de3a0', 'Source identity')
    expected_shape = scope['schema_expectation']
    check((expected_shape['frequency_label_first_mhz'], expected_shape['frequency_label_last_mhz'],
           expected_shape['frequency_label_step_mhz'], expected_shape['frequency_columns']) == (1800, 2800, 1, 1001), 'Frozen bin grid')
    analysis = scope['analysis']
    check((analysis['fixed_neighborhood_lower_mhz'], analysis['fixed_neighborhood_upper_exclusive_mhz'],
           analysis['notch_flag_label_lower_inclusive_mhz'], analysis['notch_flag_label_upper_inclusive_mhz']) == (2298, 2302, 2300, 2360), 'Frozen neighborhood/notch')
    labels = [str(frequency)+'.0' for frequency in range(1800, 2801)]
    tables, receipts, pinned = {}, {}, {str(scope_path): digest(scope_raw)}
    for source in scope['inputs']:
        detector = source['detector']
        check(detector in EXPECTED and detector not in tables, 'Detector identity')
        check((source['bytes'], source['git_blob_sha1']) == EXPECTED[detector], 'Frozen source file identity')
        path = scope_path.parent/source['local_relative_path']
        check(not path.is_symlink() and path.resolve().is_relative_to(scope_path.parent.resolve()), 'Input path escapes scope')
        raw = path.read_bytes()
        git_sha = hashlib.sha1(('blob '+str(len(raw))+'\0').encode('ascii')+raw).hexdigest()
        check((len(raw), git_sha) == EXPECTED[detector], 'Original source bytes differ')
        table, blanks = read_table(raw, labels, scope['limits'])
        tables[detector] = table
        pinned[str(path)] = digest(raw)
        receipts[detector] = {'bytes': len(raw), 'git_blob_sha1': git_sha, 'sha256': digest(raw),
                              'published_rows': len(table), 'empty_physical_records': blanks,
                              'all_counts_integer_finite_nonnegative': True}
    check(set(tables) == set(EXPECTED), 'Both tables required')
    ids = independent_identities(tables)
    bins = independent_bins(tables, ids, range(1800, 2801))
    expected_datasets = {}
    for detector, table in tables.items():
        total = positive = zeros = 0
        for values in table.values():
            if all(value == 0 for value in values):
                zeros += 1
            for value in values:
                total += value
                positive += value != 0
        expected_datasets[detector] = {
            **receipts[detector], 'frequency_bins': 1001,
            'total_count_cells': len(table)*1001,
            'total_hit_counts_all_bins': total, 'nonzero_count_cells': positive,
            'all_zero_observation_rows': zeros,
            'all_zero_frequency_bins': sum(all(values[index] == 0 for values in table.values()) for index in range(1001)),
        }
    paths = [production/name for name in ['SUMMARY_RFI_BY.json', 'PER_BIN_RFI_BY.json',
             'PER_BIN_RFI_BY.csv', 'OBSERVATION_IDS_RFI_BY.json']]
    raw_outputs = {p.name: p.read_bytes() for p in paths}
    pinned.update({str(p): digest(raw_outputs[p.name]) for p in paths})
    summary = json.loads(raw_outputs['SUMMARY_RFI_BY.json'])
    check(summary['status'] == 'PASS_DESCRIPTIVE_DERIVED_COUNTS', 'Production did not pass')
    check(summary['scope_sha256'] == digest(scope_raw), 'Scope binding differs')
    check(json.loads(raw_outputs['OBSERVATION_IDS_RFI_BY.json']) == ids, 'Observation identity outputs differ')
    check(json.loads(raw_outputs['PER_BIN_RFI_BY.json']) == {'schema': 'SETI_BY_RFI_ALL_BINS_V1', 'bins': bins}, 'Per-bin JSON differs')
    verify_csv(raw_outputs['PER_BIN_RFI_BY.csv'], bins)
    check(summary['datasets'] == expected_datasets, 'Dataset summary differs')
    check(summary['fixed_neighborhood'] == bins[498:502] and summary['notch_flagged_label_bins'] == 61, 'Neighborhood/notch summary differs')
    for mode in ('raw', 'canonical'):
        check(summary[mode+'_filename_intersection_count'] == ids[mode]['intersection_count'], 'Pair count differs')
    check(summary['identity_matching'] == scope['identity_matching'] and summary['interpretation_limits'] == scope['interpretation_limits'], 'Interpretation changed')
    check(summary['frequency_label_range_mhz'] == [1800, 2800], 'Frequency extent differs')
    check(summary['source_commit'] == scope['source_commit'] and summary['source_repository'] == scope['source_repository'], 'Summary source differs')
    check(summary['analyzer_sha256'] == digest((scope_path.parent/'analyze_rfi.py').read_bytes()), 'Analyzer source binding differs')
    check(summary['all_inputs_unchanged'] is True, 'Input closure missing')
    for field in ('new_raw_SETI_searches', 'new_original_technical_MHz_visits', 'new_original_unique_archive_ids'):
        check(summary[field] == 0, 'Unjustified search credit')
    check(summary['output_sha256'] == {name: digest(raw) for name, raw in raw_outputs.items() if name != 'SUMMARY_RFI_BY.json'}, 'Output hashes differ')
    for path, value in pinned.items():
        check(digest(Path(path).read_bytes()) == value, 'Bound bytes changed during audit')
    check(out.is_absolute() and str(out).startswith('/dev/shm/'), 'Exclusive tmpfs output required')
    out.mkdir(parents=True, exist_ok=False)
    result = {
        'schema': 'SETI_BY_INDEPENDENT_DERIVED_RFI_REVIEW_V1',
        'status': 'PASS_INDEPENDENT_RFI_REVIEW', 'scope_sha256': digest(scope_raw),
        'reviewer_sha256': digest(Path(__file__).read_bytes()),
        'summary_sha256': digest(raw_outputs['SUMMARY_RFI_BY.json']),
        'all_original_count_cells_checked': sum(len(t)*1001 for t in tables.values()),
        'all_frequency_bins_checked': len(bins),
        'published_rows': {key: len(value) for key, value in tables.items()},
        'raw_pairs': ids['raw']['intersection_count'], 'canonical_pairs': ids['canonical']['intersection_count'],
        'fixed_neighborhood_bins_checked': 4, 'source_notch_label_bins_flagged': 61,
        'all_per_bin_medians_counts_fractions_and_pair_cells_exact': True,
        'all_identifiers_and_unmatched_lists_exact': True,
        'JSON_and_CSV_outputs_checked': True, 'all_bound_bytes_unchanged': True,
        'bound_sha256': pinned,
        'limits': ['CSV decoder and Python runtime are shared; parsing arithmetic, reductions and identity joins are independently implemented.',
                   'This checks descriptive published hit counts, not telescope powers, historical processing settings or exposure validity.',
                   'No independent source execution, false-alarm calibration, detector ranking or new SETI search coverage.'],
        'completed_utc': datetime.now(timezone.utc).isoformat(),
    }
    with (out/'REVIEW_RFI_BY.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--production', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    def timeout(signum, frame):
        raise TimeoutError('RFI independent review time cap')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    result = run(args.scope, args.production, args.out)
    signal.alarm(0)
    print(json.dumps({'status': result['status'], 'count_cells_checked': result['all_original_count_cells_checked']}))
