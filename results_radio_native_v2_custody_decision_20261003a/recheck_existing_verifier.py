#!/usr/bin/env python3
"""Reobserve archive-only evidence; change only the final evidence destination/label.

This is a metadata recheck, not a test suite, runtime qualification, protected
control or independent human review. The pinned retained verifier performs its
existing read-only checks. Its final output is saved exclusively in this new
evidence directory; existing receipts and every production source stay intact.
"""
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'results_radio_native_v2_archive_contract_20261003a'
DESTINATION = Path(__file__).parent / 'current-evidence-recheck.json'
SOURCE_PIN = {'bytes': 14485, 'sha256': 'a63d5d3c5d482fba2905c8e5263173145259c794476cebfab8581308b26c2fb3'}


def main():
    source_path = OLD / 'review_final.py'
    raw = source_path.read_bytes()
    if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != SOURCE_PIN:
        raise ValueError('Retained verifier differs from its independent published pin')
    module = types.ModuleType('retained_archive_verifier')
    module.__file__ = str(source_path)
    exec(compile(raw, str(source_path), 'exec'), module.__dict__)
    original_open = Path.open
    original_canonical = module.canonical
    adapter_raw = Path(__file__).read_bytes()
    adapter_pin = {'bytes': len(adapter_raw), 'sha256': hashlib.sha256(adapter_raw).hexdigest()}

    def evidence_open(path, *args, **kwargs):
        if path == OLD / 'review-final-local.json':
            if args != ('xb',) or kwargs:
                raise ValueError('Only the exclusive final evidence write can be redirected')
            return original_open(DESTINATION, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    def evidence_canonical(value):
        if type(value) is dict and value.get('schema') == 'radio-native-v2-archive-contract-final-independent-review-v1':
            value = dict(value)
            value['schema'] = 'radio-native-v2-archive-contract-retained-verifier-recheck-v1'
            value['review_type'] = 'retained_read_only_verifier_recheck_by_primary_agent'
            value['independent_review'] = False
            value['retained_verifier_source_pin'] = SOURCE_PIN
            value['evidence_output_adapter_pin'] = adapter_pin
            value['verification_only_no_new_test_suite'] = True
        return original_canonical(value)

    Path.open = evidence_open
    module.canonical = evidence_canonical
    try:
        module.main()
    finally:
        Path.open = original_open
        module.canonical = original_canonical
    result = json.loads(DESTINATION.read_bytes())
    if result['review_type'] != 'retained_read_only_verifier_recheck_by_primary_agent' or result['independent_review'] is not False:
        raise ValueError('Recheck must not claim independent review')


if __name__ == '__main__':
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('Use Python -I -S -B for this bounded metadata recheck')
    main()
