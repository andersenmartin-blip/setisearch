"""Closed-stream integrity fences and exclusive atomic JSONL publication.

Publication prevents partial content from appearing at the final pathname.
It does not prove that a file can never change later. The complete manifest
must therefore be verified at child end, at parent end, and by the independent
final review. An earlier PASS never overrides a later integrity failure.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import os
import re
import stat

METHODS = ('current', 'legacy')
STATES = ('PASS', 'UNSUPPORTED', 'THREE_ON_FAIL', 'OFF_VETO')
MAX_LINE_BYTES = 8*1024*1024


class ClosureError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(ok, code, message):
    if not ok:
        raise ClosureError(code, message)


def specification():
    return {
        'schema': 'SETI_BR_STREAM_CLOSURE_SPEC_V1',
        'manifest_methods': list(METHODS),
        'receipt_fields': ['path', 'bytes', 'sha256', 'records', 'complete'],
        'path_policy': 'Canonical absolute nonsymlink payload directory; stream paths must be plain basenames, no slash/backslash/NUL/dot/dotdot',
        'file_policy': 'O_NOFOLLOW and O_NONBLOCK, regular files only, stable fd/path device+inode+size+mtime+ctime during reading',
        'verification': 'Every saved byte streamed into SHA256; exact size/record count; each line newline-terminated strict finite JSON object; status counts/source_ON_hits/flags match manifest',
        'max_JSONL_record_bytes': MAX_LINE_BYTES,
        'publication': 'Exclusive .<name>.pending write; flush, chmod0444, fsync, close, verify pending, atomic exclusive hardlink to final, fsync directory, verify final, unlink pending, fsync directory, verify final again',
        'no_overwrite': True,
        'fences': ['child_end', 'parent_end', 'independent_review'],
        'cross_fence_comparison': 'Compare complete stream receipts including device/inode/size/mtime/ctime and content counters',
        'effective_status': 'FAIL for any closure exception or receipt change, irrespective of earlier child or computation PASS',
        'limitations': 'A point-in-time integrity check does not establish why earlier files changed or prevent mutation after the last check.',
        'scientific_changes': 'None: no input generation, normalization, scan scoring, candidate changes or endpoint changes.',
    }


def _name(value):
    require(isinstance(value, str) and value not in ('', '.', '..')
            and '/' not in value and '\\' not in value and '\x00' not in value
            and not Path(value).is_absolute(), 'UNSAFE_PATH', 'Stream path must be a safe basename')
    return value


def _open_payload(payload):
    path = Path(payload)
    require(path.is_absolute(), 'PAYLOAD_PATH', 'Payload path must be absolute')
    require(not path.is_symlink(), 'PAYLOAD_SYMLINK', 'Payload directory cannot be a symlink')
    require(path.absolute() == path.resolve(strict=True), 'PAYLOAD_ALIAS', 'Payload path must be canonical without symlink components')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path, flags)
    info = os.fstat(fd)
    require(stat.S_ISDIR(info.st_mode), 'PAYLOAD_TYPE', 'Payload must be a directory')
    return path, fd, (info.st_dev, info.st_ino)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, stat.S_IFMT(info.st_mode))


def _strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'DUPLICATE_JSON_KEY', 'Duplicate JSON object key')
        value[key] = item
    return value


def _bad_constant(value):
    raise ClosureError('NONFINITE_JSON', 'Nonfinite JSON constant '+value)


def _finite_json(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'NONFINITE_JSON', 'JSON number overflowed to nonfinite')
    elif isinstance(value, dict):
        for item in value.values():
            _finite_json(item)
    elif isinstance(value, list):
        for item in value:
            _finite_json(item)


def _receipt(receipt):
    require(isinstance(receipt, dict), 'BAD_RECEIPT', 'Association stream receipt must be an object')
    require(set(receipt) >= {'path','bytes','sha256','records','complete'}, 'BAD_RECEIPT', 'Incomplete association receipt')
    _name(receipt['path'])
    for key in ('bytes','records'):
        require(isinstance(receipt[key], int) and not isinstance(receipt[key], bool) and receipt[key] >= 0,
                'BAD_RECEIPT', 'Receipt count must be a nonnegative integer')
    require(isinstance(receipt['sha256'], str) and re.fullmatch('[0-9a-f]{64}', receipt['sha256']) is not None,
            'BAD_RECEIPT', 'Invalid receipt SHA256')
    require(receipt['complete'] is True, 'INCOMPLETE_STREAM', 'Stream receipt is not closed')


def _verify_named_stream(directory_fd, receipt):
    _receipt(receipt)
    name = receipt['path']
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise ClosureError('OPEN_FAILED', 'Stream missing, symlinked or unreadable: '+name) from exc
    try:
        start = os.fstat(fd)
        require(stat.S_ISREG(start.st_mode), 'NONREGULAR_STREAM', 'Stream is not a regular file: '+name)
        path_start = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        require(stat.S_ISREG(path_start.st_mode) and _identity(start) == _identity(path_start),
                'PATH_IDENTITY', 'Opened descriptor does not match stream pathname')
        require(start.st_size == receipt['bytes'], 'BYTE_COUNT', 'Stream byte count differs: '+name)
        digest, byte_count, record_count = hashlib.sha256(), 0, 0
        counts = {state: 0 for state in STATES}
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            while True:
                line = stream.readline(MAX_LINE_BYTES+1)
                if not line:
                    break
                require(len(line) <= MAX_LINE_BYTES, 'RECORD_TOO_LONG', 'JSONL record exceeds fixed validation cap')
                digest.update(line)
                byte_count += len(line)
                require(line.endswith(b'\n'), 'MISSING_NEWLINE', 'Incomplete final JSONL record: '+name)
                require(line != b'\n', 'EMPTY_RECORD', 'Empty JSONL record')
                try:
                    record = json.loads(line.decode('utf-8'), object_pairs_hook=_strict_pairs, parse_constant=_bad_constant)
                except ClosureError:
                    raise
                except (ValueError, UnicodeError, RecursionError) as exc:
                    raise ClosureError('INVALID_JSON', 'Invalid UTF-8 JSONL record: '+name) from exc
                require(isinstance(record, dict), 'RECORD_SCHEMA', 'Association record must be a JSON object')
                _finite_json(record)
                require(record.get('status') in counts, 'RECORD_STATUS', 'Unknown association status in stream')
                counts[record['status']] += 1
                record_count += 1
        end = os.fstat(fd)
        path_end = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        require(stat.S_ISREG(path_end.st_mode) and _identity(start) == _identity(end) == _identity(path_end),
                'POSTCLOSE_MUTATION', 'Stream changed while its closed receipt was being verified')
        require(byte_count == receipt['bytes'], 'BYTE_COUNT', 'Read byte count differs: '+name)
        require(digest.hexdigest() == receipt['sha256'], 'SHA256', 'Stream SHA256 differs: '+name)
        require(record_count == receipt['records'], 'RECORD_COUNT', 'Stream record count differs: '+name)
        return {'path':name, 'bytes':byte_count, 'sha256':digest.hexdigest(), 'records':record_count,
                'status_counts':counts, 'file_device':end.st_dev, 'file_inode':end.st_ino,
                'mtime_ns':end.st_mtime_ns, 'ctime_ns':end.st_ctime_ns, 'complete':True}
    finally:
        os.close(fd)


def verify_manifest_streams(payload, result):
    """Read-only exact verification of both complete association streams."""
    require(isinstance(result, dict) and isinstance(result.get('method_results'), dict),
            'RESULT_SCHEMA', 'Result must contain method_results')
    require(set(result['method_results']) == set(METHODS), 'RESULT_METHODS', 'Both and only current/legacy methods required')
    path, directory_fd, root_identity = _open_payload(payload)
    try:
        output = []
        seen = set()
        for method in METHODS:
            item = result['method_results'][method]
            receipt = item.get('association_stream')
            _receipt(receipt)
            require(receipt['path'] not in seen, 'DUPLICATE_STREAM', 'Methods cannot share one association stream')
            seen.add(receipt['path'])
            verified = _verify_named_stream(directory_fd, receipt)
            require(item.get('association_counts') == verified['status_counts'],
                    'STATUS_COUNTS', 'Association status counters differ: '+method)
            require(item.get('source_ON_hits') == verified['records'],
                    'SOURCE_COUNT', 'Source catalogue count differs from complete stream: '+method)
            require(item.get('flags') == verified['status_counts']['PASS'],
                    'FLAG_COUNT', 'Flag count differs from stream: '+method)
            output.append({'method':method, **verified})
        root_end = os.stat(path, follow_symlinks=False)
        require(stat.S_ISDIR(root_end.st_mode) and (root_end.st_dev,root_end.st_ino) == root_identity,
                'PAYLOAD_REPLACED', 'Payload pathname changed during validation')
        return {'schema':'SETI_BR_STREAM_BINDING_CHECK_V1', 'status':'PASS',
                'streams':output, 'total_records':sum(x['records'] for x in output),
                'total_bytes':sum(x['bytes'] for x in output)}
    finally:
        os.close(directory_fd)


def evaluate_closure(payload, result, stage, previous_check=None):
    """Return an explicit effective FAIL on any integrity failure at a fence."""
    require(stage in ('child_end','parent_end','independent_review'), 'BAD_STAGE', 'Unknown closure fence')
    computation_status = result.get('status') if isinstance(result,dict) else None
    try:
        verified = verify_manifest_streams(payload,result)
        if previous_check is not None:
            require(previous_check.get('status') == 'PASS' and previous_check.get('effective_status') == 'PASS',
                    'PREVIOUS_FENCE_FAILED', 'Previous closure fence was not a complete PASS')
            require(previous_check.get('verification') == verified,
                    'CROSS_FENCE_MUTATION', 'Stream identities or content changed after previous closure fence')
        return {'schema':'SETI_BR_EFFECTIVE_CLOSURE_V1','stage':stage,'status':'PASS',
                'computation_status_preserved':computation_status,
                'effective_status':'PASS' if computation_status=='PASS' else 'FAIL',
                'verification':verified}
    except Exception as exc:
        return {'schema':'SETI_BR_EFFECTIVE_CLOSURE_V1','stage':stage,'status':'FAIL',
                'computation_status_preserved':computation_status,'effective_status':'FAIL',
                'error_code':getattr(exc,'code',type(exc).__name__),'error':str(exc)}


class AtomicJSONLPublisher:
    """Publish an exclusive immutable-name stream only after complete closure."""
    def __init__(self,payload,filename):
        self.path,self.directory_fd,self.root_identity = _open_payload(payload)
        self.filename = _name(filename)
        self.pending = _name('.'+self.filename+'.pending')
        self.closed = False
        self.published = False
        self.digest = hashlib.sha256()
        self.bytes,self.records = 0,0
        try:
            try:
                os.stat(self.filename,dir_fd=self.directory_fd,follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError('Final association stream already exists: '+self.filename)
            fd = os.open(self.pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.directory_fd)
            self.stream = os.fdopen(fd,'wb',buffering=1048576)
        except BaseException:
            os.close(self.directory_fd)
            self.directory_fd = None
            raise

    def append(self,record):
        require(not self.closed,'WRITER_CLOSED','Publisher is closed')
        payload=(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
        require(len(payload)<=MAX_LINE_BYTES,'RECORD_TOO_LONG','Record exceeds fixed publication cap')
        written=self.stream.write(payload)
        require(written==len(payload),'SHORT_WRITE','Incomplete pending-stream write')
        self.digest.update(payload)
        self.bytes+=len(payload)
        self.records+=1

    def close(self):
        require(not self.closed,'WRITER_CLOSED','Publisher already closed')
        receipt={'path':self.filename,'bytes':self.bytes,'sha256':self.digest.hexdigest(),
                 'records':self.records,'complete':True}
        try:
            self.stream.flush()
            os.fchmod(self.stream.fileno(),0o444)
            os.fsync(self.stream.fileno())
            self.stream.close()
            self.closed=True
            _verify_named_stream(self.directory_fd,{**receipt,'path':self.pending})
            # Hardlink creation is atomic and fails if final already exists;
            # unlike rename(), it can never silently overwrite earlier evidence.
            os.link(self.pending,self.filename,src_dir_fd=self.directory_fd,
                    dst_dir_fd=self.directory_fd,follow_symlinks=False)
            self.published=True
            os.fsync(self.directory_fd)
            _verify_named_stream(self.directory_fd,receipt)
            # Remove only this writer's closed pending name after verified final
            # publication. Failed or partial pending files are never discarded.
            os.unlink(self.pending,dir_fd=self.directory_fd)
            os.fsync(self.directory_fd)
            _verify_named_stream(self.directory_fd,receipt)
            root_end=os.stat(self.path,follow_symlinks=False)
            require(stat.S_ISDIR(root_end.st_mode) and (root_end.st_dev,root_end.st_ino)==self.root_identity,
                    'PAYLOAD_REPLACED','Publisher payload pathname changed')
            return receipt
        finally:
            if not self.closed:
                self.close_partial()
            if self.directory_fd is not None:
                os.close(self.directory_fd)
                self.directory_fd=None

    def close_partial(self):
        if not self.closed:
            try:
                self.stream.flush()
                os.fsync(self.stream.fileno())
            finally:
                self.stream.close()
                self.closed=True
        if self.directory_fd is not None:
            os.close(self.directory_fd)
            self.directory_fd=None
