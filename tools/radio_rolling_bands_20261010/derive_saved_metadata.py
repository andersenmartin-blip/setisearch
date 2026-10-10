"""Offline-only exact chunk-index derivation; never reads spectral payloads.

Reuses only the original pure parse_node function by AST extraction. No Source
object, original node method, HTTP client or array decoder is instantiated.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import struct
import tarfile
import time

WORK = Path(__file__).resolve().parents[3] / 'seti_fullpower_work'
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = WORK / 'historical_index_discovery/pilot_source_20261008/primary'
ARCHIVES = WORK / 'metadata_recovery/index_archives'
sha = lambda b: hashlib.sha256(b).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode()
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def load_pinned(path, expected):
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError('Input identity changed: ' + str(path))
    return json.loads(raw)


def main():
    start_cpu, start_wall = time.process_time(), time.monotonic()
    old = load_pinned(OLD / 'source_manifest.json',
                      '6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec')
    previous = load_pinned(ROOT / 'tools/radio_fresh_band_20261009/source_manifest.json',
                           'd2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c')
    cfg_raw = (OLD / 'direct_chunk_metadata_config.json').read_bytes()
    cfg = json.loads(cfg_raw)
    parser_raw = (OLD / 'direct_chunk_metadata.py').read_bytes()
    # The copied original parser identity is also checked against the discovery
    # receipt's complete list of SHA-pinned fetched files below.
    receipt = json.loads((WORK / 'historical_index_discovery/DISCOVERY_RECEIPT.json').read_text())
    fetched = receipt['text_file_readback']
    pin_by_path = {x['repo_path']: x['sha256'] for x in fetched}
    for name, raw in [('direct_chunk_metadata.py', parser_raw),
                      ('direct_chunk_metadata_config.json', cfg_raw),
                      ('cached_metadata_ranges_manifest.json', (OLD / 'cached_metadata_ranges_manifest.json').read_bytes()),
                      ('direct_metadata_evidence_manifest.json', (OLD / 'direct_metadata_evidence_manifest.json').read_bytes())]:
        if sha(raw) != pin_by_path['pilot_source_20261008/primary/' + name]:
            raise ValueError('Historical text pin changed: ' + name)
    parser_source = parser_raw.decode()
    function = next(x for x in ast.parse(parser_source).body
                    if isinstance(x, ast.FunctionDef) and x.name == 'parse_node')
    pure = ast.get_source_segment(parser_source, function)
    env = {'struct': struct}
    exec(compile(pure, '<pinned-original-pure-parse_node>', 'exec'), env)
    parse_node = env['parse_node']
    if cfg['root_address'] != 7432 or cfg['node_bytes'] != 3136:
        raise ValueError('Original index geometry changed')
    scans = cfg['scans']
    if [s['label'] for s in scans] != [s['label'] for s in previous['sources']]:
        raise ValueError('Source order changed')
    members = {}
    archive_pins = {}
    for name in ['cached_metadata_ranges', 'direct_metadata_evidence']:
        manifest = json.loads((OLD / (name + '_manifest.json')).read_text())
        raw = (ARCHIVES / (name + '.tar.gz')).read_bytes()
        if len(raw) != manifest['archive_bytes'] or sha(raw) != previous['metadata_archives'][name]:
            raise ValueError('Pinned archive identity changed')
        archive_pins[name] = {'bytes': len(raw), 'sha256': sha(raw)}
        with tarfile.open(ARCHIVES / (name + '.tar.gz'), 'r:gz') as tar:
            declared = {m['path']: m for m in manifest['members']}
            if set(tar.getnames()) != set(declared):
                raise ValueError('Metadata archive member family changed')
            for member in tar.getmembers():
                if not member.isfile():
                    raise ValueError('Non-file archive member')
                body = tar.extractfile(member).read()
                pin = declared[member.name]
                if len(body) != pin['bytes'] or sha(body) != pin['sha256']:
                    raise ValueError('Metadata member identity changed')
                members[member.name] = body
    caches = {}
    for scan, prior, historical in zip(scans, previous['sources'], old['sources']):
        label, size = scan['label'], scan['expected_remote_size_bytes']
        for key, expected in [('url', scan['url']), ('etag', scan['expected_etag']), ('source_file_bytes', size)]:
            if prior[key] != expected or historical[key] != expected:
                raise ValueError('Historical/current source identity mismatch')
        if prior['current_header'] != historical['current_header']:
            raise ValueError('Historical source header changed')
        if prior['current_header']['dataset_chunks'] != [1, 1, 1048576] or prior['dtype_exact'] != '<f4':
            raise ValueError('Decode geometry changed')
        cache = {}
        for prefix in ['metadata_ranges', 'direct_metadata_ranges']:
            rp = f'{prefix}/{label}/receipts.json'
            raw_receipt = members[rp]
            if prefix == 'metadata_ranges' and sha(raw_receipt) != scan['receipts_sha256']:
                raise ValueError('Old range receipts identity changed')
            for r in json.loads(raw_receipt):
                filename = r.get('retained_file')
                if not filename:
                    continue
                off, n = r['offset'], r['requested_bytes']
                headers = r['response_headers']
                if (r['state'] != 'PASS' or r['status'] != 206 or r['final_url'] != scan['url']
                        or headers.get('ETag') != scan['expected_etag']
                        or headers.get('Content-Range') != f'bytes {off}-{off+n-1}/{size}'
                        or int(headers.get('Content-Length', '-1')) != n):
                    raise ValueError('Metadata receipt lacks exact source qualification')
                body = members[f'{prefix}/{label}/{filename}']
                if len(body) != n or sha(body) != r['body_sha256']:
                    raise ValueError('Receipt body pin changed')
                if prefix == 'metadata_ranges' and sha(body) != scan['cached_ranges'][filename]:
                    raise ValueError('Cached metadata config pin changed')
                if (off, n) in cache and cache[(off, n)] != body:
                    raise ValueError('Conflicting metadata caches')
                cache[(off, n)] = body
        caches[label] = cache

    def lookup(scan, row, chunk):
        target = (row, 0, chunk * 1048576, 0)
        address, previous_level, traversal = cfg['root_address'], None, []
        for depth in range(3):
            # A missing metadata entry fails here: no HTTP fallback exists.
            raw = caches[scan['label']][(address, 3136)]
            level, keys, coords, children = parse_node(raw, address, scan['expected_remote_size_bytes'])
            if previous_level is not None and level != previous_level - 1:
                raise ValueError('Index depth changed')
            if any(x['address'] == address for x in traversal):
                raise ValueError('Index cycle')
            traversal.append({'address': address, 'level': level, 'sha256': sha(raw)})
            choices = [i for i in range(len(children)) if coords[i] <= target < coords[i+1]]
            if len(choices) != 1:
                raise ValueError('Target lacks unique index interval')
            i = choices[0]
            if level == 0:
                if coords[i] != target:
                    raise ValueError('Exact chunk origin absent')
                n, mask = keys[i][:2]
                payload = children[i]
                if not 0 < n <= cfg['max_stored_chunk_bytes'] or not 0 <= payload <= scan['expected_remote_size_bytes'] - n or mask != 0:
                    raise ValueError('Payload index geometry not eligible')
                return {'time_row': row, 'chunk_origin': list(target[:3]), 'byte_offset': payload,
                        'stored_size': n, 'byte_range': f'bytes={payload}-{payload+n-1}',
                        'filter_mask': mask, 'decoded_size': 4194304, 'traversal': traversal,
                        'spectral_payload_fetched': False}
            previous_level, address = level, children[i]
        raise ValueError('Exceeded pinned index depth')

    # Metadata-only positive identity control: all 96 old q151 descriptors.
    for scan, prior in zip(scans, previous['sources']):
        for row, entry in enumerate(prior['chunks']):
            if lookup(scan, row, 151) != entry:
                raise ValueError('Old chunk151 metadata reproduction failed')
    protected = [old['prior_use']['old_validation_chunk'], old['prior_use']['old_calibration_chunk']]
    if set(protected) & {155, 157, 158}:
        raise ValueError('Selected chunk overlaps protected historical input')
    pins = {}
    missing = []
    derived = {}
    for chunk in [155, 157, 158]:
        derived[chunk] = {}
        for scan in scans:
            derived[chunk][scan['label']] = []
            for row in range(16):
                try:
                    derived[chunk][scan['label']].append(lookup(scan, row, chunk))
                except KeyError as error:
                    missing.append({'native_chunk_index': chunk, 'label': scan['label'], 'time_row': row,
                                    'missing_metadata_address': error.args[0][0], 'node_bytes': error.args[0][1]})
    for chunk in [155, 157, 158]:
        if any(m['native_chunk_index'] == chunk for m in missing):
            continue
        result = copy.deepcopy(previous)
        lo, hi = chunk * 1048576, (chunk+1) * 1048576
        result.update(schema='SETI_FROZEN_NEXT_NATIVE_BAND_V1', native_chunk_index=chunk,
                      selection_rule='Prospective metadata-only ascending continuation155 then157; protected156/159 skipped. Chunk158 is metadata-only capacity forecast, independent of all signal outcomes.',
                      physical_channel_interval_half_open=[lo, hi],
                      frequency_center_limits_MHz=sorted([(result['fch1_hz']+x*result['df_hz'])/1e6 for x in [lo, hi-1]]),
                      protected_prior_native_chunk_indices=protected,
                      protected_prior_native_chunk_values_opened=False,
                      previous_chunk151_source_manifest_sha256=sha((ROOT/'tools/radio_fresh_band_20261009/source_manifest.json').read_bytes()),
                      metadata_151_identity_control_all96=True,
                      metadata_only_all96_this_chunk_descriptors_derived=True)
        for scan, source in zip(scans, result['sources']):
            source['chunks'] = derived[chunk][scan['label']]
            source['future_spectral_payload_bytes'] = sum(x['stored_size'] for x in source['chunks'])
            source['new_chunk_ranges_HTTP_tested'] = False
            source['prior_source_identity_and_range_capability_reused'] = True
            if 'all_needed_chunk_ranges_qualified' in source:
                del source['all_needed_chunk_ranges_qualified']
        result['total_future_spectral_payload_bytes'] = sum(s['future_spectral_payload_bytes'] for s in result['sources'])
        pins[str(chunk)] = save(OUT / f'source_manifest_chunk{chunk}.json', result)
    result = {'schema': 'SETI_OFFLINE_SAVED_INDEX_DERIVATION_V1', 'status': 'PASS_EXACT_288_NEXT_AND_FORECAST_DESCRIPTORS' if not missing else 'MISSING_METADATA_NO_SOURCE_GET_NO_ESTIMATED_PAYLOAD',
              'original_pure_parser_sha256': sha(parser_raw), 'original_config_sha256': sha(cfg_raw),
              'archives': archive_pins, 'manifest_pins': pins, 'old151_descriptor_matches': 96,
              'new_chunk_indices': [155, 157, 158], 'new_descriptors_per_chunk': 96,
              'node_bytes': 3136, 'protected_prior_chunks': protected,
              'missing_metadata_descriptors': missing,
              'known_descriptor_counts_per_chunk': {str(q): sum(len(x) for x in derived[q].values()) for q in derived},
              'known_compressed_payload_lower_bounds_per_chunk_bytes': {str(q): sum(c['stored_size'] for rows in derived[q].values() for c in rows) for q in derived},
              'unique_missing_metadata_nodes': sorted({(x['label'], x['missing_metadata_address'], x['node_bytes']) for x in missing}),
              'observation_values_read': False, 'telescope_HTTP_requests': 0,
              'metadata_get_fallback_implemented': False,
              'cpu_s': time.process_time()-start_cpu, 'wall_s': time.monotonic()-start_wall}
    save(ROOT / 'results/radio_rolling_bands_20261010/OFFLINE_METADATA_DERIVATION.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
