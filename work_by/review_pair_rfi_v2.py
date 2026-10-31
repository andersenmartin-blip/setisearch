"""Independent review of separately declared, post-exposure BY V2 ID pairing.

The existing independent Fraction-based CSV parser is reused. No production
parser, identity helper, occupancy reducer or median implementation is imported.
"""
from pathlib import Path
from datetime import datetime, timezone
from fractions import Fraction
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import signal
import time

SUFFIXES = ('.gpuspec.0000.datnew.dat', '.rawspec.0000.datnew.dat')
EXPECTED = {
    'turboSETI': (708936, 'cbbf8b0e3bf5a672ce644fe09eeb035bc191a5f0',
                 '8abf461a2510913de4642d9c9ab4f07c2311d997e6ea859a0e854088a82d8b80'),
    'energy_detection': (700244, 'c8eb396c7bf21bb648fabd83ee8230ea5273b9b4',
                        'b0fb3926f27a055a3d3b54a472c8f9438fa9018b51f470894ce0f90e54693648'),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    def bad(value):
        raise ValueError('Nonfinite JSON: '+value)
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(),object_pairs_hook=pairs,parse_constant=bad)


def identities(turbo, energy):
    pattern = re.compile(r'(.+)(\.(?:gpuspec|rawspec)\.0000\.datnew\.dat)\Z',re.DOTALL)
    stripped = {}
    suffix_counts = dict.fromkeys(SUFFIXES,0)
    for raw in turbo:
        match = pattern.fullmatch(raw)
        require(match is not None, 'Unknown terminal processing suffix or empty stem')
        stem,suffix = match.groups()
        require(stem not in stripped, 'Canonical turbo identifier collision')
        stripped[stem] = raw
        suffix_counts[suffix] += 1
    unchanged = {}
    for raw in energy:
        require(raw and raw not in unchanged, 'Empty or duplicate energy identity')
        unchanged[raw] = raw
    common = sorted(set(stripped)&set(unchanged))
    return dict(schema='SETI_BY_V2_DECLARED_IDENTIFIER_PAIRS',
                raw_intersection_count=len(set(turbo)&set(energy)),
                canonical_intersection_count=len(common),
                turboSETI_processing_suffix_counts=suffix_counts,
                pairs=[dict(canonical_stem=key,turboSETI_filename=stripped[key],
                            energy_detection_filename=unchanged[key]) for key in common],
                turboSETI_unmatched=[dict(canonical_stem=key,filename=stripped[key])
                                     for key in sorted(set(stripped)-set(unchanged))],
                energy_detection_unmatched=[dict(canonical_stem=key,filename=unchanged[key])
                                             for key in sorted(set(unchanged)-set(stripped))],
                all_raw_filenames=dict(turboSETI=sorted(turbo),energy_detection=sorted(energy)))


