"""Read saved metadata only; write a bounded continuation inventory in this directory."""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / 'work_harps_20261101'
EXT = BASE / 'v2/extension02'
TARGETS = ('HD122640', 'HD135204')
SOURCES = {}

def source(path):
    raw = path.read_bytes()
    SOURCES[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return raw.decode()

def js(path):
    return json.loads(source(path))

def cs(path):
    return list(csv.DictReader(source(path).splitlines()))

def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def table(name, rows):
    with (HERE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

manifests = [
    ('initial100', BASE / 'acquisition/DOWNLOAD_MANIFEST.json', 'main_unopened'),
    ('v2_first100', BASE / 'v2/acquisition/DOWNLOAD_MANIFEST.json', 'v2_main_unopened'),
    ('extension02', EXT / 'acquisition/DOWNLOAD_MANIFEST.json', 'extension02_unopened'),
]
inventory = []
main_ids = set()
for cohort, path, role in manifests:
    main = [r for r in js(path) if r['role'] == role]
    assert len(main) == 100
    for r in main:
        assert r['dp_id'] not in main_ids
        main_ids.add(r['dp_id'])
        if r['canonical_target'] not in TARGETS:
            continue
        h = r['primary_header']
        assert r['download_status'] == 'DOWNLOADED' and r['header_status'] == 'PASS_METADATA_ONLY'
        relative = r.get('relative_path') or r['path'].split('work_harps_20261101/', 1)[1]
        inventory.append(dict(target=r['canonical_target'], cohort=cohort, dp_id=r['dp_id'],
                              observation_utc=h['DATE-OBS'], mjd=h['MJD-OBS'],
                              berv_km_s=h['HIERARCH ESO DRS BERV'], nominal_resolving_power=h['SPEC_RES'],
                              source_manifest=str(path.relative_to(ROOT)),
                              canonical_product_path='work_harps_20261101/' + relative,
                              product_bytes=r['bytes'], recorded_product_sha256=r['sha256'],
                              raw_progenitor_id=r['raw_progenitor_ids'][0],
                              binary_rehashed_in_this_task=False))
inventory.sort(key=lambda r: (r['target'], r['observation_utc'], r['dp_id']))
table('EXISTING_TARGET_EXPOSURES.csv', inventory)
queue = cs(EXT / 'unresolved_context_20261102/ACTION_QUEUE.csv')
context = {r['candidate_id']: r for r in cs(EXT / 'unresolved_context_20261102/EVENT_CONTEXT.csv')}
selected = [r for r in queue if r['primary_evidence_route'] == 'FRAME_BASELINE_CONTEXT']
assert len(selected) == 10
for r in selected:
    assert r['current_code_unchanged'] == 'U'
    c = context[r['candidate_id']]
    for k in ('center_bary_air_angstrom', 'source_input_sha256', 'berv_span_km_s', 'berv_span_resolution_elements'):
        r[k] = c[k]
table('FRAME_BASELINE_QUEUE.csv', selected)

current = cs(BASE / 'v2/CURRENT_V2_DISPOSITIONS.csv')
counts = dict(Counter(r['current_code'] for r in current))
assert counts == {'U': 185, 'O': 46, 'A': 403, 'M': 35}
assert {r['review_id']: r['current_code'] for r in current}.items() >= {r['candidate_id']: 'U' for r in selected}.items()
expanded = cs(BASE / 'expansion/EXTRA_ELIGIBLE_METADATA.csv')
extra = [r for r in expanded if r['canonical_target'] in TARGETS]
unused = [r for r in extra if r['dp_id'] not in main_ids]
assert len(extra) == 19 and not unused
source(BASE / 'v2/next_sample/TARGET_INVENTORY.csv')
source(BASE / 'v2/next_sample/CURRENT_OBSCORE.csv')
source(EXT / 'epoch_followup/PLAN.json')
source(EXT / 'epoch_followup/EVENT_SUMMARY.csv')
normalization = js(EXT / 'normalization_context_20261102/SUMMARY.json')
mapping = js(EXT / 'mapping_followup_remaining_20261102/SUMMARY.json')
source(ROOT / 'work_rubin_20261102/next_data_route/README.md')
source(BASE / 'README.md'); source(BASE / 'v2/README.md')
source(EXT / 'checkpoints/INPUT_CHECKPOINTS.json')
source(EXT / 'checkpoints/LIBRARY_INPUTS.json')

resolution = 299792.458 / 115000
coverage = []
for t in TARGETS:
    for label in ('extension02_only', 'earlier200_only', 'all_existing300'):
        rows = [r for r in inventory if r['target'] == t and
                (label == 'all_existing300' or (r['cohort'] == 'extension02') == (label == 'extension02_only'))]
        lo, hi = min(r['berv_km_s'] for r in rows), max(r['berv_km_s'] for r in rows)
        coverage.append(dict(target=t, scope=label, exposures=len(rows),
                             observation_first_utc=min(r['observation_utc'] for r in rows),
                             observation_last_utc=max(r['observation_utc'] for r in rows),
                             berv_min_km_s=lo, berv_max_km_s=hi, berv_span_km_s=hi-lo,
                             nominal_resolution_km_s=resolution,
                             span_resolution_elements=(hi-lo)/resolution,
                             below_one_resolution_element=hi-lo < resolution))
table('BERV_COVERAGE.csv', coverage)
for t in TARGETS:
    c = next(r for r in coverage if r['target'] == t and r['scope'] == 'extension02_only')
    for r in selected:
        if r['target'] == t:
            assert abs(float(r['berv_span_km_s']) - c['berv_span_km_s']) < 1e-12

handoff = {
    'schema': 'HARPS_METADATA_ONLY_NEXT_FOLLOWUP_V1',
    'status': 'READY_FOR_BOUNDED_BROADER_DATE_METADATA_PREFLIGHT_NO_NEW_SCIENCE',
    'scope': {'metadata_only': True, 'science_arrays_read': 0, 'network_requests': 0,
              'new_acquisitions': 0, 'original_labels_changed': 0},
    'first_route': 'FRAME_BASELINE_CONTEXT',
    'first_event': 'V2E2-0229', 'first_target': 'HD122640',
    'queue_ids_by_target': {t: [r['candidate_id'] for r in selected if r['target'] == t] for t in TARGETS},
    'candidate_id_namespace_warning': 'V2E2-0231 is an unresolved extension02 event; V2-0231 is an older mapping event. Do not conflate them.',
    'coverage': coverage,
    'existing_catalog_inventory': {'eligible_rows_for_two_targets': len(extra), 'unused_after_existing300': 0,
                                   'coverage_claim': 'Only the saved eligible inventory is exhausted, not the ESO archive.'},
    'next_action': {
        'kind': 'PROSPECTIVE_METADATA_PREFLIGHT_ONLY',
        'targets_in_order': list(TARGETS),
        'purpose': 'Find public same-target HARPS single-exposure metadata outside the existing 2023-02-19 to 2023-03-01 observation interval, to assess whether wider BERV separation is available.',
        'bounds_to_freeze_before_execution': {'target_queries_max': 2, 'attempts_per_query_max': 1,
                                             'rows_per_target_max': 1000, 'response_bytes_per_query_max': 4*1024*1024,
                                             'timeout_seconds_per_query': 30, 'redirects': 0, 'science_payload_downloads': 0},
        'before_request': 'Verify the official metadata contract, then freeze exact ADQL/parameters, target coordinates/aliases, public-access checks, exclusion of all300 DP/raw IDs, output paths, caps and failure handling. This handoff does not execute that plan.',
        'selection_rule': 'Metadata inventory only: same verified target, HARPS, public single-exposure science product, valid time/coordinate provenance. Do not rank on spectral values. Preserve all returned exclusions and truncation flags.',
        'berv_gate': 'Observation date alone does not establish BERV. Verify recorded per-exposure BERV through a documented metadata/header route under a separate bounded plan before selecting science payloads. Aim to exceed the existing sub-resolution span; one nominal resolution element is a descriptive planning benchmark, not a classification or statistical-power threshold.',
        'stop': 'If both queries yield no suitable new epochs, lack public metadata, exceed caps or fail, record the precise limitation and stop this route without retrying or opening spectra. Any new header/payload acquisition requires its own frozen scope.',
        'later_science': 'Only after useful verified BERV coverage: freeze an event-specific same-target comparison using the10 listed events and exact newly selected epochs; inherit existing frame/normalization conventions, retain stellar-RV, wavelength-calibration and photon-origin uncertainty. No new classifier or label update implied.'
    },
    'do_not_repeat': {
        'mapping': {'status': mapping['status'], 'records': mapping['total_mapping_limited_records'], 'exposures': mapping['total_unique_exposures'], 'source': 'work_harps_20261101/v2/extension02/mapping_followup_remaining_20261102/SUMMARY.json'},
        'normalization': {'status': normalization['status'], 'events': ['V2E2-0092', 'V2E2-0104'], 'source': 'work_harps_20261101/v2/extension02/normalization_context_20261102/SUMMARY.json', 'finding': 'All4 low profiles are a later reference epoch, neither discovery is low; positive scalar normalization alone cannot increase Pearson correlation.'},
        'epoch_pipeline': 'Original extension02 all336 comparison is complete:2185 pairs/4370 profiles. Do not rerun to recreate this metadata inventory.',
        'Rubin': {'source': 'work_rubin_20261102/next_data_route/README.md', 'status': 'STOPPED_AFTER_ONE_EMPTY_SEPTEMBER_REQUEST_AND_ONE_ACCOUNT_GATED_ALTERNATIVE', 'main_stars_used': 190, 'main_ceiling': 500, 'remaining_ceiling': 310, 'source_evaluable': 2, 'forced_evaluable_separate': 4, 'minimum50_met': False, 'new_requests_authorized_by_this_handoff': 0}
    },
    'preserved_current_counts': counts,
    'input_manifest_paths': [str(p.relative_to(ROOT)) for _,p,_ in manifests],
    'saved_input_archives': [
        {'cohort': 'initial100', 'name': 'SETI_HARPS_INPUT_CHECKPOINT_2026-11-01.zip', 'bytes': 226849385, 'sha256': 'a9562b266fac4a481777162d85311d41ca6a6effd10ac74f8bd5d3a50346cfc7', 'library_file_id': 'libfile_728e045275c08191b7a390bf2fc08db1', 'source': 'work_harps_20261101/README.md'},
        {'cohort': 'v2_first100', 'name': 'SETI_HARPS_V2_INPUTS_2026-11-01.zip', 'bytes': 395957057, 'sha256': '8afd05a57d9c5e82488a9660704c0a77588f53b7e93434666dabe368a7c1662f', 'library_file_id': 'libfile_be85ea6d8e9c81918350b1141689f52e', 'source': 'work_harps_20261101/v2/README.md'},
        {'cohort': 'extension02', 'exact_parts_and_members': 'work_harps_20261101/v2/extension02/checkpoints/INPUT_CHECKPOINTS.json', 'saved_receipts': 'work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json'}
    ],
    'restore_note': 'No binary inputs are needed for this metadata-only task. Future restore uses staging and exact member hashes in EXISTING_TARGET_EXPOSURES.csv; old absolute scratch paths must not be reused. Product hashes here are archived manifest claims, not freshly rehashed arrays.',
    'source_hash_manifest': 'SOURCE_HASHES.json',
}
save('HANDOFF.json', handoff)
source(Path(__file__))
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == x['sha256'] for p,x in SOURCES.items())
save('SOURCE_HASHES.json', SOURCES)
save('PRESERVATION_CHECK.json', {'status': 'PASS', 'source_files_unchanged': len(SOURCES), 'all669_counts': counts, 'all185_U_preserved': True, 'all35_M_preserved': True, 'science_arrays_read': 0, 'network_requests': 0})
print(json.dumps({'status': 'PASS', 'source_files': len(SOURCES), 'event_records': len(selected), 'target_exposures': len(inventory), 'coverage': coverage}, indent=2))
