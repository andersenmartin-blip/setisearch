"""Inventory staged result publication and verify frozen earlier engineering inputs.

Administrative byte reads only. Never calls the bootstrap, pip, or package code.
The result inventory excludes itself to avoid a circular content hash.
"""
from pathlib import Path
import hashlib
import json
import stat
import subprocess

BASE = Path('/workspace/scratch/d804553c0e89')
REPO = BASE / 'setisearch-status-20261004'
NS = 'results_radio_runtime_bootstrap_preparation_20261005a'
E_COMMIT = 'c1ff02e8da9dae07b5711595df6d57fd7857e67c'
E_TREE = '6023d788555862b9616298dfb2eef44817ef5faa'
INVENTORY = 'RADIO_RUNTIME_PACKAGE_BOOTSTRAP_2026-10-05A_RESULT_INVENTORY.json'
STATUS = {'PROJECT_STATUS.md', 'PROJECT_DIRECTION.md',
          'RADIO_TWO_WEEK_PLAN_2026-09-26.md', 'RADIO_PILOT_INTERIM_2026-10-03.md'}
ALLOWED = STATUS | {'RADIO_RUNTIME_PACKAGE_BOOTSTRAP_2026-10-05A_RESULT.md', INVENTORY}


def row(path):
    file = REPO / path
    before = file.stat(follow_symlinks=False)
    assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    raw = file.read_bytes()
    after = file.stat(follow_symlinks=False)
    assert (before.st_dev, before.st_ino, before.st_mode, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns) == (
            after.st_dev, after.st_ino, after.st_mode, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns)
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
                mode='100755' if stat.S_IMODE(before.st_mode) & 0o111 else '100644')


def main():
    frozen = []
    for phase in ('bootstrap-a-preparation', 'bootstrap-a-activation'):
        meta = json.loads((BASE / (phase + '-meta.json')).read_bytes())
        for original in meta['files']:
            observed = row(original['path'])
            assert all(observed[key] == original[key] for key in observed), original['path']
        frozen.append(dict(phase=phase, files=meta['file_count'], bytes=meta['bytes'],
                           full_local_bytes_and_modes_unchanged=True))
    diff = subprocess.run(['git', 'diff', '--cached', '--name-status', E_TREE],
                          cwd=REPO, capture_output=True, text=True, check=True)
    rows = []
    for line in diff.stdout.splitlines():
        change, path = line.split('\t')
        assert change in ('A', 'M') and (path.startswith(NS + '/') or path in ALLOWED)
        assert change == ('M' if path in STATUS else 'A'), (change, path)
        if path == INVENTORY:
            continue
        rows.append(dict(status=change, **row(path)))
    report = json.loads((REPO / NS / 'actual-independent-review.json').read_bytes())
    prior = json.loads((REPO / NS / 'administrative/prior-scope-preservation.json').read_bytes())
    receipt = row(NS + '/administrative/invocation-receipt.json')
    obj = dict(schema='radio-runtime-package-bootstrap-result-inventory-v1',
               result_base_commit=E_COMMIT, result_base_tree=E_TREE,
               self_excluded_path=INVENTORY, files=rows, file_count=len(rows),
               bytes=sum(item['bytes'] for item in rows),
               frozen_earlier_publication_unchanged=frozen,
               semantic_status='CLOSED_FAILED', pip_invocations=0,
               actual_review_verdict=report.get('verdict', report.get('status')),
               prior_scope_preservation_verdict=prior.get('verdict', prior.get('status')),
               caller_receipt_pin=receipt, allocation_spent=True,
               new_engineering_allocation=dict(seconds=300, MiB=1536),
               selected_cumulative_engineering_allocation=dict(seconds=1330, MiB=1592),
               allocation_is_not_observed_measurement=True,
               scientific_authority=False, scientific_fields_all_pending=True,
               bootstrap_replay=False, automatic_successor=False)
    raw = (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
    (REPO / INVENTORY).write_bytes(raw)
    print(json.dumps(dict(file_count=len(rows), bytes=obj['bytes'],
                          inventory_bytes=len(raw), inventory_sha256=hashlib.sha256(raw).hexdigest(),
                          frozen_earlier_publication_unchanged=frozen), sort_keys=True))


if __name__ == '__main__':
    main()
