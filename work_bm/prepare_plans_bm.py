"""Build the finite remaining native170 BM scope from retained, pinned metadata only.

No telescope power decoding or new network request. Rebuilding/overwriting
existing plans is refused. Full native rows are decoded only by the frozen
search after publication of the plans and executable sources.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bm'
BATCHES = ([list(range(start,start+8)) for start in range(33,121,8)]
         + [list(range(121,128))]
         + [list(range(start,start+8)) for start in range(129,249,8)]
         + [list(range(249,255))])

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')

def main():
    if sys.flags.optimize != 0:
        raise ValueError('Plan assertions require unoptimized Python')
    allq = [q for qs in BATCHES for q in qs]
    assert len(BATCHES) == 28 and len(allq) == len(set(allq)) == 221
    assert allq == list(range(33,128)) + list(range(129,255))
    prior = read(ROOT / 'work_bl/results/CAMPAIGN_COMPLETE_BL.json')
    assert prior['status'] == 'ALL_FOUR_BATCHES_SEARCHED_AND_AUDITED'
    assert prior['q_list'] == list(range(1,33))
    source = ROOT / 'work_bl/source_manifest_v2.json'
    receipt = ROOT / 'work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json'
    original = read(receipt)
    assert sha(source) == original['source_manifest_sha256']
    retained = read(source)
    assert retained['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED'
    native = retained['by_native_chunk']['170']
    assert native['physical_channel_interval_half_open'] == [178257920, 179306496]
    compact = {f['scan_id']: f for f in original['files'] if f['native'] == 170}
    scans = []
    for i, s in enumerate(native['sources']):
        h = s['current_header']['data_attributes']
        record = compact[s['label']]
        path = ROOT / 'adjacent_raw/analysis/s2017_next_native/results/acquire' / Path(record['path']).name
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']
        fch1 = h['fch1'] + 178257920 * h['foff']
        assert fch1 == 2304.78515625 and h['tsamp'] == 18.253611008
        assert h['foff'] * 1e6 == -2.7939677238464355
        assert s['label'] == original['scan_order'][i]
        assert s['role'].upper() == ['ON', 'OFF'][i % 2]
        scans.append(dict(scan=i, label=s['label'], id=s.get('catalog_id', s['label']),
                          role=s['role'].upper(), path=str(path.resolve()),
                          input_sha256=record['sha256'], nrows=16, nchannels=1048576,
                          fch1_mhz=fch1, df_hz=h['foff'] * 1e6,
                          dt_seconds=h['tsamp'],
                          tref_midpoint_mjd=h['tstart'] + 7.5 * h['tsamp'] / 86400))
    paths = [WORK / 'bounded_search_bm.py', WORK / 'review/audit_real_results_bm.py',
             WORK / 'run_campaign_bm.py', Path(__file__).resolve(),
             ROOT / 'work_be/science_root/work_az/detector/kernel_v.py',
             ROOT / 'work_be/science_root/work_az/detector/continuous_normalization_ac.py']
    sources = {str(p.resolve()): sha(p) for p in paths}
    template = read(ROOT / 'work_bl/plans/batch01.json')
    template.update(schema='S2017_BM_LOCAL_Q_ESS_V1', native_channel_start=178257920,
                    dataset_manifest_path=str(source.resolve()), dataset_manifest_sha256=sha(source),
                    prior_completed_delivery_path=str((ROOT / 'work_bl/DELIVERY_BL.json').resolve()),
                    prior_completed_delivery_sha256=sha(ROOT / 'work_bl/DELIVERY_BL.json'),
                    prior_completed_campaign_path=str((ROOT / 'work_bl/results/CAMPAIGN_COMPLETE_BL.json').resolve()),
                    prior_completed_campaign_sha256=sha(ROOT / 'work_bl/results/CAMPAIGN_COMPLETE_BL.json'),
                    scans=scans, source_sha256=sources,
                    scope_continuation='Distinct remaining native170 descriptive scope: 28 fixed batches, q33..127 and q129..254, 221 carrier cores. Completed BL q1..32 and native171 are not replayed; native172 is outside this execution.',
                    historical_outcomes_preserved=original['historical_outcomes_preserved'],
                    prior_native170_historical_searches='Some bands were previously searched under a different full-native ESS family; this local-q family is descriptive reanalysis, not new data or independence.',
                    prepared_adjacent_receipt_path=str(receipt.resolve()),
                    prepared_adjacent_receipt_sha256=sha(receipt))
    template.pop('prior_failed_actual_path', None)
    template.pop('prior_failed_actual_sha256', None)
    for i, qs in enumerate(BATCHES, 1):
        plan = copy.deepcopy(template)
        plan.update(core_q_list=qs, expected_track_trials=len(qs) * 54125568,
                    expected_selected_scalar_sum_checks=len(qs) * 216,
                    expected_shared_kernel_calibration_vectors=len(qs) * 72)
        write(WORK / 'plans' / f'batch{i:02d}.json', plan)
    write(WORK / 'METADATA_PREFLIGHT_BM.json', dict(
        status='PASS_METADATA_AND_COMPACT_BYTES_NO_DECODE_NO_SCORES', native=170,
        q_list=allq, frozen_batch_count=28, expected_track_trials=11961750528,
        source_manifest_sha256=sha(source),
        prepared_receipt_sha256=sha(receipt), input_sha256={s['label']:s['input_sha256'] for s in scans},
        plan_sha256={f'batch{i:02d}':sha(WORK/'plans'/f'batch{i:02d}.json') for i in range(1,29)},
        new_archive_requests=0, new_observations=0))
    print('PASS: 28 remaining native170 metadata-pinned plans, 221 carrier cores; no decoded power values or scores')

if __name__ == '__main__':
    main()
