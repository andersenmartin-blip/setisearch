#!/usr/bin/env python3
"""Independent raw-struct/scalar audit; never imports the suite producer."""
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from ls8a_l2_audit import ROW, parse, score

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'results_ls8b_l2_metadata'
OUT = ROOT / 'results_ls8b_l2_suite'
KEYS = [f'CH_PR100006_TG00030{i}_V0300' for i in range(2, 6)]


def load(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def manifest(directory, write=False):
    if write:
        (directory / 'SHA256SUMS').write_text(''.join(
            f'{sha(p.read_bytes())}  {p.relative_to(directory)}\n' for p in sorted(directory.rglob('*'))
            if p.is_file() and p.name != 'SHA256SUMS'))
    else:
        for line in (directory / 'SHA256SUMS').read_text().splitlines():
            expected, name = line.split('  ', 1)
            assert sha((directory / name).read_bytes()) == expected, name


def groups(rows, sign):
    selected = sorted((r for r in rows if sign * r['score'] >= 8.5),
                      key=lambda r: (r['start'], r['start'] + r['duration']))
    result = []
    for row in selected:
        end = row['start'] + row['duration'] - 1
        if not result or row['start'] > result[-1]['end'] + 1:
            result.append({'start': row['start'], 'end': end, 'members': [row]})
        else:
            result[-1]['end'] = max(result[-1]['end'], end)
            result[-1]['members'].append(row)
    for group in result:
        group['representative'] = min(group['members'], key=lambda r: (-sign * r['score'], r['duration'], r['start']))
    return result


def audit():
    assert sha((ROOT / 'scripts/ls8a_l2_audit.py').read_bytes()) == \
        'd98ab8c538b1287d8bae45ba8d4f011bc37b82901197a5346c8c871babb6c736'
    manifest(META)
    manifest(OUT)
    suite = load(OUT / 'summary.json')
    assert [s['file_key'] for s in suite['visits']] == KEYS
    assert suite['screen_threshold'] == 8.5 and suite['image_bytes_acquired'] == 0
    assert suite['other_apertures_opened'] is False and suite['detector_qualified'] is False
    assert suite['candidate_claims'] == 0
    all_audits = []
    original_columns = load(ROOT / 'results_ls8a_l2_metadata/summary.json')['columns']
    expected_schema = [(c['name'], c['format']) for c in original_columns]
    for key, suite_summary in zip(KEYS, suite['visits']):
        directory = OUT / key
        meta = load(META / key / 'summary.json')
        assert [(c['name'], c['format']) for c in meta['columns']] == expected_schema
        raw = (directory / 'lightcurve_table.bin').read_bytes()
        source = load(directory / 'source.json')
        assert source['sha256'] == sha(raw)
        assert len(raw) == meta['table_bytes_declared'] == meta['rows'] * ROW.size
        assert source['start'] == meta['table_data_start'] and source['count'] == len(raw)
        assert source['status'] == 206
        assert source['content_range'] == f'bytes {source["start"]}-{source["start"]+len(raw)-1}/{meta["total"]}'
        for field in ['total', 'etag', 'content_disposition']:
            assert source[field] == meta[field]
        data = parse(raw)
        cadence = float(meta['keywords']['TEXPTIME'])
        rebuilt = []
        attempted = 0
        for duration in (1, 2, 3):
            for start in range(len(data['flux']) - duration + 1):
                attempted += 1
                row = score(data, start, duration, cadence)
                if row is not None:
                    rebuilt.append({'start': start, 'duration': duration, **row})
        saved = [json.loads(line) for line in gzip.decompress((directory / 'ledger.jsonl.gz').read_bytes()).splitlines()]
        assert [(r['start'], r['duration']) for r in rebuilt] == [(r['start'], r['duration']) for r in saved]
        comparisons = 0
        differences = {'score': 0., 'excess': 0., 'sigma': 0., 'denom': 0.}
        for rebuilt_row, saved_row in zip(rebuilt, saved):
            for field, saved_field in [('score', 'score'), ('excess', 'excess_electrons'),
                                       ('sigma', 'sigma_electrons'), ('denom', 'denominator_electrons')]:
                a, b = rebuilt_row[field], saved_row[saved_field]
                differences[field] = max(differences[field], abs(a-b))
                assert math.isclose(a, b, rel_tol=2e-8, abs_tol=2e-10), (key, field, a, b)
                comparisons += 1
            start, duration = rebuilt_row['start'], rebuilt_row['duration']
            indices = list(range(start, start + duration))
            assert saved_row['event_indices'] == indices
            assert (saved_row['context_start'], saved_row['context_stop']) == (start-14, start+duration+14)
            assert saved_row['event_or'] == rebuilt_row['event_or']
            assert saved_row['context_event_or'] == int(np.bitwise_or.reduce(data['event'][start-14:start+duration+14]))
            assert saved_row['bjd_mid'] == float(np.mean(data['bjd'][indices]))
            comparisons += 5
        summary = load(directory / 'summary.json')
        assert summary == suite_summary
        assert summary['rows'] == len(data['flux']) and summary['cadence_seconds'] == cadence
        assert summary['eligible_windows'] == len(rebuilt)
        signed_groups = load(directory / 'clusters.json')
        for sign, label in [(1, 'positive'), (-1, 'negative')]:
            actual = groups(rebuilt, sign)
            published = signed_groups[label]
            assert summary[label + '_windows'] == sum(sign*r['score'] >= 8.5 for r in rebuilt)
            assert summary[label + '_clusters'] == len(actual) == len(published)
            for index, (group, published_group) in enumerate(zip(actual, published)):
                assert published_group['cluster_id'] == index
                assert (published_group['min_start'], published_group['max_end']) == (group['start'], group['end'])
                for field in ['start', 'duration']:
                    assert group['representative'][field] == published_group['representative'][field]
                assert [(r['start'], r['duration']) for r in group['members']] == [
                    (r['start'], r['duration']) for r in published_group['members']]
                for a, b in zip(group['members'], published_group['members']):
                    assert math.isclose(a['score'], b['score'], rel_tol=2e-8, abs_tol=2e-10)
                assert math.isclose(group['representative']['score'], published_group['representative']['score'],
                                    rel_tol=2e-8, abs_tol=2e-10)
        union = {i for r in rebuilt for i in range(r['start'], r['start']+r['duration'])}
        assert summary['unique_event_rows'] == len(union)
        assert summary['eligible_event_row_union_seconds'] == len(union) * cadence
        for field, operation in [('maximum_score', max), ('minimum_score', min)]:
            expected = operation((r['score'] for r in rebuilt), default=None)
            if expected is None:
                assert summary[field] is None
            else:
                assert math.isclose(summary[field], expected, rel_tol=2e-8, abs_tol=2e-10)
        assert [d['duration_rows'] for d in summary['duration_results']] == [1, 2, 3]
        for d in summary['duration_results']:
            subset = [r for r in rebuilt if r['duration'] == d['duration_rows']]
            assert d['eligible_windows'] == len(subset)
            assert d['duration_seconds'] == d['duration_rows'] * cadence
            assert d['positive_windows'] == sum(r['score'] >= 8.5 for r in subset)
            assert d['negative_windows'] == sum(r['score'] <= -8.5 for r in subset)
        all_audits.append({'file_key': key, 'status': 'PASS', 'raw_rows': len(data['flux']),
                           'enumerated_windows': attempted, 'eligible_windows': len(rebuilt),
                           'numeric_and_discrete_window_comparisons': comparisons,
                           'maximum_absolute_differences': differences,
                           'all_signed_clusters_counts_unions_and_summaries_verified': True})
    result = {'status': 'PASS', 'method': 'Unchanged LS8A struct parser and scalar normal equations; independent signed clustering.',
              'visits': all_audits, 'numeric_and_discrete_window_comparisons': sum(
                  a['numeric_and_discrete_window_comparisons'] for a in all_audits)}
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    suite['status'] = 'COMPLETE_AUDITED'
    (OUT / 'summary.json').write_text(json.dumps(suite, indent=2) + '\n')
    manifest(OUT, write=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    audit()
