"""Restore one frozen source using <=512 MiB of ordinary segment files.

Operational replacement for large sparse mirrors. Every downloaded byte is
bound to the original published ranges, live identity and SHA256. The original
row extraction, normalization, source receipt and anchor arithmetic are reused.
No telescope-sized file is created. No scientific endpoint is evaluated.
"""
import argparse
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
from urllib.error import URLError

import numpy as np

from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from seti_repeater import source_m43h as source
from seti_repeater import transfer_m43i as transfer
from seti_repeater import transport_m43h as transport
from seti_repeater import http_range_v0p6 as http
from seti_repeater import search_v0p6 as core

ROOT = Path(__file__).resolve().parents[1]
WINDOW = 'm37_1412p5'
MAX_PACKED_BYTES = 512 * 1024**2
FREE_RESERVE_BYTES = 2 * 1024**3
MAX_WORKERS = 4
LABELS = tuple(f'epoch{e}_{kind}' for e in (1, 2, 3) for kind in ('on', 'off'))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while data := f.read(1024**2):
            h.update(data)
    return h.hexdigest()


class SegmentReader(io.RawIOBase):
    """Read only verified published spans; holes and oversized reads fail closed."""
    def __init__(self, directory, segments, size):
        super().__init__()
        self.directory, self.size, self.position = Path(directory), size, 0
        self.segments = sorted(segments, key=lambda s: s['start'])
        self.starts = [s['start'] for s in self.segments]
        previous_stop = 0
        for s in self.segments:
            if not previous_stop <= s['start'] < s['stop'] <= size:
                raise ValueError('overlapping or invalid published span')
            previous_stop = s['stop']
            path = self.path(s)
            if path.stat().st_size != s['stop'] - s['start'] or file_sha(path) != s['sha256']:
                raise ValueError('segment bytes differ from original published digest')

    def path(self, segment):
        return self.directory / f"{segment['start']:016d}-{segment['stop']:016d}.part"

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=os.SEEK_SET):
        if whence not in (os.SEEK_SET, os.SEEK_CUR, os.SEEK_END):
            raise ValueError('invalid seek origin')
        p = offset + (0 if whence == os.SEEK_SET else self.position if whence == os.SEEK_CUR else self.size)
        if p < 0:
            raise ValueError('negative seek')
        self.position = p
        return p

    def read(self, size=-1):
        if type(size) is not int or not 0 <= size <= transport.MAX_READ:
            raise ValueError('unbounded or oversized HDF5 read rejected')
        stop = min(self.position + size, self.size)
        chunks = []
        while self.position < stop:
            i = bisect_right(self.starts, self.position) - 1
            if i < 0 or self.position >= self.segments[i]['stop']:
                raise ValueError('HDF5 requested an unpublished byte range')
            s = self.segments[i]
            end = min(stop, s['stop'])
            with self.path(s).open('rb') as f:
                f.seek(self.position - s['start'])
                data = f.read(end - self.position)
            if len(data) != end - self.position:
                raise ValueError('truncated verified segment')
            chunks.append(data)
            self.position = end
        return b''.join(chunks)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def original_receipt(label):
    if label not in LABELS:
        raise ValueError('unknown source')
    prefix = 'results_m43h_widened_source' if label.startswith('epoch1_') else 'results_m43m_epoch_sources'
    receipt = source.verify(json.loads((ROOT / prefix / f'{label}_{WINDOW}.telescope-source.json').read_text()))
    source_config = json.loads((ROOT / 'config/m43o_real_stacks.json').read_text())
    expected = next(s for s in source_config['sources'] if s['scan'] == label)
    if receipt['receipt_sha256'] != expected['receipt_sha256']:
        raise ValueError('source receipt differs from independent M43O trust anchor')
    cp = receipt['transport']['checkpoint']
    source.verify_transport_checkpoint(cp, cp['remote'])
    return receipt


