"""Build the finite native170 BL scope from retained, pinned metadata only.

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
WORK = ROOT / 'work_bl'

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
    source = WORK / 'source_manifest_v2.json'
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
    paths = [WORK / 'bounded_search_bl.py', WORK / 'review/audit_real_results_bl.py',
             WORK / 'run_campaign_bl.py', Path(__file__).resolve(),
             ROOT / 'work_be/science_root/work_az/detector/kernel_v.py',
             ROOT / 'work_be/science_root/work_az/detector/continuous_normalization_ac.py']
    sources = {str(p.resolve()): sha(p) for p in paths}
    template = read(ROOT / 'work_bk/plans/batch01.json')
    template.update(schema='S2017_BL_LOCAL_Q_ESS_V1', native_channel_start=178257920,
                    dataset_manifest_path=str(source.resolve()), dataset_manifest_sha256=sha(source),
                    prior_completed_delivery_path=str((ROOT / 'work_bk/DELIVERY_BK.json').resolve()),
                    prior_completed_delivery_sha256=sha(ROOT / 'work_bk/DELIVERY_BK.json'),
                    scans=scans, source_sha256=sources,
                    scope_continuation='Distinct native170 descriptive scope: four fixed eight-core batches q1..32. Native171 completed family is not replayed; native172 is outside this execution.',
                    historical_outcomes_preserved=original['historical_outcomes_preserved'],
                    prior_native170_historical_searches='Some bands were previously searched under a different full-native ESS family; this local-q family is descriptive reanalysis, not new data or independence.',
                    prepared_adjacent_receipt_path=str(receipt.resolve()),
                    prepared_adjacent_receipt_sha256=sha(receipt))
    template.pop('prior_failed_actual_path', None)
    template.pop('prior_failed_actual_sha256', None)
    for i, start in enumerate(range(1, 33, 8), 1):
        plan = copy.deepcopy(template)
        plan.update(core_q_list=list(range(start, start + 8)), expected_track_trials=8 * 54125568,
                    expected_selected_scalar_sum_checks=8 * 216,
                    expected_shared_kernel_calibration_vectors=8 * 72)
        write(WORK / 'plans' / f'batch{i:02d}.json', plan)
    write(WORK / 'METADATA_PREFLIGHT_BL.json', dict(
        status='PASS_METADATA_AND_COMPACT_BYTES_NO_DECODE_NO_SCORES', native=170,
        q_list=list(range(1,33)), source_manifest_sha256=sha(source),
        prepared_receipt_sha256=sha(receipt), input_sha256={s['label']:s['input_sha256'] for s in scans},
        plan_sha256={f'batch{i:02d}':sha(WORK/'plans'/f'batch{i:02d}.json') for i in range(1,5)},
        new_archive_requests=0, new_observations=0))
    print('PASS: four native170 metadata-pinned plans; no decoded power values or scores')

if __name__ == '__main__':
    main()
