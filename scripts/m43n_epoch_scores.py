#!/usr/bin/env python3
"""M43N: exhaustive native and integrated checks on the four M43M sources."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43j_exhaustive_anchors import batches
from m43k_native_filters import bank_coverage
from m43l_reference import build_reference
from m43l_wider_integrated import FileAbort, qualify_batch, validate_batches
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43n_epoch_scores'
CONFIG = ROOT / 'config/m43n_epoch_scores.json'


def native_gate(cache, reference):
    h = cache.width // 2
    n = cache.source.geometry.channel_count
    if reference.width != cache.width or reference.geometry != cache.source.geometry:
        raise ValueError('native reference scope differs')
    rows = []
    for i, actual in enumerate(cache.values):
        expected = reference.values[i, h:n-h]
        if actual.dtype != expected.dtype or not np.array_equal(actual, expected):
            raise ValueError('native reference values differ')
        digest = transfer.array_hash(actual)
        if digest != reference.row_sha256[i]:
            raise ValueError('native reference row digest differs')
        rows.append({'row': i, 'values_compared': len(actual), 'sha256': digest, 'exact': True})
    if cache.payload_sha256 != reference.filtered_payload_sha256:
        raise ValueError('native reference payload differs')
    return rows


def inventory(checks, cfg):
    expected = [(a['scan'], w) for a in cfg['anchors'] for w in cfg['widths']]
    if [(r['scan'], r['width']) for r in checks] != expected:
        raise ValueError('incomplete, duplicate or reordered source/width inventory')
    return {'sources': len(cfg['anchors']), 'widths': cfg['widths'],
        'source_width_checks': len(checks), 'complete_template_vectors': len(checks)*cfg['template_count'],
        'batches_completed': sum(r['batch_count'] for r in checks),
        'native_values_compared': sum(r['native_values_compared'] for r in checks),
        'integrated_score_cells_compared': sum(r['cells_compared'] for r in checks)}


def frozen(freeze):
    cfg = json.loads(CONFIG.read_text())
    for name, expected in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen input changed: '+name)
    if subprocess.check_output(['git', 'show', freeze+':config/m43n_epoch_scores.json'], cwd=ROOT) != CONFIG.read_bytes():
        raise ValueError('config differs from public freeze')
    if np.__version__ != cfg['numpy_version']:
        raise ValueError('NumPy differs')
    parent = read_sealed(ROOT/'results_m43m_epoch_sources/qualification.json')
    if parent['result_sha256'] != cfg['m43m_result_sha256']:
        raise ValueError('M43M source inventory changed')
    if [(x['scan'],x['source_receipt_sha256']) for x in parent['new_sources']] != [(a['scan'],a['source_receipt_sha256']) for a in cfg['anchors']]:
        raise ValueError('M43M source anchors differ')
    return cfg, hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def one(label, width, work_root, freeze, abort):
    try:
        cfg, contract = frozen(freeze)
        anchor = next(a for a in cfg['anchors'] if a['scan'] == label)
        if width not in cfg['widths']: raise ValueError('unfrozen width')
        if abort.is_set(): raise RuntimeError('peer failure; stopped before source load')
        _,_,_,_,basis,bank,table,_ = build_context()
        if table.template_bank_sha256 != cfg['bank_sha256'] or table.factor_table_sha256 != cfg['factor_table_sha256']:
            raise ValueError('bank/factor identity differs')
        matrix = core.factor_table_for_scan(table,basis,label)
        if len(matrix) != cfg['template_count'] or core.factor_table_sha256(matrix) != anchor['scan_factor_sha256']:
            raise ValueError('scan factors differ')
        grid = core.make_m37_proxy_carrier_grid(cfg['window'])
        if core.proxy_carrier_grid_sha256(grid) != cfg['grid_sha256']: raise ValueError('grid differs')
        source = transfer.load_telescope_source(work_root/label/cfg['window'], trusted_receipt_sha256=anchor['source_receipt_sha256'])
        cache = transfer.build_telescope_cache(source,matrix,grid,width,bank_sha256=cfg['bank_sha256'])
        reference = build_reference(source.values,source.geometry,width,chunk_centers=cfg['native_reference_chunk'])
        native_rows = native_gate(cache,reference)
        coverage = bank_coverage(source.geometry,matrix,grid,width)
        checkpoint = {'milestone':'M43N','freeze_commit':freeze,'config_sha256':contract,'scan':label,'width':width,
            'receipt_sha256':source.trusted_receipt_sha256,'source_identity':source.identity,
            'cache_identity':cache.identity,'cache_payload_sha256':cache.payload_sha256,
            'native_reference_sha256':reference.filtered_payload_sha256,'native_rows':native_rows,
            'native_values_compared':sum(x['values_compared'] for x in native_rows),'bank_coverage':coverage,
            'batches':[],'complete':False}
        target = OUT/f'{label}.width{width:03d}.json'
        write_sealed(target,checkpoint)
        for index,(a,b) in enumerate(batches(len(matrix),cfg['template_batch'])):
            if abort.is_set(): raise RuntimeError('peer failure; stopped before batch')
            record,_ = qualify_batch(cache,reference,a,b,gather_chunk=cfg['gather_chunk'],
                reference_chunk=cfg['reference_chunk'],retain_indices=[])
            checkpoint['batches'].append(record)
            write_sealed(target,checkpoint)
            if (index+1)%8 == 0 or b == len(matrix):
                print(f'{label} width {width}: {b}/{len(matrix)} templates exact',flush=True)
        count = validate_batches(checkpoint['batches'],cfg['template_count'],cfg['template_batch'],grid.support_bin_count)
        checkpoint.update(complete=True,cells_compared=count)
        write_sealed(target,checkpoint)
    except BaseException:
        abort.set()
        raise


def collect(label,width,cfg,contract,freeze):
    path=OUT/f'{label}.width{width:03d}.json';cp=read_sealed(path)
    anchor=next(a for a in cfg['anchors'] if a['scan']==label)
    if (cp['complete'] is not True or cp['freeze_commit']!=freeze or cp['config_sha256']!=contract
            or cp['scan']!=label or cp['width']!=width or cp['receipt_sha256']!=anchor['source_receipt_sha256']):
        raise ValueError('completed checkpoint identity differs')
    cells=validate_batches(cp['batches'],cfg['template_count'],cfg['template_batch'],cfg['support_carriers'])
    if cells!=cp['cells_compared']: raise ValueError('completed cell count differs')
    return {'scan':label,'width':width,'checkpoint':str(path.relative_to(ROOT)),
        'checkpoint_sha256':cp['result_sha256'],'source_identity':cp['source_identity'],'cache_identity':cp['cache_identity'],
        'native_values_compared':cp['native_values_compared'],'cells_compared':cells,'batch_count':len(cp['batches'])}


def run(work_root,freeze):
    cfg,contract=frozen(freeze);OUT.mkdir(exist_ok=True);started=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='m43n-control-') as d:
            abort_path=Path(d)/'abort';abort=FileAbort(abort_path)
            def child(label,width):
                if abort.is_set(): raise RuntimeError('peer failure; queued job stopped')
                result=subprocess.run([sys.executable,__file__,'--work-root',str(work_root),'--freeze-commit',freeze,
                    '--scan',label,'--width',str(width),'--abort-file',str(abort_path)])
                if result.returncode:
                    abort.set();raise RuntimeError(f'{label} width {width} exited {result.returncode}')
                return collect(label,width,cfg,contract,freeze)
            with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
                jobs=[pool.submit(child,a['scan'],w) for w in reversed(cfg['widths']) for a in cfg['anchors']]
                try:
                    for job in as_completed(jobs): job.result()
                except BaseException:
                    abort.set()
                    for job in jobs: job.cancel()
                    raise
        checks=[collect(a['scan'],w,cfg,contract,freeze) for a in cfg['anchors'] for w in cfg['widths']]
        summary=inventory(checks,cfg)
        if summary!=cfg['expected_summary']: raise ValueError('frozen endpoint denominator differs')
        result=write_sealed(OUT/'qualification.json',{'milestone':'M43N','status':'additional-epoch-scores-qualified',
            'freeze_commit':freeze,'config_sha256':contract,'m43m_result_sha256':cfg['m43m_result_sha256'],
            'bank_sha256':cfg['bank_sha256'],'factor_table_sha256':cfg['factor_table_sha256'],'grid_sha256':cfg['grid_sha256'],
            'checks':checks,'summary':summary,'new_remote_requests':0,'candidate_selection_performed':False,
            'multi_epoch_real_stack_qualified':False,'detection_threshold_calibrated':False,'recovery_measured':False,
            'workers':cfg['workers'],'numpy_version':np.__version__,'elapsed_seconds':round(time.monotonic()-started,3)})
        print(json.dumps({'result_sha256':result['result_sha256'],'summary':summary}),flush=True)
    except BaseException as error:
        write_sealed(OUT/'run_failure.json',{'milestone':'M43N','freeze_commit':freeze,'config_sha256':contract,
            'status':'incomplete','error_type':type(error).__name__,'reason':str(error),
            'checkpoint_paths':sorted(str(p.relative_to(ROOT)) for p in OUT.glob('epoch*.json'))})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);p.add_argument('--freeze-commit',required=True)
    p.add_argument('--scan');p.add_argument('--width',type=int);p.add_argument('--abort-file',type=Path);a=p.parse_args()
    if a.scan:
        if a.width is None or a.abort_file is None:p.error('scan requires width and abort-file')
        one(a.scan,a.width,a.work_root,a.freeze_commit,FileAbort(a.abort_file))
    else:run(a.work_root,a.freeze_commit)
