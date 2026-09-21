#!/usr/bin/env python3
"""Transfer pinned LS8K acquisition/scoring functions to the frozen GJ 436 pair."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import ls8k_l2_screen as implementation
from seti_repeater.cheops_url_timeout import resolve_url

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'results_ls8w_l2_metadata'
OUT = ROOT / 'results_ls8w_l2_screen'
KEYS = ['CH_PR100041_TG000302_V0300', 'CH_PR100041_TG001301_V0300']


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--freeze', required=True)
    args = parser.parse_args()
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == args.freeze
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT)
    assert not OUT.exists(), 'refuse LS8W output overwrite'
    cfg = json.loads((ROOT / 'config/ls8w_l2_scope.json').read_text())
    for relative, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    for line in (META / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        assert hashlib.sha256((META / relative).read_bytes()).hexdigest() == digest, relative
    metadata = json.loads((META / 'summary.json').read_text())
    assert metadata['status'] == 'PASS_COMPATIBLE' and metadata['table_data_bytes_acquired'] == 0
    assert metadata['selected_keys'] == KEYS == cfg['selected_keys']
    assert metadata['products'] == cfg['products'], 'source metadata differs from frozen scope'
    assert sum(p['table_bytes_declared'] for p in metadata['products']) == cfg['total_table_bytes']
    assert (implementation.SIDE, implementation.GUARD, implementation.DURATIONS, implementation.SCREEN) == (12, 2, (1, 2, 3), 8.5)
    implementation.META = META; implementation.OUT = OUT; implementation.KEYS = KEYS
    OUT.mkdir()
    attempts = []
    original_resolver = implementation.get_url
    def record(entry):
        attempts.append(entry)
        implementation.save(OUT / 'transport_attempts.json', attempts)
    def bounded_resolver(key):
        return resolve_url(key, original_resolver, record)
    implementation.get_url = bounded_resolver
    by_key = {p['file_key']: p for p in metadata['products']}
    results = [implementation.evaluate_visit(key, by_key[key]) for key in KEYS]
    summary = {'stage': 'LS8W_GJ436_TWO_VISIT_L2_SCREEN', 'status': 'COMPLETE_UNAUDITED',
        'evaluation_freeze_commit': args.freeze, 'target': 'GJ 436', 'selected_keys': KEYS,
        'method': 'unchanged pinned LS8K flux-centered DEFAULT-L2 scorer and signed clustering',
        'sideband_rows_each_side': 12, 'guard_rows': 2, 'durations_rows': [1, 2, 3], 'screen_threshold': 8.5,
        'visits': results,
        'totals': {**{name: sum(r[name] for r in results) for name in
            ['rows', 'eligible_windows', 'positive_windows', 'negative_windows', 'positive_clusters', 'negative_clusters']},
            'science_table_bytes': sum(p['table_bytes_declared'] for p in metadata['products'])},
        'other_apertures_opened': False, 'image_bytes_acquired': 0, 'raw_imagettes_opened': False,
        'detector_qualified': False, 'candidate_claims': 0,
        'interpretation': 'Independent rank-6 two-visit L2 screen; signed endpoints are not Gaussian significances.'}
    implementation.save(OUT / 'summary.json', summary)
    implementation.manifest()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