def median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    if n%2:
        return ordered[n//2]
    return float(Fraction(ordered[n//2-1]+ordered[n//2],2))


def bins_from_pairs(turbo, energy, matches, frequencies):
    output = []
    pairs = matches['pairs']
    n = len(pairs)
    for index,frequency in enumerate(frequencies):
        turbo_counts = {pair['canonical_stem']:turbo[pair['turboSETI_filename']][index] for pair in pairs}
        energy_counts = {pair['canonical_stem']:energy[pair['energy_detection_filename']][index] for pair in pairs}
        t = {key for key,value in turbo_counts.items() if value != 0}
        e = {key for key,value in energy_counts.items() if value != 0}
        tonly,eonly,both = t-e,e-t,t&e
        output.append(dict(lower_edge_mhz=frequency,upper_edge_mhz=frequency+1,
                           source_notch_label_flag=2300 <= frequency <= 2360,
                           fixed_neighborhood=2298 <= frequency < 2302,
                           paired_observations=n,turbo_nonzero_rows=len(t),energy_nonzero_rows=len(e),
                           both_nonzero_rows=len(both),turbo_only_rows=len(tonly),energy_only_rows=len(eonly),
                           neither_nonzero_rows=n-len(t|e),
                           turbo_nonzero_fraction=len(t)/n if n else None,
                           energy_nonzero_fraction=len(e)/n if n else None,
                           energy_minus_turbo_nonzero_fraction=(len(e)-len(t))/n if n else None,
                           turbo_total_hit_count=sum(turbo_counts.values()),
                           energy_total_hit_count=sum(energy_counts.values()),
                           turbo_median_hit_count=median(turbo_counts.values()),
                           energy_median_hit_count=median(energy_counts.values())))
    return output


def run(scope_path, production, out):
    start = time.monotonic()
    scope_path,production,out = map(Path,(scope_path,production,out))
    root = scope_path.parent
    scope = read(scope_path)
    require(scope['schema'] == 'SETI_BY_POSTEXPOSURE_IDENTIFIER_PAIRING_V2', 'Wrong scope family')
    require(scope['source_repository'] == 'dbautista98/Breakthrough_Listen' and
            scope['source_commit'] == 'de774a274fd2dfe44e31ba88178c9dd8305de3a0', 'Wrong source identity')
    require(scope['after_original_data_exposure'] is True and
            scope['prior_pairing_results_preserved'] == {'raw_intersection':0,'original_terminal_dat_only_intersection':0},
            'Post-exposure declaration/history differs')
    require(scope['whitelisted_terminal_suffixes'] == list(SUFFIXES) and
            scope['energy_identifier_rule'] == 'unchanged' and
            scope['join_rule'] == 'exact canonical string equality', 'Join rule differs')
    require(scope['frequency_lower_edges_mhz'] == [1800,2800,1] and
            scope['fixed_neighborhood_mhz'] == [2298,2302] and
            scope['source_notch_label_region_inclusive_mhz'] == [2300,2360], 'Frequency scope differs')
    pins = {str(scope_path):sha(scope_path.read_bytes()),
            str(Path(__file__).resolve()):sha(Path(__file__).read_bytes())}
    require(Path(__file__).name in scope['metadata_and_source_sha256'] and
            'review_rfi.py' in scope['metadata_and_source_sha256'], 'Independent audit code dependencies must be pinned')
    for relative,digest in scope['metadata_and_source_sha256'].items():
        path = root/relative
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'Metadata path escapes scope')
        pins[str(path)] = digest
    require(all(sha(Path(path).read_bytes()) == digest for path,digest in pins.items()), 'Frozen dependencies differ')
    helper_path = root/'review_rfi.py'
    helper_hash = sha(helper_path.read_bytes())
    require(pins[str(helper_path)] == helper_hash, 'Independent CSV parser differs from frozen source')
    spec = importlib.util.spec_from_file_location('by_v2_independent_csv',helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    parent_path = root/scope['original_scope_relative_path']
    original = read(parent_path)
    require(original['schema'] == 'SETI_BY_DERIVED_RFI_SCOPE_V1', 'Wrong original scope')
    pins[str(parent_path)] = sha(parent_path.read_bytes())
    original_summary_path = root/'SUMMARY_RFI_BY.json'
    original_summary = read(original_summary_path)
    require(original_summary['raw_filename_intersection_count'] ==
            original_summary['canonical_filename_intersection_count'] == 0,
            'Original no-match summary changed')
    require(original_summary['status'] == 'PASS_DESCRIPTIVE_DERIVED_COUNTS', 'Original analysis status differs')
    pins[str(original_summary_path)] = sha(original_summary_path.read_bytes())
    require(all(sha(Path(path).read_bytes()) == digest for path,digest in pins.items()), 'Frozen dependencies differ')
    tables,receipts = {},{}
    labels = [str(frequency)+'.0' for frequency in range(1800,2801)]
    for item in scope['inputs']:
        name = item['detector']
        require(name in EXPECTED and name not in tables, 'Detector identity differs')
        require((item['bytes'],item['git_blob_sha1'],item['sha256']) == EXPECTED[name], 'Input metadata differs')
        path = root/item['local_relative_path']
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'CSV path escapes scope')
        raw = path.read_bytes()
        blob = hashlib.sha1(('blob '+str(len(raw))+'\0').encode('ascii')+raw).hexdigest()
        require((len(raw),blob,sha(raw)) == EXPECTED[name], 'Original published source bytes differ')
        table,blank = helper.read_table(raw,labels,original['limits'])
        tables[name] = table
        pins[str(path)] = sha(raw)
        receipts[name] = dict(bytes=len(raw),sha256=sha(raw),git_blob_sha1=blob,
                              published_rows=len(table),empty_physical_records=blank)
    require(set(tables) == set(EXPECTED), 'Both detector tables required')
    matches = identities(tables['turboSETI'],tables['energy_detection'])
    bins = bins_from_pairs(tables['turboSETI'],tables['energy_detection'],matches,range(1800,2801))
    names = ('SUMMARY_PAIRING_BY_V2.json','OBSERVATION_IDS_PAIRING_BY_V2.json',
             'PER_BIN_PAIRING_BY_V2.json','PER_BIN_PAIRING_BY_V2.csv')
    saved = {name:(production/name).read_bytes() for name in names}
    pins.update({str(production/name):sha(raw) for name,raw in saved.items()})
    summary = read(production/'SUMMARY_PAIRING_BY_V2.json')
    require(summary['status'] == 'PASS_DECLARED_IDENTIFIER_PAIRING_V2', 'Production did not pass')
    require(summary['source_repository'] == scope['source_repository'] and
            summary['source_commit'] == scope['source_commit'], 'Summary source provenance differs')
    require(summary['scope_sha256'] == pins[str(scope_path)] and
            summary['production_sha256'] == sha((root/'pair_rfi_v2.py').read_bytes()), 'Summary bindings differ')
    require(read(production/'OBSERVATION_IDS_PAIRING_BY_V2.json') == matches, 'ID pairing/mapping/unmatched differ')
    require(read(production/'PER_BIN_PAIRING_BY_V2.json') ==
            {'schema':'SETI_BY_V2_PAIRED_HISTOGRAM_BINS','bins':bins}, 'Paired per-bin table differs')
    csv_rows = list(csv.DictReader(io.StringIO(saved['PER_BIN_PAIRING_BY_V2.csv'].decode('utf-8'),newline=''),strict=True))
    require(len(csv_rows) == len(bins), 'Paired CSV length differs')
    for actual,expected in zip(csv_rows,bins):
        require(actual == {key:'' if value is None else str(value) for key,value in expected.items()},
                'Paired CSV value differs')
    require(summary['inputs'] == receipts, 'Source table receipt differs')
    require(summary['paired_observations'] == matches['canonical_intersection_count'] and
            summary['raw_filename_intersection_count'] == matches['raw_intersection_count'], 'Join counts differ')
    require(summary['unmatched_observations'] == {name:len(matches[name+'_unmatched']) for name in tables},
            'Unmatched counts differ')
    require(summary['processing_suffix_counts'] == matches['turboSETI_processing_suffix_counts'], 'Suffix totals differ')
    require(summary['frequency_bins'] == 1001 and summary['frequency_label_range_mhz'] == [1800,2800] and
            summary['source_notch_label_bins_flagged'] == 61, 'Frequency summary differs')
    require(summary['fixed_neighborhood'] == [row for row in bins if 2298 <= row['lower_edge_mhz'] < 2302],
            'Fixed four-bin neighborhood differs')
    total_keys = ('turbo_nonzero_rows','energy_nonzero_rows','both_nonzero_rows',
                  'turbo_only_rows','energy_only_rows','neither_nonzero_rows',
                  'turbo_total_hit_count','energy_total_hit_count')
    require(summary['all_matched_bin_totals'] == {key:sum(row[key] for row in bins) for key in total_keys},
            'All-bin paired totals differ')
    require(summary['output_sha256'] == {name:sha(raw) for name,raw in saved.items()
                                         if name != 'SUMMARY_PAIRING_BY_V2.json'}, 'Output hash inventory differs')
    require(summary['after_original_data_exposure'] is True and
            summary['original_analysis_outputs_changed'] is False and
            summary['all_bound_bytes_unchanged'] is True and
            summary['new_raw_SETI_searches'] == summary['new_original_technical_MHz_visits'] ==
            summary['new_original_unique_archive_ids'] == 0, 'Scientific scope claims differ')
    require(summary['interpretation_limits'] == scope['interpretation_limits'], 'Interpretation limits differ')
    require(all(sha(Path(path).read_bytes()) == digest for path,digest in pins.items()), 'Bound bytes changed during review')
    result = dict(schema='SETI_BY_INDEPENDENT_IDENTIFIER_PAIRING_REVIEW_V2',
                  status='PASS_INDEPENDENT_IDENTIFIER_PAIRING_V2',scope_sha256=pins[str(scope_path)],
                  reviewer_sha256=sha(Path(__file__).read_bytes()),independent_csv_parser_sha256=helper_hash,
                  production_summary_sha256=sha(saved['SUMMARY_PAIRING_BY_V2.json']),
                  paired_observations=matches['canonical_intersection_count'],
                  unmatched_observations=summary['unmatched_observations'],
                  all_published_input_count_cells_checked=sum(len(table)*1001 for table in tables.values()),
                  all_paired_frequency_bins_checked=1001,fixed_neighborhood_bins_checked=4,
                  all_paired_medians_totals_and_occupancy_states_checked=True,
                  exact_matched_and_unmatched_identifiers_checked=True,
                  original_no_match_summary_unchanged=True,original_summary_sha256=pins[str(original_summary_path)],
                  all_bound_bytes_unchanged=True,new_raw_SETI_searches=0,
                  limits=['Independent Fraction count parser, regex identity construction, set occupancy and sorted order-statistic medians; no production functions imported.',
                          'CSV syntax parser and Python runtime arithmetic are shared primitives.',
                          'Operational stem matches after data exposure; not independent native-header or exposure validation.',
                          'Derived detector histograms only; no raw signal search, detector ranking, calibrated sensitivity or original survey coverage.'],
                  wall_seconds=time.monotonic()-start,completed_utc=datetime.now(timezone.utc).isoformat())
    require(out.is_absolute() and str(out).startswith('/dev/shm/'), 'Exclusive tmpfs audit outputs required')
    out.mkdir(parents=True,exist_ok=False)
    with (out/'REVIEW_PAIR_BY_V2.json').open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',required=True,type=Path)
    parser.add_argument('--production',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args()
    def expired(signum,frame):
        raise TimeoutError('BY V2 fixed 60-second independent pairing review budget')
    signal.signal(signal.SIGALRM,expired);signal.alarm(60)
    value = run(args.scope,args.production,args.out)
    signal.alarm(0)
    print(json.dumps({'status':value['status'],'paired_observations':value['paired_observations'],
                      'bins_checked':value['all_paired_frequency_bins_checked']}),flush=True)
