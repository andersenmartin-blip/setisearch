"""Exercise the unchanged public decode function, not scientific QA/main."""
import ast
import copy
import hashlib
import json
from pathlib import Path

from legacy_bridge import TypedStore, legacy_descriptor
from runtime import guard, store


class InterfaceChecks:
    def __init__(self): self.checks = 0
    def eq(self, got, expected, label):
        if got != expected: raise ValueError(label)
        self.checks += 1


def main():
    root = Path(__file__).resolve().parent
    scope = json.loads((root / 'COMPATIBILITY_SCOPE.json').read_text())
    for name, pin in scope['source_pins'].items():
        if store.digest_file(root / name) != pin: raise ValueError('Compatibility source differs')
    qa = root.parent.parent / 'analysis/sixscan_burst_20261015/qa.py'
    if store.digest_file(qa) != scope['prior_QA_source_sha256']:
        raise ValueError('Original public QA source differs')
    text = qa.read_text(); tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('decode', 'array_sha')]
    if {n.name for n in nodes} != {'decode', 'array_sha'}:
        raise ValueError('Decode-only source selection differs')
    for node in nodes:
        if hashlib.sha256(ast.get_source_segment(text, node).encode()).hexdigest() != scope['function_sha256'][node.name]:
            raise ValueError('Public decoder function bytes differ')
    env = {'hashlib': hashlib}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(qa) + ':decode_only', 'exec'), env)
    # Neither module import, main, admission, numerical QA nor reproduction/RNG
    # functions are selected or executed by this source extraction.
    case = root / 'results/suite/complete_case/payload'
    document = json.loads((case / 'CASE_ARRAYS.json').read_text())
    entries = document['arrays']; selected = [entries[0]]
    for predicate in (
        lambda d: d['path'][-1] == 'widths',
        lambda d: d['path'][-1] == 'retained_valid',
        lambda d: d['kind'] == 'OFF_inventory' and d['path'][-1] == 'native4_centers',
        lambda d: d['kind'] == 'edge' and d['dtype'] == '<f8',
        lambda d: d['kind'] == 'edge' and d['dtype'] == '>f4'):
        selected.append(next(d for d in entries if predicate(d)))
    typed_store = TypedStore(case / 'case_arrays.npz', entries)
    checks = InterfaceChecks(); verified = []
    for d in selected:
        result = env['decode']({'nested': [legacy_descriptor(d)]}, typed_store, checks)['nested'][0]
        if (result.dtype.str != d['dtype'] or list(result.shape) != d['shape'] or
                hashlib.sha256(result.tobytes(order='C')).hexdigest() != d['C_order_input_sha256']):
            raise ValueError('Restored consumer array differs')
        verified.append({'path': d['path'], 'shape': d['shape'], 'dtype': d['dtype'],
                         'nbytes': d['nbytes'], 'bit_exact': True})
        del result
    rejected = []
    for field, value in [('shape', [999]), ('dtype', 'int64'), ('C_order_bytes_sha256', '0' * 64)]:
        bad = legacy_descriptor(selected[0]);bad['array_descriptor'][field] = value
        try: env['decode'](bad, typed_store, InterfaceChecks())
        except ValueError as error: rejected.append({'field': field, 'rejection': str(error)})
        else: raise AssertionError('Malformed legacy descriptor accepted')
    guard.durable_json(root / 'results/LEGACY_INTERFACE_RESULT.json', {
        'status': 'PASS_LEGACY_ARRAY_DESCRIPTOR_INTERFACE_ONLY',
        'unchanged_public_decoder_checks': checks.checks,
        'arrays_bit_checked': verified, 'mutated_descriptors_rejected': rejected,
        'prior_QA_module_imported': False, 'prior_QA_main_or_admit_run': False,
        'scientific_QA_or_recovery_or_admission_established': False,
        'new_scientific_arrays_drawn': 0})


if __name__ == '__main__': main()
