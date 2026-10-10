"""Authenticate/restore adjacent170/172 compressed sidecars from complete H5.

No HTTP, power decoding, search, deletion, resume or overwrite. Run from the
extracted RAW archive root with the acquisition SHA from its payload manifest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

STAGE = Path('analysis/s2017_next_native/results/acquire')
MANIFEST = Path('analysis/s2017_next_native/source_manifest_v2.json')
MANIFEST_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
NATIVES = (170, 172)
COMPLETE = 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts, 'Relative confined path required')
    result = (root / p).resolve()
    require(result.is_relative_to(root), 'Path leaves extracted workspace')
    return result


def contract(root, acquisition_sha256):
    receipt_path = root / STAGE / 'ACQUISITION_RESULT.json'
    require(digest(receipt_path) == acquisition_sha256, 'Acquisition receipt pin differs')
    require(digest(root / MANIFEST) == MANIFEST_SHA, 'Corrected V2 metadata pin differs')
    receipt = json.loads(receipt_path.read_bytes())
    manifest = json.loads((root / MANIFEST).read_bytes())
    require(receipt['status'] == COMPLETE, 'Complete actual acquisition required')
    require(receipt['source_manifest_sha256'] == MANIFEST_SHA, 'Acquisition uses different manifest')
    require(receipt['new_telescope_HTTP_requests'] == 192 and
            receipt['new_telescope_BODY_bytes'] == 597792529, 'Actual192 BODY accounting differs')
    require(len(receipt['decoded_files']) == 12 and len(receipt['raw_range_records']) == 192,
            'Exactly12 compact files and192 raw records required')
    expected = [(n, s) for n in NATIVES for s in SCANS]
    require([(x['native_chunk_index'], x['scan_id']) for x in receipt['decoded_files']] == expected,
            'Ordered170six then172six compact inventory differs')
    records = receipt['raw_range_records']
    keys = [(x['native_chunk_index'], x['scan_id'], x['time_row']) for x in records]
    require(keys == [(n, s, row) for n, s in expected for row in range(16)],
            'Ordered192 unique raw records required')
    require(len({x['path'] for x in records}) == 192, 'Raw paths repeat')
    return receipt, manifest


def verify_compacts(root, acquisition_sha256, require_sidecars=False, restore=False):
    receipt, manifest = contract(root, acquisition_sha256)
    if restore:
        require(not require_sidecars, 'Restore and existing-sidecar check are exclusive')
        # Fail before any writes if even one target already exists.
        for item in receipt['raw_range_records']:
            require(not confined(root, STAGE / item['path']).exists(), 'Restore target already exists')
    for name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
        os.environ[name] = '1'
    import sys
    sys.path.insert(0, str(root / 'analysis/deps'))
    import h5py
    require(h5py.__version__ == '3.15.1' and h5py.version.hdf5_version == '1.14.6',
            'Exact h5py/HDF5 direct-chunk runtime required')
    rawmap = {(x['native_chunk_index'], x['scan_id'], x['time_row']): x
              for x in receipt['raw_range_records']}
    verified = []
    for source in receipt['decoded_files']:
        native, scan = source['native_chunk_index'], source['scan_id']
        expected_name = 'native%d_%s.compact.h5' % (native, scan)
        require(source['array_file'] == expected_name, 'Compact path differs')
        path = confined(root, STAGE / expected_name)
        require(path.stat().st_size == source['bytes'] and digest(path) == source['file_sha256'],
                'Complete H5 full-file pin differs')
        original = next(x for x in manifest['by_native_chunk'][str(native)]['sources']
                        if x['label'] == scan)
        require(len(source['decoded_rows']) == 16, 'Decoded-row receipt is incomplete')
        with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
            data = handle['data']
            require(data.shape == (16, 1, 1048576) and data.dtype.str == '<f4' and
                    data.chunks == (1, 1, 1048576), 'Compact geometry differs')
            require(int(data.attrs['original_source_frequency_chunk_origin']) == native * 1048576
                    and data.attrs['original_source_url'] == original['url']
                    and data.attrs['original_source_etag'] == original['etag'],
                    'Physical source identity differs')
            for desc in original['chunks']:
                row = desc['time_row']
                item = rawmap[(native, scan, row)]
                require(item['path'] == 'raw_ranges/native%d_%s_row%02d.raw.bin' % (native, scan, row)
                        and item['original_source_chunk_origin'] == [row, 0, native * 1048576]
                        and item['source_range'] == desc['byte_range']
                        and item['stored_size'] == desc['stored_size'] and item['filter_mask'] == 0
                        and item['compact_raw_roundtrip_sha256'] == item['raw_sha256'],
                        'Raw-record physical descriptor differs')
                mask, raw = data.id.read_direct_chunk((row, 0, 0))
                require(mask == 0 and len(raw) == item['stored_size'] and
                        hashlib.sha256(raw).hexdigest() == item['raw_sha256'],
                        'Compressed H5 raw chunk differs')
                target = confined(root, STAGE / item['path'])
                if require_sidecars:
                    require(target.stat().st_size == len(raw) and digest(target) == item['raw_sha256'],
                            'Durable raw sidecar differs')
                if restore:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as out:
                        out.write(raw)
                        out.flush()
                        os.fsync(out.fileno())
                    fd = os.open(target.parent, os.O_RDONLY)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                verified.append({'local_path': (STAGE / item['path']).as_posix(),
                                 'bytes': len(raw), 'sha256': item['raw_sha256'],
                                 'compact_path': path.relative_to(root).as_posix(),
                                 'compact_file_sha256': source['file_sha256'],
                                 'compact_chunk_origin': [row, 0, 0],
                                 'original_source_chunk_origin': item['original_source_chunk_origin']})
    require(len(verified) == 192, 'Exactly192 raw chunks must be authenticated')
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--acquisition-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    records = verify_compacts(Path(args.root).resolve(), args.acquisition_sha256,
                              restore=not args.verify_only)
    print(json.dumps({'status': 'PASS192_EXACT_H5_RAW_CHUNKS' if args.verify_only else
                      'RESTORED192_EXACT_COMPRESSED_SIDECARS', 'records': len(records),
                      'HTTP_requests': 0, 'decoded_power_rows': 0, 'search_runs': 0}))


if __name__ == '__main__':
    main()
