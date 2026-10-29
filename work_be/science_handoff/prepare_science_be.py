"""Prepare a new BE engine from the hash-bound, unchanged BC copy.

--check validates source identities without copying. --prepare writes only a
fresh engine source tree, runtime symlink and preparation metadata. No powers,
network, detector execution, plan refreeze, or release record are produced.
"""
from datetime import datetime, timezone
import argparse
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from common_be import Context, sha, read, new, require

BASE = Path(__file__).resolve().parents[2]
WORK = BASE / 'work_be'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['check', 'prepare'])
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--relocations', required=True)
    a = parser.parse_args()
    ctx = Context(a.evidence_root, a.relocations)
    previous_path = ctx.resolve('work_bc/SCIENCE_SOURCE_PREPARATION_BC.json')
    previous = read(previous_path)
    require(previous['status'] == 'PASS' and previous['numerical_sources_changed'] is False,
            'Original unchanged-engine preparation proof required')
    source = ctx.evidence / 'work_bc/science_root/work_az'
    dest = WORK / 'science_root/work_az'
    require(source.is_dir(), 'Missing original source engine')
    paths = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix in ('.py', '.json'))
    require(len(paths) == 33 and sum(p.suffix == '.py' for p in paths) == 25,
            'Expected only 33 original engine files (25 Python)')
    oldpairs = {ctx.resolve(x['copied_path']): x for x in previous['source_pairs']}
    require(set(oldpairs) == set(paths), 'Current engine files differ from frozen preparation')
    pins, pairs = {}, []
    ctx.pin(previous_path, pins)
    ctx.pin(ctx.relocations_path, pins)
    for path in paths:
        pair = oldpairs[path]
        require(pair['byte_identical'] is True, 'Original source pair not byte identical')
        ctx.pin(path, pins, pair['sha256'])
        pairs.append({'original_path': str(path), 'copied_path': str(dest / path.relative_to(source)),
                      'sha256': pair['sha256'], 'byte_identical': True})
    ctx.verify_pins(pins)
    if a.action == 'check':
        print('PASS_BE_UNCHANGED_ENGINE_SOURCES_NO_WRITES')
        return
    require(not dest.exists() and not (WORK / 'SCIENCE_SOURCE_PREPARATION_BE.json').exists(),
            'Fresh BE preparation required; no automatic restart')
    for pair in pairs:
        sourcepath, target = Path(pair['original_path']), Path(pair['copied_path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), 'Copy target already exists')
        # Exclusive output preserves a partially prepared tree on any failure.
        with sourcepath.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        require(sha(target) == pair['sha256'], 'Copied engine source differs')
    (dest / 'runtime').symlink_to(WORK / 'runtime', target_is_directory=True)
    ctx.verify_pins(pins)
    record = {'schema': 'SETI_BE_IDENTICAL_BB_BC_ENGINE_PREPARATION_V1', 'status': 'PASS',
              'prepared_utc': datetime.now(timezone.utc).isoformat(), 'source_pairs': pairs,
              'parent_preparation_path': str(previous_path), 'parent_preparation_sha256': sha(previous_path),
              'source_and_state_sha256': pins, 'numerical_sources_changed': False,
              'metadata_or_expression_substitutions': [], 'engine_topology': 'Legacy work_az under fresh BE science_root',
              'followup_timing': 'Original BB producer/reviewer plans are inherited byte-identically; no refreeze after BB87+BC1 powers.',
              'runtime': 'Symlink only; runtime identity is checked before later native/science execution. Historical RUNTIME_AZ remains unchanged.',
              'target_power_arrays_opened': False, 'network_requests': 0, 'scientific_execution_authorized': False}
    new(WORK / 'SCIENCE_SOURCE_PREPARATION_BE.json', record)
    print('PASS_BE_UNCHANGED_ENGINE_PREPARED_NO_RELEASE')


if __name__ == '__main__':
    main()
