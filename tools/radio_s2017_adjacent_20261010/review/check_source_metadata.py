"""Independent JSON/code/retained-TREE-only check. Never opens power files."""
from pathlib import Path
import ast
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
COUNT = 1048576
SCANS = ['epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    base = ROOT / 'analysis/s2017_next_native'
    source_path = base / 'source_manifest_v2.json'
    source_raw = source_path.read_bytes()
    source = json.loads(source_raw)
    assert digest(source_raw) == '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
    old_path = ROOT / 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
    old_raw = old_path.read_bytes()
    old = json.loads(old_raw)
    assert digest(old_raw) == source['original171_source_manifest_sha256']
    original_scope = json.loads((ROOT / 'analysis/next_visit/DIRECT_MIDPOINT_METADATA_SCOPE.json').read_bytes())
    parser_path = Path(original_scope['pinned_original_parser_path'])
    parser_raw = parser_path.read_bytes()
    assert digest(parser_raw) == 'e868886941a807c5d95d14c1e7aad5597edfac389dcef98b5a522bb17f812d21'
    code = parser_raw.decode()
    func = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'parse_node')
    env = {'struct': struct}
    exec(compile(ast.get_source_segment(code, func), '<pure-metadata-only-parse-node>', 'exec'), env)
    parse = env['parse_node']
    extraction_path = ROOT / source['metadata_extraction_receipt_path']
    extraction_raw = extraction_path.read_bytes()
    extraction = json.loads(extraction_raw)
    assert digest(extraction_raw) == source['metadata_extraction_receipt_sha256'] == '6640a20608b858eec974adb5d190ef8de1d13ef71a1d9b91132927a6be5bffff'
    assert extraction['status'] == 'PASS_EXACT192_ADJACENT_DESCRIPTORS_RETAINED_METADATA_ONLY'
    assert extraction['descriptor_count'] == 192 and extraction['missing_metadata_ranges'] == []
    assert source['code_and_metadata_pins'] == extraction['code_and_metadata_pins']
    for name, pin in source['code_and_metadata_pins'].items():
        path = ROOT / name
        assert path.suffix not in ['.h5', '.hdf5', '.npz', '.npy']
        raw = path.read_bytes()
        assert len(raw) == pin['bytes'] and digest(raw) == pin['sha256']
    assert source['scan_order'] == SCANS and source['native_chunk_indices'] == [170, 172]
    assert source['native_chunk_channels'] == COUNT and source['rows_per_scan'] == 16
    assert (source['fch1_hz'], source['df_hz'], source['tsamp_s']) == (2802832031.25, -2.7939677238464355, 18.253611008)
    v1_raw = (base / 'source_manifest.json').read_bytes()
    assert digest(v1_raw) == '3606432138fcc0f04676c7e6953e487d5f01fa2c485b715d9d97f59d99dd25a1'
    v1 = json.loads(v1_raw)
    results, totals, ranges = [], {}, {label: [] for label in SCANS}
    descriptors = node_occurrences = 0
    for native in [170, 172]:
        band = source['by_native_chunk'][str(native)]
        c0 = native * COUNT
        assert band['native_chunk_index'] == native
        assert band['physical_channel_interval_half_open'] == [c0, c0 + COUNT]
        frequencies = sorted([(source['fch1_hz'] + source['df_hz'] * c0) / 1e6,
                              (source['fch1_hz'] + source['df_hz'] * (c0 + COUNT - 1)) / 1e6])
        assert band['frequency_center_limits_MHz'] == frequencies
        assert [s['label'] for s in band['sources']] == SCANS
        total = 0
        for idx, item in enumerate(band['sources']):
            prior = old['sources'][idx]
            header, attrs = item['current_header'], item['current_header']['data_attributes']
            assert item['role'] == ('on' if idx % 2 == 0 else 'off')
            changed = {'chunks', 'future_spectral_payload_bytes', 'metadata_map_receipt_path',
                       'metadata_map_receipt_sha256', 'original171_metadata_map_receipt_path',
                       'original171_metadata_map_receipt_sha256', 'metadata_mapping_method'}
            assert all(item[k] == prior[k] for k in item if k not in changed)
            assert item['original171_metadata_map_receipt_path'] == prior['metadata_map_receipt_path']
            assert item['original171_metadata_map_receipt_sha256'] == prior['metadata_map_receipt_sha256']
            assert Path(item['metadata_map_receipt_path']) == extraction_path
            assert item['metadata_map_receipt_sha256'] == digest(extraction_raw)
            assert item['metadata_mapping_method'] == 'OFFLINE_PURE_TREE_LOOKUP_FROM_AUTHENTICATED_RETAINED_NODES'
            assert header['dataset_shape'] == [16, 1, 343 * COUNT]
            assert header['dataset_chunks'] == [1, 1, COUNT]
            assert header['dataset_dtype'] == 'float32' and header['dtype_exact'] == item['dtype_exact'] == '<f4'
            assert attrs['nchans'] == 343 * COUNT and attrs['nifs'] == 1 and attrs['nbits'] == 32
            assert attrs['fch1'] * 1e6 == source['fch1_hz'] and attrs['foff'] * 1e6 == source['df_hz']
            assert attrs['tsamp'] == source['tsamp_s']
            assert item['frequency_axis_order'] == 'descending'
            assert item['physical_dataset_axis_order'] == ['time', 'feed', 'frequency']
            assert item['chunks'] == v1['by_native_chunk'][str(native)]['sources'][idx]['chunks']
            assert len(item['chunks']) == 16 and [c['time_row'] for c in item['chunks']] == list(range(16))
            payload = 0
            for row, chunk in enumerate(item['chunks']):
                assert chunk['chunk_origin'] == [row, 0, c0]
                assert chunk['filter_mask'] == 0 and chunk['decoded_size'] == 4 * COUNT
                start, size = chunk['byte_offset'], chunk['stored_size']
                assert 0 < start <= item['source_file_bytes'] - size and 0 < size <= 4 * COUNT
                assert chunk['byte_range'] == f'bytes={start}-{start + size - 1}'
                assert chunk['spectral_payload_fetched'] is False
                target = (row, 0, c0, 0)
                traversal = chunk['traversal']
                assert [v['level'] for v in traversal] == [2, 1, 0]
                for j, node_pin in enumerate(traversal):
                    metadata = (ROOT / node_pin['retained_metadata_path']).read_bytes()
                    offset = node_pin['offset_in_retained_metadata']
                    node = metadata[offset:offset + 3136]
                    assert len(node) == 3136 and digest(node) == node_pin['sha256']
                    level, keys, coords, children = parse(node, node_pin['address'], item['source_file_bytes'])
                    assert level == node_pin['level']
                    choices = [i for i in range(len(children)) if coords[i] <= target < coords[i + 1]]
                    assert len(choices) == 1
                    i = choices[0]
                    if j < 2:
                        assert children[i] == traversal[j + 1]['address']
                    else:
                        assert coords[i] == target and keys[i][:2] == (size, 0) and children[i] == start
                    node_occurrences += 1
                ranges[item['label']].append((start, start + size, native, row))
                payload += size
                descriptors += 1
            assert item['future_spectral_payload_bytes'] == payload
            total += payload
            results.append({'native_chunk_index': native, 'scan_id': item['label'], 'payload_bytes': payload,
                            'rows': 16, 'source_channel0': c0})
        assert band['total_future_spectral_payload_bytes'] == total
        totals[str(native)] = total
    for label, entries in ranges.items():
        entries.sort()
        assert all(a[1] <= b[0] for a, b in zip(entries, entries[1:]))
        prior = next(s for s in old['sources'] if s['label'] == label)
        assert all(not (a < c['byte_offset'] + c['stored_size'] and c['byte_offset'] < b)
                   for a, b, _, _ in entries for c in prior['chunks'])
    assert sum(totals.values()) == source['total_future_spectral_payload_bytes'] == extraction['exact_future_payload_bytes'] == 597792529
    assert source['decoded_complete_chunk_bytes'] == 192 * COUNT * 4 == 805306368
    assert source['spectral_values_read'] is source['spectral_payload_fetched'] is False
    assert source['new_metadata_HTTP_requests'] == source['new_power_HTTP_requests'] == 0
    receipt = {'status': 'PASS_V2_SOURCE_METADATA_STATIC_AND_RETAINED_TREE_ONLY_NO_VALUES',
               'source_path': source_path.relative_to(ROOT).as_posix(), 'source_sha256': digest(source_raw),
               'metadata_receipt_sha256': digest(extraction_raw),
               'mapper_v2_sha256': digest((base / 'map_retained_metadata_v2.py').read_bytes()),
               'review_code_sha256': digest(Path(__file__).read_bytes()), 'descriptors_checked': descriptors,
               'tree_node_occurrences_reparsed': node_occurrences, 'code_and_metadata_pins_checked': len(source['code_and_metadata_pins']),
               'native_payload_bytes': totals, 'source_rows': results, 'total_payload_bytes': sum(totals.values()),
               'decoded_complete_chunk_bytes': source['decoded_complete_chunk_bytes'],
               'all_new_ranges_mutually_disjoint_and_disjoint_from_prior171': True,
               'all_source_file_headers_and_identities_match_original_actual_headers': True,
               'v1_source_preserved_and_exact192_chunk_descriptors_unchanged': True,
               'all12_stale_per_source_totals_corrected': True,
               'all12_adjacent_mapping_receipts_distinguished_from_original171_inputs': True,
               'mapper_review': 'V2 recomputes each source total after offline pure TREE traversal. Exact row/feed/native-origin matches, source bounds, filter masks, node levels, overlap consistency, and old171 disjointness are required. No HTTP or numerical power package is imported.',
               'blockers': [], 'new_HTTP_requests': 0, 'HDF5_NPZ_power_reads': 0,
               'detector_or_science_runs': 0, 'not_an_acquisition_or_science_QA_pass': True}
    output = HERE / 'SOURCE_METADATA_V2_STATIC_REVIEW.json'
    with output.open('x') as handle:
        json.dump(receipt, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'status': receipt['status'], 'receipt_path': str(output),
                      'receipt_sha256': digest(output.read_bytes())}))


if __name__ == '__main__':
    main()
