#!/usr/bin/env python3
"""Audit M43H fixture, HDF5 and live receipts with their distinct provenance."""
import argparse
import json
from pathlib import Path
import numpy as np
from m43h_fixture import fixture_values
from seti_repeater import source_m43h as src

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43h_widened_source'
INITIAL_FREEZE='4db1a35bce82117de47689c83713ad4b2d208c2e'
LIVE_FREEZE='bbc686467ff925390006b49d88fb569eff2fbd76'


def main(work_root):
    cfg,contract,metadata,preflight=src.frozen_inputs(ROOT)
    fixture=src.verify(json.loads((OUT/'fixture_qualification.json').read_text()),'result_sha256')
    integration=src.verify(json.loads((OUT/'hdf5_integration.json').read_text()),'result_sha256')
    live=src.verify(json.loads((OUT/'live_result.json').read_text()),'result_sha256')
    assert fixture['contract_sha256']==cfg['fixture_contract_sha256']
    assert live['contract_sha256']==contract
    assert live['hdf5_integration_result_sha256']==integration['result_sha256']==cfg['hdf5_integration_result_sha256']
    assert integration['status']=='local-hdf5-codec-integration-qualified'
    assert integration['runtime']==cfg['hdf5_runtime']
    for p,h in integration['implementation_sha256'].items():assert src.file_hash(ROOT/p)==h
    expected={(x['scan'],x['window']) for x in cfg['anchors']}
    assert len(fixture['fixtures'])==2 and {(x['scan'],x['window']) for x in fixture['fixtures']}==expected
    fixture_rows=0;live_rows=0
    for f in fixture['fixtures']:
        assert f['kind']=='local-fixture' and f['rows']==16 and f['native_channels']==1_132_270
        assert f['interrupted_after_rows']==5 and f['completed_restart_reused_rows']==16
        assert f['sorted_reference_rows_exact']==16 and f['hdf5_decode_exercised'] is False
        receipt=src.verify(json.loads((ROOT/f['receipt_path']).read_text()))
        assert receipt['receipt_sha256']==f['source_receipt_sha256']
        directory=work_root/'fixtures'/f['scan']/f['window']
        assert src.rehydrate(directory,f['source_receipt_sha256'],required_kind='local-fixture')==receipt
        start,stop=receipt['scope']['archive_interval']
        for row in range(16):
            actual=np.load(directory/f'row{row:02d}.native.npy',allow_pickle=False,mmap_mode='r')
            np.testing.assert_array_equal(actual,fixture_values(row,start,stop));fixture_rows+=1
    assert len(integration['checks'])==2
    assert {r['codec'] for r in integration['checks']}=={'gzip','bitshuffle_lz4'}
    for r in integration['checks']:
        assert r['hdf5_rows']==3 and r['actual_hdf5_decode'] is True and r['http_is_local_fixture'] is True
        assert r['native_and_sorted_normalization_exact'] and r['wrong_header_rejected']
        assert r['completed_restart_new_http_requests']==0
    assert len(live['anchors'])==2 and {(a['scan'],a['window']) for a in live['anchors']}==expected
    success=0
    for a in live['anchors']:
        if a['status']=='telescope-source-attested':
            success+=1;assert a['telescope_rows']==a['sorted_reference_rows_exact']==16
            receipt=src.verify(json.loads((ROOT/a['receipt_path']).read_text()))
            assert receipt['receipt_sha256']==a['source_receipt_sha256']
            assert receipt['scope']['kind']=='telescope-remote'
            assert receipt['scope']['archive_interval']==[163032021,164164291]
            assert receipt['scope']['contract_sha256']==contract
            src.verify_transport_checkpoint(receipt['transport']['checkpoint'],receipt['transport']['identity'])
            plan_path=OUT/(a['scan']+'_'+a['window']+'.range-plan.json')
            plan=json.loads(plan_path.read_text())
            # Publish the exact inherited transport encoding, whose file SHA
            # is bound by the source receipt (the M43H JSON writer adds a newline).
            raw_plan=src.old_transport._canonical_json_bytes(plan)
            assert src.old_transport._sha256_bytes(raw_plan)==receipt['transport']['range_plan_file_sha256']
            src.old_transport._write_atomic(plan_path,raw_plan)
            directory=work_root/'live'/a['scan']/a['window']
            assert src.rehydrate(directory,a['source_receipt_sha256'])==receipt
            live_rows+=16
    assert live['attested_telescope_products']==success and live['attested_telescope_rows']==live_rows
    assert live['status']==('live-source-gate-passed' if success==2 else 'live-source-gate-incomplete')
    for k,v in live['transport_counters'].items():assert v==sum(a['transport_counters'][k] for a in live['anchors'])
    assert live['score_calculation_performed'] is False and live['recovery_measured'] is False and live['threshold_calibrated'] is False
    audit={'fixture_result_sha256':fixture['result_sha256'],'integration_result_sha256':integration['result_sha256'],
        'live_result_sha256':live['result_sha256'],'frozen_files_checked':len(cfg['pinned_sha256']),
        'fixture_rows_regenerated':fixture_rows,'actual_local_hdf5_rows_qualified':6,
        'telescope_sources_rehydrated':success,'telescope_rows_rehydrated':live_rows,'inventory_exact':True}
    src.atomic_json(OUT/'verification.json',audit)
    title='two widened telescope sources verified' if success==2 else 'local source chain qualified; live source gate incomplete'
    lead='**Both frozen ON/OFF telescope anchors pass the widened-source gate.**' if success==2 else '**The local source and HDF5 checks pass; the live telescope gate is incomplete.**'
    lines=['# M43H: '+title,'',lead,'',
        'M43H adds a separately named widened-source factory, row receipts and bounded HTTP range transport. It preserves exact native hyperslabs, normalizes from the new ascending extraction origin, and verifies row bytes and normalization before restart or rehydration. The old M37 source contract and M43G synthetic adapter remain unchanged.','',
        '## Results by stage','',
        '| Stage | Exact scope | Result |','|---|---|---|',
        '| Development tests | 55 M43-family tests, including 11 source/transport tests | Passed |',
        '| Full-size local dataset facade | 2 sources, each 16 x 1,132,270 float32 values | Passed |',
        '| Interrupted source extraction | Stop after 5 rows, resume only the remaining 11 per source | Passed |',
        '| Fixture normalization | 32 full rows against independent sorted median/MAD | Exact |',
        '| Completed fixture restart | 16 reused rows per source; zero new dataset reads | Identical receipts |',
        '| Actual local HDF5 integration | gzip and Bitshuffle/LZ4; 3 rows each through bounded sparse interface | Passed |',
        '| HDF5 restart and fault checks | Interrupt after row 1, resume, reject changed header, completed restart without new HTTP requests | Passed |',
        f'| Live telescope sources | epoch1_on and epoch1_off at 1412.5 MHz | {success}/2 attested; {live_rows}/32 rows verified |','',
        'All stages keep their own provenance. The full-size dataset facade has the real metadata/dimensions but locally generated values and does not decode HDF5. The codec fixtures decode real local HDF5 files with simulated HTTP responses. Neither fixture category counts as telescope data. No broader repository test run is claimed.','',
        '## Live anchor outcomes','',
        '| Scan | Source gate | HEAD attempted/completed | Range attempted/completed | Accepted range bytes |',
        '|---|---|---:|---:|---:|']
    for a in live['anchors']:
        c=a['transport_counters']
        lines.append(f"| {a['scan']} | {a['status']} | {c['head_attempts']}/{c['head_completed']} | {c['range_attempts']}/{c['range_completed']} | {c['accepted_range_bytes']:,} |")
    for a in live['anchors']:
        if a['status']!='telescope-source-attested':
            lines+=['',f"`{a['scan']}`: `{a['error_type']}` — {a['reason']}. Committed partial-row receipts: {a['committed_partial_row_receipts']}."]
    lines+=['',
        'The fixed archive interval is [163032021, 164164291), start-inclusive and stop-exclusive. The prospective factory owns live URL/size/ETag, header, chunk-geometry and exact `data[row, 0, start:stop]` checks. A successful source binds the qualified runtime, observed dataset filters, range plan and hashed transport checkpoint to native and normalized row receipts. Every completed live source is also compared against the independent sorted normalization reference and rehydrated in the result audit. Accepted HTTP byte counts include prefetched compressed/metadata regions; they are not the number of decoded science-array bytes.','',
        '## Integrity, normalization and resource scope','',
        'Each native descending row and its internally derived normalized ascending row is written atomically as .npy, flushed and fsynced. Its receipt is published last. Restart checks file and payload hashes, dtype, shape, row order and normalization before reuse. No incomplete row inventory is a complete source. Rehydration requires an independently retained source-receipt SHA and the expected source kind; local fixtures cannot satisfy telescope-kind rehydration. Checksums do not provide a cryptographic guarantee against a malicious server or runtime.','',
        'Normalization uses the M43G-qualified float32 median/MAD arithmetic in 4096-channel blocks from the new extraction zero, including the terminal block. No old normalized-source or threshold receipt is reused. A verified mirror may grow for another window without changing an earlier complete source identity when its original segments and exact row inventory survive.','',
        f'The declared buffer model is {src.resource_bound(1_132_270)/1024**2:.2f} MiB per selected source, under a 256 MiB cap. HTTP requests are at most 8 MiB; file-object reads at most 32 MiB; configured HDF5 chunk cache 8 MiB; accepted decoded chunks at most 16 MiB. HTTP identity/range checks precede a body read bounded to requested length plus one byte. This is static buffer accounting and exercised integration behavior, not a measured full-process RSS ceiling or a bound on all HDF5/compression/OS internals.','',
        '## Environment change and public freezes','',
        'The installation tool initially reported that network approval was cancelled. Both required packages subsequently became available. The first full-size fixture run correctly left live access blocked because HDF5 integration had not yet been qualified; that historical result and configuration remain published. The local HDF5/codec checks were then completed, and their receipt and the live amendment were public before the telescope attempts. The earlier dependency limitation is historical, not a current missing-package claim.','',
        f'Qualified runtime: NumPy {integration["runtime"]["numpy"]}, h5py {integration["runtime"]["h5py"]}, HDF5 {integration["runtime"]["hdf5"]}, hdf5plugin {integration["runtime"]["hdf5plugin"]}. Initial fixture freeze: `{INITIAL_FREEZE}`. Live amendment freeze: `{LIVE_FREEZE}`. Both were fetched and verified before their respective evaluations.','',
        '## Next gate and scientific limits','']
    if success==2:
        lines+=['The two selected sources are ready for the next separately qualified physical cache/score path. Next compare selected full-grid real-data score anchors with direct native-window calculations for the fixed bank, preserving ON/OFF controls and repeated-channel correlations. Renew null/threshold calibration before interpreting new-bank detections.']
    else:
        lines+=['Resolve the documented live-source failure while retaining the same predetermined anchors and existing checkpoints. Any source/transport contract change needs an explicit amendment and relevant tests before retry. Only completed, independently verified telescope source receipts can feed the next physical cache/score anchors.']
    lines+=['','No spectral filter, signal-track score, injection recovery rate, candidate ranking or new threshold is produced by M43H. Source verification is a prerequisite to those calculations. All earlier scientific results retain their original scope and denominators.','',
        '## Reproduction and audit','',
        f'Live result identity: `{live["result_sha256"]}`. Fixture identity: `{fixture["result_sha256"]}`. HDF5 integration identity: `{integration["result_sha256"]}`. The manifest pins the plans, implementation, tests and derived receipts. Intermediate row arrays are reproducible working inputs and are not published as user-facing datasets.','',
        'The audit rechecks frozen inputs, exact stage inventories and transport counters, regenerates every full-size fixture raw row, and rehydrates all completed source receipts. Published range plans use the inherited transport encoding so their file SHA matches the source receipt. The audit does not repeat remote downloads or claim independent telescope observations. To reproduce the historical facade stage, use its original public freeze; the current configuration advances to live sources.','',
        '```bash',
        "PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_m43*.py' -q",
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_hdf5_integration.py',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_live_sources.py --work-root /absolute/working-directory',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43h_result_report.py --work-root /absolute/working-directory','```','']
    (ROOT/'MILESTONE_43H_WIDENED_SOURCE_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);main(p.parse_args().work_root)
