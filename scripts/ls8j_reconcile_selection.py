#!/usr/bin/env python3
"""Audit the frozen census and retain a separately dated full product inventory.

Original LS8J records are never replaced. This is metadata-only reconciliation,
not recovery of the discarded original browse responses.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results_ls8j_selection'
OUT = ROOT / 'results_ls8j_reconciliation'
SOURCE_COMMIT = '81692343a774b19d26c28dd9596ad1dd1a31ef01'
EXCLUDE = {'55cnc', 'gj876', 'gj514', 'gj849', 'gj649'}


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if hasattr(value, 'tolist'):
        return plain(value.tolist())
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, 'item'):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save(path, value):
    path.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(columns):
    lengths = {len(v) for v in columns.values()}
    assert len(lengths) == 1, 'ragged archive response'
    return [dict(zip(columns, values)) for values in zip(*columns.values())]


def normalize(name):
    return ''.join(c for c in str(name or '').lower() if c in 'abcdefghijklmnopqrstuvwxyz0123456789')


def independent_reasons(row):
    reasons = []
    key = str(row.get('file_key') or '')
    if not key.endswith('_V0300'): reasons.append('NOT_V0300')
    if str(row.get('data_pipe_version') or '') != '14.1.2': reasons.append('PIPE_NOT_14_1_2')
    if row.get('status_published') is not True: reasons.append('NOT_PUBLISHED')
    if row.get('db_lc_available') is not True: reasons.append('NO_PUBLIC_LC')
    if not str(row.get('obj_id_catname') or '').strip(): reasons.append('NO_TARGET_NAME')
    try:
        exposure = float(row.get('obs_exptime'))
        n = int(row.get('obs_nexp'))
        stacked = float(row.get('obs_total_exptime'))
        if not math.isfinite(exposure) or exposure <= 0: reasons.append('BAD_EXPTIME')
        if n <= 0: reasons.append('BAD_NEXP')
        if not math.isfinite(stacked) or not 0 < stacked <= 60: reasons.append('STACKED_EXPOSURE_OUTSIDE_BOUND')
    except (TypeError, ValueError, OverflowError):
        reasons.append('MISSING_EXPOSURE_METADATA')
    if not key: reasons.append('NO_FILE_KEY')
    if normalize(row.get('obj_id_catname')) in EXCLUDE: reasons.append('CLOSED_HOST')
    return reasons


def inventory_flags(columns):
    rows = table_rows(columns)
    types = sorted({str(r.get('file_ext') or '') for r in rows})
    default = any('SCI_COR_Lightcurve-DEFAULT' in str(r.get('file') or '')
                  and str(r.get('file') or '').endswith('_V0300.fits') for r in rows)
    return {'product_rows': len(rows), 'has_default_lightcurve': default,
            'has_cal_subarray': 'SCI_CAL_SubArray' in types,
            'has_cor_subarray': 'SCI_COR_SubArray' in types,
            'eligible': default and {'SCI_CAL_SubArray','SCI_COR_SubArray'}.issubset(types),
            'file_types': types}


def ranking(ledger):
    groups = defaultdict(list)
    for row in ledger:
        if row['eligible']:
            groups[normalize(row['obj_id_catname'])].append(row)
    order = []
    for name, visits in groups.items():
        visits = sorted(visits, key=lambda r: (float(r['date_mjd_start']), r['file_key']))
        if len(visits) >= 2:
            order.append({'normalized_target': name,
                          'archive_target_name': visits[0]['obj_id_catname'],
                          'eligible_visit_count': len(visits),
                          'first_mjd': float(visits[0]['date_mjd_start']),
                          'second_mjd': float(visits[1]['date_mjd_start']),
                          'eligible_file_keys': [v['file_key'] for v in visits],
                          'selected_visits': visits[:2]})
    order.sort(key=lambda c: (c['second_mjd'], c['first_mjd'], c['normalized_target']))
    return [dict(c, rank=i) for i, c in enumerate(order, 1)]


def audit_saved():
    # Pin actual public Git blob identities, independently of the stored manifest.
    pins = {'census.json': '796d47051f21f2e093c732ceede6ac6111f68a7a',
            'selection.json': '24b6ea87814358f9a6a78702c77db20365ad38a5'}
    for name, pin in pins.items():
        raw = (SOURCE / name).read_bytes()
        assert hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest() == pin
    census = json.loads((SOURCE / 'census.json').read_text())
    saved = json.loads((SOURCE / 'selection.json').read_text())
    raw_rows = table_rows(census['result'])
    assert len(raw_rows) == census['row_count'] == saved['census_rows'] == 1000
    assert all(r['status_published'] is True for r in raw_rows)
    starts = [r['date_mjd_start'] for r in raw_rows]
    assert all(math.isfinite(v) for v in starts) and starts == sorted(starts)
    by_key = {r['file_key']: r for r in raw_rows}
    assert len(by_key) == 1000 == saved['unique_file_keys']
    assert len(saved['visit_ledger']) == 1000
    assert [r['file_key'] for r in saved['visit_ledger']] == [
        r['file_key'] for r in sorted(raw_rows, key=lambda r: (r['date_mjd_start'], r['file_key']))]
    compared_fields = 0
    for row in saved['visit_ledger']:
        raw = by_key[row['file_key']]
        for field in ('file_key','visit_id','obs_id','obj_id_catname','date_mjd_start','date_mjd_end',
                      'data_pipe_version','data_arch_rev','obs_exptime','obs_nexp','obs_total_exptime',
                      'status_published','db_lc_available'):
            assert row[field] == raw[field], (row['file_key'], field)
            compared_fields += 1
        reasons = independent_reasons(raw)
        assert row['normalized_target'] == normalize(raw['obj_id_catname'])
        assert row['basic_eligible'] == (not reasons)
        if not reasons:
            flags = row['products']
            for field, reason in [('has_default_lightcurve','NO_DEFAULT_LIGHTCURVE_PRODUCT'),
                                  ('has_cal_subarray','NO_CAL_SUBARRAY'),('has_cor_subarray','NO_COR_SUBARRAY')]:
                if not flags[field]: reasons.append(reason)
        assert row['reasons'] == reasons
        assert row['eligible'] == (not reasons)
        compared_fields += 4
    cohorts = ranking(saved['visit_ledger'])
    assert cohorts == saved['eligible_cohorts']
    assert cohorts[0] == saved['selection']
    for name in ('science_product_bytes_read','fits_table_rows_read','lightcurve_values_read',
                 'image_pixels_read','product_download_calls'):
        assert saved[name] == 0
    report = {'status': 'PASS_CONDITIONAL_ON_SAVED_PRODUCT_SUMMARIES',
              'source_commit': SOURCE_COMMIT, 'census_rows': len(raw_rows),
              'metadata_field_checks': compared_fields,
              'basic_eligible_visits': sum(r['basic_eligible'] for r in saved['visit_ledger']),
              'eligible_visits': sum(r['eligible'] for r in saved['visit_ledger']),
              'ranked_cohorts': len(cohorts), 'all_rankings_equal': True,
              'selected_target': cohorts[0]['archive_target_name'],
              'selected_keys': [r['file_key'] for r in cohorts[0]['selected_visits']],
              'historical_limitation': 'Original full product responses were not retained; summaries alone cannot prove their filenames.',
              'census_sha256': digest(SOURCE/'census.json'),
              'selection_sha256': digest(SOURCE/'selection.json')}
    return report, saved


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--offline', action='store_true')
    args = p.parse_args()
    audit, saved = audit_saved()
    if args.offline:
        print(json.dumps(audit, indent=2)); return
    assert not OUT.exists(), 'refuse reconciliation overwrite'
    for line in (SOURCE/'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert digest(SOURCE/name) == expected, name
    OUT.mkdir(); (OUT/'products').mkdir()
    save(OUT/'saved_selection_audit.json', audit)
    from dace_query import DaceClass
    from dace_query.cheops import CheopsClass
    client = CheopsClass(DaceClass(dace_rc_config_path=Path('/dev/null')))
    disagreements = []
    fresh_ledger = []
    evidence = []
    queries = 0
    for row in saved['visit_ledger']:
        new = dict(row)
        new['reasons'] = independent_reasons(row)
        if row['basic_eligible']:
            key = row['file_key']
            response = plain(client.browse_products(filters={'file_key': {'equal': [key]}},
                                                    file_type='all', output_format='dict'))
            queries += 1
            path = OUT/'products'/f'{key}.json'
            save(path, {'file_key': key, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                        'kind': 'FRESH_METADATA_RESPONSE_NOT_ORIGINAL', 'result': response})
            flags = inventory_flags(response)
            if flags != row['products']:
                disagreements.append({'file_key': key, 'saved': row['products'], 'fresh': flags})
            new['products'] = flags
            for field, reason in [('has_default_lightcurve','NO_DEFAULT_LIGHTCURVE_PRODUCT'),
                                  ('has_cal_subarray','NO_CAL_SUBARRAY'),('has_cor_subarray','NO_COR_SUBARRAY')]:
                if not flags[field]: new['reasons'].append(reason)
            evidence.append({'file_key': key, 'path': str(path.relative_to(OUT)), 'sha256': digest(path),
                             'product_rows': flags['product_rows'], 'summary_equal': flags == row['products']})
            if queries % 50 == 0: print(f'Full metadata inventories retained: {queries}', flush=True)
        new['eligible'] = not new['reasons']
        fresh_ledger.append(new)
    cohorts = ranking(fresh_ledger)
    order_equal = cohorts == saved['eligible_cohorts']
    result = {'stage': 'LS8J_METADATA_RECONCILIATION',
              'status': 'PASS' if not disagreements and order_equal else 'FAIL',
              'source_commit': SOURCE_COMMIT, 'metadata_only': True,
              'historical_limitation_preserved': audit['historical_limitation'],
              'fresh_product_inventory_queries': queries, 'inventory_evidence': evidence,
              'disagreements': disagreements, 'complete_cohort_order_equal': order_equal,
              'visit_ledger': fresh_ledger, 'eligible_cohorts': cohorts,
              'selection': cohorts[0] if cohorts else None,
              'science_product_bytes_read': 0, 'fits_table_rows_read': 0,
              'lightcurve_values_read': 0, 'image_pixels_read': 0, 'product_download_calls': 0}
    save(OUT/'reconciliation.json', result)
    print(json.dumps({'status': result['status'], 'inventories': queries,
                      'changed_summaries': len(disagreements), 'complete_cohort_order_equal': order_equal,
                      'selected_target': None if not cohorts else cohorts[0]['archive_target_name'],
                      'science_product_bytes_read': 0}, indent=2))


if __name__ == '__main__':
    main()
