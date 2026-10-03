"""Repartition already verified compressed bytes for bounded public readback.

No evidence execution or source-byte change; use the retained archive utility
to verify/restore the result separately. Source and output paths must differ.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--utility', required=True)
    args = parser.parse_args()
    source, destination = Path(args.archive), Path(args.output)
    utility = Path(args.utility)
    spec = importlib.util.spec_from_file_location('retained_archive_utility', utility)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((source / 'archive-manifest.json').read_bytes())
    source_manifest = (source / 'source-manifest.json').read_bytes()
    if (hashlib.sha256(source_manifest).hexdigest() != original['source_manifest_sha256']
            or len(source_manifest) != original['source_manifest_bytes']
            or original['compressed_bytes'] > 64 * 1024**2):
        raise ValueError('Original manifest identity or bound changed')
    destination.mkdir(parents=True, exist_ok=False)
    sink = module.PartWriter(destination, 512 * 1024, 64 * 1024**2)
    for expected in original['parts']:
        name = expected['filename']
        if Path(name).name != name:
            raise ValueError('Plain original part filename required')
        path = source / name
        before = path.lstat()
        signature = module.file_signature(path)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected['bytes']:
            raise ValueError('Original part size or type changed')
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            while payload := handle.read(64 * 1024):
                digest.update(payload)
                sink.write(payload)
        if digest.hexdigest() != expected['sha256'] or module.file_signature(path) != signature:
            raise ValueError('Original part changed during read')
    sink.close()
    if sink.total != original['compressed_bytes'] or sink.full_hash.hexdigest() != original['compressed_sha256']:
        raise ValueError('Repartition changed compressed archive bytes')
    manifest = copy.deepcopy(original)
    manifest['parts'] = sink.parts
    manifest['fixed_caps']['part_bytes'] = 512 * 1024
    module.write_verified_file(destination / 'source-manifest.json', source_manifest)
    module.write_verified_file(destination / 'archive-manifest.json', module.canonical_json(manifest))
    module.write_verified_file(destination / 'repartition-receipt.json', module.canonical_json({
        'schema': 'setisearch-lossless-archive-repartition-v1', 'status': 'PASS',
        'original_archive_manifest_sha256': hashlib.sha256((source / 'archive-manifest.json').read_bytes()).hexdigest(),
        'compressed_sha256': sink.full_hash.hexdigest(), 'compressed_bytes': sink.total,
        'parts': len(sink.parts), 'maximum_part_bytes': 512 * 1024,
        'source_manifest_sha256': original['source_manifest_sha256'],
        'utility_sha256': hashlib.sha256(utility.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'separate_restore_verification_required': True, 'scientific_admission': False,
    }))
    print(json.dumps({'status': 'PASS', 'compressed_bytes': sink.total,
                      'compressed_sha256': sink.full_hash.hexdigest(), 'parts': len(sink.parts)}))


if __name__ == '__main__':
    main()
