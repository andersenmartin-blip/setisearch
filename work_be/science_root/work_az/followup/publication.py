"""Publish validated NPZ/PNG bytes from closed private /tmp staging files.

No overwrites, links, repairs or retries. Failure evidence is copied separately.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import tempfile
import uuid
import zipfile

import numpy as np
from PIL import Image


class PublicationError(RuntimeError):
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__('Publication failed; retained evidence: ' + str(receipt.get('failure_receipt_path')))


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _identity(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def _fingerprint(path):
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Expected regular file')
        h, count = hashlib.sha256(), 0
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
            count += len(block)
        after = os.fstat(f.fileno())
    current = Path(path).lstat()
    if _identity(before) != _identity(after) or _identity(after) != _identity(current) or count != after.st_size:
        raise ValueError('File changed during fingerprint')
    return dict(size_bytes=count, sha256=h.hexdigest(), device=after.st_dev, inode=after.st_ino)


def _same_bytes(a, b):
    return (a['size_bytes'], a['sha256']) == (b['size_bytes'], b['sha256'])


def _same_inode(a, b):
    return (a['device'], a['inode']) == (b['device'], b['inode'])


def _writer_info(f):
    f.flush()
    os.fsync(f.fileno())
    s = os.fstat(f.fileno())
    return dict(size_bytes=s.st_size, device=s.st_dev, inode=s.st_ino)


def _copy_exclusive(source, destination):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    read_flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(source, read_flags), 'rb') as src:
        if not stat.S_ISREG(os.fstat(src.fileno()).st_mode):
            raise ValueError('Copy source must be regular')
        with os.fdopen(os.open(destination, flags, 0o600), 'wb') as dst:
            for block in iter(lambda: src.read(1048576), b''):
                dst.write(block)
            return _writer_info(dst)


def _publish_copy(source, destination):
    # Separate from the evidence-copy primitive for synthetic corruption tests.
    return _copy_exclusive(source, destination)


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _validate_npz(path, arrays):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != {k + '.npy' for k in arrays}:
            raise ValueError('NPZ member identities differ')
        bad = z.testzip()
        if bad is not None:
            raise ValueError('NPZ CRC failure: ' + bad)
    signature = {}
    with np.load(path, allow_pickle=False) as z:
        if set(z.files) != set(arrays):
            raise ValueError('NPZ keys differ')
        for key, expected in arrays.items():
            actual = z[key]
            if (actual.dtype != expected.dtype or actual.shape != expected.shape or
                    actual.tobytes(order='C') != expected.tobytes(order='C')):
                raise ValueError('NPZ typed array differs: ' + key)
            signature[key] = dict(shape=list(actual.shape), dtype=str(actual.dtype),
                dtype_descr=actual.dtype.descr,
                C_order_bytes_sha256=hashlib.sha256(actual.tobytes(order='C')).hexdigest())
    return dict(CRC_verified=True, exact_typed_arrays_verified=True, arrays=signature)


def _validate_png(path):
    with Image.open(path) as im:
        if im.format != 'PNG':
            raise ValueError('Expected PNG')
        im.verify()
    with Image.open(path) as im:
        im.load()
        if im.format != 'PNG' or im.width <= 0 or im.height <= 0:
            raise ValueError('Invalid decoded PNG dimensions')
        return dict(PIL_verify_passed=True, full_pixel_decode_passed=True,
                    width=im.width, height=im.height, mode=im.mode,
                    decoded_pixels_sha256=hashlib.sha256(im.tobytes()).hexdigest())


def _retain_failure(receipt, stage, destination):
    """Preserve independently copied failed bytes; never alter their originals."""
    evidence = destination.parent / 'failed_publication' / uuid.uuid4().hex
    receipt['failure_directory'] = str(evidence)
    receipt['preserved_copies'] = []
    receipt['preservation_errors'] = []
    try:
        evidence.mkdir(parents=True, mode=0o700, exist_ok=False)
        for label, source in [('stage', stage), ('failed_canonical', destination)]:
            if source is None or not os.path.lexists(source):
                continue
            try:
                observed = _fingerprint(source)
                copy = evidence / (label + destination.suffix)
                writer = _copy_exclusive(source, copy)
                copied = _fingerprint(copy)
                if not (_same_bytes(observed, copied) and _same_inode(writer, copied)
                        and not _same_inode(observed, copied)):
                    raise ValueError('Failure evidence copy differs')
                receipt['preserved_copies'].append(dict(kind=label, source=str(source),
                    path=str(copy), original=observed, copy=copied, independent_inode=True))
            except BaseException as error:
                receipt['preservation_errors'].append(dict(kind=label, error=repr(error)))
        receipt_path = evidence / 'FAILURE_RECEIPT.json'
        receipt['failure_receipt_path'] = str(receipt_path)
        temporary = Path(tempfile.mkdtemp(prefix='seti-s-publication-receipt-', dir='/tmp'))/'failure.json'
        with temporary.open('x') as f:
            json.dump(receipt, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n')
            _writer_info(f)
        _copy_exclusive(temporary, receipt_path)
        if not _same_bytes(_fingerprint(temporary), _fingerprint(receipt_path)):
            raise ValueError('Failure receipt copy differs')
        _fsync_dir(evidence)
        _fsync_dir(evidence.parent)
    except BaseException as error:
        receipt['preservation_errors'].append(dict(kind='failure_receipt', error=repr(error)))


def _publish(destination, kind, create_stage, validate):
    destination = Path(destination).absolute()
    private = Path(tempfile.mkdtemp(prefix='seti-s-publication-', dir='/tmp'))
    stage = private / ('artifact.' + kind)
    receipt = dict(schema='SETI_S_CONTEXT_PUBLICATION_V1', format=kind,
        started_utc=_utc(), destination=str(destination), staging_path=str(stage),
        status='FAILED_RETAINED', all_publication_checks_pass=False,
        no_overwrite_repair_or_retry=True)
    try:
        if not destination.parent.is_dir():
            raise FileNotFoundError('Destination parent is absent')
        if destination.parent.resolve() == private or private.is_relative_to(destination.parent.resolve()):
            raise ValueError('Staging must be outside destination tree')
        if os.path.lexists(destination):
            raise FileExistsError('Destination already exists; original retained')
        with stage.open('xb') as f:
            create_stage(f)
            receipt['stage_writer'] = _writer_info(f)
        receipt['stage'] = _fingerprint(stage)
        if not (_same_inode(receipt['stage_writer'], receipt['stage']) and
                receipt['stage_writer']['size_bytes'] == receipt['stage']['size_bytes']):
            raise ValueError('Closed stage writer/path identity differs')
        receipt['stage_validation'] = validate(stage)
        if _fingerprint(stage) != receipt['stage']:
            raise ValueError('Stage changed during format validation')
        receipt['published_writer'] = _publish_copy(stage, destination)
        _fsync_dir(destination.parent)
        receipt['published'] = _fingerprint(destination)
        if not (_same_bytes(receipt['stage'], receipt['published']) and
                _same_inode(receipt['published_writer'], receipt['published']) and
                receipt['published_writer']['size_bytes'] == receipt['published']['size_bytes'] and
                not _same_inode(receipt['stage'], receipt['published'])):
            raise ValueError('Published byte/hash/writer-inode validation failed')
        receipt['published_validation'] = validate(destination)
        if receipt['stage_validation'] != receipt['published_validation']:
            raise ValueError('Decoded stage/publication differ')
        if _fingerprint(destination) != receipt['published']:
            raise ValueError('Published file changed during format validation')
        receipt.update(status='PASS', all_publication_checks_pass=True, completed_utc=_utc())
        return receipt
    except BaseException as error:
        receipt.update(error=repr(error), completed_utc=_utc())
        _retain_failure(receipt, stage if stage.exists() else None, destination)
        raise PublicationError(receipt) from error


def publish_npz(arrays, destination):
    """Publish exact typed arrays; raise PublicationError with retained evidence."""
    expected = {}
    def create(f):
        if any(not isinstance(k, str) or not k or '/' in k or '\\' in k for k in arrays):
            raise ValueError('NPZ keys must be simple nonempty strings')
        expected.update({k: np.array(v, copy=True, subok=False) for k, v in arrays.items()})
        if any(v.dtype.hasobject or v.dtype.metadata for v in expected.values()):
            raise ValueError('Object arrays and dtype metadata are not permitted')
        np.savez_compressed(f, **expected)
    return _publish(destination, 'npz', create, lambda path: _validate_npz(path, expected))


def publish_png(fig, destination, **save_kwargs):
    """Publish a PNG after PIL verification and complete pixel decoding."""
    options = dict(save_kwargs)
    def create(f):
        if options.pop('format', 'png').lower() != 'png':
            raise ValueError('publish_png requires PNG format')
        fig.savefig(f, format='png', **options)
    return _publish(destination, 'png', create, _validate_png)