def plan(label, runtime):
    receipt = original_receipt(label)
    segments = receipt['transport']['checkpoint']['segments']
    lengths = [s['stop'] - s['start'] for s in segments]
    if sum(lengths) > MAX_PACKED_BYTES or max(lengths) > transport.MAX_REQUEST:
        raise ValueError('published cache exceeds bounded recovery contract')
    kind = label.split('_')[-1]
    support_count = core.make_m37_proxy_carrier_grid(WINDOW).support_bin_count
    anchor_bytes = 0
    for width in core.M37_SPECTRAL_WIDTHS:
        cp = read_sealed(ROOT / f'results_m43p_combined_controls/{kind}.width{width:03d}.json')
        spec = next(s for s in cp['sources'] if s['scan'] == label)
        for a in spec['arrays']:
            if not (runtime / 'anchors' / a['path']).exists():
                anchor_bytes += (a['template_stop'] - a['template_start']) * support_count * 4 + 256
    scope = receipt['scope']
    source_bytes = scope['definition']['expected_header']['dataset_shape'][0] * scope['geometry']['channel_count'] * 8 + 1024**2
    required = FREE_RESERVE_BYTES + sum(lengths) + anchor_bytes + source_bytes
    return dict(scan=label, published_segments=len(segments), packed_download_bytes=sum(lengths),
        largest_download_file_bytes=max(lengths), maximum_packed_bytes=MAX_PACKED_BYTES,
        new_anchor_bound_bytes=anchor_bytes, source_bound_bytes=source_bytes,
        free_reserve_bytes=FREE_RESERVE_BYTES, required_free_bytes=required,
        free_bytes=shutil.disk_usage(runtime).free, concurrent_requests=MAX_WORKERS,
        telescope_sized_sparse_file_created=False, new_scientific_evaluations=0)


def restore_source(label, runtime, output, receipt):
    import h5py
    import hdf5plugin  # noqa: F401 -- original HDF5 compression filter
    observed = dict(numpy=np.__version__, h5py=h5py.__version__,
                    hdf5=h5py.version.hdf5_version,
                    hdf5plugin=importlib.metadata.version('hdf5plugin'))
    if observed != receipt['transport']['hdf5_runtime']:
        raise ValueError('original source HDF5 runtime differs')
    directory = runtime / 'sources' / label / WINDOW
    if (directory / 'source.json').exists():
        source.rehydrate(directory, receipt['receipt_sha256'])
        return dict(reused_source=True, original_receipt_exact=True, downloaded_bytes=0)
    cp = receipt['transport']['checkpoint']
    expected = cp['remote']
    identity = transport.live_identity(expected['url'])
    if identity.record() != expected:
        raise ValueError('live source identity changed')
    parts = runtime / 'bounded_segments' / label
    parts.mkdir(parents=True, exist_ok=True)

    def segment(s):
        path = parts / f"{s['start']:016d}-{s['stop']:016d}.part"
        reused = path.exists() and path.stat().st_size == s['stop'] - s['start'] and file_sha(path) == s['sha256']
        if not reused:
            if shutil.disk_usage(runtime).free < FREE_RESERVE_BYTES + MAX_WORKERS * transport.MAX_REQUEST:
                raise OSError('bounded recovery stopped before consuming disk reserve')
            for attempt in range(3):
                try:
                    data = transport.BoundedMirror._request(SimpleNamespace(identity=identity), http.ByteRange(s['start'], s['stop']))
                    break
                except (URLError, TimeoutError, ConnectionError):
                    if attempt == 2: raise
            if hashlib.sha256(data).hexdigest() != s['sha256']:
                raise ValueError('download differs from original published segment')
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(data)
            temporary.replace(path)
        return dict(**s, reused=reused, original_digest_exact=True)

    checks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for r in pool.map(segment, cp['segments']):
            checks.append(r)
            if len(checks) % 16 == 0:
                print(f'{label}: {len(checks)}/{len(cp["segments"])} bounded segment hashes exact', flush=True)
    with SegmentReader(parts, cp['segments'], identity.size) as reader:
        with h5py.File(reader, 'r', rdcc_nbytes=source.HDF5_CACHE_BYTES) as handle:
            source.validate_dataset(handle, receipt['scope'])
            rows, resumed = source._extract_rows(handle, receipt['scope'], directory)
    restored = source._complete(directory, receipt['scope'], rows, receipt['transport'])
    if restored != receipt:
        raise ValueError('reconstructed source receipt differs from frozen original')
    source.rehydrate(directory, receipt['receipt_sha256'])
    record = dict(scan=label, complete=True, original_receipt_exact=True,
        source_receipt_sha256=receipt['receipt_sha256'], segments=checks,
        published_checkpoint_sha256=cp['checkpoint_sha256'],
        downloaded_bytes=sum(s['stop'] - s['start'] for s in checks if not s['reused']),
        ordinary_segment_files=True, telescope_sized_sparse_file_created=False,
        source_and_normalization_arithmetic_changed=False, new_scientific_evaluations=0)
    write_sealed(output / f'bounded_transport.{label}.json', record)
    shutil.rmtree(parts)
    print(label + ': original source receipt exact; bounded download parts removed', flush=True)
    return record


