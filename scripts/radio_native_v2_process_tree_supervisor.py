#!/usr/bin/env python3
"""Dedicated Linux subreaper evidence; tiny probes and guarded preparation.

The reusable function must run in a fresh, dedicated process. Its evidence is
not an admission path for the SETI pipeline or a complete runtime/host join.
ECHILD establishes termination of this kernel subreaper's adoption scope. Every
launched root installs an inherited no-new-privileges/seccomp guard before exec;
the guard refuses namespace creation/transitions, tracing and clone3. Broader
kernel escape and the supervisor's own final lifetime remain unqualified.
The caller must independently observe this supervisor through its termination.
"""
import argparse
import ctypes
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import resource
import select
import selectors
import signal
import stat
import subprocess
import sys
import time
import types

SCHEMA = 'radio-native-v2-dedicated-subreaper-engineering-v1'
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
MAX_SECONDS = 10.0
MAX_OUTPUT_BYTES = 65536
MAX_REAPED_CHILDREN = 64
MAX_STORAGE_BYTES = 2 * 1024 * 1024
MAX_STORAGE_ENTRIES = 32768
MAX_RSS_BYTES = 512 * 1024 * 1024
PREPARE_MAX_SECONDS = 600.0
CASE_STORAGE_BYTES = 192 * 1024 * 1024
RUN_STORAGE_BYTES = 1536 * 1024 * 1024
ROLE_LIMITS = {
    'prepare': {'seconds': 600.0, 'output_bytes': 65536, 'shared_storage_bytes': CASE_STORAGE_BYTES},
    'caller': {'seconds': 600.0, 'output_bytes': 65536, 'shared_storage_bytes': CASE_STORAGE_BYTES},
    'command': {'seconds': 120.0, 'output_bytes': 2 * 1024 * 1024, 'shared_storage_bytes': CASE_STORAGE_BYTES},
    'lossless-project': {'seconds': 600.0, 'output_bytes': 65536, 'shared_storage_bytes': CASE_STORAGE_BYTES},
    'lossless-verify-retained': {'seconds': 600.0, 'output_bytes': 65536, 'shared_storage_bytes': CASE_STORAGE_BYTES},
    'control': {'seconds': 4800.0, 'output_bytes': 65536, 'shared_storage_bytes': RUN_STORAGE_BYTES},
    'verifier': {'seconds': 4800.0, 'output_bytes': 65536, 'shared_storage_bytes': RUN_STORAGE_BYTES},
}
RECEIPT_RESERVATION_BYTES = 131072
DIRECTORY_RESERVATION_BYTES = 65536
# Independently reviewed implementation pins bootstrap admission. Supplied
# bundle hashes cannot select executable validator/fixture implementations.
# Updating either implementation requires reviewing and refreshing this table.
BOOTSTRAP_SOURCE_PINS = {'scripts/radio_native_v2_worker_admission.py': {'bytes': 82049, 'sha256': '1660d0b644674fd839aec2364fee1b1adf08539b524191dba9b54a83ea722917'}, 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 129756, 'sha256': '9d73a4b31a97423fd7bc5fdee176b9d090b8534153b4727c54bc2da073cfcd1d'}}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'network_fetches': 0, 'actual_connector_calls': 0,
    'actual_functions_sdk_calls': 0, 'real_public_github_mutations': 0,
    'pipeline_integration_qualified': False, 'runtime_closure_qualified': False,
    'host_ledger_join_complete': False, 'automatic_retry': False}

# These probes are deliberately small. Pipeline role entrypoints separately
# require exact admission and the independently pinned closed fixture gate.
PROBES = {
    'nested-wait': "import subprocess,sys; subprocess.run([sys.executable,'-I','-S','-B','-c',\"import sys; payload=bytearray(2*1024*1024); print('tiny-grandchild')\"],check=True); print('tiny-root')",
    'orphan': "import subprocess,sys,os; subprocess.Popen([sys.executable,'-I','-S','-B','-c',\"import time; time.sleep(0.06); print('tiny-orphan')\"]); os._exit(0)",
    'adopted-nonzero': "import subprocess,sys,os; subprocess.Popen([sys.executable,'-I','-S','-B','-c',\"import time; time.sleep(0.06); raise SystemExit(7)\"]); os._exit(0)",
    'double-fork': "import os,time\nchild=os.fork()\nif child==0:\n grandchild=os.fork()\n if grandchild: os._exit(0)\n time.sleep(0.08); os._exit(0)\nos.waitpid(child,0); os._exit(0)",
    'timeout': "import subprocess,sys,time; subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time; time.sleep(60)']); time.sleep(60)",
    'output-overflow': "import sys; sys.stdout.write('x'*200000); sys.stdout.flush()",
    'stdout-passthrough': "import sys; sys.stdout.buffer.write(b'tiny exact forwarded output\\n'); sys.stdout.buffer.flush()",
    'rss-handshake': "import json,os,sys,time\nfrom pathlib import Path\nroot=Path(sys.argv[1]); start=time.time_ns()//1000000\nidentity={'identity':'engineering-probe-proc:'+os.readlink('/proc/self'),'pid':os.getpid(),'proc_pid':int(os.readlink('/proc/self')),'started_at_epoch_ms':start}\n(root/'caller-start.json').write_text(json.dumps(identity))\npayload=bytearray(2*1024*1024)\nrequest={'dispatch_at_epoch_ms':start,'returned_at_epoch_ms':time.time_ns()//1000000,'client_sha256':'1'*64}\n(root/'rss-observation-request.json').write_text(json.dumps(request))\nend=time.monotonic()+2\nwhile not (root/'rss-observation.json').exists() and time.monotonic()<end: time.sleep(0.005)\nresponse=json.loads((root/'rss-observation.json').read_bytes())\nassert response['client_sha256']==request['client_sha256'] and response['client_peak_rss_bytes']>0\nassert response['interval_start_epoch_ms']<=start and response['interval_end_epoch_ms']>=request['returned_at_epoch_ms']\nassert response['includes_entire_caller_lifetime'] is False\nprint('tiny handshake complete')",
    'escape-guard': "import ctypes,errno,os\narch=os.uname().machine\nnumbers={'x86_64':(272,308,101,435),'aarch64':(97,268,117,435)}[arch]\nlibc=ctypes.CDLL(None,use_errno=True)\nfor nr,args in ((numbers[0],(0x20000000,)),(numbers[1],(-1,0)),(numbers[2],(0,0,0,0)),(numbers[3],(0,0))):\n ctypes.set_errno(0); result=libc.syscall(nr,*args); assert result == -1 and ctypes.get_errno() == errno.EPERM\nstatus=dict(line.split(':',1) for line in open('/proc/self/status') if ':' in line)\nassert status['NoNewPrivs'].strip()=='1' and status['Seccomp'].strip()=='2'\nprint('escape guard active')",
}


# Linux seccomp_data layout and classic BPF constants. The prospective runtime
# already freezes the executable/ELF platform. Unknown architectures close
# before child exec instead of silently launching without the guard.
_SECCOMP_ARCH = {
    'x86_64': {'audit': 0xC000003E, 'clone': 56,
        'blocked': (101, 272, 308, 310, 311, 425, 435)},
    'aarch64': {'audit': 0xC00000B7, 'clone': 220,
        'blocked': (97, 117, 268, 270, 271, 425, 435)},
}
_CLONE_NAMESPACE_FLAGS = (0x00020000 | 0x02000000 | 0x04000000 |
    0x08000000 | 0x10000000 | 0x20000000 | 0x40000000)


class _SockFilter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
        ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint32)]


class _SockFprog(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(_SockFilter))]


def _bpf(code, k, jt=0, jf=0):
    return _SockFilter(code=code, jt=jt, jf=jf, k=k)


def install_child_escape_guard():
    """Install an irreversible inherited escape guard in Popen's child.

    This runs after fork and before exec in the fresh single-threaded dedicated
    supervisor. It does not claim a general syscall sandbox. It closes the
    process-tree escapes material to the subreaper proof: namespace creation or
    transition, ptrace/process_vm injection, clone3 and io_uring setup. Ordinary
    fork/vfork and clone without namespace flags remain available to workers.
    """
    architecture = os.uname().machine
    contract = _SECCOMP_ARCH.get(architecture)
    if contract is None:
        raise OSError(95, 'Unsupported architecture for child escape guard')
    # BPF_LD|BPF_W|BPF_ABS, BPF_JMP|BPF_JEQ|BPF_K,
    # BPF_JMP|BPF_JSET|BPF_K and BPF_RET|BPF_K.
    instructions = [_bpf(0x20, 4), _bpf(0x15, contract['audit'], jt=1),
        _bpf(0x06, 0x80000000), _bpf(0x20, 0)]
    deny = 0x00050000 | 1  # SECCOMP_RET_ERRNO | EPERM
    for number in contract['blocked']:
        instructions.extend((_bpf(0x15, number, jf=1), _bpf(0x06, deny)))
    # If this is not clone, skip the argument load, JSET and deny instruction.
    instructions.extend((_bpf(0x15, contract['clone'], jf=3),
        _bpf(0x20, 16), _bpf(0x45, _CLONE_NAMESPACE_FLAGS, jf=1),
        _bpf(0x06, deny), _bpf(0x06, 0x7FFF0000)))
    array = (_SockFilter * len(instructions))(*instructions)
    program = _SockFprog(len=len(instructions), filter=array)
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), 'PR_SET_NO_NEW_PRIVS failed')
    if library.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:  # PR_SET_SECCOMP/FILTER
        raise OSError(ctypes.get_errno(), 'PR_SET_SECCOMP filter failed')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


