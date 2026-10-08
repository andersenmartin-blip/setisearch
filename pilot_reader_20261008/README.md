# Prospective bounded pilot reader — preparation only

`value_reader.py` is inert at import. It has not been executed and no source
payload or numeric values have been fetched for its preparation. Fetching is
closed until fresh independent validation passes and root admits the specific
source, validation-summary and cumulative-source-ledger SHA256s.

The source contract is `pilot_source_20261008/primary/source_manifest.json`:
six complete scans, 16 time rows each, exactly 96 metadata-qualified payload
ranges totalling 305,133,821 bytes. It retains original URLs, strong ETags,
file lengths, range offsets, little-endian float32 type, filter masks and
physical `[1,1,1048576]` chunks. There is no source enumeration, full-file GET,
redirect, automatic retry or alternative URL. Existing metadata source bytes
are charged before any prospective GET against the 2 GiB cadence ceiling.

The admitted job checks HTTP 206, exact ETag, Content-Range, Content-Length and
identity encoding before reading each bounded body. Partial/failing reads are
logged and charged; a failure closes the run. Every request's full allowed body
length plus one overflow-check byte is charged prospectively against the
ceiling, separately from observed received bytes, so a failed or interrupted
request cannot erase its possible consumption. One new output directory is used;
an existing output cannot be resumed. The ordinary job has a 30-minute wall
deadline, 4 GiB address-space guard, 8 GiB artifact ceiling and measured wall,
CPU and peak RSS. The guard is an address-space bound, not a measurement of RAM.

Compressed bytes are copied unchanged with the supported `write_direct_chunk`
API into six compact normal HDF5 datasets of shape `[16,1,1048576]`. The source
frequency-chunk origin is recorded separately; compact chunk origins are
rebased to `[row,0,0]`. Every stored raw chunk and its filter mask are read back
and compared before numeric access. This proves the retained compressed copy,
not a claim about the historical runtime or a full-file archive MD5.

Use the official `hdf5plugin` package and its `from_filter_options` converter.
The original `[0,3,4,0,2]` filter options include reserved version/type fields;
passing that whole tuple as creation user options would be incorrect. The
current supported codec can stamp a newer reserved version prefix. The reader
records original and actual pipelines and requires exact semantic element
size, block size, compressor, filter ID, flags and raw filter masks. It does
not claim identical original and current encoder-version metadata. No private
bitshuffle parser, custom decompressor, native instrumentation or runtime
recovery is used.

The application reads only source channels `[159903921,159911759)`: 7,838
columns in every one of the 16 rows. HDF5 necessarily decompresses each full
4 MiB physical chunk internally; this is reported as 402,653,184 total physical
decoded bytes. The returned six application arrays occupy 3,009,792 bytes.
Finite shape/type checks and array hashes are retained. These are acquired
pilot values, not a completed search or a signal result. The detector operates
on the saved arrays under its separately frozen science protocol.

Dependencies must be demonstrated before an admitted GET. Preparing this
script does not install packages, prove current codec availability, certify
an actual decode or open the scientific value gate.

Primary documentation reviewed for this design:

- h5py direct chunk read/write and mask semantics: https://api.h5py.org/h5d.html
- hdf5plugin supported read registration and stored-option conversion:
  https://hdf5plugin.readthedocs.io/en/stable/usage.html
- Original bitshuffle set-local/decode semantics:
  https://github.com/kiyo-masui/bitshuffle/blob/master/src/bshuf_h5filter.c
- h5py chunked storage: https://docs.h5py.org/en/stable/high/dataset.html
