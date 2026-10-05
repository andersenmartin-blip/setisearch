"""Caller-only repository-source/readiness check; no genuine gate invocation."""
import hashlib
import json
from pathlib import Path
import stat

REPO = Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004')
NS = REPO / 'results_radio_runtime_bootstrap_preparation_20261005a'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(REPO)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())


def main():
    freeze = REPO / 'config/radio_runtime_bootstrap_20261005a.freeze.json'
    contract = json.loads(freeze.read_bytes())
    reviews = [NS / 'preparation-independent-review.json', NS / 'headroom-review.json']
    review_data = [json.loads(path.read_bytes()) for path in reviews]
    if any('NO_BLOCKING' not in str(obj.get('verdict', obj.get('status', ''))) for obj in review_data):
        raise ValueError('independent preparation/headroom verdict not ready')
    checked = []
    for source in contract['source_pins']:
        path = Path(source['path'])
        if not path.is_relative_to(REPO):
            raise ValueError('caller source validation is repository-only')
        item = path.lstat()
        raw = path.read_bytes()
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1 or len(raw) != source['bytes'] or hashlib.sha256(raw).hexdigest() != source['sha256'] or '%04o' % stat.S_IMODE(item.st_mode) != source['mode']:
            raise ValueError('selected preparation source changed: ' + str(path))
        checked.append(pin(path))
    marker = REPO / 'config/radio_runtime_bootstrap_20261005a.activate.json'
    if marker.exists():
        raise ValueError('activation must remain absent at this inert checkpoint')
    report = dict(schema='radio-runtime-package-bootstrap-caller-readiness-v1',
        status='READY_FOR_PREPARATION_PUBLICATION_ONLY', bootstrap_identity=contract['bootstrap_identity'],
        freeze=pin(freeze), independent_reviews=[pin(path) for path in reviews],
        all_repository_source_pins_equal=True, selected_repository_source_files=len(checked),
        selected_repository_source_bytes=sum(row['bytes'] for row in checked), source_files=checked,
        runtime_original_files_read_here=0, genuine_bootstrap_invocations=0, genuine_installer_invocations=0,
        activation_exists=False, allocation_created=False, scientific_authority=False, all_eleven_fields_pending=True,
        scientific_certificate_issued=False, selected_engineering_before=dict(seconds=1030, MiB=56),
        selected_engineering_only_after_distinct_activation=dict(seconds=1330, MiB=1592),
        final_producer_checks=dict(wheel_io=55, pure_builder=22, supervisor=83, total=160),
        full_immutable_preparation_readback_required=True, marker_only_activation_readback_required=True,
        detached_full_source_proof_external_raw_pin_required=True, genuine_single_invocation_required=True,
        no_retry_even_pre_spent_refusal=True, caller_stdout_stderr_exclusive_creation_required=True,
        execution_session_must_remain_awaited_until_terminal_result=True,
        old_scopes_rearmed=False, holdouts_opened=False, consolidation_date='2026-10-09')
    path = NS / 'READINESS.json'
    with path.open('xb') as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k!='source_files'}, sort_keys=True))


if __name__ == '__main__':
    main()
