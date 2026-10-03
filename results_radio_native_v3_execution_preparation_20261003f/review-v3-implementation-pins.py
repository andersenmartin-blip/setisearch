#!/usr/bin/env python3
"""Read the complete fixed 27-edge implementation graph without importing it.

This operator check reads only named source files and the fixed Git executable.
It grants no activation, preclaim, execution or scientific authority. A stale
graph is expected between source edits and the separately requested refresh.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
WORKER = 'scripts/radio_native_v3_worker_admission.py'
FIXTURE = 'scripts/radio_native_v3_compact_eight_case_resource_fixture.py'
ACTIVATION = 'scripts/radio_native_v3_control_activation.py'
SPENDING = 'scripts/radio_native_v3_prospective_spending.py'
CLAIMS = 'scripts/radio_native_v3_public_claim.py'
CUSTODY = 'scripts/radio_native_v3_custody_observation.py'
SUPERVISOR = 'scripts/radio_native_v3_process_tree_supervisor.py'
FINALIZER = 'scripts/radio_native_v3_resource_finalization.py'
LAUNCHER = 'scripts/radio_native_v3_compact_control_launch.py'
OBSERVER = 'scripts/radio_native_v3_engineering_observer.py'
ENVIRONMENT = 'scripts/radio_native_v3_activation_environment.py'
AUDIT = 'scripts/radio_native_v3_compact_preparation_audit.py'
FREEZER = 'scripts/radio_native_v3_runner_freeze.py'
V2_CUSTODY = 'scripts/radio_native_v2_runtime_custody.py'
V2_HISTORY = 'scripts/radio_native_v2_historical_storage.py'
GIT = '/usr/local/bin/git'
LAUNCH_TARGETS = (ENVIRONMENT, FIXTURE, AUDIT, V2_HISTORY, SPENDING,
    FINALIZER, FREEZER, V2_CUSTODY, WORKER, CUSTODY, CLAIMS)
EDGES = (
    (ACTIVATION, 'CUSTODY_IMPLEMENTATION_PIN', None, V2_CUSTODY),
    (ACTIVATION, 'ACTIVATION_GIT_IMPLEMENTATION_PIN', None, GIT),
    (WORKER, 'CUSTODY_IMPLEMENTATION_PIN', None, V2_CUSTODY),
    (WORKER, 'PUBLIC_CLAIM_IMPLEMENTATION_PIN', None, CLAIMS),
    (WORKER, 'SPENDING_IMPLEMENTATION_PIN', None, SPENDING),
    (FIXTURE, 'WORKER_ADMISSION_IMPLEMENTATION_PIN', None, WORKER),
    (FIXTURE, 'CONTROL_ACTIVATION_IMPLEMENTATION_PIN', None, ACTIVATION),
    (FIXTURE, 'INVOCATION_SPENDING_IMPLEMENTATION_PIN', None, SPENDING),
    (FIXTURE, 'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN', None, CUSTODY),
    (FIXTURE, 'ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN', None, ENVIRONMENT),
    (FIXTURE, 'PUBLIC_CLAIM_IMPLEMENTATION_PIN', None, CLAIMS),
    *((SUPERVISOR, 'BOOTSTRAP_SOURCE_PINS', path, path)
        for path in (WORKER, FIXTURE)),
    *((FINALIZER, 'BOOTSTRAP_SOURCE_PINS', path, path)
        for path in (FIXTURE, WORKER, SUPERVISOR)),
    *((LAUNCHER, 'BOOTSTRAP_SOURCE_PINS', path, path) for path in LAUNCH_TARGETS),
)
assert len(EDGES) == 27
FIXED_PINS = {
    V2_CUSTODY: {'bytes': 22519, 'sha256': 'd0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'},
    V2_HISTORY: {'bytes': 25274, 'sha256': '9f709c42ad726732b9da98d2b830a9905e6d3ae90f3a8ba1f49482d11db299d5'},
    GIT: {'bytes': 19135768, 'sha256': '2dae8066ef4d6a926561b4b0eaca7b458d4f5b56bb83760656e6baa7fc3e974f'},
}
E_SPENT = ('radio-native-v3-control-activation-transition-20261003e',
    'config/radio_native_v3_control_activation_20261003e.activate.json',
    '2cde096565519be82d8effe5d9cc878d6122ab45')
E_PUBLIC = {
    'namespace': E_SPENT[0], 'activation_commit': E_SPENT[2],
    'registry_path': 'config/radio_native_v3_control_spent_20261003e.claim.json',
    'create_only_ref': 'refs/heads/radio-native-v3-spent-20261003e',
    'commit': '4c28009b98ea5d4596b900c97fbee1f0b3e63bd3',
    'tree': '97a0d58ec03027fddda419199c73baee90cd18ab',
    'blob': 'f88175a1ce9c1756298e793f4a91d2dc6c669563',
    'raw_sha256': '759184e96e50e7785351ad14ef66a626f388501c8bd6310e2308f028bdf26bec',
}
F_PROTECTED = ('config/radio_native_v3_control_activation_20261003f.activate.json',
    'config/radio_native_v3_control_spent_20261003f.claim.json',
    '.radio-native-v3-invocation-ledger-20261003f',
    'results_radio_native_v3_predispatch_20261003f',
    'results_radio_native_v3_compact_eight_input_control_20261003f')
E_EXCLUSIONS = ('results_radio_native_v3_compact_eight_input_control_20261003e',
    '.radio-native-v3-invocation-ledger-20261003e',
    'results_radio_native_v3_predispatch_20261003e',
    'config/radio_native_v3_control_spent_20261003e.claim.json')


def pin_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_regular(path, *, runtime=False):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        cap = 32*1024**2 if runtime else 2*1024**2
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= cap
                or (not runtime and before.st_nlink != 1)):
            raise ValueError('Bounded regular graph material required: '+str(path))
        chunks = []; count = 0
        while True:
            block = os.read(fd, 65536)
            if not block: break
            chunks.append(block); count += len(block)
            if count > cap: raise ValueError('Graph material exceeded read cap')
        after = os.fstat(fd); named = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,
            s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(named) or count != before.st_size:
            raise ValueError('Graph material changed during read: '+str(path))
        return b''.join(chunks)
    finally:
        os.close(fd)


def literal(raw, name):
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == name]
    if len(nodes) != 1: raise ValueError('Unique literal assignment required: '+name)
    return ast.literal_eval(nodes[0].value)


def source_path(root, relative):
    return Path(relative) if relative.startswith('/') else Path(root)/relative


def snapshot(root):
    names = {owner for owner,_,_,_ in EDGES} | {target for _,_,_,target in EDGES} | {OBSERVER}
    return {path: read_regular(source_path(root,path), runtime=path==GIT) for path in sorted(names)}


def validate_identities(raws):
    activation_ns = 'radio-native-v3-control-activation-transition-20261003f'
    control_ns = 'radio-native-v3-compact-eight-input-control-20261003f'
    marker, registry, ledger, predispatch, scope = F_PROTECTED
    expected = {
        ACTIVATION: {'NAMESPACE':activation_ns,'MARKER':marker,'INVOCATION_LEDGER_DIRECTORY':ledger},
        SPENDING: {'NAMESPACE':activation_ns,'MARKER':marker,'LEDGER_DIRECTORY':ledger},
        CLAIMS: {'NAMESPACE':activation_ns,'MARKER':marker,'REGISTRY_PATH':registry,
            'CLAIM_REF':'refs/heads/radio-native-v3-spent-20261003f','LEDGER_DIRECTORY':ledger},
        CUSTODY: {'CURRENT_LEDGER_DIRECTORY':ledger,
            'CURRENT_PUBLIC_CLAIM_PATH':predispatch+'/public-spending-envelope.json',
            'CURRENT_LAUNCH_CONFIG_PATH':predispatch+'/launch-config.json',
            'CURRENT_OBSERVER_CAPSULE_PATH':predispatch+'/observer-capsule.json'},
        WORKER: {'NAMESPACE':control_ns,'PREFIX':scope,'ACTIVATION_NAMESPACE':activation_ns,
            'ACTIVATION_MARKER':marker,'INVOCATION_LEDGER_DIRECTORY':ledger},
        FIXTURE: {'NAMESPACE':control_ns,'PREFIX':scope},
        LAUNCHER: {'NAMESPACE':control_ns,'CONFIG_PATH':predispatch+'/launch-config.json'},
        FINALIZER: {'NAMESPACE':control_ns},
        OBSERVER: {'NAMESPACE':control_ns,'SCOPE_NAME':scope,
            'CONFIG_PATH':predispatch+'/launch-config.json','CAPSULE_PATH':predispatch+'/observer-capsule.json'},
    }
    for path, values in expected.items():
        for name,wanted in values.items():
            if literal(raws[path],name) != wanted: raise ValueError('F identity differs: '+path+':'+name)
    spent = literal(raws[CLAIMS],'SPENT_ACTIVATIONS')
    if len(spent) != 4 or spent[-1] != E_SPENT:
        raise ValueError('Exact a/b/c/E spent tombstones required')
    for path in (ACTIVATION,SPENDING,WORKER,CUSTODY):
        if literal(raws[path],'SPENT_ACTIVATIONS') != spent: raise ValueError('Spent tombstones disagree')
    if literal(raws[CLAIMS],'PUBLIC_SPENT_TOMBSTONES') != (E_PUBLIC,):
        raise ValueError('Exact immutable E public tombstone reference required')
    roots = literal(raws[CUSTODY],'HISTORICAL_RELATIVE_ROOTS')
    if not set(E_EXCLUSIONS) <= set(roots): raise ValueError('E path exclusions missing')
    if literal(raws[WORKER],'FREEZE_NAMESPACE') != 'radio-native-v2-engineering-20260930a':
        raise ValueError('Original freeze schema namespace changed')
    if literal(raws[FREEZER],'NAMESPACE') != 'radio-native-v2-engineering-20260930a':
        raise ValueError('Original freezer namespace changed')
    return True


def review(root=ROOT, *, raws=None, verify_readback=True):
    root = Path(root)
    if raws is None: raws = snapshot(root)
    validate_identities(raws)
    for path,wanted in FIXED_PINS.items():
        if pin_bytes(raws[path]) != wanted: raise ValueError('Immutable v2/Git pin changed: '+path)
    for owner,paths in ((SUPERVISOR,{WORKER,FIXTURE}),
            (FINALIZER,{FIXTURE,WORKER,SUPERVISOR}),(LAUNCHER,set(LAUNCH_TARGETS))):
        if set(literal(raws[owner],'BOOTSTRAP_SOURCE_PINS')) != paths:
            raise ValueError('Fixed bootstrap graph membership differs: '+owner)
    edges = []
    for owner,name,key,target in EDGES:
        table = literal(raws[owner],name)
        supplied = table if key is None else table[key]
        actual = pin_bytes(raws[target])
        if target == GIT: actual = {'path':GIT,**actual}
        edges.append({'owner':owner,'assignment':name,'key':key,'target':target,
            'literal_pin':supplied,'actual_pin':actual,'matches':supplied==actual})
    if verify_readback:
        for path,raw in raws.items():
            if read_regular(source_path(root,path),runtime=path==GIT) != raw:
                raise ValueError('Graph source changed through review: '+path)
    mismatches = [edge for edge in edges if not edge['matches']]
    return {'schema':'radio-native-v3-implementation-graph-review-v1',
        'status':'PASS_EXACT_27_EDGE_GRAPH' if not mismatches else 'BLOCKED_STALE_IMPLEMENTATION_PINS',
        'repository_root':str(root),'relationship_count':len(edges),'mismatch_count':len(mismatches),
        'all_literal_pins_match':not mismatches,'F_identities_and_E_tombstone_verified':True,
        'fixed_v2_and_git_pins_unchanged':True,'edges':edges,
        'source_pins':{path:pin_bytes(raw) for path,raw in raws.items()},
        'source_write_operations':0,'private_journal_content_reads':0,'network_operations':0,
        'original_1190_preservation_checked':False,'execution_authorized':False,
        'scientific_execution_authorized':False,'automatic_retry':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-matching',action='store_true')
    args = parser.parse_args()
    result = review()
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 2 if args.require_matching and not result['all_literal_pins_match'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