# These are serialization bounds, not enlarged execution/resource allowances.
# Every dynamic final/pending field is listed, and checked again before fsync.
# In particular all 64 originally retained wait4 rows are reserved, regardless
# of the smaller child count requested by a generic engineering probe.
MAX_REAP_ROW_JSON_BYTES = 512
MAX_REASON_JSON_BYTES = 8192
RUNTIME_FIELD_JSON_LIMITS = {
    'status': 64, 'reason': MAX_REASON_JSON_BYTES,
    'supervisor_identity': 512, 'root_identity': 4096, 'root_exit_code': 128,
    'subreaper_scope_reaped_to_echild': 5,
    'reaped_processes': 2 + MAX_REAPED_CHILDREN * (MAX_REAP_ROW_JSON_BYTES + 1),
    'reaped_process_count': 128, 'maximum_individual_process_rss_bytes': 128,
    'launched_root_procfs_peak_rss_bytes': 128, 'launched_root_procfs_sample_count': 128,
    'caller_accessor_observation': 4096, 'complete_descendant_wait_chain_verified': 5,
    'child_escape_guard_installed_before_exec': 5,
    'child_escape_guard_no_new_privileges': 5, 'child_escape_guard_seccomp_filter': 5,
    'tree_termination_coverage': 64, 'observed_output_bytes': 256,
    'retained_output_bytes': 256, 'stdout_sha256_of_retained_prefix': 66,
    'stderr_sha256_of_retained_prefix': 66, 'pidfd_cancellation_count': 128,
    'elapsed_seconds_before_final_receipt_fsync': 128,
    'storage_bytes_before_receipt': 128, 'raw_output_passthrough_complete': 5,
    'measurements_fsynced_before_disposition': 5,
    'filesystem_checks_completed_before_disposition': 5,
    'storage_bytes_after_measurements': 128,
    'whole_case_storage_bytes_before_final_receipt': 128,
    'admitted_storage_quota_sample_count': 128,
    'admitted_external_storage_snapshot_sha256': 66,
    'admitted_storage_monitor_is_sampled_not_transient_peak_proof': 5,
}
ADMITTED_LAYOUT_KEYS = {'worker_scope', 'receipt_scope', 'shared_storage_root',
    'command_label', 'runtime_name'}
STRUCTURAL_BASE_KEYS = frozenset(('schema', 'status', 'namespace', 'case_ordinal',
    'source_case_id', 'source_domain_hex', 'archive_prefix', 'role', 'bundle_path',
    'bundle_exact_file_sha256', 'plan_canonical_sha256', 'complete_freeze_canonical_sha256',
    'public_preread_canonical_sha256', 'preparation_commit_claim',
    'supplied_public_preread_structure_checked', 'publication_claim_independently_verified',
    'remote_immutable_publication_fetched', 'independently_retained_bundle_digest_matched',
    'exact_worker_argv_checked', 'complete_child_environment_checked',
    'current_materialized_code_and_derived_pins_checked', 'runtime_custody_manifest_sha256',
    'material_runtime_custody_rechecked', 'activation_only_git_used_by_worker',
    'activation_only_git_aliases_enumerated_by_worker', 'fresh_preparation_output_names_absent',
    'fresh_role_output_names_absent', 'running_caller_snapshot_recheck',
    'live_caller_parent_identity_independently_verified', 'worker_role_layout',
    'loaded_validator_code', 'complete_expected_runtime_closure_verified',
    'current_parent_environment_verified', 'runtime_and_supplement_join_verified',
    'fixture_execution_guard_still_required', 'pipeline_integration_qualified',
    'large_source_generation_admitted', 'all_original_execution_blockers_closed',
    'checks_remain_subject_to_postcheck_mutation', 'execution_authorized',
    'reservation_authorized', 'scientific_execution_authorized', 'native_case_reservations',
    'native_case_executions', 'scientific_cases_run', 'rng_draws', 'telescope_reads',
    'actual_functions_sdk_calls', 'actual_connector_calls', 'network_fetches',
    'actual_git_processes', 'real_public_github_mutations', 'automatic_retry',
    'native_case_binding_verified', 'host_ledger_join_complete', 'hidden_http_bytes_known'))
STRUCTURAL_PHASE_KEYS = {'phase_input_pins', 'role_identity_metadata_checked',
    'full_source_domain_content_verified', 'complete_retained_transport_semantics_verified'}
PHASE_PIN_KEYS = {'plan_json', 'freeze_json', 'preread_json', 'prepared_json',
    'arguments_json', 'preparation_bundle', 'caller_transcript', 'source_wire',
    'deterministic_source', 'projection', 'compact_input_plan'}


