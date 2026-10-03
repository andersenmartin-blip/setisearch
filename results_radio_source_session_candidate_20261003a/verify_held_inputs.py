"""Verify retained file identities; no execution or lifetime qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import os

ROOT = Path('/workspace/scratch/fb4056c33767')


def digest_file(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    after = path.stat()
    names = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, n) != getattr(after, n) for n in names):
        raise ValueError('File changed during verification: ' + str(path))
    return digest.hexdigest(), after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    reports = []
    for baseline_name, root_key, fallback, check_stat in (
        ('frozen-project/snapshot.json', 'snapshot_root', ROOT/'frozen-project', False),
        ('runtime-before.json', 'runtime_root', None, True),
    ):
        path = ROOT / baseline_name
        baseline_digest, _ = digest_file(path)
        baseline = json.loads(path.read_bytes())
        folder = Path(baseline.get(root_key, fallback))
        byte_count = 0
        for expected in baseline['files']:
            digest, details = digest_file(folder / expected['path'])
            if digest != expected['sha256'] or details.st_size != expected['bytes']:
                raise ValueError('Held file payload differs: ' + expected['path'])
            if check_stat:
                for field, attribute in (('device', 'st_dev'), ('inode', 'st_ino'),
                                         ('mtime_ns', 'st_mtime_ns'), ('ctime_ns', 'st_ctime_ns')):
                    if details.__getattribute__(attribute) != expected[field]:
                        raise ValueError('Observed runtime file identity differs: ' + expected['path'])
            byte_count += details.st_size
        reports.append({'baseline': str(path), 'baseline_sha256': baseline_digest,
                        'files_checked': len(baseline['files']), 'bytes_checked': byte_count,
                        'all_payloads_unchanged': True, 'recorded_runtime_file_stats_checked': check_stat})
    report = {'schema': 'setisearch-retained-input-file-verification-v1', 'status': 'PASS',
              'baselines': reports, 'complete_runtime_or_lifetime_certificate': False,
              'telescope_or_holdout_payloads_read': False, 'scientific_admission': False}
    with Path(args.output).open('xb') as handle:
        handle.write((json.dumps(report, indent=2) + '\n').encode())
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({'status': 'PASS', 'counts': [x['files_checked'] for x in reports]}))


if __name__ == '__main__':
    main()
