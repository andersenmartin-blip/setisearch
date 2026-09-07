"""Restore lost runtime bytes against already public M43H/M/P hashes.

No new source scope or scientific rule. Original result files are read only.
The experiment's frozen input checks remain authoritative after restoration.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from seti_repeater import source_m43h as source
from seti_repeater import transport_m43h as transport
from seti_repeater import transfer_m43i as transfer
from seti_repeater import search_v0p6 as core

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43t_mask_comparison'
WINDOW = 'm37_1412p5'


def one(runtime, label):
    started = time.monotonic(); OUT.mkdir(exist_ok=True)
    record = {'scan': label, 'purpose': 'restore exact previously published inputs',
              'original_results_modified': False, 'new_observation_coverage': False}
    try:
        parent = json.loads((ROOT / 'config/m43o_real_stacks.json').read_text())
        expected = next(x for x in parent['sources'] if x['scan'] == label)
        directory = runtime / 'sources' / label / WINDOW
        for attempt in range(1, 4):
            try:
                receipt, detail = source.extract_remote(ROOT, label, WINDOW, directory,
                    runtime / 'mirrors', spectral_access_authorized=True)
                break
            except (TimeoutError, ConnectionError) as error:
                print(f'{label}: transient transport attempt {attempt}: {error}', flush=True)
                if attempt == 3:
                    raise
        if receipt['receipt_sha256'] != expected['receipt_sha256']:
            raise ValueError('restored source receipt differs from original trusted receipt')
        source.rehydrate(directory, expected['receipt_sha256'])
        record['source_receipt_sha256'] = receipt['receipt_sha256']
        print(label + ': complete original source receipt reproduced', flush=True)
        _, _, _, metadata, basis, bank, table, _ = build_context()
        grid = core.make_m37_proxy_carrier_grid(WINDOW)
        factors = core.factor_table_for_scan(table, basis, label)
        src = transfer.load_telescope_source(directory, trusted_receipt_sha256=expected['receipt_sha256'])
        kind = label.split('_')[-1]; work = runtime / 'anchors'; work.mkdir(exist_ok=True)
        checks = []
        for width in core.M37_SPECTRAL_WIDTHS:
            cp = read_sealed(ROOT / f'results_m43p_combined_controls/{kind}.width{width:03d}.json')
            old = next(x for x in cp['sources'] if x['scan'] == label)
            cache = transfer.build_telescope_cache(src, factors, grid, width, bank_sha256=table.template_bank_sha256)
            if src.identity != old['source_identity'] or cache.identity != old['cache_identity']:
                raise ValueError('restored source/cache identity differs from M43P')
            for spec in old['arrays']:
                path = work / spec['path']
                if path.exists():
                    values = np.load(path, mmap_mode='r', allow_pickle=False)
                    reused = True
                else:
                    values = transfer.gather_bank_slice(cache, 0, grid.support_bin_count,
                        template_indices=np.arange(spec['template_start'], spec['template_stop']), chunk_bins=4096)
                    reused = False
                observed = transfer.array_hash(values)
                if observed != spec['score_sha256']:
                    raise ValueError('restored anchor score digest differs: ' + spec['path'])
                if not reused:
                    temp = path.with_suffix('.tmp.npy'); np.save(temp, values, allow_pickle=False); temp.replace(path)
                checks.append({'path': spec['path'], 'score_sha256': observed, 'shape': list(values.shape),
                               'reused': reused, 'original_digest_exact': True})
                del values
            del cache
            print(f'{label}: width {width}, {len(checks)}/16 original arrays exact', flush=True)
        record.update(complete=True, arrays=checks, transport_counters=dict(transport.COUNTERS))
    except Exception as error:
        record.update(complete=False, error=repr(error), transport_counters=dict(transport.COUNTERS))
        raise
    finally:
        record['wall_seconds'] = round(time.monotonic()-started, 3)
        write_sealed(OUT / ('restore.' + label + '.json'), record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--scan'); p.add_argument('--wait-for-mirrors', action='store_true')
    a = p.parse_args(); a.runtime_root.mkdir(parents=True, exist_ok=True)
    if a.scan:
        one(a.runtime_root, a.scan)
    else:
        labels = [f'epoch{e}_{kind}' for e in (1, 2, 3) for kind in ('on', 'off')]
        def launch(label):
            if a.wait_for_mirrors:
                deadline = time.monotonic() + 1800
                proof = OUT / ('mirror_restore.' + label + '.json')
                while not proof.exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError('mirror recovery did not complete: ' + label)
                    time.sleep(1)
                if read_sealed(proof)['complete'] is not True:
                    raise ValueError('incomplete mirror recovery')
            return subprocess.run([sys.executable, __file__, '--runtime-root', str(a.runtime_root), '--scan', label]).returncode
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(launch, labels))
        sys.exit(int(any(codes)))