def _exact_pin(value):
    if (type(value) is not dict or set(value) != {'bytes', 'sha256'}
            or type(value['bytes']) is not int or not 0 <= value['bytes'] < 2**63
            or type(value['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', value['sha256'])):
        raise ValueError('Exact bounded byte/SHA256 pin required')


def compact_admitted_attestation(checked):
    """Persist observational references after all full-evidence guards pass.

    This never replaces the raw checked object used by admission/finalization.
    References acquire no authority: the independently retained exact bundle
    remains necessary to recover and revalidate any referenced evidence.
    """
    required = {'schema', 'role', 'ordinal', 'argv', 'bundle_path', 'bundle_sha256',
        'supervisor_python_path', 'activation_evidence', 'structural_admission',
        'materialized_fixture_execution_status',
        'independent_immutable_publication_join_complete'} | ADMITTED_LAYOUT_KEYS | set(AUTHORITY)
    if type(checked) is not dict or set(checked) != required or checked['role'] not in ROLE_LIMITS:
        raise ValueError('Exact checked admission fields required for bounded attestation')
    role = checked['role']; structural = checked['structural_admission']
    keys = set(STRUCTURAL_BASE_KEYS)
    if role != 'prepare': keys |= STRUCTURAL_PHASE_KEYS
    if role == 'command': keys.add('command_binding')
    if type(structural) is not dict or set(structural) != keys:
        raise ValueError('Exact structural admission fields required')
    nested = {'worker_role_layout', 'loaded_validator_code', 'phase_input_pins', 'command_binding'}
    if any(type(value) not in (str, int, bool, type(None))
            for key, value in structural.items() if key not in nested):
        raise ValueError('Structural admission scalar fields cannot contain arbitrary bulk')
    if structural['worker_role_layout'] != {key: checked[key] for key in ADMITTED_LAYOUT_KEYS}:
        raise ValueError('Structural admission layout differs from exact checked layout')
    _exact_pin(structural['loaded_validator_code'])
    if role != 'prepare':
        pins = structural['phase_input_pins']
        if type(pins) is not dict or not set(pins) <= PHASE_PIN_KEYS:
            raise ValueError('Exact bounded phase pin inventory required')
        for pin in pins.values(): _exact_pin(pin)
    if role == 'command':
        binding = structural['command_binding']
        reader = {'kind', 'reader_ordinal', 'selected_output_sha256'}
        tail = {'kind', 'terminal_ordinal', 'payload_bytes', 'complete_client_binding_independently_recovered'}
        if type(binding) is not dict or set(binding) not in (reader, tail):
            raise ValueError('Exact compact command binding fields required')
    if len(canonical(structural)) > 16384:
        raise ValueError('Bounded unchanged structural admission metadata required')
    evidence = checked['activation_evidence']
    names = {'activation_receipt', 'plan', 'freeze', 'preread', 'execution_scope',
        'invocation_spending', 'repository_root'}
    if type(evidence) is not dict or set(evidence) != names:
        raise ValueError('Exact raw checked activation evidence inventory required')
    scalar = required - {'activation_evidence', 'structural_admission', 'argv'}
    if any(type(checked[key]) not in (str, int, bool, type(None)) for key in scalar):
        raise ValueError('Checked admission scalar fields cannot contain arbitrary bulk')
    if type(checked['argv']) is not list or not checked['argv'] or any(type(item) is not str for item in checked['argv']):
        raise ValueError('Exact checked argv strings required')
    scope = evidence['execution_scope']
    if type(scope) is not str or str(Path(scope).absolute()) != scope:
        raise ValueError('Canonical exact activation execution scope required')
    repository_root = evidence['repository_root']
    if (type(repository_root) is not str or not Path(repository_root).is_absolute()
            or '..' in Path(repository_root).parts
            or str(Path(repository_root)) != repository_root):
        raise ValueError('Canonical independent invocation repository root required')
    references = {}
    for name in sorted(names):
        raw = canonical(evidence[name])
        references[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return {**{key: value for key, value in checked.items() if key != 'activation_evidence'},
        'activation_evidence_reference': {'schema': SCHEMA + '-activation-evidence-reference-v1',
            'execution_scope': scope, 'repository_root': repository_root,
            'canonical_input_pins': references,
            'full_activation_evidence_persisted': False,
            'reference_is_execution_authority': False}}


def verify_admitted_attestation(attestation, checked):
    """Read-only exact reference comparison; raw guards must run separately."""
    if attestation != compact_admitted_attestation(checked):
        raise ValueError('Persisted admitted attestation differs from checked evidence')
    return True


def _validate_input_pin(pin):
    if pin is None: return
    if type(pin) is not dict: raise ValueError('Exact bounded engineering input pin required')
    kind = pin.get('kind')
    if kind == 'fixed_tiny_engineering_probe':
        if set(pin) != {'kind', 'probe', 'source_bytes', 'source_sha256'} or pin['probe'] not in PROBES:
            raise ValueError('Exact fixed tiny probe pin required')
        _exact_pin({'bytes': pin['source_bytes'], 'sha256': pin['source_sha256']})
        raw = PROBES[pin['probe']].encode()
        if pin['source_bytes'] != len(raw) or pin['source_sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError('Fixed tiny probe input pin differs from actual probe source')
    elif kind in ('admission-bound-prepare-worker', 'admission-bound-role-worker'):
        if set(pin) != {'kind', 'bundle_sha256', 'role', 'ordinal'} or pin['role'] not in ROLE_LIMITS:
            raise ValueError('Exact admission-bound worker input pin required')
        if type(pin['bundle_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', pin['bundle_sha256']):
            raise ValueError('Exact input bundle hash required')
        if pin['ordinal'] is not None and (type(pin['ordinal']) is not int or not 0 <= pin['ordinal'] < 8):
            raise ValueError('Bounded original case ordinal required')
    else: raise ValueError('Unknown engineering input pin fields refused')
    if len(canonical(pin)) > 1024: raise ValueError('Bounded engineering input pin required')


def _receipt_fixed_fields(controls, code_pin, runtime_pin, input_pin, attestation,
        shared_storage_root, shared_storage_cap, passthrough):
    return {'schema': SCHEMA, 'subreaper_set_and_get_verified': True,
        'sole_wait4_owner': True, 'concurrent_process_rss_sum_measured': False,
        'complete_process_tree_qualified': False,
        'descendant_wait_chain_scope': 'INHERITED_SECCOMP_GUARD_AND_LINUX_SUBREAPER_TO_ECHILD',
        'child_escape_guard_denied_operations': ['clone-namespace-flags', 'clone3', 'io-uring-setup',
            'process-vm-read', 'process-vm-write', 'ptrace', 'setns', 'unshare'],
        'procfs_descendant_escape_detection_complete': False,
        'raw_stdout_duplicate_written': False, 'raw_stderr_duplicate_written': False,
        'failed_cleanup_grace_seconds': 1.0,
        'supervisor_final_receipt_and_termination_independently_observed': False,
        'shared_storage_and_original_case_run_limits_joined': False,
        'controls': controls, 'controls_sha256': hashlib.sha256(canonical(controls)).hexdigest(),
        'supervisor_code': code_pin,
        'python_executable': {'path': str(Path(sys.executable).resolve()), **runtime_pin},
        'engineering_input_pin': input_pin, 'child_environment': ENVIRONMENT,
        'receipt_storage_reserved_bytes': RECEIPT_RESERVATION_BYTES,
        'directory_storage_reserved_bytes': DIRECTORY_RESERVATION_BYTES,
        'whole_case_storage_accounted': shared_storage_root is not None,
        'admitted_preparation_check': attestation if attestation is not None and attestation['role'] == 'prepare' else None,
        'admitted_worker_check': attestation,
        'shared_storage_root': str(shared_storage_root) if shared_storage_root is not None else None,
        'shared_storage_cap_bytes': shared_storage_cap if shared_storage_root is not None else None,
        'raw_output_passthrough_requested': passthrough,
        'limitations': ['The inherited seccomp guard covers declared namespace/tracing/process-vm/clone3 escapes; broader kernel escape and procfs tracing are unqualified.',
            'Outer supervisor lifetime, complete runtime closure, pipeline admission and storage/time joins are required separately.'],
        **AUTHORITY}


def receipt_capacity_bound(controls, *, code_pin, runtime_pin, input_pin=None,
        checked=None, shared_storage_root=None, shared_storage_cap=CASE_STORAGE_BYTES,
        passthrough=False):
    """Bound BOTH full envelopes before mutation using closed dynamic widths."""
    _validate_input_pin(input_pin)
    if checked is not None and input_pin != {'kind': 'admission-bound-prepare-worker' if checked['role'] == 'prepare' else 'admission-bound-role-worker',
            'bundle_sha256': checked['bundle_sha256'], 'role': checked['role'], 'ordinal': checked['ordinal']}:
        raise ValueError('Input pin differs from exact checked dispatch')
    if checked is None: validate_controls(controls)
    elif controls['schema'] == SCHEMA + '-admitted-prepare-controls': validate_admitted_prepare_controls(controls)
    else: validate_admitted_role_controls(controls)
    _exact_pin(code_pin); _exact_pin(runtime_pin)
    attestation = compact_admitted_attestation(checked) if checked is not None else None
    fixed = _receipt_fixed_fields(controls, code_pin, runtime_pin, input_pin, attestation,
        shared_storage_root, shared_storage_cap, passthrough)
    # Adding a field adds its JSON key, colon, value and at most one comma.
    # Final-only fields are included here, so the pending envelope also fits.
    bound = len(canonical(fixed)) + 1 + sum(
        len(canonical(key)) + 2 + maximum
        for key, maximum in RUNTIME_FIELD_JSON_LIMITS.items())
    if bound > RECEIPT_RESERVATION_BYTES:
        raise ValueError('Complete supervisor receipt capacity exceeded before dispatch')
    return fixed, bound


def _bounded_reason(reason):
    if reason is None or len(canonical(reason)) <= MAX_REASON_JSON_BYTES: return reason
    raw = reason.encode('utf-8', errors='backslashreplace')
    return 'Failure diagnostic exceeded bounded text; bytes=' + str(len(raw)) + '; sha256=' + hashlib.sha256(raw).hexdigest()


def _validate_receipt_runtime_fields(receipt, fixed):
    if not set(fixed) <= set(receipt) or not set(receipt) <= set(fixed) | set(RUNTIME_FIELD_JSON_LIMITS):
        raise RuntimeError('Unbounded supervisor receipt field inventory refused')
    if any(receipt[key] != value for key, value in fixed.items()):
        raise RuntimeError('Fixed supervisor receipt evidence changed before persistence')
    for key in set(receipt) - set(fixed):
        if len(canonical(receipt[key])) > RUNTIME_FIELD_JSON_LIMITS[key]:
            raise RuntimeError('Bounded supervisor runtime field exceeded: ' + key)
    rows = receipt['reaped_processes']
    if len(rows) > MAX_REAPED_CHILDREN or any(len(canonical(row)) > MAX_REAP_ROW_JSON_BYTES for row in rows):
        raise RuntimeError('Original retained wait4 row serialization bound exceeded')


class EvidenceChangedDuringRead(ValueError):
    """A bounded live publication was observed before its write completed."""


def bounded_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError('Bounded sole-link engineering evidence required')
        chunks = []; remaining = limit + 1
        while remaining:
            raw = os.read(fd, min(65536, remaining))
            if not raw: break
            chunks.append(raw); remaining -= len(raw)
        after = os.fstat(fd)
        raw = b''.join(chunks)
        if len(raw) != before.st_size or (before.st_dev, before.st_ino,
                before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev,
                after.st_ino, after.st_mtime_ns, after.st_ctime_ns):
            raise EvidenceChangedDuringRead('Engineering evidence changed during read')
        return raw
    finally:
        os.close(fd)


def source_module(path, name, expected=None):
    """Compile checked source bytes directly; never load repository bytecode."""
    raw = bounded_bytes(path, 2 * 1024 * 1024)
    observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None and observed != expected:
        raise ValueError('Materialized admission/fixture source pin drift')
    module = types.ModuleType(name); module.__file__ = str(Path(path).absolute())
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def check_admitted_worker(bundle_path, *, role='prepare', ordinal=None, expected_bundle_sha256):
    """Read-only structural check; neither launches work nor creates a scope."""
    if role not in ROLE_LIMITS:
        raise ValueError('Exact supported admitted worker role required')
    if not isinstance(expected_bundle_sha256, str) or not re.fullmatch('[a-f0-9]{64}', expected_bundle_sha256):
        raise ValueError('Independently retained exact admission-bundle SHA256 required')
    raw = bounded_bytes(bundle_path, 16 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != expected_bundle_sha256:
        raise ValueError('Admission bundle differs from independently retained byte hash')
    bundle = json.loads(raw)
    code_files = bundle['plan']['code_files']
    own_key = 'scripts/radio_native_v2_process_tree_supervisor.py'
    if pin_file(Path(__file__).resolve()) != code_files[own_key]:
        raise ValueError('Dispatcher source differs from materialized admission pins')
    module_key = 'scripts/radio_native_v2_worker_admission.py'
    # The module is loaded only from the prospectively pinned materialization.
    if code_files.get(module_key) != BOOTSTRAP_SOURCE_PINS[module_key]:
        raise ValueError('Supplied admission implementation differs from dispatcher bootstrap pins')
    admission = source_module(Path(bundle['code_root']) / module_key,
        'pinned_worker_admission', BOOTSTRAP_SOURCE_PINS[module_key])
    argv = admission.expected_worker_argv(bundle, str(Path(bundle_path).absolute()),
        role=role, ordinal=ordinal, expected_bundle_sha256=expected_bundle_sha256)
    structural = admission.validate_worker_admission(bundle_path, role=role,
        ordinal=ordinal, argv=argv, environment=ENVIRONMENT,
        expected_bundle_sha256=expected_bundle_sha256)
    if hasattr(admission, 'worker_role_layout'):
        layout = admission.worker_role_layout(bundle, role=role, ordinal=ordinal)
    elif role == 'prepare':
        # Compatibility with the original V1 preparation-only implementation.
        layout = {'worker_scope': argv[5], 'receipt_scope': str(Path(argv[5]) / 'preparation-supervisor'),
            'shared_storage_root': argv[5], 'command_label': None, 'runtime_name': 'python'}
    else:
        raise ValueError('Pinned validator does not support this worker role')
    fixture_key = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
    if code_files.get(fixture_key) != BOOTSTRAP_SOURCE_PINS[fixture_key]:
        raise ValueError('Supplied fixture implementation differs from dispatcher bootstrap pins')
    fixture = source_module(Path(bundle['code_root']) / fixture_key,
        'pinned_preparation_fixture', BOOTSTRAP_SOURCE_PINS[fixture_key])
    return {'schema': SCHEMA + ('-admitted-prepare-check' if role == 'prepare' else '-admitted-worker-check'), 'role': role,
        'ordinal': ordinal, 'argv': argv, 'bundle_path': str(Path(bundle_path).absolute()),
        'bundle_sha256': expected_bundle_sha256, **layout,
        'supervisor_python_path': bundle['plan']['runtime_executables']['python']['path'],
        'activation_evidence': {'activation_receipt':bundle['activation_receipt'],
            'plan':bundle['plan'],'freeze':bundle['complete_freeze'],
            'preread':bundle['public_preread'], 'execution_scope':bundle['execution_scope'],
            'invocation_spending':bundle['invocation_spending'],
            'repository_root':bundle['invocation_repository_root']},
        'structural_admission': structural,
        'materialized_fixture_execution_status': fixture.EXECUTION_STATUS,
        'independent_immutable_publication_join_complete': False,
        **AUTHORITY}, fixture


def check_admitted_prepare_worker(bundle_path, *, ordinal, expected_bundle_sha256):
    return check_admitted_worker(bundle_path, role='prepare', ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256)


def validate_admitted_prepare_controls(controls):
    expected_keys = {'schema', 'seconds', 'output_bytes', 'reaped_children',
        'case_storage_bytes', 'rss_bytes', 'worker_role'}
    if not isinstance(controls, dict) or set(controls) != expected_keys:
        raise ValueError('Exact admitted preparation controls required')
    if (controls['schema'] != SCHEMA + '-admitted-prepare-controls'
            or controls['worker_role'] != 'prepare'
            or type(controls['seconds']) not in (int, float)
            or not 0 < controls['seconds'] <= PREPARE_MAX_SECONDS
            or type(controls['output_bytes']) is not int or controls['output_bytes'] != MAX_OUTPUT_BYTES
            or type(controls['reaped_children']) is not int or controls['reaped_children'] != MAX_REAPED_CHILDREN
            or type(controls['case_storage_bytes']) is not int or controls['case_storage_bytes'] != CASE_STORAGE_BYTES
            or type(controls['rss_bytes']) is not int or controls['rss_bytes'] != MAX_RSS_BYTES):
        raise ValueError('Original prescribed preparation caps required')


def validate_admitted_role_controls(controls):
    expected_keys = {'schema', 'seconds', 'output_bytes', 'reaped_children',
        'shared_storage_bytes', 'rss_bytes', 'worker_role'}
    if not isinstance(controls, dict) or set(controls) != expected_keys:
        raise ValueError('Exact admitted role controls required')
    role = controls['worker_role']
    if type(role) is not str or role not in ROLE_LIMITS:
        raise ValueError('Exact supported admitted role required')
    limits = ROLE_LIMITS[role]
    if (controls['schema'] != SCHEMA + '-admitted-role-controls'
            or type(controls['seconds']) not in (int, float)
            or not 0 < controls['seconds'] <= limits['seconds']
            or type(controls['output_bytes']) is not int or controls['output_bytes'] != limits['output_bytes']
            or type(controls['reaped_children']) is not int or controls['reaped_children'] != MAX_REAPED_CHILDREN
            or type(controls['shared_storage_bytes']) is not int or controls['shared_storage_bytes'] != limits['shared_storage_bytes']
            or type(controls['rss_bytes']) is not int or controls['rss_bytes'] != MAX_RSS_BYTES):
        raise ValueError('Original prescribed role-specific caps required')


def admitted_role_controls(role, seconds):
    if role not in ROLE_LIMITS:
        raise ValueError('Supported admission-bound role required')
    limits = ROLE_LIMITS[role]
    controls = {'schema': SCHEMA + '-admitted-role-controls', 'seconds': seconds,
        'output_bytes': limits['output_bytes'], 'reaped_children': MAX_REAPED_CHILDREN,
        'shared_storage_bytes': limits['shared_storage_bytes'], 'rss_bytes': MAX_RSS_BYTES,
        'worker_role': role}
    validate_admitted_role_controls(controls)
    return controls


def require_isolated_supervisor_runtime(*, check_environment=False):
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError('Actual isolated no-site no-bytecode supervisor required')
    if check_environment and dict(os.environ) != ENVIRONMENT:
        raise RuntimeError('Exact complete minimal supervisor environment required')


def require_exact_supervisor_invocation(checked):
    prefix = [checked['supervisor_python_path'], '-I', '-S', '-B', str(Path(__file__).absolute())]
    if list(sys.orig_argv[:5]) != prefix:
        raise RuntimeError('Exact supervisor interpreter invocation required; extra options or aliases refused')


def dispatch_admitted_prepare_worker(bundle_path, scope, *, ordinal,
        expected_bundle_sha256, seconds=PREPARE_MAX_SECONDS):
    started = time.monotonic()
    checked, fixture = check_admitted_prepare_worker(bundle_path, ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256)
    if str(Path(scope).absolute()) != checked['receipt_scope']:
        raise ValueError('Exact admission-bound preparation supervisor scope required')
    controls = {'schema': SCHEMA + '-admitted-prepare-controls', 'seconds': seconds,
        'output_bytes': MAX_OUTPUT_BYTES, 'reaped_children': MAX_REAPED_CHILDREN,
        'case_storage_bytes': CASE_STORAGE_BYTES, 'rss_bytes': MAX_RSS_BYTES,
        'worker_role': 'prepare'}
    validate_admitted_prepare_controls(controls)
    require_isolated_supervisor_runtime()
    # The independently materialized fixture is the actual authority gate.
    # A successful local structural check cannot open this closed branch.
    fixture.require_execution_ready(**checked['activation_evidence'])
    require_isolated_supervisor_runtime(check_environment=True)
    require_exact_supervisor_invocation(checked)
    return supervise_engineering_subprocess(checked['argv'], scope, controls,
        dedicated_process=True, input_pin={'kind': 'admission-bound-prepare-worker',
            'bundle_sha256': expected_bundle_sha256, 'role': 'prepare', 'ordinal': ordinal},
        _admitted_dispatch=checked, _started_at=started)


def dispatch_admitted_worker(bundle_path, scope, *, role, ordinal=None,
        expected_bundle_sha256, seconds=None):
    if role == 'prepare':
        return dispatch_admitted_prepare_worker(bundle_path, scope, ordinal=ordinal,
            expected_bundle_sha256=expected_bundle_sha256,
            seconds=PREPARE_MAX_SECONDS if seconds is None else seconds)
    started = time.monotonic()
    checked, fixture = check_admitted_worker(bundle_path, role=role, ordinal=ordinal,
        expected_bundle_sha256=expected_bundle_sha256)
    if str(Path(scope).absolute()) != checked['receipt_scope']:
        raise ValueError('Exact admission-bound worker supervisor scope required')
    controls = admitted_role_controls(role, ROLE_LIMITS[role]['seconds'] if seconds is None else seconds)
    require_isolated_supervisor_runtime()
    fixture.require_execution_ready(**checked['activation_evidence'])
    require_isolated_supervisor_runtime(check_environment=True)
    require_exact_supervisor_invocation(checked)
    return supervise_engineering_subprocess(checked['argv'], scope, controls,
        dedicated_process=True, input_pin={'kind': 'admission-bound-role-worker',
            'bundle_sha256': expected_bundle_sha256, 'role': role, 'ordinal': ordinal},
        _admitted_dispatch=checked, _started_at=started,
        _passthrough_output=role == 'command')


def pin_file(path, *, maximum=128 * 1024 * 1024):
    digest = hashlib.sha256(); count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError('Bounded regular pinned engineering file required')
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            count += len(raw)
            if count > maximum:
                raise ValueError('Pinned engineering file exceeded bounded byte count')
            digest.update(raw)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Engineering pin changed during hash')
    finally:
        os.close(fd)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def durable_json(path, value):
    raw = canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(raw)
        while view:
            amount = os.write(fd, view)
            if amount <= 0: raise OSError('Incomplete engineering receipt write')
            view = view[amount:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


def storage_bytes(scope):
    logical = allocated = 0
    for count, path in enumerate(itertools.chain((scope,), scope.rglob('*')), 1):
        if count > MAX_STORAGE_ENTRIES:
            raise ValueError('Bounded engineering storage entry count required')
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) and (
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError('Ordinary sole-link engineering evidence required')
        logical += info.st_size; allocated += info.st_blocks * 512
    return max(logical, allocated)


def sampled_storage_inventory(scope):
    """Bounded nofollow quota sample while admitted files can still grow.

    Identity, sole-link and named descriptor bindings remain mandatory. File
    size/block growth is allowed and the larger before/after amount is charged.
    Membership is sampled, not proof of a transient peak between polls. Stable
    content/metadata observations remain mandatory at every phase boundary.
    """
    scope = Path(scope)
    if not scope.is_absolute() or '..' in scope.parts or str(scope) != str(scope.absolute()):
        raise ValueError('Canonical absolute sampled storage scope required')
    held = []; ancestors = []; rows = []
    stable_directory = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
    def metadata(info):
        return {'bytes': info.st_size, 'allocated_bytes': info.st_blocks*512,
            'device': info.st_dev, 'inode': info.st_ino, 'mode': stat.S_IMODE(info.st_mode),
            'nlink': info.st_nlink, 'uid': info.st_uid, 'gid': info.st_gid,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}
    def visit(fd, relative):
        if len(relative.encode('utf-8')) > 4096 or len(Path(relative).parts) > 64:
            raise ValueError('Bounded sampled storage path required')
        before = os.fstat(fd)
        if not stat.S_ISDIR(before.st_mode): raise ValueError('Nofollow sampled directory required')
        if len(rows) >= MAX_STORAGE_ENTRIES: raise ValueError('Bounded sampled inventory entries required')
        row = {'path': relative, 'kind': 'directory', **metadata(before)}; rows.append(row)
        for name in sorted(os.listdir(fd)):
            if len(rows) >= MAX_STORAGE_ENTRIES: raise ValueError('Bounded sampled inventory entries required')
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            child_relative = name if relative == '.' else relative+'/'+name
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if stat.S_ISDIR(named.st_mode): flags |= os.O_DIRECTORY
            elif not stat.S_ISREG(named.st_mode) or named.st_nlink != 1:
                raise ValueError('Ordinary sole-link sampled storage required')
            child = os.open(name, flags, dir_fd=fd)
            try:
                opened = os.fstat(child)
                if stable_directory(named) != stable_directory(opened):
                    raise ValueError('Sampled storage identity changed during open')
                if stat.S_ISDIR(opened.st_mode): child_row = visit(child, child_relative)
                else:
                    after = os.fstat(child)
                    if (not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
                            or stable_directory(opened) != stable_directory(after)):
                        raise ValueError('Sampled ordinary file binding changed')
                    value = metadata(after)
                    value['bytes'] = max(named.st_size, opened.st_size, after.st_size)
                    value['allocated_bytes'] = max(named.st_blocks, opened.st_blocks, after.st_blocks)*512
                    child_row = {'path': child_relative, 'kind': 'file', **value}; rows.append(child_row)
                current = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stable_directory(os.fstat(child)) != stable_directory(current):
                    raise ValueError('Sampled storage named binding changed')
                if not stat.S_ISDIR(current.st_mode) and (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1):
                    raise ValueError('Sampled sole-link file changed after read')
                logical = max(child_row['bytes'], current.st_size)
                allocated = max(child_row['allocated_bytes'], current.st_blocks*512)
                child_row.update(metadata(current))
                child_row.update(bytes=logical, allocated_bytes=allocated)
            finally: os.close(child)
        after = os.fstat(fd)
        if stable_directory(before) != stable_directory(after):
            raise ValueError('Sampled directory binding changed')
        row.update(metadata(after))
        row['bytes'] = max(before.st_size, after.st_size)
        row['allocated_bytes'] = max(before.st_blocks, after.st_blocks)*512
        return row
    try:
        fd = os.open(scope.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW); held.append(fd)
        for name in scope.parts[1:]:
            parent = fd; named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode): raise ValueError('Ordinary nofollow sampled ancestor required')
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent); held.append(fd)
            if stable_directory(named) != stable_directory(os.fstat(fd)):
                raise ValueError('Sampled ancestor changed during open')
            ancestors.append((parent, name, fd, stable_directory(named)))
        root_row = visit(fd, '.')
        for parent, name, child, expected in ancestors:
            latest = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (stable_directory(os.fstat(child)) != expected or stable_directory(latest) != expected):
                raise ValueError('Sampled ancestor named binding changed')
            if child == fd:
                logical = max(root_row['bytes'], latest.st_size)
                allocated = max(root_row['allocated_bytes'], latest.st_blocks*512)
                root_row.update(metadata(latest)); root_row.update(bytes=logical, allocated_bytes=allocated)
        return {'scope': str(scope), 'rows': rows, 'entry_count': len(rows),
            'logical_bytes': sum(row['bytes'] for row in rows),
            'allocated_bytes': sum(row['allocated_bytes'] for row in rows)}
    finally:
        for fd in reversed(held): os.close(fd)


def prepare_admitted_storage_monitor(checked, fixture):
    """Build a strict sampled quota monitor solely from checked material code."""
    evidence = checked['activation_evidence']; scope = Path(evidence['execution_scope'])
    code_root = Path(fixture.__file__).absolute().parents[1]
    joined = fixture.observe_authenticated_invocation_storage(code_root,
        evidence['plan'], evidence['freeze'], evidence['activation_receipt'], evidence['invocation_spending'],
        execution_scope=evidence['execution_scope'], repository_root=evidence['repository_root'])
    joined = json.loads(canonical(joined))
    relative = 'scripts/radio_native_v2_resource_finalization.py'
    finalizer = fixture.pinned_component(code_root, relative, evidence['plan']['code_files'])
    digest = hashlib.sha256(canonical(joined)).hexdigest()
    state = {'samples': 0, 'external_sha256': digest}
    external_fields = {'kind', 'bytes', 'allocated_bytes', 'device', 'inode', 'mode',
        'nlink', 'uid', 'gid', 'mtime_ns', 'ctime_ns'}
    expected = {}
    for component in joined['components']:
        root = component['root']
        expected[root] = {row['path']: {key: row[key] for key in external_fields}
            for row in joined['rows'] if row['component'] == component['role']}
    def monitor():
        for root, wanted in expected.items():
            sample = sampled_storage_inventory(Path(root))
            observed = {root if row['path'] == '.' else root+'/'+row['path']:
                {key: row[key] for key in external_fields} for row in sample['rows']}
            if observed != wanted:
                raise ValueError('Authenticated historical/prospective storage metadata or membership changed during workload')
        inventory = sampled_storage_inventory(scope)
        allocation = finalizer['allocate_storage'](inventory, external_inventory=joined)
        # The current supervisor has not yet retained both bounded receipts.
        # Keep their original allowances plus directory growth prospectively,
        # even once some bytes materialize; this is a conservative charge.
        future = 2*RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES
        if max(allocation['whole_logical_bytes_with_remaining_reservation'],
                allocation['whole_allocated_bytes_with_remaining_reservation']) + future > RUN_STORAGE_BYTES:
            raise ValueError('Original whole storage cap exceeded with future supervisor receipts')
        for row in allocation['cases']:
            extra = future/8 if checked['role'] in ('control', 'verifier') else (
                future if row['ordinal'] == checked['ordinal'] else 0)
            if max(row['complete_logical_bytes'], row['complete_allocated_bytes']) + extra > CASE_STORAGE_BYTES:
                raise ValueError('Original case storage cap exceeded with shared history and future supervisor receipts')
        state['samples'] += 1
        return allocation
    monitor()
    return monitor, state


def proc_identity(procfs_pid):
    text = (Path('/proc') / str(procfs_pid) / 'status').read_text()
    parent = re.search(r'^PPid:\s+(\d+)', text, re.M)
    namespace = re.search(r'^NSpid:\s+([0-9 \t]+)$', text, re.M)
    if not parent or not namespace:
        raise ValueError('Kernel PPid and PID-namespace mapping required')
    chain = [int(value) for value in namespace.group(1).split()]
    ticks = (Path('/proc') / str(procfs_pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]
    return {'procfs_pid': procfs_pid, 'parent_procfs_pid': int(parent.group(1)),
        'namespace_pid_chain': chain, 'procfs_start_ticks': ticks}


def sample_root_memory(root_identity, observer):
    current = proc_identity(root_identity['procfs_pid'])
    if (current['procfs_start_ticks'] != root_identity['procfs_start_ticks']
            or current['parent_procfs_pid'] != observer['procfs_pid']
            or current['namespace_pid_chain'] != root_identity['namespace_pid_chain']):
        raise ValueError('Independently launched root procfs identity changed')
    fields = {}
    for line in (Path('/proc') / str(root_identity['procfs_pid']) / 'status').read_text().splitlines():
        if ':' in line:
            key, value = line.split(':', 1); fields[key] = value.strip()
    return {'at_epoch_ms': time.time_ns() // 1000000,
        'rss_bytes': int(fields.get('VmRSS', '0 kB').split()[0]) * 1024,
        'kernel_vm_hwm_bytes': int(fields.get('VmHWM', '0 kB').split()[0]) * 1024}


def read_json_evidence(path, limit=65536):
    raw = bounded_bytes(path, limit)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate caller observation evidence key refused')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Nonfinite caller observation evidence refused')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite), raw


def caller_rss_handshake(worker_scope, *, root_identity, observer, launch_epoch_ms,
        sample_count, root_peak, state, runtime_prefix='node-proc'):
    """Bind a provisional accessor receipt to the independent launched PID.

    This response covers the wrapper's start-through-tail accessor interval.
    Final root memory/termination evidence follows separately after ECHILD.
    """
    if state.get('completed'): return
    scope = Path(worker_scope); request_path = scope / 'rss-observation-request.json'
    if not request_path.exists(): return
    try:
        request, raw = read_json_evidence(request_path)
        started, _ = read_json_evidence(scope / 'caller-start.json')
    except (json.JSONDecodeError, EvidenceChangedDuringRead):
        # The child writes these small files exclusively, then fsyncs. A
        # visible incomplete JSON prefix can be retried without reexecuting it.
        return
    if (type(request) is not dict or set(request) != {'dispatch_at_epoch_ms', 'returned_at_epoch_ms', 'client_sha256'}
            or any(type(request[name]) is not int for name in ('dispatch_at_epoch_ms', 'returned_at_epoch_ms'))
            or type(request['client_sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', request['client_sha256'])):
        raise ValueError('Exact caller RSS accessor request required')
    now = time.time_ns() // 1000000
    if not launch_epoch_ms <= request['dispatch_at_epoch_ms'] <= request['returned_at_epoch_ms'] <= now:
        raise ValueError('Caller RSS request must lie inside independently launched interval')
    if (type(started) is not dict or set(started) != {'identity', 'pid', 'proc_pid', 'started_at_epoch_ms'}
            or type(started['pid']) is not int or started['pid'] != root_identity['namespace_pid']
            or type(started['proc_pid']) is not int or started['proc_pid'] != root_identity['procfs_pid']
            or started['identity'] != runtime_prefix + ':' + str(root_identity['procfs_pid'])
            or type(started['started_at_epoch_ms']) is not int
            or not launch_epoch_ms <= started['started_at_epoch_ms'] <= request['dispatch_at_epoch_ms']):
        raise ValueError('Caller reported start differs from independently launched PID/interval')
    live = sample_root_memory(root_identity, observer)
    if live['rss_bytes'] <= 0:
        raise ValueError('Live caller memory sample required for RSS accessor response')
    root_peak = max(root_peak, live['rss_bytes'], live['kernel_vm_hwm_bytes'])
    sample_count += 1
    now = time.time_ns() // 1000000
    if type(sample_count) is not int or sample_count <= 0 or not 0 < root_peak <= MAX_RSS_BYTES:
        raise ValueError('Positive bounded independent live caller observation required')
    response = {'schema': 'radio-native-v2-independent-client-rss-v1', 'measured': True,
        'client_peak_rss_bytes': root_peak, 'observer_source': 'independent_procfs',
        'caller_runtime_identity': runtime_prefix + ':' + str(root_identity['procfs_pid']),
        'observer_runtime_identity': 'python-proc:' + str(observer['procfs_pid']),
        'interval_start_epoch_ms': launch_epoch_ms, 'interval_end_epoch_ms': now,
        'procfs_sample_count': sample_count, 'client_sha256': request['client_sha256'],
        'includes_entire_caller_lifetime': False,
        'observation_scope': 'independently_launched_start_through_tail_accessor',
        'final_root_lifetime_observation_join_required': True}
    durable_json(scope / 'rss-observation.json', response)
    state.update({'completed': True, 'request_sha256': hashlib.sha256(raw).hexdigest(),
        'client_sha256': request['client_sha256'], 'response_pin': pin_file(scope / 'rss-observation.json', maximum=65536),
        'accessor_peak_rss_bytes': root_peak, 'accessor_interval_end_epoch_ms': now,
        'additional_root_samples': 1})


def direct_children(observer):
    found = []
    depth = len(observer['namespace_pid_chain']) - 1
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            candidate = proc_identity(int(entry.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if candidate['parent_procfs_pid'] != observer['procfs_pid']: continue
        if len(candidate['namespace_pid_chain']) <= depth:
            raise ValueError('Adopted child is outside observer PID namespace')
        candidate['namespace_pid'] = candidate['namespace_pid_chain'][depth]
        found.append(candidate)
    return found


def set_subreaper():
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Dedicated subreaper component requires Linux')
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    enabled = ctypes.c_int()
    if library.prctl(37, ctypes.byref(enabled), 0, 0, 0) != 0 or enabled.value != 1:
        raise RuntimeError('PR_GET_CHILD_SUBREAPER did not verify activation')


def cancel_direct_children(observer):
    """Signal independently mapped direct/adopted children through pidfds only."""
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Identity-safe pidfd cancellation is unavailable')
    cancellations = []
    for candidate in direct_children(observer):
        try:
            fd = os.pidfd_open(candidate['namespace_pid'], 0)
        except ProcessLookupError:
            continue
        try:
            after = proc_identity(candidate['procfs_pid'])
            if (after['procfs_start_ticks'] != candidate['procfs_start_ticks']
                    or after['parent_procfs_pid'] != observer['procfs_pid']):
                raise ValueError('Cancellation PID mapping changed before pidfd signal')
            signal.pidfd_send_signal(fd, signal.SIGKILL)
            cancellations.append(candidate)
        except ProcessLookupError:
            pass
        finally:
            os.close(fd)
    return cancellations


def bounded_output_passthrough(stream, raw, *, deadline):
    """Forward exact bytes without allowing pipe backpressure to lose deadline."""
    fd = stream.fileno(); previous = os.get_blocking(fd)
    os.set_blocking(fd, False)
    try:
        view = memoryview(raw); count = 0
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('Fixed output passthrough deadline exceeded')
            try:
                written = os.write(fd, view[:65536])
            except BlockingIOError:
                select.select([], [fd], [], min(0.005, remaining))
                continue
            if written <= 0:
                raise OSError('Incomplete exact output passthrough')
            count += written; view = view[written:]
        return count
    finally:
        os.set_blocking(fd, previous)


def validate_controls(controls):
    if set(controls) != {'schema', 'seconds', 'output_bytes', 'reaped_children'} or controls['schema'] != SCHEMA + '-controls':
        raise ValueError('Exact dedicated engineering control schema required')
    seconds = controls['seconds']; output = controls['output_bytes']; children = controls['reaped_children']
    if type(seconds) not in (int, float) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('Positive engineering deadline at most ten seconds required')
    if type(output) is not int or not 0 < output <= MAX_OUTPUT_BYTES:
        raise ValueError('Bounded engineering output allowance required')
    if type(children) is not int or not 0 < children <= MAX_REAPED_CHILDREN:
        raise ValueError('Bounded engineering child-receipt count required')


def supervise_engineering_subprocess(argv, scope, controls, *, dedicated_process=False,
        input_pin=None, _admitted_dispatch=None, _started_at=None,
        _passthrough_output=False, _caller_handshake_scope=None,
        _caller_runtime_prefix='node-proc'):
    """Reusable future component; only call from a fresh dedicated process.

    Generic argv admission is the future integrating caller's responsibility.
    No arbitrary-argv CLI is exposed, and this function grants no scientific or
    large-source authority. The original deadline includes cleanup; exceeding
    it remains CLOSED_FAILED even when cleanup reaches ECHILD afterwards.
    """
    if dedicated_process is not True:
        raise RuntimeError('Fresh dedicated-process invocation required')
    require_isolated_supervisor_runtime()
    shared_storage_root = None
    shared_storage_cap = CASE_STORAGE_BYTES
    admitted_storage_monitor = None
    storage_monitor_state = {'samples': 0, 'external_sha256': None}
    if _admitted_dispatch is None:
        validate_controls(controls)
        if _started_at is not None:
            raise ValueError('Custom dispatch timing requires checked worker admission')
    else:
        role = _admitted_dispatch['role']
        if controls['schema'] == SCHEMA + '-admitted-prepare-controls':
            validate_admitted_prepare_controls(controls)
        else:
            validate_admitted_role_controls(controls)
        if controls['worker_role'] != role:
            raise ValueError('Worker role and fixed control profile differ')
        if role == 'prepare':
            checked, fixture = check_admitted_prepare_worker(_admitted_dispatch['bundle_path'],
                ordinal=_admitted_dispatch['ordinal'],
                expected_bundle_sha256=_admitted_dispatch['bundle_sha256'])
        else:
            checked, fixture = check_admitted_worker(_admitted_dispatch['bundle_path'], role=role,
                ordinal=_admitted_dispatch['ordinal'],
                expected_bundle_sha256=_admitted_dispatch['bundle_sha256'])
        if (checked != _admitted_dispatch or argv != checked['argv']
                or str(Path(scope).absolute()) != checked['receipt_scope']):
            raise ValueError('Exact read-only checked role dispatch required')
        fixture.require_execution_ready(**checked['activation_evidence'])
        require_isolated_supervisor_runtime(check_environment=True)
        require_exact_supervisor_invocation(checked)
        shared_storage_root = Path(checked['shared_storage_root'])
        shared_storage_cap = ROLE_LIMITS[role]['shared_storage_bytes']
        if _passthrough_output is not (role == 'command'):
            raise ValueError('Exact command-only pipeline output passthrough required')
        if role == 'caller':
            _caller_handshake_scope = Path(checked['worker_scope'])
            _caller_runtime_prefix = 'node-proc'
        elif _caller_handshake_scope is not None:
            raise ValueError('Caller RSS accessor cannot be attached to another role')
    if not isinstance(argv, list) or not argv or any(type(item) is not str for item in argv):
        raise ValueError('Exact engineering argv strings required')
    argv_cap = 128 * 1024 if _admitted_dispatch is not None and _admitted_dispatch['role'] == 'command' else 32768
    if not Path(argv[0]).is_absolute() or sum(len(item.encode()) for item in argv) > argv_cap:
        raise ValueError('Absolute executable and bounded engineering argv required')
    started = time.monotonic() if _started_at is None else _started_at
    if type(started) not in (int, float) or not 0 < started <= time.monotonic():
        raise ValueError('Valid admission-inclusive monotonic dispatch start required')
    deadline = started + controls['seconds']
    code_pin = pin_file(Path(__file__).resolve())
    runtime_pin = pin_file(Path(sys.executable).resolve())
    fixed_receipt, capacity_bound = receipt_capacity_bound(controls, code_pin=code_pin,
        runtime_pin=runtime_pin, input_pin=input_pin, checked=_admitted_dispatch,
        shared_storage_root=shared_storage_root, shared_storage_cap=shared_storage_cap,
        passthrough=_passthrough_output)
    if time.monotonic() >= deadline:
        raise RuntimeError('Admission checks consumed the fixed preparation deadline')
    if _admitted_dispatch is not None:
        admitted_storage_monitor, storage_monitor_state = prepare_admitted_storage_monitor(checked, fixture)
        if time.monotonic() >= deadline:
            raise RuntimeError('Joined storage monitor consumed the fixed preparation deadline')
    observer = proc_identity(int(os.readlink('/proc/self')))
    if len(list((Path('/proc/self/task')).iterdir())) != 1 or direct_children(observer):
        raise RuntimeError('Dedicated supervisor must start with one thread and no children')
    # Establish cancellation support before creating a scope or spawning work.
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Identity-safe pidfd cancellation is unavailable')
    if _caller_handshake_scope is not None:
        for name in ('caller-start.json', 'rss-observation-request.json', 'rss-observation.json'):
            if os.path.lexists(Path(_caller_handshake_scope) / name):
                raise RuntimeError('Fresh exclusive caller observation paths required before dispatch')
    set_subreaper()
    scope = Path(scope).absolute()
    scope.mkdir(mode=0o700, exist_ok=False)
    identity = {'procfs_pid': observer['procfs_pid'], 'namespace_pid': os.getpid()}
    durable_json(scope / 'supervisor-identity.json', identity)
    durable_json(scope / 'controls.json', controls)
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    observed_bytes = {'stdout': 0, 'stderr': 0}
    selector = selectors.DefaultSelector()
    child = None; root_identity = None; root_status = None; rows = []
    echild = False; reason = None; cancellation_count = 0; reap_count = 0; kernel_peak = 0
    failure_cleanup_deadline = None
    setup_error = None
    root_peak = 0; root_samples = 0; callback_state = {}; launch_epoch_ms = None; callback_samples_accounted = 0
    try:
        if time.monotonic() >= deadline:
            raise RuntimeError('Supervisor setup consumed the fixed preparation deadline')
        launch_epoch_ms = time.time_ns() // 1000000
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=ENVIRONMENT, close_fds=True,
            preexec_fn=install_child_escape_guard)
        candidates = [row for row in direct_children(observer) if row['namespace_pid'] == child.pid]
        if len(candidates) != 1:
            raise RuntimeError('Unique launched root PID mapping required')
        root_identity = candidates[0]
        for name, stream in (('stdout', child.stdout), ('stderr', child.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while not echild or selector.get_map():
            if root_status is None:
                try:
                    sample = sample_root_memory(root_identity, observer)
                    root_samples += 1
                    root_peak = max(root_peak, sample['rss_bytes'], sample['kernel_vm_hwm_bytes'])
                    if root_peak > MAX_RSS_BYTES:
                        reason = reason or 'Independent live root RSS cap exceeded'
                    if _caller_handshake_scope is not None:
                        caller_rss_handshake(_caller_handshake_scope, root_identity=root_identity,
                            observer=observer, launch_epoch_ms=launch_epoch_ms,
                            sample_count=root_samples, root_peak=root_peak, state=callback_state,
                            runtime_prefix=_caller_runtime_prefix)
                        additional = callback_state.get('additional_root_samples', 0)
                        root_samples += additional - callback_samples_accounted
                        callback_samples_accounted = additional
                        root_peak = max(root_peak, callback_state.get('accessor_peak_rss_bytes', 0))
                except (FileNotFoundError, ProcessLookupError):
                    pass
            for key, _ in selector.select(0.005):
                raw = os.read(key.fileobj.fileno(), 65536)
                if not raw:
                    selector.unregister(key.fileobj); key.fileobj.close(); continue
                name = key.data; observed_bytes[name] += len(raw)
                remaining = max(0, controls['output_bytes'] - len(output[name]))
                output[name].extend(raw[:remaining])
                if observed_bytes[name] > controls['output_bytes']:
                    reason = reason or 'Bounded engineering output cap exceeded'
            while True:
                try:
                    pid, status, usage = os.wait4(-1, os.WNOHANG)
                except ChildProcessError:
                    echild = True; break
                if not pid: break
                reap_count += 1
                kernel_peak = max(kernel_peak, usage.ru_maxrss * 1024)
                exit_code = os.waitstatus_to_exitcode(status)
                is_root = pid == child.pid
                if is_root:
                    root_status = exit_code; child.returncode = exit_code
                if len(rows) < controls['reaped_children']:
                    rows.append({'namespace_pid': pid, 'kind': 'launched_root' if is_root else 'adopted_orphan',
                        'exit_code': exit_code, 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
                        'wait4_user_seconds': usage.ru_utime, 'wait4_system_seconds': usage.ru_stime})
                if reap_count > controls['reaped_children']:
                    reason = reason or 'Bounded engineering reaped-child count exceeded'
                if exit_code != 0:
                    reason = reason or 'Reaped engineering process returned nonzero'
                if usage.ru_maxrss * 1024 > MAX_RSS_BYTES:
                    reason = reason or 'Engineering individual-process RSS cap exceeded'
            if time.monotonic() > deadline:
                reason = reason or 'Fixed engineering scope deadline exceeded'
            if storage_bytes(scope) + 2 * RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > MAX_STORAGE_BYTES:
                reason = reason or 'Bounded engineering receipt storage allowance exceeded'
            if shared_storage_root is not None and (
                    storage_bytes(shared_storage_root) + 2 * RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > shared_storage_cap):
                reason = reason or 'Original role shared-storage allowance exceeded'
            if admitted_storage_monitor is not None:
                admitted_storage_monitor()
            if reason and not echild:
                if failure_cleanup_deadline is None:
                    failure_cleanup_deadline = min(deadline + 1.0, time.monotonic() + 1.0)
                cancellation_count += len(cancel_direct_children(observer))
                # Cancellation may cause another orphan generation to be
                # adopted. Each subsequent tick discovers and cancels it.
            if reason and echild:
                for key in list(selector.get_map().values()):
                    selector.unregister(key.fileobj); key.fileobj.close()
                break
            if reason and failure_cleanup_deadline is not None and time.monotonic() > failure_cleanup_deadline:
                # A killed task in uninterruptible sleep cannot be promised
                # reaped. Preserve a closed result for independent outer kill.
                break
        if not echild or root_status is None:
            reason = reason or 'Subreaper did not reach root status and terminal ECHILD'
        if _caller_handshake_scope is not None and not callback_state.get('completed'):
            reason = reason or 'Caller RSS accessor handshake did not complete'
    except BaseException as failure:
        setup_error = repr(failure)
        reason = reason or 'Dedicated engineering supervisor failed: ' + setup_error
        if child is not None:
            try:
                failure_cleanup_deadline = min(deadline + 1.0, time.monotonic() + 1.0)
                cancellation_count += len(cancel_direct_children(observer))
                while time.monotonic() <= failure_cleanup_deadline:
                    try: pid, status, usage = os.wait4(-1, os.WNOHANG)
                    except ChildProcessError: echild = True; break
                    if not pid:
                        cancellation_count += len(cancel_direct_children(observer)); time.sleep(0.005); continue
                    reap_count += 1
                    kernel_peak = max(kernel_peak, usage.ru_maxrss * 1024)
                    if pid == child.pid:
                        root_status = os.waitstatus_to_exitcode(status); child.returncode = root_status
                    if len(rows) < controls['reaped_children']:
                        rows.append({'namespace_pid': pid, 'kind': 'launched_root' if pid == child.pid else 'adopted_orphan',
                            'exit_code': os.waitstatus_to_exitcode(status), 'wait4_ru_maxrss_bytes': usage.ru_maxrss * 1024,
                            'wait4_user_seconds': usage.ru_utime, 'wait4_system_seconds': usage.ru_stime})
            except BaseException as cleanup_failure:
                reason += '; identity-safe cleanup failed: ' + repr(cleanup_failure)
    finally:
        for key in list(selector.get_map().values()):
            selector.unregister(key.fileobj); key.fileobj.close()
        selector.close()
        if child is not None:
            for stream in (child.stdout, child.stderr):
                if stream is not None: stream.close()
    maximum = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, kernel_peak, root_peak)
    if maximum > MAX_RSS_BYTES:
        reason = reason or 'Engineering supervisor or reaped-process RSS cap exceeded'
    elapsed = time.monotonic() - started
    if elapsed > controls['seconds']:
        reason = reason or 'Fixed engineering scope deadline exceeded'
    # Raw stdout is counted and discarded. It is never duplicated into files.
    descendant_wait_complete = reason is None and echild and root_status == 0
    reason = _bounded_reason(reason)
    receipt = {**fixed_receipt,
        'status': 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' if descendant_wait_complete else 'CLOSED_FAILED',
        'reason': reason,
        'supervisor_identity': identity,
        'root_identity': root_identity,
        'root_exit_code': root_status,
        'subreaper_scope_reaped_to_echild': echild,
        'reaped_processes': rows,
        'reaped_process_count': reap_count,
        'maximum_individual_process_rss_bytes': maximum,
        'launched_root_procfs_peak_rss_bytes': root_peak,
        'launched_root_procfs_sample_count': root_samples,
        'caller_accessor_observation': callback_state or None,
        'complete_descendant_wait_chain_verified': descendant_wait_complete,
        'child_escape_guard_installed_before_exec': child is not None,
        'child_escape_guard_no_new_privileges': child is not None,
        'child_escape_guard_seccomp_filter': child is not None,
        'tree_termination_coverage': 'SUBREAPER_ECHILD_OBSERVED' if echild else 'UNKNOWN_ON_FAILURE',
        'observed_output_bytes': observed_bytes,
        'retained_output_bytes': {name: len(raw) for name, raw in output.items()},
        'stdout_sha256_of_retained_prefix': hashlib.sha256(output['stdout']).hexdigest(),
        'stderr_sha256_of_retained_prefix': hashlib.sha256(output['stderr']).hexdigest(),
        'pidfd_cancellation_count': cancellation_count,
        'elapsed_seconds_before_final_receipt_fsync': elapsed,
        'storage_bytes_before_receipt': storage_bytes(scope),
        'raw_output_passthrough_complete': False,
        'admitted_storage_quota_sample_count': storage_monitor_state['samples'],
        'admitted_external_storage_snapshot_sha256': storage_monitor_state['external_sha256'],
        'admitted_storage_monitor_is_sampled_not_transient_peak_proof': True}
    _validate_receipt_runtime_fields(receipt, fixed_receipt)
    # Persist measurements with a pending status before deriving disposition.
    # No durable success is left behind by a subsequent filesystem check.
    pending = {**receipt, 'status': 'PENDING_FILESYSTEM_DISPOSITION'}
    if len(canonical(pending)) + 1 > RECEIPT_RESERVATION_BYTES:
        raise RuntimeError('Bounded supervisor measurements reservation exceeded')
    durable_json(scope / 'subreaper-measurements.json', pending)
    checked_storage = storage_bytes(scope)
    if checked_storage + RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > MAX_STORAGE_BYTES:
        reason = reason or 'Final engineering receipt storage cap reservation exceeded'
    shared_storage = None
    if shared_storage_root is not None:
        try:
            shared_storage = storage_bytes(shared_storage_root)
            if shared_storage + RECEIPT_RESERVATION_BYTES + DIRECTORY_RESERVATION_BYTES > shared_storage_cap:
                reason = reason or 'Final original shared-storage cap reservation exceeded'
        except (ValueError, OSError) as failure:
            reason = reason or 'Final whole-case filesystem checks failed: ' + repr(failure)
    if admitted_storage_monitor is not None:
        try: admitted_storage_monitor()
        except (ValueError, OSError, RuntimeError) as failure:
            reason = reason or 'Final joined storage quota sample failed: ' + repr(failure)
    if time.monotonic() > deadline:
        reason = reason or 'Fixed engineering scope deadline exceeded after filesystem checks'
    if _caller_handshake_scope is not None and callback_state.get('completed'):
        try:
            request_pin = pin_file(Path(_caller_handshake_scope) / 'rss-observation-request.json', maximum=65536)
            if request_pin['sha256'] != callback_state['request_sha256'] or (
                    pin_file(Path(_caller_handshake_scope) / 'rss-observation.json', maximum=65536) != callback_state['response_pin']):
                raise ValueError('Caller accessor evidence changed after handshake')
        except (ValueError, OSError) as failure:
            reason = reason or 'Final caller accessor evidence check failed: ' + repr(failure)
    if _passthrough_output and reason is None and echild and root_status == 0:
        try:
            bounded_output_passthrough(sys.stdout.buffer, output['stdout'], deadline=deadline)
            bounded_output_passthrough(sys.stderr.buffer, output['stderr'], deadline=deadline)
            receipt['raw_output_passthrough_complete'] = True
        except (OSError, ValueError, RuntimeError) as failure:
            reason = reason or 'Bounded command output passthrough failed: ' + repr(failure)
    if time.monotonic() > deadline:
        reason = reason or 'Fixed engineering scope deadline exceeded during final disposition'
    reason = _bounded_reason(reason)
    receipt.update({'status': 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' if reason is None and echild and root_status == 0 else 'CLOSED_FAILED',
        'reason': reason, 'measurements_fsynced_before_disposition': True,
        'filesystem_checks_completed_before_disposition': True,
        'storage_bytes_after_measurements': checked_storage,
        'whole_case_storage_bytes_before_final_receipt': shared_storage,
        'admitted_storage_quota_sample_count': storage_monitor_state['samples'],
        'elapsed_seconds_before_final_receipt_fsync': time.monotonic() - started})
    _validate_receipt_runtime_fields(receipt, fixed_receipt)
    if len(canonical(receipt)) + 1 > RECEIPT_RESERVATION_BYTES:
        raise RuntimeError('Bounded final supervisor receipt reservation exceeded')
    durable_json(scope / 'subreaper-receipt.json', receipt)
    if admitted_storage_monitor is not None:
        # A failure after receipt fsync produces a nonzero dispatcher lifetime;
        # that receipt cannot qualify without the parent's complete observation.
        admitted_storage_monitor()
    # The integrating outer observer covers this fsync, final allocation and
    # process termination. This local receipt explicitly leaves that join false.
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe', choices=sorted(PROBES))
    mode.add_argument('--admitted-prepare-worker', action='store_true')
    mode.add_argument('--admitted-worker', action='store_true')
    mode.add_argument('--admission-check-only', action='store_true')
    parser.add_argument('--worker-role', choices=sorted(ROLE_LIMITS), default='prepare')
    parser.add_argument('--scope', type=Path)
    parser.add_argument('--admission-bundle', type=Path)
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--ordinal', type=int)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--output-bytes', type=int, default=MAX_OUTPUT_BYTES)
    parser.add_argument('--reaped-children', type=int, default=MAX_REAPED_CHILDREN)
    args = parser.parse_args()
    if args.admitted_prepare_worker or args.admitted_worker or args.admission_check_only:
        if args.admitted_prepare_worker and args.worker_role != 'prepare':
            parser.error('Preparation compatibility entrypoint requires role prepare')
        if any(value is None for value in (args.admission_bundle, args.bundle_sha256)) or (
                args.worker_role not in ('control', 'verifier') and args.ordinal is None):
            parser.error('Exact admission bundle, retained SHA256 and case-role outer ordinal required')
        if args.worker_role in ('control', 'verifier') and args.ordinal is not None:
            parser.error('Whole control/verifier roles accept no case ordinal')
        if args.output_bytes != MAX_OUTPUT_BYTES or args.reaped_children != MAX_REAPED_CHILDREN:
            parser.error('Admitted preparation output and child caps are fixed')
        if args.admission_check_only:
            if args.scope is not None or args.seconds is not None:
                parser.error('Admission-check-only accepts no receipt scope or timing mutation')
            checked, _ = check_admitted_worker(args.admission_bundle, role=args.worker_role,
                ordinal=args.ordinal, expected_bundle_sha256=args.bundle_sha256)
            print(canonical(checked).decode()); return 0
        if args.scope is None:
            parser.error('Exact admission-bound preparation supervisor scope required')
        receipt = dispatch_admitted_worker(args.admission_bundle, args.scope, role=args.worker_role,
            ordinal=args.ordinal, expected_bundle_sha256=args.bundle_sha256, seconds=args.seconds)
        if args.worker_role != 'command':
            print(canonical({'schema': SCHEMA, 'status': receipt['status'], 'reason': receipt['reason'], **AUTHORITY}).decode())
        elif receipt['status'] != 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE':
            print(canonical({'schema': SCHEMA, 'status': receipt['status'], 'reason': receipt['reason'], **AUTHORITY}).decode(), file=sys.stderr)
        return 0 if receipt['status'] == 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' else 2
    if args.scope is None or args.worker_role != 'prepare' or any(value is not None for value in (args.admission_bundle, args.bundle_sha256, args.ordinal)):
        parser.error('Tiny probe requires a fresh scope and accepts no pipeline admission')
    source = PROBES[args.probe]
    controls = {'schema': SCHEMA + '-controls', 'seconds': 3.0 if args.seconds is None else args.seconds,
        'output_bytes': args.output_bytes, 'reaped_children': args.reaped_children}
    argv = [str(Path(sys.executable).resolve()), '-I', '-S', '-B', '-c', source]
    if args.probe == 'rss-handshake': argv.append(str(args.scope.absolute()))
    receipt = supervise_engineering_subprocess(argv,
        args.scope, controls, dedicated_process=True,
        input_pin={'kind': 'fixed_tiny_engineering_probe', 'probe': args.probe,
            'source_bytes': len(source.encode()), 'source_sha256': hashlib.sha256(source.encode()).hexdigest()},
        _passthrough_output=args.probe == 'stdout-passthrough',
        _caller_handshake_scope=args.scope if args.probe == 'rss-handshake' else None,
        _caller_runtime_prefix='engineering-probe-proc')
    if args.probe != 'stdout-passthrough':
        print(canonical({'schema': SCHEMA, 'status': receipt['status'], 'reason': receipt['reason'],
            'subreaper_scope_reaped_to_echild': receipt['subreaper_scope_reaped_to_echild'], **AUTHORITY}).decode())
    return 0 if receipt['status'] == 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
