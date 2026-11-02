"""Validate deterministic evidence restoration using isolated temporary fixtures.

Run only after native extraction, plots and evidence packaging are complete.
Canonical evidence is checked before and after; all damaged files are temporary.
"""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(script, *args, success=True):
    result = subprocess.run([sys.executable, str(script), *map(str, args)],
                            text=True, capture_output=True)
    require((result.returncode == 0) == success,
            'Unexpected restore result: ' + result.stdout + result.stderr)
    return result


def main():
    manifest = json.loads((ROOT / 'EVIDENCE_ARCHIVE.json').read_text())
    parts = json.loads((ROOT / 'EVIDENCE_PARTS.json').read_text())
    before = {m['path']: sha(ROOT / m['path']) for m in manifest['members']}
    require(all(before[m['path']] == m['sha256'] for m in manifest['members']),
            'Original evidence hash mismatch')
    expected_archive_hash = manifest['sha256']
    fixed_files = ['EVIDENCE.zip', 'EVIDENCE_ARCHIVE.json', 'EVIDENCE_PARTS.json'] + [p['path'] for p in parts['parts']]
    original_package = {name: sha(ROOT / name) for name in fixed_files}
    checks = []

    command(ROOT / 'package_evidence.py')
    require({name: sha(ROOT / name) for name in fixed_files} == original_package,
            'Repeat package build changed deterministic artifacts')
    checks.append(dict(name='DETERMINISTIC_REBUILD', passed=True))

    with tempfile.TemporaryDirectory(prefix='seti_batch05_evidence_restore_') as temporary:
        work = Path(temporary)
        source = work / 'split_only'; source.mkdir()
        for name in ['restore_evidence.py', 'EVIDENCE_ARCHIVE.json', 'EVIDENCE_PARTS.json']:
            shutil.copyfile(ROOT / name, source / name)
        for part in parts['parts']:
            target = source / part['path']; target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / part['path'], target)
        require(not (source / 'EVIDENCE.zip').exists(), 'Fresh restore already has ZIP')
        restored = json.loads(command(source / 'restore_evidence.py').stdout)
        require(restored['created_files'] == manifest['member_count'], 'Fresh restore member count mismatch')
        require(sha(source / 'EVIDENCE.zip') == expected_archive_hash,
                'Reconstructed ZIP hash mismatch')
        require(all(sha(source / m['path']) == m['sha256'] for m in manifest['members']),
                'Fresh restored member hash mismatch')
        checks.append(dict(name='FRESH_SPLIT_ONLY_RECONSTRUCTION_ALL_MEMBERS', passed=True,
                           members=manifest['member_count']))

        mtimes = {m['path']: (source / m['path']).stat().st_mtime_ns for m in manifest['members']}
        repeated = json.loads(command(source / 'restore_evidence.py').stdout)
        require(repeated['created_files'] == 0, 'Identical files were recreated')
        require(all((source / m['path']).stat().st_mtime_ns == mtimes[m['path']]
                    for m in manifest['members']), 'Identical-file modification time changed')
        checks.append(dict(name='IDENTICAL_EXISTING_FILES_RETAINED', passed=True))

        first = manifest['members'][0]
        different = work / 'different_destination'; target = different / first['path']
        target.parent.mkdir(parents=True); target.write_bytes(b'not the original scientific evidence\n')
        damaged = target.read_bytes()
        refused = command(source / 'restore_evidence.py', '--destination', different, success=False)
        require('Existing evidence differs' in refused.stderr and target.read_bytes() == damaged,
                'Different evidence was not safely refused')
        require([p for p in different.rglob('*') if p.is_file()] == [target],
                'Refused destination received unexpected files')
        checks.append(dict(name='DIFFERENT_EXISTING_FILE_REFUSED_BEFORE_EXTRACTION', passed=True))

        linked = work / 'symlink_destination'; target = linked / first['path']
        target.parent.mkdir(parents=True); target.symlink_to(ROOT / first['path'])
        refused = command(source / 'restore_evidence.py', '--destination', linked, success=False)
        require('Symlink destination refused' in refused.stderr and target.is_symlink(),
                'Symlink evidence was not safely refused')
        require([p for p in linked.rglob('*') if p.is_file()] == [target],
                'Refused symlink destination received unexpected files')
        checks.append(dict(name='SYMLINK_DESTINATION_REFUSED', passed=True))

        corrupt = work / 'corrupt_part'; corrupt.mkdir()
        for name in ['restore_evidence.py', 'EVIDENCE_ARCHIVE.json', 'EVIDENCE_PARTS.json']:
            shutil.copyfile(ROOT / name, corrupt / name)
        for part in parts['parts']:
            target = corrupt / part['path']; target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / part['path'], target)
        target = corrupt / parts['parts'][0]['path']
        data = bytearray(target.read_bytes()); data[-1] ^= 1; target.write_bytes(data)
        refused = command(corrupt / 'restore_evidence.py', '--verify-only', success=False)
        require('Part hash/size mismatch' in refused.stderr and not (corrupt / 'EVIDENCE.zip').exists(),
                'Corrupt part was not refused before ZIP reconstruction')
        checks.append(dict(name='CORRUPT_PART_REFUSED_BEFORE_RECONSTRUCTION', passed=True))

    require(all(sha(ROOT / name) == h for name, h in before.items()), 'Original evidence mutated')
    require({name: sha(ROOT / name) for name in fixed_files} == original_package,
            'Original package artifacts mutated')
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='PASS', archive_sha256=expected_archive_hash, archive_bytes=manifest['bytes'],
        member_count=manifest['member_count'], native_cutouts=manifest['native_cutouts'],
        reference_grids=manifest['reference_grids'], part_count=len(parts['parts']),
        checks=checks, restore_script_sha256=sha(ROOT / 'restore_evidence.py'),
        package_script_sha256=sha(ROOT / 'package_evidence.py'),
        validation_script_sha256=sha(Path(__file__)), mutated_original_evidence=False)
    (ROOT / 'EVIDENCE_RESTORE_VALIDATION.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', checks=len(checks), members=manifest['member_count'],
                         archive_sha256=expected_archive_hash), indent=2))


if __name__ == '__main__':
    main()
