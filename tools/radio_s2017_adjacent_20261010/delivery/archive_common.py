"""Bounded, create-only ZIP assembly and exact CRC/member-byte verification."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import time
import zipfile
from reconstruct_raw_sidecars import confined, digest, require

CAP = 8 * 1024 ** 3
CPU_CAP = 180
WALL_CAP = 1800
MEMORY_CAP = 2 * 1024 ** 3


def workspace_allocated(root):
    """Count allocated blocks once per inode, never follow symbolic links."""
    seen, total = set(), 0
    for folder, dirs, names in os.walk(root, followlinks=False):
        for p in [Path(folder)] + [Path(folder) / x for x in names + dirs]:
            try:
                s = p.lstat()
            except FileNotFoundError:
                continue
            key = (s.st_dev, s.st_ino)
            if key not in seen:
                total += s.st_blocks * 512
                seen.add(key)
    return total


def encode_json(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def save_new(path, value):
    with Path(path).open('xb') as handle:
        handle.write(encode_json(value))
        handle.flush()
        os.fsync(handle.fileno())


def pin(root, relative):
    p = confined(root, relative)
    require(stat.S_ISREG(p.stat().st_mode) and not (root / relative).is_symlink(),
            'Regular source file required')
    return {'path': Path(relative).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}


def limits(started):
    def deadline(signum, frame):
        raise TimeoutError('Archive CPU/wall cap exceeded')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_including_imports': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def assemble(root, stage, filename, payload, kind, context, started):
    """Single attempt; preserves a partial ZIP and failure receipt on error."""
    require(Path(filename).name == filename and filename.endswith('.zip'),
            'Archive filename must be one ZIP basename')
    require(len(payload) == len(set(payload)), 'Duplicate payload paths')
    entries = [pin(root, p) for p in sorted(payload)]
    manifest = {'schema': 'SETI_ADJACENT170_172_PACKAGE_PAYLOAD_MANIFEST_V1',
                'kind': kind, 'context': context, 'files': entries,
                'self_excluded': True, 'archive_checksum_external': True}
    manifest_raw = encode_json(manifest)
    # Stored payload size + ZIP/manifest overhead is a conservative bound even
    # when the RESULTS stream later uses deflate.
    predicted = sum(x['bytes'] for x in entries) + len(manifest_raw) + \
        2 * 1024 * 1024 + 1024 * len(entries)
    before = workspace_allocated(root)
    require(before + predicted <= CAP, 'Conservative8GiB workspace admission failed')
    free = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
    require(free >= predicted, 'Insufficient physical filesystem free space')
    stage.mkdir(parents=True, exist_ok=False)
    archive = stage / filename
    try:
        compression = zipfile.ZIP_STORED if kind == 'RAW' else zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(archive, 'x', compression=compression, compresslevel=None if
                             kind == 'RAW' else 6, allowZip64=True) as z:
            z.writestr('PACKAGE_MANIFEST.json', manifest_raw)
            for index, item in enumerate(entries):
                p = confined(root, item['path'])
                require(p.stat().st_size == item['bytes'] and digest(p) == item['sha256'],
                        'Payload source changed before ZIP write')
                z.write(p, item['path'])
                if item['bytes'] >= 1024 * 1024 or index % 128 == 0:
                    require(workspace_allocated(root) <= CAP, 'Measured workspace cap exceeded')
        with archive.open('rb') as handle:
            os.fsync(handle.fileno())
        with zipfile.ZipFile(archive, 'r') as z:
            require(len(z.infolist()) == len(entries) + 1 and
                    len(set(z.namelist())) == len(entries) + 1, 'ZIP member count or uniqueness differs')
            require(z.read('PACKAGE_MANIFEST.json') == manifest_raw, 'Embedded manifest differs')
            for item in entries:
                h, count = hashlib.sha256(), 0
                with z.open(item['path']) as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b''):
                        count += len(block)
                        h.update(block)
                # Reading every complete member checks its CRC in zipfile too.
                require(count == item['bytes'] and h.hexdigest() == item['sha256'],
                        'ZIP member SHA/byte/CRC check failed')
            require(z.testzip() is None, 'ZIP full CRC check failed')
        for item in entries:
            require(pin(root, item['path']) == item, 'Source changed during package/verification')
        archive_sha = digest(archive)
        use, after = measured(started), workspace_allocated(root)
        require(use['process_CPU_seconds_including_imports'] <= CPU_CAP and
                use['wall_seconds_including_imports'] <= WALL_CAP and
                use['peak_RSS_bytes'] <= MEMORY_CAP and after <= CAP, 'Measured archive cap exceeded')
        receipt = {'status': 'PASS_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256', 'kind': kind,
                   'public_freeze_commit': context['public_freeze_commit'],
                   'archive_path': archive.relative_to(root).as_posix(),
                   'archive_bytes': archive.stat().st_size, 'archive_sha256': archive_sha,
                   'member_count': len(entries) + 1, 'payload_file_count': len(entries),
                   'uncompressed_payload_bytes': sum(x['bytes'] for x in entries),
                   'uncompressed_manifest_bytes': len(manifest_raw), 'context': context,
                   'workspace_unique_allocated_before': before, 'workspace_unique_allocated_after': after,
                   'conservative_addition_admitted_bytes': predicted,
                   'workspace_cap_bytes': CAP, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
                   'memory_cap_bytes': MEMORY_CAP, **use,
                   'new_HTTP_requests': 0, 'new_decoded_power_rows': 0,
                   'new_detector_or_measurement_runs': 0, 'source_payloads_deleted': False,
                   'durable_remote_save_performed': False}
        save_new(stage / 'PACKAGE_RECEIPT.json', receipt)
        return receipt
    except BaseException as error:
        save_new(stage / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_PRESERVE_NO_RETRY_NO_OVERWRITE',
                 'public_freeze_commit': context['public_freeze_commit'],
                 'kind': kind, 'error_type': type(error).__name__, 'error': str(error),
                 'context': context, **measured(started), 'new_HTTP_requests': 0,
                 'source_payloads_deleted': False})
        raise
