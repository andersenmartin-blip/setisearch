"""BQ: streaming completion of saved BP A04 association postprocessing only.

This new execution identity preserves the original BP RSS failure. It never
generates input powers, normalizes data, calculates a new scan score, changes
the candidate family, or executes BP's materializing assess_case. Imports
alone open no score arrays. Production input access requires the separately
published BQ plan and the root runner's capture/pin enforcement.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
BP_PATH = ROOT/'work_bp/paired_search.py'
BP_PLAN_PATH = ROOT/'work_bp/BP_FIXED24_PLAN.json'
BP_SOURCE_SHA256 = '5b9fd6aab563649eca3bc2fcac4f3a0d95853b9f13e851af8f945e84fa51df25'
STATES = ('PASS', 'UNSUPPORTED', 'THREE_ON_FAIL', 'OFF_VETO')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def specification():
    return {
        'schema': 'SETI_BQ_STREAM_ASSOCIATION_SPEC_V1',
        'scope': 'Saved BP A04 association_broad and paired N04 score artifacts only',
        'BP_source_sha256': BP_SOURCE_SHA256,
        'BP_failure_preserved': True,
        'BP_success_count_remains': 23,
        'BP_A04_remains': 'INCOMPLETE_AFTER_RSS_STOP',
        'new_execution_identity': 'BQ_A04_ASSOC_V1',
        'allowed_BP_functions': ['ScoreStore', 'force', 'truth_candidates'],
        'candidate_order': 'current then legacy; ON scan0,2,4; each original hits list in saved order',
        'association_cap_per_method': 50000,
        'cap_check': 'Count original saved source hits before forcing a method; reject above exact original cap',
        'numerical_and_endpoint_changes': 'None: call frozen BP force/truth_candidates directly',
        'stream_format': 'One unchanged BP association object per UTF-8 JSONL line, sort_keys=True, allow_nan=False, compact separators',
        'retention': 'Full association records streamed; only status counters and the small original truth-candidate list retained in RAM',
        'stream_closure': 'flush, fsync, close; saved byte count and whole-file SHA256 must match incremental writer receipt',
        'gate': 'Exact original A04 no-current-flag and supported OFF-veto or all-truth-supported-three-ON-rejection clauses',
        'input_binding': 'Every supplied absolute path/bytes/SHA pin verified before score access and after both streams close',
        'required_pins': 'A04 six RESULT+arrays, N04 six RESULT+arrays, BP plan and every source pinned by BP plan; root may bind additional preserved evidence',
        'source_case_binding': 'case_spec must equal pinned BP plan A04 object; scan path identities bind A04 and N04 cases',
        'RNG_calls': 0, 'new_scan_scores': 0, 'astronomical_powers_opened': 0,
        'excluded': ['BP rerun/retry', 'new synthetic power generation', 'threshold or endpoint tuning',
                     'full839 stage', 'DATA admission', 'astronomical search'],
    }


def load_bp():
    require(sha(BP_PATH) == BP_SOURCE_SHA256, 'Frozen BP comparator source changed')
    spec = importlib.util.spec_from_file_location('bq_frozen_bp_comparator', BP_PATH)
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    require(bp.MAX_ASSOCIATIONS_PER_METHOD == 50000, 'Frozen BP cap differs')
    require(tuple(bp.ON) == (0,2,4), 'Frozen source scan order differs')
    return bp


def verify_pins(input_pins):
    require(isinstance(input_pins, list) and input_pins, 'Explicit input pins required')
    verified = []
    seen = set()
    for pin in input_pins:
        require(set(pin) >= {'path', 'bytes', 'sha256'}, 'Incomplete input pin')
        path = Path(pin['path'])
        require(path.is_absolute(), 'Input pins must use absolute paths')
        require(not path.is_symlink(), 'Symlink inputs are forbidden')
        resolved = path.resolve(strict=True)
        require(str(resolved) not in seen, 'Duplicate input pin')
        seen.add(str(resolved))
        require(isinstance(pin['bytes'], int) and not isinstance(pin['bytes'], bool) and pin['bytes'] >= 0,
                'Invalid pinned size')
        require(isinstance(pin['sha256'], str) and re.fullmatch('[0-9a-f]{64}', pin['sha256']),
                'Invalid pinned digest')
        info = path.stat()
        require(stat.S_ISREG(info.st_mode), 'Input must be a regular file')
        require(info.st_size == pin['bytes'], 'Input size differs: '+str(path))
        require(sha(path) == pin['sha256'], 'Input SHA differs: '+str(path))
        verified.append({'path': str(resolved), 'bytes': pin['bytes'], 'sha256': pin['sha256']})
    return verified


class AssociationWriter:
    """One-record working set, with complete ordered evidence on disk."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('xb', buffering=1048576)
        self.digest = hashlib.sha256()
        self.bytes = 0
        self.records = 0
        self.closed = False

    def append(self, record):
        require(not self.closed, 'Association stream is already closed')
        payload = (json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
        written = self.stream.write(payload)
        require(written == len(payload), 'Short association write')
        self.digest.update(payload)
        self.bytes += len(payload)
        self.records += 1

    def close(self):
        require(not self.closed, 'Association stream was closed twice')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        self.closed = True
        require(self.path.stat().st_size == self.bytes, 'Saved association byte count differs')
        actual = sha(self.path)
        require(actual == self.digest.hexdigest(), 'Saved association SHA differs')
        return {'path': self.path.name, 'bytes': self.bytes, 'sha256': actual,
                'records': self.records, 'complete': True}

    def close_partial(self):
        if not self.closed:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()
            self.closed = True


def _stream_stores(bp, store, base, case_spec, output_dir):
    """Exact A04 semantic comparator, exposing stores solely for unit tests."""
    require(case_spec['case_id'] == 'A04' and case_spec['kind'] == 'association_broad',
            'BQ is restricted to A04 saved postprocessing')
    require(base is not None, 'The exact paired N04 store is required')
    out = Path(output_dir)
    result = {'schema': 'SETI_BQ_STREAM_ASSESSMENT_V1', 'case_id': case_spec['case_id'],
              'kind': case_spec['kind'], 'association_policy': 'NEW_BP_TARGET_PHYSICAL_Q_FIXED_GRID',
              'method_results': {}}
    for method in ('current', 'legacy'):
        count = sum(len(store.results[scan]['hits'][method]) for scan in bp.ON)
        bp.require(count <= bp.MAX_ASSOCIATIONS_PER_METHOD, 'Frozen association cap exceeded')
        counts = {state: 0 for state in STATES}
        writer = AssociationWriter(out/f'{method}_associations.jsonl')
        try:
            for scan in bp.ON:
                for hit in store.results[scan]['hits'][method]:
                    association = bp.force(store, method, hit)
                    require(association['status'] in counts, 'Unknown frozen association status')
                    writer.append(association)
                    counts[association['status']] += 1
                    del association
            stream = writer.close()
        except BaseException:
            writer.close_partial()
            raise
        require(stream['records'] == count and sum(counts.values()) == count,
                'Association count differs from saved source catalog')
        matched = []
        truth = case_spec.get('truth')
        if truth is not None:
            for candidate in bp.truth_candidates(truth):
                a = bp.force(store, method, candidate)
                b = bp.force(base, method, candidate)
                credited = a['flag'] and b is not None and b['supported'] and not b['flag']
                matched.append({'injected': a, 'uninjected': b, 'recovery_credit': credited})
        result['method_results'][method] = {
            'source_ON_hits': count, 'association_counts': counts,
            'association_stream': stream, 'flags': counts['PASS'],
            'truth': matched, 'truth_recovered': any(m['recovery_credit'] for m in matched),
            'truth_any_supported': any(m['injected']['supported'] for m in matched),
            'truth_any_supported_OFF_veto': any(m['injected']['supported'] and m['injected']['OFF_veto'] for m in matched),
            'truth_all_supported_fail_three_ON': bool(matched) and all(m['injected']['supported'] and not m['injected']['three_ON_pass'] for m in matched),
        }
    current = result['method_results']['current']
    legacy = result['method_results']['legacy']
    status, reasons = 'PASS', []
    if current['flags']:
        status = 'FAIL'
        reasons.append('ASSOCIATION_HAS_SUPPORTED_THREE_ON_NO_OFF_FLAG')
    expected_rejection = (current['truth_any_supported_OFF_veto']
                          or current['truth_all_supported_fail_three_ON'])
    reasons.append('REQUIRES_SUPPORTED_OFF_OR_THREE_ON_REJECTION')
    if not expected_rejection:
        status = 'FAIL'
        reasons.append('EXPECTED_SUPPORTED_REJECTION_NOT_DEMONSTRATED')
    result.update(status=status, gate_reasons=reasons,
                  current_flags=current['flags'], legacy_flags=legacy['flags'],
                  current_truth_recovered=current['truth_recovered'],
                  legacy_truth_recovered=legacy['truth_recovered'])
    return result


def run_stream_assessment(scan_dirs, case_spec, output_dir, base_scan_dirs, input_pins):
    """Verify all bound evidence, then stream unchanged saved A04 associations."""
    require(len(scan_dirs) == 6 and len(base_scan_dirs) == 6, 'Six A04 and six N04 scans required')
    before = verify_pins(input_pins)
    pinned = {p['path']: p for p in before}
    require(str(BP_PATH.resolve()) in pinned and str(BP_PLAN_PATH.resolve()) in pinned,
            'BP comparator and plan must be pinned')
    require(pinned[str(BP_PATH.resolve())]['sha256'] == BP_SOURCE_SHA256,
            'Unexpected BP comparator pin')
    bp_plan = json.loads(BP_PLAN_PATH.read_text())
    original_case = next(c for c in bp_plan['cases'] if c['case_id'] == 'A04')
    require(case_spec == original_case, 'A04 case differs from frozen BP plan')
    for source in bp_plan['source_pins']:
        path = str((ROOT/source['path']).resolve())
        require(path in pinned and pinned[path]['bytes'] == source['bytes']
                and pinned[path]['sha256'] == source['sha256'], 'BP source pin missing or changed: '+path)
    for identity, paths in [('A04', scan_dirs), ('N04', base_scan_dirs)]:
        for scan, raw_path in enumerate(paths):
            path = Path(raw_path).resolve()
            require(path.name == f'scan{scan}' and path.parent.name == 'payload'
                    and path.parent.parent.name == identity, 'Saved scan identity differs')
            for name in ('RESULT.json', 'arrays.npz'):
                require(str((path/name).resolve()) in pinned, 'Saved scan result/array is not pinned')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    bp = load_bp()
    store = bp.ScoreStore(scan_dirs)
    base = bp.ScoreStore(base_scan_dirs)
    result = _stream_stores(bp, store, base, case_spec, out)
    after = verify_pins(input_pins)
    require(before == after, 'Input pin receipts changed')
    result.update(
        execution_identity='BQ_A04_ASSOC_V1',
        input_pins_before_and_after=before,
        BP_source_sha256=BP_SOURCE_SHA256,
        BP_case_identity_preserved='A04_INCOMPLETE_AFTER_RSS_STOP',
        BP_terminal_status_preserved='FAIL', BP_passed_cases_preserved=23,
        BP_rerun=False, new_scan_scores=0, RNG_calls=0,
        astronomical_powers_opened=0, new_archive_requests=0,
        qualification='Separate saved-score association postprocessing only; no BP retry, full839 qualification, astronomical search or sensitivity/FAP claim.')
    return result
