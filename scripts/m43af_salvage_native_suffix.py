"""Recover complete original sources from the known surviving ZIP suffix.

This is operational recovery only. The missing prefix is never synthesized;
every restored source must match the independent original telescope receipt.
"""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import zipfile

from m43af_recover_bounded import LABELS, WINDOW, file_sha, original_receipt
from m43e_economical_bank import write_sealed
from seti_repeater import source_m43h as source

OFFSET = 419430400
TOTAL = 770327542
SUFFIX_SHA256 = '58f5cfabb8ab13f04a4a8b79770b44ded12ca405dc4d055466d1554e739329f2'
MAX_MEMBER = 16 * 1024**2
RESERVE = 2 * 1024**3


class KnownSuffix(io.RawIOBase):
    def __init__(self, path):
        super().__init__()
        self.handle = path.open('rb')
        self.position = OFFSET

    def close(self):
        self.handle.close()
        super().close()

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=os.SEEK_SET):
        if whence not in (os.SEEK_SET, os.SEEK_CUR, os.SEEK_END):
            raise ValueError('invalid seek')
        p = offset + (0 if whence == os.SEEK_SET else self.position if whence == os.SEEK_CUR else TOTAL)
        if not 0 <= p <= TOTAL:
            raise ValueError('seek outside original archive')
        self.position = p
        return p

    def read(self, size=-1):
        if self.position < OFFSET:
            raise OSError('required ZIP prefix is unavailable')
        if size < 0:
            size = TOTAL - self.position
        if size > MAX_MEMBER:
            raise OSError('oversized ZIP read rejected')
        self.handle.seek(self.position - OFFSET)
        data = self.handle.read(min(size, TOTAL - self.position))
        self.position += len(data)
        return data


def run(path, runtime, output):
    assert path.stat().st_size == TOTAL - OFFSET
    assert file_sha(path) == SUFFIX_SHA256
    runtime.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = output / 'native_suffix_recovery.json'
    assert not receipt_path.exists(), 'preserve completed recovery receipt'
    recovered = []
    with KnownSuffix(path) as stream, zipfile.ZipFile(stream) as archive:
        inventory = archive.infolist()
        assert len({i.filename for i in inventory}) == len(inventory)
        for label in LABELS:
            prefix = f'sources/{label}/{WINDOW}/'
            members = [i for i in inventory if i.filename.startswith(prefix)]
            if len(members) != 50 or any(i.header_offset < OFFSET for i in members):
                continue
            assert all(0 < i.file_size <= MAX_MEMBER and not i.is_dir() for i in members)
            assert shutil.disk_usage(runtime).free > RESERVE + sum(i.file_size for i in members)
            staging = runtime / 'suffix_staging' / label / WINDOW
            staging.mkdir(parents=True, exist_ok=True)
            for item in members:
                name = item.filename[len(prefix):]
                assert name and Path(name).name == name and name not in ('.', '..')
                assert (item.external_attr >> 16) & 0o170000 != 0o120000
                data = archive.read(item)
                assert len(data) == item.file_size
                dest = staging / name
                if dest.exists():
                    assert dest.read_bytes() == data
                else:
                    dest.write_bytes(data)
            original = original_receipt(label)
            assert json.loads((staging / 'source.json').read_text()) == original
            source.rehydrate(staging, original['receipt_sha256'])
            destination = runtime / 'sources' / label / WINDOW
            if destination.exists():
                source.rehydrate(destination, original['receipt_sha256'])
                for item in members:
                    name = item.filename[len(prefix):]
                    assert (destination / name).read_bytes() == (staging / name).read_bytes()
                shutil.rmtree(staging)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                staging.rename(destination)
            recovered.append(dict(scan=label, files=len(members),
                original_receipt_sha256=original['receipt_sha256'],
                source_receipt_exact=True, raw_and_normalized_rows_verified=True))
            print(label + ': all 50 original source files verified from ZIP suffix', flush=True)
    assert [r['scan'] for r in recovered] == ['epoch3_on', 'epoch3_off']
    result = dict(complete=True, suffix_sha256=SUFFIX_SHA256, suffix_offset=OFFSET,
        original_archive_size=TOTAL, recovered_sources=recovered,
        missing_prefix_synthesized=False, telescope_data_downloaded_bytes=0,
        new_scientific_evaluations=0, original_source_arithmetic_changed=False)
    write_sealed(receipt_path, result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suffix', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.suffix, args.runtime_root, args.output)
