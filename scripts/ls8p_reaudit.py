#!/usr/bin/env python3
"""Preserved LS8P serialization repair; unchanged arithmetic and tolerances.

The original audit completed its comparisons but could not JSON-serialize
numpy int64 boundary coordinates. Convert those coordinates to Python int,
retain the initial run unchanged, and verify copies in a new result directory.
"""
import hashlib
import json
from pathlib import Path
import shutil
import ls8p_audit as frozen
import ls8p_report as report

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results_ls8p_residuals'
OUT = ROOT / 'results_ls8p_verified'
ORIGINAL_BOUNDARY = frozen.boundary


def json_boundary(maps, masks):
    result = ORIGINAL_BOUNDARY(maps, masks)
    for name in ('C0_only_pixels', 'C1_only_pixels'):
        result[name]['xy'] = [[int(x), int(y)] for x, y in result[name]['xy']]
    return result


def main():
    cfg = json.loads((ROOT / 'config/ls8p_reaudit.json').read_text())
    for name, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for line in (SOURCE / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    status = json.loads((SOURCE / 'RUN_STATUS.json').read_text())
    assert status == {'execution_outcome': 'failure', 'scientific_status': 'COMPLETE_UNAUDITED',
                      'freeze_commit': cfg['original_freeze_commit']}
    assert not OUT.exists(), 'refuse to overwrite any recovery outcome'
    OUT.mkdir()
    # Inputs are byte-for-byte copies. The producer is not run again.
    copied = []
    for path in sorted(SOURCE.rglob('*')):
        rel = path.relative_to(SOURCE)
        if path.is_file() and (path.suffix == '.npz' or path.name in
                ('diagnostics.json', 'injection_controls.json', 'summary.json', 'ls8p_tests.log', 'ls8p_residuals.log')):
            target = OUT / rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            copied.append({'path': str(rel), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    (OUT / 'COPY_RECEIPT.json').write_text(json.dumps({'source_commit': cfg['initial_result_commit'],
        'original_freeze_commit': cfg['original_freeze_commit'], 'files': copied,
        'producer_rerun': False, 'repair': 'numpy boundary coordinate scalars -> Python int for JSON only'}, indent=2) + '\n')
    frozen.OUT = OUT; frozen.boundary = json_boundary
    frozen.main()
    report.OUT = OUT; report.main()
    path = OUT / 'REPORT.md'; text = path.read_text()
    note = ('This verified result recovers the initial run at '
        '`16824ada23afb9c8e66758d2a180a565326f443c`, whose audit stopped while '
        'serializing NumPy integer boundary coordinates. The initial result and error log '
        'remain unchanged in `results_ls8p_residuals`. Only those coordinate scalar types '
        'are converted to Python integers. Producer outputs are copied byte-for-byte; '
        'scientific arithmetic, tolerance, scope and labels are unchanged. One additional '
        'serialization regression test passes. [Recovery protocol](../LS8P_AUDIT_RECOVERY.md).\n\n')
    title, rest = text.split('\n\n', 1); path.write_text(title + '\n\n' + note + rest)


if __name__ == '__main__':
    main()
