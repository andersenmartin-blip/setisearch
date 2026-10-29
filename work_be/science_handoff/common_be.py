"""Read-only evidence resolution and fail-closed BE adapter primitives.

No network, runtime installation, telescope decoding, or release on import.
Relocation is explicit and hash-bound by each phase's external GO record.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work_be'
LINEAGE = {'inherited_BB_rows': 87, 'inherited_BC_rows': 1, 'inherited_rows': 88,
           'new_rows': 8, 'total_rows': 96,
           'inherited_repeat_checks': 5, 'new_repeat_checks': 1}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def utc():
    return datetime.now(timezone.utc).isoformat()


class Context:
    def __init__(self, evidence_root, relocations_path):
        self.root = ROOT
        self.work = WORK
        self.evidence = Path(evidence_root).resolve()
        require(self.evidence.is_relative_to(ROOT), 'Evidence root escapes workspace')
        self.relocations_path = Path(relocations_path).resolve()
        require(self.relocations_path.is_relative_to(ROOT) and self.relocations_path.is_file(),
                'Explicit local relocation map required')
        config = read(self.relocations_path)
        require(config['schema'] == 'SETI_BE_EXPLICIT_RELOCATIONS_V1', 'Relocation schema differs')
        require(config['network_requests_authorized'] == 0, 'Relocations cannot grant network access')
        self.relocations = []
        for entry in config['mappings']:
            source = Path(entry['from'])
            dest = Path(entry['to'])
            dest = (ROOT / dest).resolve() if not dest.is_absolute() else dest.resolve()
            require(source.is_absolute() and '..' not in source.parts, 'Unsafe historical root')
            require(dest.is_relative_to(self.evidence), 'Relocation must land under evidence root')
            self.relocations.append((source, dest))
        require(len({str(x[0]) for x in self.relocations}) == len(self.relocations),
                'Duplicate historical relocation prefix')
        self.relocations.sort(key=lambda pair: len(pair[0].parts), reverse=True)

    def resolve(self, value):
        path = Path(value)
        require('..' not in path.parts, 'Unsafe path traversal')
        if path.is_absolute() and not path.is_relative_to(ROOT):
            matches = [(old, dest) for old, dest in self.relocations if path.is_relative_to(old)]
            require(bool(matches), 'Unmapped historical absolute path: ' + str(path))
            old, dest = matches[0]
            path = dest / path.relative_to(old)
        elif not path.is_absolute():
            # Legacy BB/BC logical paths resolve only through the declared root.
            path = self.evidence / path if path.parts and path.parts[0] in ('work_bb', 'work_bc', 'work_be', 'restore_bb', 'restored_ba') else ROOT / path
        path = path.resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), 'Missing or external evidence file: ' + str(path))
        return path

    def pin(self, value, pins, expected=None):
        path = self.resolve(value)
        digest = sha(path)
        require(expected is None or digest == expected, 'Evidence hash differs: ' + str(path))
        require(str(path) not in pins or pins[str(path)] == digest, 'Conflicting prior pin')
        pins[str(path)] = digest
        return path

    def actual(self, value, expected, pins):
        path = self.pin(value, pins)
        actual = read(path)
        require(actual['actual_exit_code'] == expected and actual['stdout_eof'] is True
                and actual['child_wait_completed'] is True, 'Actual phase exit/EOF/wait differs')
        log = self.pin(actual['log_path'], pins, actual['log_sha256'])
        require(log.stat().st_size == actual['log_bytes'], 'Actual phase log length differs')
        return actual

    def verify_pins(self, pins):
        for path, digest in pins.items():
            require(sha(self.resolve(path)) == digest, 'Source/evidence mutated: ' + path)

    def pin_relocations(self, go, pins):
        require(go['relocations_sha256'] == sha(self.relocations_path), 'Relocation map is not GO-bound')
        self.pin(self.relocations_path, pins, go['relocations_sha256'])
        require(self.resolve(go['relocations_path']) == self.relocations_path, 'GO relocation path differs')

