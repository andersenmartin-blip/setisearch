# Cache-only typed HDF5 metadata planning, V2

This distinct prospective parser preserves the frozen BLC66 parser and its actual invalid result. The six BLC66 prefixes were subsequently lost; this phase neither reconstructs them nor repeats their requests. It can consume newly admitted cache spans from a separately frozen source family, including the new session31/BLC77 transport capture. No actual telescope cache has been read with this V2 parser.

`structure.py` is pure standard-library code. It accepts authenticated in-memory spans and a logical file length. It has no filesystem, network, h5py, NumPy or dataset-value API. Addresses and extents come from verified fields in the supplied source bytes. Prefix length, addresses and channel geometry are never borrowed from another observation. Missing fragments are evidence, not HTTP authorization.

The supported subset remains v0 superblocks with O=L=8, v1 object headers and continuations, root hard links named `data`, legacy group TREE type0/local HEAP/SNOD metadata, and typed variable-length string attributes. Unsupported versions or schemas fail closed. Layout storage and raw chunk TREE pointers are never traversed. This parser establishes structural coverage, not six-source geometry, signal significance or independent validation.

## Narrow reference-count compatibility

The prior parser required positive GCOL live-object reference counts. The official HDF5 1.10.5 source initializes a newly allocated live object's count to zero. Its variable-length disk writer inserts the object and encodes its identifier without calling the reference-count increment function. Reading the object does not require a positive count. V2 therefore accepts reference count zero for a typed string attribute. It retains the exact sequence-length equality, positive representable object index, reserved-byte, collection-size and object-boundary checks. Free object0 still requires reference count zero and a size including its own header.

This is compatibility with the official implementation, not a claim that the current specification's positive-count sentence says otherwise. The official specification and implementation distinction is recorded in `OFFICIAL_IMPLEMENTATION_COMPATIBILITY.json`.

## Safe collection coverage

A typed string attribute first proves a GCOL collection address and header. A separate bounded coverage pass walks only its sequential 16-byte object headers, using each live object's declared aligned size to locate the next header. It runs even when a separately referenced data object-header continuation is missing.

Known string-attribute objects permit only their typed attribute data and alignment padding to be proposed. An unrelated live object's data is skipped. If its uncached body would prevent complete collection coverage, the source is unsupported for whole-collection completion, and those bytes are never queued. A completely cached unrelated object requires no request and can be skipped without interpreting its contents.

An object0 header proves final free space only if its reference count is zero and its declared size equals the remaining collection extent including its header. Missing bytes inside that proven free extent are eligible metadata slack. A final remainder smaller than an object header is admitted as the specification's implied free tail. Every proposal includes the authenticated collection header, prior header or free header, originating typed attribute and exact cache subtraction. No signature scan or arbitrary pointer-shaped bytes establish this evidence.

The free/slack policy supports metadata readers that cache GCOL collections as whole blocks while preventing an opaque live dataset object from becoming a metadata fetch proposal. It does not guarantee that a later HDF5 reader will support every file. Invalid or unsupported plans remain blocked for acquisition.

## Bounds and synthetic check

Per source: cache4MiB, individual typed object64KiB, 128 object headers or collections, 2,048 messages, depth8, 128 missing fragments and at most1MiB summed missing bytes. HTTP requests, spectral-value reads and payload-range proposals remain zero.

The prepared 24-case fixture uses handmade metadata only. It includes zero-count live objects, retained length mismatch rejection, unknown live-data holes, and simultaneous missing object-header continuation plus a proven free tail. Its source is reviewed before root invokes it once. No parser, fixture or real cache execution is authorized merely by these files.

```bash
python /ABS_REPO/tools/radio_visit2019_structure_v2_20261010/HDF5_TYPED_METADATA_TOY_FIXTURE_V3.py \
  --structure-source /ABS_REPO/tools/radio_visit2019_structure_v2_20261010/structure.py \
  --expected-structure-sha256 EXACT_SOURCE_SHA256 \
  --receipt /ABS_PRIVATE/HDF5_TYPED_METADATA_V3_RESULT.json
```

## Primary format sources

The HDF Group's [HDF5 File Format Specification4.0](https://support.hdfgroup.org/documentation/hdf5/latest/_f_m_t4.html), sections II.A, III.A–E, IV.A and IV.B, defines the admitted layouts. III.E describes sequential live objects, alignment, object0 and implied trailing free space. The reference-count compatibility is supported by official [H5HG.c](https://github.com/HDFGroup/hdf5/blob/hdf5-1_10_5/src/H5HG.c) and [H5Tvlen.c](https://github.com/HDFGroup/hdf5/blob/hdf5-1_10_5/src/H5Tvlen.c), with exact Git blob identities recorded separately.
