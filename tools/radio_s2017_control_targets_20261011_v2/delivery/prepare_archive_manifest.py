"""Root-executed byte manifest preparation after final report science PASS.

No archive production, numerical imports, data-array decoding or result
arithmetic. Preparation of this source does not execute its main function.
At its later authorized execution, NPZs are authenticated as opaque bytes
against the completed QA and writer inventories.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys

BASE = 'analysis/s2017_control_targets_20261011_v2'
BUILD = BASE + '/delivery/build_archive.py'
BUILD_SHA = '19da8e2b9bd0f82acc8b51a2f42fe675e8f900317c0037894153258ab0f56222'
PRIMARY_QA_SHA = '67c11a8d3d09a29e4d8dbdc2b22d1183e8a8bebcecf87f5100d7e46297f7cd45'
CONTEXT_QA_SHA = '37b8cb78bcfb93a5c2ae4c6bbc8553ca78c74ae1ef8c295eab29353c36fccec6'
REPORT_NAMES = ('SUMMARY.json', 'TOP60.csv', 'CORE_MAX753.csv', 'CONTEXT54.csv',
                'SETI_CONTROL_TARGETS_2026-10-11.md', 'SETI_CONTROL_TARGETS_2026-10-11.png')
FAILED_REPORT_SHA = 'ba55a26f0c9f82ee06f92ea45cf472e00319764aaad65660299c2688a5f6be11'
NEXT = {
    'continuation_20261011/metadata/control_target_adjacent_feasibility/NEXT_QUEUE_FEASIBILITY.json':
        '49a8e9998cd3b572cc5675579a703ede34d4772eb2f9febc0c6aa3f695e460ae',
    'continuation_20261011/metadata/control_target_adjacent_feasibility/SOURCE_ONLY_NOVELTY_AND_RAW_DURABILITY_PROOF.json':
        'e2cc9512715bd2c5898338edc230a3a80703085e641076f3efe4a1205f538d3a'}
PUBLIC_PY = {'driver.py', 'prepare_scope.py', 'launch_primary.py', 'context_profiles.py',
    'prepare_context_scope.py', 'qa_saved.py', 'qa_context.py', 'delivery/build_archive.py',
    'delivery/prepare_archive_manifest.py', 'delivery/make_report.py', 'delivery/make_report_prereview_v1.py',
    'delivery/make_report_prereview_v2.py', 'delivery/render_figure_v2.py'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--report-completion-sha256', required=True)
    parser.add_argument('--report-source-sha256', required=True)
    parser.add_argument('--renderer-source-sha256', required=True)
    parser.add_argument('--report-science-review-sha256', required=True)
    parser.add_argument('--report-science-review', default=BASE + '/review/REPORT_SCIENCE_REVIEW.json')
    parser.add_argument('--output', default=BASE + '/delivery/ARCHIVE_MANIFEST.json')
    parser.add_argument('--root-go-after-final-science-review', action='store_true', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    for value in (args.source_sha256, args.report_completion_sha256, args.report_source_sha256,
                  args.renderer_source_sha256, args.report_science_review_sha256):
        if not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('Exact closed SHA256 arguments required')
    def digest(path):
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024**2), b''):
                h.update(chunk)
        return h.hexdigest()
    if digest(Path(__file__).resolve()) != args.source_sha256 or digest(root / BUILD) != BUILD_SHA:
        raise ValueError('Reviewed manifest maker/frozen archive builder differs')
    spec = importlib.util.spec_from_file_location('closed_control_archive_metadata_helpers', root / BUILD)
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    spec.loader.exec_module(helper)  # Standard-library definitions only; never calls archive main.
    check = helper.check
    output = helper.confined(root, args.output)
    check(output.suffix == '.json' and args.root_go_after_final_science_review
          and not output.exists(), 'Root GO and create-only manifest required')
    resource.setrlimit(resource.RLIMIT_CPU, (180, 181))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    def deadline(signum, frame):
        raise TimeoutError('300s manifest wall bound')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(300)
    handles = []
    try:
        for name in ('ACTIVE_FAMILY_FLOCK.lock', 'delivery/MANIFEST_FLOCK.lock'):
            stream = (root / BASE / name).open('a+b')
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            handles.append(stream)
        members, expected = {}, {}
        def admissible(name):
            path = helper.confined(root, name)
            parts = path.relative_to(root).parts
            excluded = {args.output, BASE + '/delivery/ARCHIVE_MANIFEST.json', BASE + '/delivery/ARCHIVE_ROOT_GO.json'}
            return name not in excluded and path.suffix.lower() in ('.py', '.json', '.md', '.txt', '.csv', '.log', '.png', '.npz') \
                and not any(p in ('__pycache__', 'prior_preparation', 'private_helpers', 'private_helper') or p.startswith('.')
                            or 'private' in p.lower() for p in parts)
        def add(name, declared=None):
            check(admissible(name), 'Excluded source payload/cache/private/control-cycle member: ' + name)
            path = helper.confined(root, name)
            check(path.is_file() and not path.is_symlink(), 'Regular nonsymlink selected file required')
            if path.suffix.lower() == '.npz':
                check(name.startswith(BASE + '/results/'), 'Prior scientific NPZ payload excluded')
            actual = helper.pin(root, path)
            simple = {'bytes': actual['bytes'], 'sha256': actual['sha256']}
            if declared is not None:
                check(simple == declared, 'Existing scope/QA/output byte pin differs: ' + name)
            check(name not in expected or expected[name] == simple, 'Conflicting manifest evidence')
            expected[name], members[name] = simple, {'source_path': name, 'archive_path': name, **simple}
            return actual
        def metadata(name, sha=None):
            path = helper.confined(root, name)
            check(path.suffix == '.json', 'Metadata JSON only')
            raw = path.read_bytes()
            simple = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            check(sha is None or simple['sha256'] == sha, 'Exact actual metadata SHA differs: ' + name)
            add(name, simple)
            value = helper.parse_json(raw)
            return value
        qa = metadata(BASE + '/results/review/QA_RECEIPT.json', PRIMARY_QA_SHA)
        cq = metadata(BASE + '/results/context_review/QA_RECEIPT.json', CONTEXT_QA_SHA)
        failed_report = metadata(BASE + '/delivery/REPORT_RECEIPT.json', FAILED_REPORT_SHA)
        check(failed_report['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_REPORT_RECEIPT_V1'
              and failed_report['status'] == 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY'
              and failed_report['failure_type'] == 'TypeError', 'Original failed drawing receipt must remain preserved')
        report = metadata(BASE + '/delivery/REPORT_COMPLETION_RECEIPT.json', args.report_completion_sha256)
        review = metadata(args.report_science_review, args.report_science_review_sha256)
        check(report['schema'] == 'SETI_S2017_CONTROL_REPORT_FIGURE_REPAIR_COMPLETION_V1'
              and report['status'] == 'COMPLETE_SAVED_TEXT_REPORT_AND_REPAIRED_FIGURE'
              and report['output_base_directory'] == BASE + '/delivery'
              and report['output_byte_pin_keys'] == 'basenames'
              and report['actual_primary_QA_receipt_sha256'] == PRIMARY_QA_SHA
              and report['actual_context_QA_receipt_sha256'] == CONTEXT_QA_SHA
              and report['report_source_sha256'] == args.report_source_sha256
              and report['report_receipt_sha256'] == FAILED_REPORT_SHA
              and report['renderer_source_sha256'] == args.renderer_source_sha256,
              'Actual closed saved text report and additive repaired figure required')
        check(review['status'] == 'PASS_INDEPENDENT_CONTROL_TARGET_REPORT_SCIENCE_AND_FIGURE_WITH_LIMITATIONS'
              and review['report_completion_receipt_sha256'] == args.report_completion_sha256
              and review['report_receipt_sha256'] == FAILED_REPORT_SHA
              and review['report_source_sha256'] == args.report_source_sha256
              and review['renderer_source_sha256'] == args.renderer_source_sha256
              and review['actual_primary_QA_receipt_sha256'] == PRIMARY_QA_SHA
              and review['actual_context_QA_receipt_sha256'] == CONTEXT_QA_SHA,
              'Actual final independent report science PASS must bind this report and both QAs')
        producer = add(BASE + '/delivery/make_report.py')
        check(producer['sha256'] == args.report_source_sha256, 'Final report producer differs')
        check(add(BASE + '/delivery/render_figure_v2.py')['sha256'] == args.renderer_source_sha256,
              'Reviewed repair renderer differs')
        check(set(report['output_byte_pins']) == set(REPORT_NAMES), 'Six final report outputs required')
        for name, declared in report['output_byte_pins'].items():
            add(BASE + '/delivery/' + name, declared)
        for name, declared in report['input_byte_pins'].items():
            check(name in qa['input_byte_pins'] or name in cq['input_byte_pins']
                  or name.startswith(BASE + '/')
                  or name.startswith('continuation_20261011/execution/control_target_primary_v2/'),
                  'Unrecognized report input reference')
            if admissible(name):
                add(name, declared)
        provenance = metadata(BASE + '/delivery/REPORT_RENDER_FAILURE_PROVENANCE.json',
                              '31eba3ef24c983e1c96d8dababa6c8013ea4499b7f2d5bfc9732b47387bcb3d0')
        for name, declared in provenance['existing_file_pins'].items():
            add(name, declared)
        add(BASE + '/delivery/DATA_AVAILABILITY.md', {'bytes': 3275,
            'sha256': '51c04d71e3fd75a6279a988cfa626b47ab6dab2f80ecb8a69a20545cecec0ca7'})
        add(BASE + '/delivery/SETI_CONTROL_TARGETS_FINAL_2026-10-11.md', {'bytes': 7156,
            'sha256': 'c5950bf7aa6d7218a5ff288e255011d16e8862eadb1aa7fc5bfda30152fcaf31'})
        metadata(BASE + '/delivery/FINAL_REPORT_TEXT_EDIT_RECEIPT.json',
                 'e695844525694d01f33a49c40fba2464f9133c3b911581a350ebfde58ed26b92')
        # Union the complete immutable primary53 and context57 text-pin inventories.
        for scope_name in ('scope.json', 'context_scope.json'):
            scope = metadata(BASE + '/' + scope_name)
            for name, declared in scope['text_code_pins'].items():
                if isinstance(declared, str):
                    check(add(name)['sha256'] == declared, 'Context text pin differs')
                else:
                    add(name, declared)
        # Select all new-phase outputs, including the complete QA namespaces.
        admitted = {}
        for receipt in (qa, cq):
            for name, declared in receipt['input_byte_pins'].items():
                check(name not in admitted or admitted[name] == declared, 'Actual QA pins conflict')
                admitted[name] = declared
        for path in sorted((root / BASE / 'results').rglob('*')):
            if path.is_file() and path.suffix != '.lock' and '__pycache__' not in path.parts:
                name = path.relative_to(root).as_posix()
                check(path.suffix.lower() != '.npz' or name in admitted, 'Scientific output lacks actual QA authentication')
                add(name, admitted.get(name))
        # Public sources/reviews/GO/freezes/preparation/failure metadata; unknown
        # helper Python programs are omitted. The archive GO/manifest are future controls.
        for path in sorted((root / BASE).rglob('*')):
            if not path.is_file() or (root / BASE / 'results') in path.parents:
                continue
            name, local = path.relative_to(root).as_posix(), path.relative_to(root / BASE).as_posix()
            if admissible(name) and (path.suffix != '.py' or local in PUBLIC_PY):
                add(name)
        for name in NEXT:
            check(add(name)['sha256'] == NEXT[name], 'Root-selected prospective feasibility JSON changed')
        terminal = add(BASE + '/ACTUAL_QA_CONTEXT_TERMINALS.json')
        check(terminal['bytes'] == 1721 and terminal['sha256'] == '28a6df0eaa3944d74f88168d731479b18b2d46772ca77eced4b1dc7b31ade9c9',
              'Root actual QA/context terminal proof differs')
        add('continuation_20261011/execution/control_target_primary_v2/OUTER_EXECUTION.json')
        primary_receipts = {}
        for target in helper.TARGETS:
            primary_receipts[target] = add(BASE + '/results/' + target + '/EXECUTION_RECEIPT.json',
                                          qa['input_byte_pins'][BASE + '/results/' + target + '/EXECUTION_RECEIPT.json'])
        gate_paths = {'primary_QA': 'results/review/QA_RECEIPT.json',
            'context_execution': 'results/context/EXECUTION_RECEIPT.json',
            'context_QA': 'results/context_review/QA_RECEIPT.json', 'primary_scope': 'scope.json',
            'context_scope': 'context_scope.json', 'primary_driver': 'driver.py', 'context_driver': 'context_profiles.py',
            'primary_QA_script': 'qa_saved.py', 'context_QA_script': 'qa_context.py',
            'primary_QA_scope': 'qa_scope.json', 'context_QA_scope': 'qa_context_scope.json'}
        gates = {'primary_receipts': primary_receipts, **{key: add(BASE + '/' + name) for key, name in gate_paths.items()}}
        manifest = {'schema': 'SETI_S2017_CONTROL_RESULTS_MANIFEST_V1',
            'status': 'CLOSED_ROOT_SELECTED_BYTE_MANIFEST_AFTER_ALL_QA_PASS',
            'science_public_freeze_commit': qa['public_freeze_commit'], 'gates': gates,
            'members': [members[name] for name in sorted(members)],
            'required_report_paths': [BASE + '/delivery/SETI_CONTROL_TARGETS_2026-10-11.md',
                                      BASE + '/delivery/SETI_CONTROL_TARGETS_FINAL_2026-10-11.md',
                                      BASE + '/delivery/SETI_CONTROL_TARGETS_2026-10-11.png'],
            'manifest_maker_sha256': args.source_sha256,
            'preserved_failed_report_receipt_sha256': FAILED_REPORT_SHA,
            'actual_report_completion_receipt_sha256': args.report_completion_sha256,
            'actual_final_report_science_review_sha256': args.report_science_review_sha256,
            'excluded_payloads': ['H5', 'BIN', 'prior NPZ', 'ZIP', 'locks', 'cache', 'private helpers', 'archive GO/manifest cycle'],
            'archive_producer_executed': False, 'numerical_values_decoded': False,
            'result_arithmetic_performed': False, 'new_telescope_HTTP_requests': 0}
        helper.admission(root, manifest)  # Metadata contract only; no producer/ZIP calls.
        for name, declared in expected.items():
            check(helper.pin(root, helper.confined(root, name)) == {'path': name, **declared}, 'Selected file changed before closure')
        check(digest(Path(__file__).resolve()) == args.source_sha256 and digest(root / BUILD) == BUILD_SHA,
              'Maker/frozen builder changed during closure')
        raw = (json.dumps(manifest, separators=(',', ':'), allow_nan=False) + '\n').encode()
        check(len(raw) <= 8 * 1024**2 and helper.allocated(root) + 8 * 1024**2 <= helper.WORKSPACE, 'Manifest output/workspace bound exceeded')
        with output.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        helper.sync_directory(output.parent)
        print(json.dumps({'status': manifest['status'], 'manifest': helper.pin(root, output), 'members': len(members)}))
    finally:
        signal.alarm(0)
        for stream in reversed(handles):
            stream.close()

if __name__ == '__main__':
    main()
