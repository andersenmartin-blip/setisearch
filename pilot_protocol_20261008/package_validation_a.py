#!/usr/bin/env python3
"""Deterministically preserve original complete VAL_A bytes; no scientific work."""
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import resource
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/radio_pilot_validation_a_20261008'
DEST = ROOT / 'pilot_protocol_20261008/validation_a_archives'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def byte_receipt(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()}


def archive(path, files):
    members = []
    # Fixed ordering, zero gzip/tar timestamps, fixed IDs/names/modes. Source
    # bytes are copied verbatim, and source stat changes close this operation.
    with path.open('xb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tf:
                for source in sorted(files):
                    if source.is_symlink() or not source.is_file():
                        raise ValueError(f'Only ordinary original files allowed: {source}')
                    before = source.stat()
                    raw = source.read_bytes()
                    after = source.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError(f'Original file changed during preservation: {source}')
                    name = source.relative_to(ROOT).as_posix()
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.uid, info.gid = len(raw), 0o644, 0, 0
                    info.uname = info.gname = ''
                    info.mtime = 0
                    tf.addfile(info, io.BytesIO(raw))
                    members.append({'path': name, 'bytes': len(raw),
                                    'sha256': hashlib.sha256(raw).hexdigest()})
    receipt = byte_receipt(path)
    receipt.update(member_count=len(members), original_member_bytes=sum(x['bytes'] for x in members), members=members)
    return receipt


def main():
    start, cpu = time.monotonic(), time.process_time()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    completion_file = BASE / 'completion.json'
    completion = json.loads(completion_file.read_text())  # Never wait or generate.
    if len(completion['results']) != 142 or sorted(x['index'] for x in completion['results']) != list(range(142)):
        raise ValueError('Complete original 142-case completion receipt required')
    claims = sorted((ROOT / 'pilot_protocol_20261008/validation_a_claims').glob('*.json'))
    if len(claims) != 142:
        raise ValueError('Exactly142 canonical original claims required')
    publication = ROOT / 'pilot_protocol_20261008/validation_freeze_publication.json'
    if not publication.is_file():
        raise ValueError('Original public freeze receipt required')
    cases = []
    required = {'admission.json', 'truth.json', 'synthetic_array_hashes.json',
                'resource_receipt.json', 'outcome.json', 'outcomes.json',
                'artifact_manifest.json'}
    expected_completed_members = {'scan_map_metadata.json',
                                  *[f'scan_{j:02d}_full_map.npz' for j in range(6)]}
    for i in range(142):
        directory = BASE / f'case_{i:03d}'
        files = sorted(directory.rglob('*'))
        files = [f for f in files if f.is_file()]
        if not required.issubset({f.name for f in files}):
            raise ValueError(f'Original complete case members missing: {i}')
        for prefix, suffix in [('command_', '.json'), ('admission_', '.json'), ('case_', '.log')]:
            if not (BASE / f'{prefix}{i:03d}{suffix}').is_file():
                raise ValueError(f'Original coordinator member missing: {i}')
        cases.append((files, sorted(expected_completed_members - {f.name for f in files})))
    DEST.mkdir()  # No deletion, replacement or archival replay.
    archives = []
    for i, (files, absent) in enumerate(cases):
        record = archive(DEST / f'case_{i:03d}.tar.gz', files)
        record.update(index=i, case_id=completion['results'][i]['case_id'],
                      missing_normal_completion_members=absent,
                      source_returncode=completion['results'][i]['returncode'])
        write(DEST / f'case_{i:03d}_manifest.json', record)
        archives.append(record)
        if (i + 1) % 20 == 0:
            print(f'Preserved {i+1}/142 cases', flush=True)
    coordinator_files = [f for f in BASE.iterdir() if f.is_file()]
    coordinator_files += claims + [publication, ROOT / 'pilot_protocol_20261008/validation_a_admission.json']
    coordinator = archive(DEST / 'coordinator_evidence.tar.gz', coordinator_files)
    write(DEST / 'coordinator_evidence_manifest.json', coordinator)
    manifest = {'schema': 'setisearch-val-a-complete-deterministic-archives-v1',
                'panel': 'VAL_A', 'case_count': 142, 'synthetic_control_bytes_only': True,
                'generation_search_or_numeric_decode_performed': False,
                'originals_preserved': True, 'failed_originals_preserved_without_manufacturing_maps': True,
                'deterministic_tar_and_gzip': True,
                'gzip_mtime': 0, 'tar_mtime': 0, 'tar_uid_gid': [0,0], 'tar_mode': '0644',
                'completion_original': byte_receipt(completion_file),
                'archives': archives, 'coordinator_evidence': coordinator,
                'total_archive_bytes': sum(x['bytes'] for x in archives) + coordinator['bytes'],
                'total_archived_original_member_bytes': sum(x['original_member_bytes'] for x in archives) + coordinator['original_member_bytes']}
    write(ROOT / 'pilot_protocol_20261008/validation_a_archives_manifest.json', manifest)
    receipt = {'phase': 'deterministic_VAL_A_archival_packaging', 'started_utc': started_utc,
               'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'wall_s': time.monotonic()-start, 'cpu_s': time.process_time()-cpu,
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
               'archive_count': len(archives)+1, 'total_archive_bytes': manifest['total_archive_bytes'],
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'scope': 'Whole packaging Python process through manifest creation; excludes subsequent MCP/network upload, whose CPU is unmeasured rather than zero.',
               'scientific_work_performed': False}
    write(ROOT / 'pilot_protocol_20261008/validation_a_packaging_resource_receipt.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