def restore_anchors(label, runtime, receipt):
    _, _, _, _, basis, bank, table, _ = build_context()
    grid = core.make_m37_proxy_carrier_grid(WINDOW)
    factors = core.factor_table_for_scan(table, basis, label)
    src = transfer.load_telescope_source(runtime / 'sources' / label / WINDOW,
                                         trusted_receipt_sha256=receipt['receipt_sha256'])
    anchors = runtime / 'anchors'
    anchors.mkdir(exist_ok=True)
    checks = []
    for width in core.M37_SPECTRAL_WIDTHS:
        cp = read_sealed(ROOT / f'results_m43p_combined_controls/{label.split("_")[-1]}.width{width:03d}.json')
        old = next(s for s in cp['sources'] if s['scan'] == label)
        cache = transfer.build_telescope_cache(src, factors, grid, width, bank_sha256=table.template_bank_sha256)
        if src.identity != old['source_identity'] or cache.identity != old['cache_identity']:
            raise ValueError('restored source/cache identity differs from M43P')
        for spec in old['arrays']:
            path = anchors / spec['path']
            reused = path.exists()
            if reused:
                values = np.load(path, mmap_mode='r', allow_pickle=False)
            else:
                values = transfer.gather_bank_slice(cache, 0, grid.support_bin_count,
                    template_indices=np.arange(spec['template_start'], spec['template_stop']), chunk_bins=4096)
            if transfer.array_hash(values) != spec['score_sha256']:
                raise ValueError('anchor score digest differs: ' + spec['path'])
            if not reused:
                if shutil.disk_usage(runtime).free < FREE_RESERVE_BYTES + values.nbytes + 256:
                    raise OSError('stopped before consuming disk reserve')
                temp = path.with_suffix('.tmp.npy')
                np.save(temp, values, allow_pickle=False)
                temp.replace(path)
            checks.append(dict(path=spec['path'], score_sha256=spec['score_sha256'],
                               shape=list(values.shape), original_digest_exact=True, reused=reused))
            del values
        del cache
        print(f'{label}: width {width}, {len(checks)}/16 original arrays exact', flush=True)
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scan', choices=LABELS, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    source.frozen_inputs(ROOT)
    args.runtime_root.mkdir(parents=True, exist_ok=True)
    bounds = plan(args.scan, args.runtime_root)
    print(json.dumps(bounds), flush=True)
    if args.check_only:
        return
    if bounds['free_bytes'] < bounds['required_free_bytes']:
        raise OSError('insufficient free space for one bounded source plus reserve')
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f'restore.{args.scan}.json'
    if path.exists():
        raise FileExistsError('preserve closed receipt; select a fresh output directory')
    started = time.monotonic()
    receipt = original_receipt(args.scan)
    restore_source(args.scan, args.runtime_root, args.output, receipt)
    arrays = restore_anchors(args.scan, args.runtime_root, receipt)
    write_sealed(path, dict(scan=args.scan, complete=True,
        purpose='bounded exact historical recovery after disk-risk stop',
        source_receipt_sha256=receipt['receipt_sha256'], arrays=arrays,
        bounds=bounds, final_free_bytes=shutil.disk_usage(args.runtime_root).free,
        wall_seconds=round(time.monotonic() - started, 3),
        original_results_modified=False, new_observation_coverage=False))


if __name__ == '__main__':
    main()
