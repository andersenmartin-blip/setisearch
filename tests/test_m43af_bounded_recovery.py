import hashlib
import io

import h5py
import numpy as np
import pytest

from m43af_recover_bounded import SegmentReader, plan, MAX_PACKED_BYTES


def segments(tmp_path, payload, spans):
    result = []
    for start, stop in spans:
        data = payload[start:stop]
        (tmp_path / f'{start:016d}-{stop:016d}.part').write_bytes(data)
        result.append(dict(start=start, stop=stop, sha256=hashlib.sha256(data).hexdigest()))
    return result


def test_bounded_reader_hdf5_roundtrip(tmp_path):
    original = np.arange(1600, dtype='<f4').reshape(16, 1, 100)
    buffer = io.BytesIO()
    with h5py.File(buffer, 'w') as handle:
        handle.create_dataset('data', data=original, chunks=(1, 1, 100), compression='gzip')
        handle['data'].attrs['fixture'] = 'exact bytes'
    payload = buffer.getvalue()
    specs = segments(tmp_path, payload, [(i, min(i+511, len(payload))) for i in range(0, len(payload), 511)])
    with SegmentReader(tmp_path, specs, len(payload)) as reader:
        with h5py.File(reader, 'r') as handle:
            np.testing.assert_array_equal(handle['data'][:], original)
            assert handle['data'].attrs['fixture'] == 'exact bytes'


def test_unpublished_gap_is_rejected(tmp_path):
    specs = segments(tmp_path, b'abcdefghij', [(0, 3), (5, 10)])
    with SegmentReader(tmp_path, specs, 10) as reader:
        with pytest.raises(ValueError, match='unpublished'):
            reader.read(7)


def test_corrupt_segment_rejected_before_hdf5(tmp_path):
    specs = segments(tmp_path, b'abcdef', [(0, 6)])
    next(tmp_path.glob('*.part')).write_bytes(b'abXdef')
    with pytest.raises(ValueError, match='digest'):
        SegmentReader(tmp_path, specs, 6)


def test_unbounded_and_oversized_reads_are_rejected(tmp_path):
    specs = segments(tmp_path, b'abcdef', [(0, 6)])
    with SegmentReader(tmp_path, specs, 6) as reader:
        for size in (-1, 33*1024**2):
            with pytest.raises(ValueError, match='oversized'):
                reader.read(size)


def test_overlapping_ranges_rejected(tmp_path):
    specs = segments(tmp_path, b'abcdefghij', [(0, 7), (5, 10)])
    with pytest.raises(ValueError, match='overlapping'):
        SegmentReader(tmp_path, specs, 10)


def test_published_source_disk_bound_without_download(tmp_path):
    bounds = plan('epoch2_on', tmp_path)
    assert bounds['packed_download_bytes'] <= MAX_PACKED_BYTES
    assert bounds['largest_download_file_bytes'] <= 8*1024**2
    assert bounds['required_free_bytes'] < 4*1024**3
    assert bounds['telescope_sized_sparse_file_created'] is False
    assert bounds['new_scientific_evaluations'] == 0
    assert not list(tmp_path.iterdir())
