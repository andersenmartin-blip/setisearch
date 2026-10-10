#!/usr/bin/env python3
"""Read only selected HDF5 v1 raw-chunk B-tree metadata; never chunk payloads.

This is a separate selective traversal after the preserved h5py enumeration hit
its request ceiling. No HDF5 dataset value API, codec, or array reader is used.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import resource
import struct
import sys
import time
import urllib.request
from pathlib import Path


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect prohibited for exact pinned source')


def parse_node(raw, address, file_size):
    if len(raw) != 3136 or raw[:4] != b'TREE' or raw[4] != 1:
        raise ValueError('Not the pinned 3136-byte raw-chunk v1 B-tree node')
    level, n = raw[5], struct.unpack_from('<H', raw, 6)[0]
    if not 1 <= n <= 64 or level > 2 or not 0 <= address <= file_size - len(raw):
        raise ValueError('Invalid B-tree node bounds or depth')
    keys = [struct.unpack_from('<II4Q', raw, 24 + 48*i) for i in range(n+1)]
    coords = [k[2:] for k in keys]
    if any(coords[i] >= coords[i+1] for i in range(n)):
        raise ValueError('Chunk keys are not strictly ordered')
    children = [struct.unpack_from('<Q', raw, 64 + 48*i)[0] for i in range(n)]
    return level, keys, coords, children


class Source:
    def __init__(self, scan, cfg, base, output):
        self.scan, self.cfg, self.base = scan, cfg, base
        self.output = output / scan['label']
        self.output.mkdir()
        self.receipts, self.new_nodes, self.seen = [], {}, set()
        self.body_bytes, self.requests = 0, 0
        self.start = time.monotonic()
        self.opener = urllib.request.build_opener(NoRedirect)
        self.size = scan['expected_remote_size_bytes']
        self.cache = {}
        old = json.loads((base / scan['receipts_path']).read_text())
        if sha((base / scan['receipts_path']).read_bytes()) != scan['receipts_sha256']:
            raise ValueError('Frozen metadata receipts changed')
        for r in old:
            key = r.get('retained_file')
            if not key or key not in scan['cached_ranges']:
                continue
            offset, nbytes = r['offset'], r['requested_bytes']
            headers = r['response_headers']
            if (r['state'] != 'PASS' or r['status'] != 206 or
                r['final_url'] != scan['url'] or
                headers.get('ETag') != scan['expected_etag'] or
                headers.get('Content-Range') != f'bytes {offset}-{offset+nbytes-1}/{self.size}' or
                int(headers.get('Content-Length', '-1')) != nbytes):
                raise ValueError('Cached source receipt is not pin-qualified')
            raw = (base / scan['cache_directory'] / key).read_bytes()
            if sha(raw) != scan['cached_ranges'][key] or sha(raw) != r['body_sha256'] or len(raw) != nbytes:
                raise ValueError('Cached metadata content changed')
            self.cache[(offset, nbytes)] = raw
        # These bytes are already retained from metadata-only requests.
        sb = (base / scan['superblock_path']).read_bytes()
        if sha(sb) != scan['superblock_sha256'] or sb[:8] != b'\x89HDF\r\n\x1a\n':
            raise ValueError('Superblock pin changed')
        if sb[8] != 0 or sb[13:15] != b'\x08\x08' or struct.unpack_from('<Q', sb, 24)[0] != 0:
            raise ValueError('Unsupported superblock/base/offset size')
        layout = self.cache[(1000, 512)]
        expected = b'\x03\x02\x04' + struct.pack('<Q', cfg['root_address']) + struct.pack('<4I', 1, 1, 1048576, 4)
        if layout[240:240+len(expected)] != expected:
            raise ValueError('Pinned chunked layout v3 does not match root/shape/dtype')

    def node(self, address):
        key = (address, 3136)
        if key in self.cache:
            return self.cache[key], 'retained_first_attempt'
        if address in self.new_nodes:
            return self.new_nodes[address], 'new_selective_metadata'
        # Only a validated NON-LEAF metadata child can reach this function.
        if self.requests >= self.cfg['max_new_gets_per_source'] or self.body_bytes + 3136 > self.cfg['max_new_body_bytes_per_source']:
            raise ValueError('Separate selective metadata request/byte ceiling exhausted')
        if time.monotonic() - self.start >= self.cfg['max_source_wall_s']:
            raise ValueError('Selective metadata wall-time ceiling exhausted')
        if not 0 <= address <= self.size - 3136:
            raise ValueError('Metadata child address outside pinned file')
        record = {'offset': address, 'requested_bytes': 3136,
                  'range': f'bytes={address}-{address+3135}', 'state': 'RESERVED',
                  'started_utc': utc(), 'body_bytes_observed': 0, 'attempt': 1,
                  'request_headers': {'Range': f'bytes={address}-{address+3135}',
                                      'If-Match': self.scan['expected_etag']}}
        self.requests += 1
        self.receipts.append(record)
        save(self.output / 'receipts.json', self.receipts)  # BEFORE request
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(self.scan['url'], headers=record['request_headers'])
            with self.opener.open(req, timeout=self.cfg['http_timeout_s']) as response:
                record.update(status=response.status, response_headers=dict(response.headers), final_url=response.geturl())
                # Reject 200 or mismatch before reading even one body byte.
                if (response.status != 206 or response.geturl() != self.scan['url'] or
                    response.headers.get('ETag') != self.scan['expected_etag'] or
                    response.headers.get('Content-Range') != f'bytes {address}-{address+3135}/{self.size}' or
                    response.headers.get('Content-Length') != '3136'):
                    raise ValueError('Exact metadata Range/ETag/URL response rejected before body')
                raw = response.read(3136)
                record['body_bytes_observed'] = len(raw)
                self.body_bytes += len(raw)
                if len(raw) != 3136:
                    raise ValueError('Truncated metadata node')
                # Content-Length is pinned; do not read beyond this exact range.
            parse_node(raw, address, self.size)
            filename = f'{address:012d}_003136.bin'
            (self.output / filename).write_bytes(raw)
            record.update(state='PASS', body_sha256=sha(raw), retained_file=filename)
            self.new_nodes[address] = raw
            return raw, 'new_selective_metadata'
        except Exception as error:
            record.update(state='FAILED_CLOSED', error_type=type(error).__name__, error=str(error))
            raise
        finally:
            record.update(wall_s=time.monotonic()-t0, finished_utc=utc())
            save(self.output / 'receipts.json', self.receipts)

    def lookup(self, row):
        target = (row, 0, self.cfg['frequency_chunk_origin'], 0)
        address, previous_level, traversal = self.cfg['root_address'], None, []
        for depth in range(3):
            raw, origin = self.node(address)
            level, keys, coords, children = parse_node(raw, address, self.size)
            if previous_level is not None and level != previous_level - 1:
                raise ValueError('B-tree metadata levels do not descend exactly once')
            if any(entry['address'] == address for entry in traversal):
                raise ValueError('Cyclic B-tree traversal')
            traversal.append({'address': address, 'level': level, 'sha256': sha(raw), 'origin': origin})
            choices = [i for i in range(len(children)) if coords[i] <= target < coords[i+1]]
            if len(choices) != 1:
                raise ValueError('Target does not have one lower-inclusive B-tree interval')
            i = choices[0]
            if level == 0:
                if coords[i] != target:
                    raise ValueError('Exact physical chunk origin absent')
                nbytes, mask = keys[i][:2]
                payload_address = children[i]
                if not 0 < nbytes <= self.cfg['max_stored_chunk_bytes'] or not 0 <= payload_address <= self.size-nbytes:
                    raise ValueError('Payload metadata bounds invalid')
                # Leaf child address is PAYLOAD and is returned; NEVER fetched.
                return {'time_row': row, 'chunk_origin': list(target[:3]),
                        'byte_offset': payload_address, 'stored_size': nbytes,
                        'byte_range': f'bytes={payload_address}-{payload_address+nbytes-1}',
                        'filter_mask': mask, 'decoded_size': 4194304,
                        'traversal': traversal, 'spectral_payload_fetched': False}
            previous_level, address = level, children[i]
        raise ValueError('Exceeded pinned depth')


def run_source(scan, cfg, base, output):
    start, cpu = time.monotonic(), time.thread_time()
    result = {'label': scan['label'], 'role': scan['role'], 'url': scan['url'],
              'metadata_only': True, 'spectral_values_read': False, 'chunks': [],
              'status': 'FAILED_CLOSED'}
    source = None
    try:
        source = Source(scan, cfg, base, output)
        for row in range(16):
            result['chunks'].append(source.lookup(row))
        result.update(status='EXACT_16_CHUNK_RANGES_METADATA_QUALIFIED',
                      future_spectral_payload_bytes=sum(x['stored_size'] for x in result['chunks']))
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    finally:
        result.update(new_metadata_gets=source.requests if source else 0,
                      new_metadata_body_bytes=source.body_bytes if source else 0,
                      wall_s=time.monotonic()-start, thread_cpu_s=time.thread_time()-cpu)
        save(output / (scan['label'] + '_result.json'), result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, default=Path(__file__).with_name('direct_chunk_metadata_config.json'))
    p.add_argument('--base-dir', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    cfgraw = args.config.read_bytes()
    cfg = json.loads(cfgraw)
    output = args.output or args.base_dir / 'direct_metadata_ranges'
    output.mkdir()  # One attempt only; refuse existing output.
    start, cpu = time.monotonic(), time.process_time()
    save(output / 'invocation_receipt.json', {'started_utc': utc(), 'script_sha256': sha(Path(__file__).read_bytes()),
          'config_sha256': sha(cfgraw), 'python_version': sys.version, 'argv': sys.argv,
          'spectral_values_read': False, 'metadata_only': True, 'phase': 'separate_direct_btree_metadata'})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_source, scan, cfg, args.base_dir, output) for scan in cfg['scans']]
        results = [f.result() for f in futures]
    passed = all(x['status'] == 'EXACT_16_CHUNK_RANGES_METADATA_QUALIFIED' for x in results)
    result = {'finished_utc': utc(), 'status': 'PASS_METADATA_SOURCE_RANGES' if passed else 'FAILED_CLOSED',
              'metadata_only': True, 'spectral_values_read': False, 'spectral_payload_fetched': False,
              'new_metadata_gets': sum(x['new_metadata_gets'] for x in results),
              'new_metadata_body_bytes': sum(x['new_metadata_body_bytes'] for x in results),
              'future_spectral_payload_bytes': sum(x.get('future_spectral_payload_bytes', 0) for x in results),
              'decoded_complete_chunk_bytes': 96*4194304 if passed else None,
              'wall_s': time.monotonic()-start, 'cpu_s': time.process_time()-cpu,
              'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, 'sources': results}
    save(output / 'current_direct_chunk_metadata.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'sources'}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
