#!/usr/bin/env python3
"""Prepare the local prospective freeze. Refuses any started acquisition/run."""
from pathlib import Path
import csv
import importlib.metadata
import json
import sys

sys.dont_write_bytecode = True
from common import BASE, HERE, ROLE, csvrows, dump, now, require, sha


def main():
    require(not (HERE / 'acquisition').exists() and not (HERE / 'data').exists() and not (HERE / 'production').exists(),
            'Cannot freeze or refreeze after acquisition/analysis begins')
    source = BASE / 'v2/next_sample'
    verification = json.loads((source / 'METADATA_VERIFICATION.json').read_text())
    proposal = json.loads((source / 'PROPOSAL.json').read_text())
    require(verification['main100_sha256'] == sha(source / 'MAIN100.csv'), 'Verified proposal hash mismatch')
    for name, digest in verification['source_hashes'].items():
        require(sha(source / name) == digest, 'Proposal verification input changed: ' + name)
    for name, digest in proposal['input_hashes'].items():
        require(sha(BASE / name) == digest, 'Proposal original input changed: ' + name)
    for name, digest in proposal['output_hashes'].items():
        require(sha(source / name) == digest, 'Proposal output changed: ' + name)
    rows = csvrows(source / 'MAIN100.csv')
    for i, row in enumerate(rows, 1):
        row.update(role=ROLE, proposal_status='FROZEN_BEFORE_EXTENSION02_ACQUISITION', selection_index=i)
    with (HERE / 'MAIN100.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    paths = ['selection/MAIN100.csv', 'selection/DEVELOPMENT_AND_VALIDATION.csv',
             'v2/selection/MAIN100.csv', 'v2/selection/VALIDATION4.csv']
    old = [row for name in paths for row in csvrows(BASE / name)]
    require(len(old) == len({r['dp_id'] for r in old}) == 209, 'Wrong previous input count')
    keys = sorted((r['canonical_target'], float(r['t_min'])) for r in old)
    require(len(set(keys)) == 209, 'Duplicate prior target/time')
    require({r['dp_id'] for r in old} == set(proposal['previous_adp_ids']), 'Proposal prior IDs changed')
    dump(HERE / 'PRIOR209.json', dict(created_utc=now(), previous_main_exposures=200, previous_development_validation_exposures=9,
                                    adp_ids=proposal['previous_adp_ids'], raw_ids=proposal['previous_raw_ids'], target_start_keys=keys,
                                    original_selection_sha256={name: sha(BASE / name) for name in paths},
                                    raw_id_sources=['acquisition/DOWNLOAD_MANIFEST.json', 'v2/acquisition/DOWNLOAD_MANIFEST.json']))
    protocol = dict(role=ROLE, selected_exposures=100, selected_targets=16, previous_inputs_excluded=209,
                    estimated_science_payload_bytes=538889216, total_payload_byte_cap=700000000, per_file_byte_cap=10000000,
                    workers=3, maximum_attempts_per_file=2, attempt_timeouts_seconds=[20, 60], maximum_start_wall_seconds=900,
                    accounting='Response-body bytes; retry payload included. Read errors conservatively charge the reserved byte count. HTTP/TLS overhead is not measured.',
                    ancillary_or_raw_download=False, replacement_or_scope_expansion=False, implicit_resume=False,
                    header_policy='FITS hash and target/time/coordinates/units/frame/BERV/proposal/OBID/ADP/raw-ID checks before any spectral analysis.',
                    failed_input_policy='Keep original selection; report failed or excluded inputs explicitly. Analyze only metadata-pass files, never substitute observations.',
                    analysis='Original frozen V1 and V2 code/configurations, unchanged.',
                    stable_id_rule='V2E2-0001 onwards (V1E2-0001 for V1) in frozen exposure order and unchanged detector event order.',
                    output_directory='v2/extension02/production', merge_into_original_catalog=False,
                    publication_gate='Root publishes and verifies FREEZE.json plus every new hashed input/code file before supplying commit and matching FREEZE SHA256 to acquire.py.',
                    selection_rule=proposal['selection_rule'], quality_cuts=proposal['quality_cuts'],
                    prior_search_limit=verification['overlap_limit'], metadata_scope_limit=proposal['limitations'][0],
                    science_arrays_opened_at_freeze=0, new_science_files_downloaded_at_freeze=0)
    dump(HERE / 'PROTOCOL.json', protocol)
    names = set(proposal['input_hashes'])
    names.update(str(p.relative_to(BASE)) for p in source.iterdir() if p.is_file() and p.suffix in ('.json', '.csv', '.py'))
    names.update(['acquisition/download_selected.py', 'v2/acquisition/download_selected.py',
                  'acquisition/TARGET_COORDINATE_HEADERS.json', 'code/DETECTOR_FREEZE.json', 'v2/code/FREEZE.json',
                  'v2/validation/results/SUMMARY.json', 'v2/production/V2_HITS.csv', 'v2/production/V2_DISPOSITIONS.csv',
                  'v2/production/V1_HITS.csv', 'v2/production/SUMMARY.json'])
    v2freeze = json.loads((BASE / 'v2/code/FREEZE.json').read_text())
    for name, digest in v2freeze['source_hashes'].items():
        require(sha(BASE / name) == digest, 'Original V1/V2 source hash mismatch: ' + name)
        names.add(name)
    for name in ['common.py', 'acquire.py', 'run_main.py', 'freeze_scope.py', 'verify_guards.py',
                 'MAIN100.csv', 'PRIOR209.json', 'PROTOCOL.json', 'README.md']:
        names.add('v2/extension02/' + name)
    freeze = dict(status='FROZEN_BEFORE_EXTENSION02_ACQUISITION', frozen_utc=now(),
                  role=ROLE, source_hashes={name: sha(BASE / name) for name in sorted(names)},
                  numerical_versions={name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'astropy')},
                  original_v2_detector_freeze=v2freeze, selected_exposures=100, selected_targets=16,
                  prior_main=200, prior_development_validation=9, prior_unique_inputs=209,
                  prior_exclusions=dict(ADP=209, raw=209, target_start=209),
                  snapshot_exclusion_counts=proposal['first_failing_cut_counts'], eligible_unused_before_selection=404,
                  raw_provenance_verification=verification['status'], new_raw_ID_matches_to_prior_or_pinned_references=0,
                  verified_metadata_sha256=verification['main100_sha256'], science_files_downloaded=0, science_arrays_opened=0,
                  publication_status='LOCAL_FREEZE_READY_FOR_PROSPECTIVE_COMMIT; acquisition requires independently verified remote commit.',
                  scope_limitations=proposal['limitations'])
    dump(HERE / 'FREEZE.json', freeze)
    print(json.dumps(dict(status='LOCAL_FREEZE_READY', selection_sha256=sha(HERE / 'MAIN100.csv'),
                          freeze_sha256=sha(HERE / 'FREEZE.json'), hashed_sources=len(names))))


if __name__ == '__main__':
    main()
