"""Non-scientific deterministic format fixture. No detector or RNG imports."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import time

from payload_store import (digest_file, semantic_digest, validate, verify_bundle,
                           write_bundle)


def record(i):
    scan, rem = divmod(i, 4096 * 5)
    carrier, rank = divmod(rem, 5)
    start = 2 * (i % 7)
    off = []
    for j in range(3):
        witness = {
            'ON_drift_grid_index': 2861 + rank, 'OFF_drift_grid_index': 2861 + rank,
            'ON_drift_hz_s': -0.0, 'OFF_drift_hz_s': 0.0,
            'ON_first_endpoint_error_channels': 0.125,
            'ON_last_endpoint_error_channels': -0.125,
            'ON_first_endpoint_error_hz_audit': 0.25,
            'ON_last_endpoint_error_hz_audit': -0.25,
            'endpoint_tolerance_hz_audit': 8.5,
            'endpoint_tolerance_channels': 4.25,
            'ON_first_endpoint_time_from_tref_s': -900.0 + start * 18.0,
            'ON_last_endpoint_time_from_tref_s': -846.0 + start * 18.0,
            'OFF_inventory_index': carrier * 5 + rank,
            'OFF_reference_carrier_index': carrier,
            'OFF_reference_source_channel': 1000000 + carrier,
            'OFF_width_channels': (1, 3, 9, 33)[rank % 4],
            'OFF_window_start': start, 'OFF_score': 8.0 + (i % 13) / 10,
            'OFF_native4_centers': [1000000 + carrier + k for k in range(4)]}
        off.append({'scan_id': f'FORMAT_OFF{j}', 'veto': i % 3 != 0,
                    'inventory_exhausted_before_query': True,
                    'all_threshold_records_compatibility_checked': i % 3 == 0,
                    'checked_alias_pairs': 100 + rank,
                    'witness': witness if i % 3 != 0 else None,
                    'inventory_sha256': hashlib.sha256(f'FORMAT_ONLY_{j}'.encode()).hexdigest(),
                    'inventory_rows': 2000000})
    return {'scan_id': f'FORMAT_ON{scan}', 'role': 'ON',
            'reference_carrier_index': carrier, 'reference_source_channel': 1000000 + carrier,
            'hit_id': f'FORMAT_ON{scan}:carrier{carrier:04d}:rank{rank+1}',
            'retained_rank': rank + 1, 'width_channels': (1, 3, 9, 33)[rank % 4],
            'window_start': start, 'window_source_rows': list(range(start, start + 4)),
            'window_start_row': start, 'representative_drift_grid_index': 2861 + rank,
            'representative_drift_hz_s': -0.0, 'drift_alias_first_index': 2800 + rank,
            'drift_alias_last_index': 2900 + rank,
            'native4_centers': [1000000 + carrier + k for k in range(4)],
            'ON_score': 10.0 + (i % 31) / 10, 'physical_drift_not_unique': True,
            'OFF_comparisons': off,
            'disposition': 'FORMAT_VETO' if i % 3 != 0 else 'FORMAT_UNRESOLVED'}


def edges():
    return {'negative_zero': -0.0, 'positive_zero': 0.0,
            'float64': float.fromhex('0x1.0000000000001p+0'),
            'min_int64': -(1 << 63), 'max_uint64': (1 << 64) - 1,
            'unicode': 'ÆØÅ — kontrol 星', 'empty_map': {}, 'empty_list': [],
            'true': True, 'false': False, 'null': None,
            'descriptor_lookalike': {'array_descriptor': {'npz_key': 'unmodified'}}}


def metadata(count):
    return {'schema': 'ENGINEERING_DENSE_FORMAT_FIXTURE_V1',
            'science_or_telescope_data': False, 'edges': edges(),
            'all_ON_threshold_hypotheses': [record(i) for i in range(count)],
            'declared_records': count, 'all_fields_and_orders_retained': True}


def legacy_json_stats(value):
    h = hashlib.sha256()
    count = 0
    for block in json.JSONEncoder(indent=2, sort_keys=True, allow_nan=False,
                                  ensure_ascii=True).iterencode(value):
        data = block.encode('utf-8'); h.update(data); count += len(data)
    h.update(b'\n'); count += 1
    return {'bytes': count, 'sha256': h.hexdigest()}


def same(actual, expected):
    if type(actual) is not type(expected):
        raise ValueError('Decoded type differs')
    if type(expected) is float:
        if struct.pack('>d', actual) != struct.pack('>d', expected):
            raise ValueError('Decoded binary64 bits differ')
    elif type(expected) is dict:
        if list(actual) != list(expected):
            raise ValueError('Decoded dictionary keys/order differ')
        for key in expected: same(actual[key], expected[key])
    elif type(expected) is list:
        if len(actual) != len(expected): raise ValueError('Decoded list length differs')
        for a, b in zip(actual, expected): same(a, b)
    elif actual != expected:
        raise ValueError('Decoded primitive differs')


def main():
    action, request_file = sys.argv[1:]
    request = json.loads(Path(request_file).read_text())
    if request['mode'] != 'ENGINEERING_FIXTURES_ONLY':
        raise ValueError('No science admission')
    source = Path(__file__).resolve().parent
    for name, pin in request['code_sha256'].items():
        if digest_file(source / name) != pin: raise ValueError('Source pin differs')
    folder, payload = Path(request['job_root']), Path(request['payload'])
    if action == 'produce':
        start = time.process_time()
        value = metadata(request['records'])
        validate(value)
        construction_CPU = time.process_time() - start
        before = time.process_time(); legacy = legacy_json_stats(value)
        legacy_CPU = time.process_time() - before
        asset = folder / 'OPAQUE_SOURCE.bin'
        asset.write_bytes(bytes(range(256)) * 4096)  # Exactly 1MiB, no RNG.
        before = time.process_time()
        receipt = write_bundle(payload, value, {'OPAQUE_ASSET.bin': asset}, request['payload_cap_bytes'])
        packed_CPU = time.process_time() - before
        stats = {'fixture_records': request['records'], 'OFF_receipts': request['records'] * 3,
                 'input_semantic_sha256': semantic_digest(value),
                 'legacy_indent2_sorted_JSON': legacy, 'legacy_serialization_CPU_s': legacy_CPU,
                 'construct_CPU_s': construction_CPU, 'pack_and_hash_and_write_CPU_s': packed_CPU,
                 'payload': receipt, 'opaque_source_sha256': digest_file(asset),
                 'array_numerics_or_scientific_search_run': False}
        (folder / 'PRODUCER_METRICS.json').write_text(json.dumps(stats, indent=2) + '\n')
        if request.get('fault') == 'tamper':
            with (payload / 'output.msgpack.gz').open('r+b') as out:
                out.seek(20); raw = out.read(1); out.seek(20); out.write(bytes([raw[0] ^ 1]))
        if request.get('fault') == 'CPU_after_payload':
            while True: pass
    elif action == 'verify':
        value, receipt = verify_bundle(payload, cap=request['payload_cap_bytes'])
        rows = value['all_ON_threshold_hypotheses']
        if len(rows) != request['records']: raise ValueError('Record census differs')
        same(value['edges'], edges())
        # Independently reconstruct one tiny expected record at a time: no second
        # full object tree, and exact values/order/binary64 checked for EVERY row.
        for i, row in enumerate(rows): same(row, record(i))
        metrics = json.loads((folder / 'PRODUCER_METRICS.json').read_text())
        if receipt['semantic_sha256'] != metrics['input_semantic_sha256']:
            raise ValueError('Input/decoded semantic digest differs')
        if legacy_json_stats(value) != metrics['legacy_indent2_sorted_JSON']:
            raise ValueError('Decoded canonical legacy JSON differs')
        if digest_file(payload / 'OPAQUE_ASSET.bin') != metrics['opaque_source_sha256']:
            raise ValueError('Opaque asset bytes differ')
        receipt.update(fixture_all_records_checked=len(rows),
                       fixture_OFF_receipts_checked=sum(len(row['OFF_comparisons']) for row in rows),
                       exact_fixture_comparison_including_binary64=True,
                       verified_file_inventory={p.name: {'bytes': p.stat().st_size, 'sha256': digest_file(p)}
                                                for p in payload.iterdir() if p.is_file()})
        (folder / 'VERIFICATION.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    else:
        raise ValueError('Unknown engineering action')


if __name__ == '__main__': main()
