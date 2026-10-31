"""BY V2: declared post-exposure pairing of published histogram identifiers.

This extension preserves the original zero-join analysis. It applies only the
two explicitly declared terminal-suffix removals and compares exact stems.
Stem equality is not independent confirmation of native observation headers.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import importlib.util
import json
import resource
import signal
import statistics
import sys

sys.dont_write_bytecode = True
SUFFIXES = ('.gpuspec.0000.datnew.dat', '.rawspec.0000.datnew.dat')


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_identifiers(turbo, energy):
    tk = {}
    suffix_counts = {suffix: 0 for suffix in SUFFIXES}
    for original in turbo:
        matches = [suffix for suffix in SUFFIXES if original.endswith(suffix)]
        check(len(matches) == 1, 'Turbo identifier lacks exactly one whitelisted terminal suffix')
        suffix = matches[0]
        stem = original[:-len(suffix)]
        check(stem and stem not in tk, 'Empty or duplicate turbo canonical identifier')
        tk[stem] = original
        suffix_counts[suffix] += 1
    ek = {}
    for original in energy:
        check(original and original not in ek, 'Empty or duplicate energy identifier')
        ek[original] = original
    common = sorted(set(tk).intersection(ek))
    return {
        'schema': 'SETI_BY_V2_DECLARED_IDENTIFIER_PAIRS',
        'raw_intersection_count': len(set(turbo).intersection(energy)),
        'canonical_intersection_count': len(common),
        'turboSETI_processing_suffix_counts': suffix_counts,
        'pairs': [{'canonical_stem': stem, 'turboSETI_filename': tk[stem],
                   'energy_detection_filename': ek[stem]} for stem in common],
        'turboSETI_unmatched': [{'canonical_stem': stem, 'filename': tk[stem]}
                               for stem in sorted(set(tk).difference(ek))],
        'energy_detection_unmatched': [{'canonical_stem': stem, 'filename': ek[stem]}
                                      for stem in sorted(set(ek).difference(tk))],
        'all_raw_filenames': {'turboSETI': sorted(turbo), 'energy_detection': sorted(energy)},
    }


def paired_bins(turbo, energy, identities, frequencies):
    rows = []
    pairs = identities['pairs']
    for index, frequency in enumerate(frequencies):
        t = [turbo[pair['turboSETI_filename']][index] for pair in pairs]
        e = [energy[pair['energy_detection_filename']][index] for pair in pairs]
        n = len(pairs)
        both = sum(tv > 0 and ev > 0 for tv, ev in zip(t, e))
        tonly = sum(tv > 0 and ev == 0 for tv, ev in zip(t, e))
        eonly = sum(tv == 0 and ev > 0 for tv, ev in zip(t, e))
        neither = sum(tv == 0 and ev == 0 for tv, ev in zip(t, e))
        check(both + tonly + eonly + neither == n, 'Paired occupancy partition differs')
        rows.append({
            'lower_edge_mhz': frequency, 'upper_edge_mhz': frequency + 1,
            'source_notch_label_flag': 2300 <= frequency <= 2360,
            'fixed_neighborhood': 2298 <= frequency < 2302,
            'paired_observations': n,
            'turbo_nonzero_rows': both + tonly, 'energy_nonzero_rows': both + eonly,
            'both_nonzero_rows': both, 'turbo_only_rows': tonly,
            'energy_only_rows': eonly, 'neither_nonzero_rows': neither,
            'turbo_nonzero_fraction': (both + tonly)/n if n else None,
            'energy_nonzero_fraction': (both + eonly)/n if n else None,
            'energy_minus_turbo_nonzero_fraction': (eonly - tonly)/n if n else None,
            'turbo_total_hit_count': sum(t), 'energy_total_hit_count': sum(e),
            'turbo_median_hit_count': statistics.median(t) if n else None,
            'energy_median_hit_count': statistics.median(e) if n else None,
        })
    return rows


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def run(scope_path, out):
    scope_raw = scope_path.read_bytes()
    scope = json.loads(scope_raw)
    check(scope['schema'] == 'SETI_BY_POSTEXPOSURE_IDENTIFIER_PAIRING_V2', 'Unexpected scope')
    check(scope['whitelisted_terminal_suffixes'] == list(SUFFIXES), 'Suffix whitelist changed')
    check(scope['after_original_data_exposure'] is True and scope['no_changes_to_original_outputs'] is True,
          'Post-exposure extension status must remain explicit')
    check(scope['energy_identifier_rule'] == 'unchanged' and scope['join_rule'] == 'exact canonical string equality',
          'Unexpected identity matching')
    check(scope['frequency_lower_edges_mhz'] == [1800, 2800, 1] and scope['fixed_neighborhood_mhz'] == [2298, 2302],
          'Fixed frequency domain differs')
    check(scope['source_commit'] == 'de774a274fd2dfe44e31ba88178c9dd8305de3a0', 'Original source commit differs')
    pins = {str(scope_path): sha(scope_raw)}
    root = scope_path.parent
    for relative, digest in scope['metadata_and_source_sha256'].items():
        path = root/relative
        check(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'Source path escapes scope')
        check(sha(path.read_bytes()) == digest, 'Metadata/source bytes differ: ' + relative)
        pins[str(path)] = digest
    check(scope['metadata_and_source_sha256'][Path(__file__).name] == sha(Path(__file__).read_bytes()),
          'Production code must be pinned')
    original_scope_path = root/scope['original_scope_relative_path']
    original = json.loads(original_scope_path.read_text())
    check(original['schema'] == 'SETI_BY_DERIVED_RFI_SCOPE_V1', 'Parent scope schema')
    check(original['source_commit'] == scope['source_commit'], 'Parent source commit differs')
    parser_path = root/scope['pinned_parser_relative_path']
    module_spec = importlib.util.spec_from_file_location('by_v2_pinned_csv_parser', parser_path)
    parser = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(parser)
    tables, receipts = {}, {}
    labels = [f'{frequency:.1f}' for frequency in range(1800, 2801)]
    for item in scope['inputs']:
        detector = item['detector']
        check(detector in ('turboSETI', 'energy_detection') and detector not in tables, 'Detector identity')
        path = root/item['local_relative_path']
        check(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'Input path escapes scope')
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        check(len(raw) == item['bytes'] and blob == item['git_blob_sha1'] and sha(raw) == item['sha256'],
              'Original published CSV bytes differ')
        table, blanks = parser.parse_counts(raw, labels, original['limits'])
        tables[detector] = table
        pins[str(path)] = sha(raw)
        receipts[detector] = {'bytes': len(raw), 'sha256': sha(raw), 'git_blob_sha1': blob,
                              'published_rows': len(table), 'empty_physical_records': blanks}
    check(set(tables) == {'turboSETI', 'energy_detection'}, 'Both original tables required')
    identities = canonical_identifiers(tables['turboSETI'], tables['energy_detection'])
    bins = paired_bins(tables['turboSETI'], tables['energy_detection'], identities, range(1800, 2801))
    check(out.is_absolute() and str(out).startswith('/dev/shm/'), 'Exclusive tmpfs outputs required')
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'OBSERVATION_IDS_PAIRING_BY_V2.json', identities)
    write_json(out/'PER_BIN_PAIRING_BY_V2.json', {'schema': 'SETI_BY_V2_PAIRED_HISTOGRAM_BINS', 'bins': bins})
    with (out/'PER_BIN_PAIRING_BY_V2.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(bins[0]))
        writer.writeheader()
        writer.writerows(bins)
    result = {
        'schema': 'SETI_BY_V2_PAIRED_HISTOGRAM_RESULT', 'status': 'PASS_DECLARED_IDENTIFIER_PAIRING_V2',
        'scope_sha256': sha(scope_raw), 'production_sha256': sha(Path(__file__).read_bytes()),
        'after_original_data_exposure': True, 'source_repository': scope['source_repository'],
        'source_commit': scope['source_commit'], 'inputs': receipts,
        'paired_observations': identities['canonical_intersection_count'],
        'raw_filename_intersection_count': identities['raw_intersection_count'],
        'unmatched_observations': {d: len(identities[d+'_unmatched']) for d in tables},
        'processing_suffix_counts': identities['turboSETI_processing_suffix_counts'],
        'frequency_bins': len(bins), 'frequency_label_range_mhz': [1800, 2800],
        'source_notch_label_bins_flagged': sum(row['source_notch_label_flag'] for row in bins),
        'fixed_neighborhood': [row for row in bins if row['fixed_neighborhood']],
        'all_matched_bin_totals': {key: sum(row[key] for row in bins) for key in
                                  ('turbo_nonzero_rows', 'energy_nonzero_rows', 'both_nonzero_rows',
                                   'turbo_only_rows', 'energy_only_rows', 'neither_nonzero_rows',
                                   'turbo_total_hit_count', 'energy_total_hit_count')},
        'output_sha256': {path.name: sha(path.read_bytes()) for path in sorted(out.iterdir())},
        'interpretation_limits': scope['interpretation_limits'],
        'original_analysis_outputs_changed': False, 'new_raw_SETI_searches': 0,
        'new_original_technical_MHz_visits': 0, 'new_original_unique_archive_ids': 0,
        'completed_utc': datetime.now(timezone.utc).isoformat(),
    }
    for path, digest in pins.items():
        check(sha(Path(path).read_bytes()) == digest, 'Bound input/source changed during extension')
    result['all_bound_bytes_unchanged'] = True
    write_json(out/'SUMMARY_PAIRING_BY_V2.json', result)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--scope', required=True, type=Path)
    cli.add_argument('--out', required=True, type=Path)
    args = cli.parse_args()
    def timeout(signum, frame):
        raise TimeoutError('BY V2 60-second paired-analysis limit')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*1024**2, 16*1024**2))
    value = run(args.scope, args.out)
    signal.alarm(0)
    print(json.dumps({'status': value['status'], 'paired_observations': value['paired_observations'],
                      'unmatched_observations': value['unmatched_observations']}))
