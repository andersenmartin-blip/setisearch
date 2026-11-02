"""Restore exact published discovery references and derived comparison profiles."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'PROFILE_EVIDENCE.json').read_bytes())
    archive_path = HERE / manifest['archive']
    raw = archive_path.read_bytes()
    if len(raw) != manifest['bytes'] or sha(raw) != manifest['sha256']:
        raise ValueError('Evidence archive mismatch')
    expected = {row['path']: row for row in manifest['members']}
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError('Evidence member set mismatch')
        restored = []
        for name, row in expected.items():
            destination = (HERE / name).resolve()
            if not any(destination.is_relative_to(HERE / prefix) for prefix in ['inputs/profiles', 'results/profiles']):
                raise ValueError('Unexpected profile destination')
            data = archive.read(name)
            if len(data) != row['bytes'] or sha(data) != row['sha256']:
                raise ValueError('Profile mismatch: ' + name)
            if destination.exists() and destination.read_bytes() != data:
                raise FileExistsError('Preserve differing existing profile: ' + name)
            restored.append((destination, data))
        if not args.verify_only:
            for destination, data in restored:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    with destination.open('xb') as stream:
                        stream.write(data)
    print(json.dumps({'status': 'PASS_EXACT_PROFILE_EVIDENCE', 'discovery_references': manifest['discovery_references'],
                      'new_comparison_profiles': manifest['new_comparison_profiles'], 'members': len(expected),
                      'sha256': manifest['sha256'], 'mode': 'verify_only' if args.verify_only else 'restore'}, indent=2))


if __name__ == '__main__':
    main()
