"""Restore only published sparse-mirror segments, checking every original hash.

Operational recovery of lost files, not a new source or detector evaluation.
Sixteen concurrent requests retain the original eight-MiB per-request bound and
strict live ETag, size and Content-Range checks. Original source extraction
subsequently validates the reconstructed mirror and complete source receipt.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from urllib.error import URLError
from seti_repeater import http_range_v0p6 as old
from seti_repeater import transport_m43h as transport
from seti_repeater.source_m43h import verify_transport_checkpoint
from m43e_economical_bank import write_sealed

ROOT = Path(__file__).resolve().parents[1]


def restore(runtime, label):
    started = time.monotonic()
    prefix = 'results_m43h_widened_source' if label.startswith('epoch1_') else 'results_m43m_epoch_sources'
    receipt = json.loads((ROOT / prefix / f'{label}_m37_1412p5.telescope-source.json').read_text())
    checkpoint = receipt['transport']['checkpoint']
    expected = checkpoint['remote']
    verify_transport_checkpoint(checkpoint, expected)
    for attempt in range(3):
        try:
            identity = transport.live_identity(expected['url'])
            break
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
    if identity.record() != expected:
        raise ValueError('live source identity changed')
    mirror = runtime / 'mirrors' / f'{label}.h5.sparse'
    mirror.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(mirror, os.O_RDWR | os.O_CREAT, 0o600)
    if os.fstat(fd).st_size == 0:
        os.ftruncate(fd, identity.size)
    if os.fstat(fd).st_size != identity.size:
        os.close(fd)
        raise ValueError('local sparse size differs')
    def segment(spec):
        start, stop = spec['start'], spec['stop']
        interval = old.ByteRange(start, stop)
        if interval.length > transport.MAX_REQUEST:
            raise ValueError('published segment exceeds request bound')
        payload = os.pread(fd, interval.length, start)
        reused = hashlib.sha256(payload).hexdigest() == spec['sha256']
        if not reused:
            for attempt in range(3):
                try:
                    payload = transport.BoundedMirror._request(SimpleNamespace(identity=identity), interval)
                    break
                except (URLError, TimeoutError, ConnectionError):
                    if attempt == 2:
                        raise
            if hashlib.sha256(payload).hexdigest() != spec['sha256']:
                raise ValueError('download differs from published segment hash')
            cursor = 0
            while cursor < len(payload):
                count = os.pwrite(fd, payload[cursor:], start + cursor)
                if count <= 0:
                    raise OSError('short sparse write')
                cursor += count
        return {**spec, 'original_digest_exact': True, 'reused': reused}
    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
            checks = []
            for result in pool.map(segment, checkpoint['segments']):
                checks.append(result)
                if len(checks) % 16 == 0:
                    print(f'{label}: {len(checks)}/{len(checkpoint["segments"])} segment hashes exact', flush=True)
        os.fsync(fd)
        # Publish the historical cache index only after all its bytes are
        # independently restored and checked; this is not a fresh observation.
        old._write_atomic(mirror.with_suffix(mirror.suffix + '.ranges.json'), old._canonical_json_bytes(checkpoint))
    finally:
        os.close(fd)
    write_sealed(ROOT / 'results_m43t_mask_comparison' / f'mirror_restore.{label}.json', {
        'scan': label, 'complete': True, 'new_observation_coverage': False,
        'purpose': 'exact historical sparse-cache restoration',
        'published_checkpoint_sha256': checkpoint['checkpoint_sha256'],
        'concurrent_request_limit': 16, 'per_request_limit_bytes': transport.MAX_REQUEST,
        'segments': checks, 'transport_counters_cumulative': dict(transport.COUNTERS),
        'wall_seconds': round(time.monotonic() - started, 3)})
    print(f'{label}: mirror restored in {time.monotonic() - started:.1f}s', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', required=True, type=Path)
    args = parser.parse_args()
    for epoch in (1, 2, 3):
        for kind in ('on', 'off'):
            restore(args.runtime_root, f'epoch{epoch}_{kind}')
