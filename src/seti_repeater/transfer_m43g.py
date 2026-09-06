"""M43G numerical transfer adapter; synthetic inputs only, no telescope attestation.

The legacy source/cache types and production detector are deliberately separate.
Payload arrays are backed by immutable bytes; identities bind source, geometry,
normalization scope, bank, factors, proxy grid, and filter arithmetic.
"""
from dataclasses import dataclass, asdict
import hashlib
import math
import numpy as np
from . import search_v0p6 as core
from . import source_v0p6 as legacy

CONTRACT = {
    "version": "m43g-synthetic-transfer-v2",
    "source_scope": "synthetic-only; no telescope provenance or threshold",
    "orientation": "ascending physical frequency before normalization",
    "normalization": "legacy float32 median/MAD in 4096-channel blocks",
    "normalization_origin": "ascending channel zero of NEW extraction",
    "filter": "native float32 window sum / float64 sqrt(width), cast float32",
    "mapping": "nearest-even binary64 affine coordinate; steps 0,1,2",
    "duplicates": "retain every proxy cell; no deduplication or reweighting",
    "integration": "ascending row order float32 sum / float32 sqrt(n)",
    "memory_cap_bytes": 512 * 1024**2,
    "filter_chunk_channels": 16384,
    "cache_validation": "verify source, dtype, shape, C layout, immutable flags, identities and payload hash",
}
CONTRACT_SHA256 = hashlib.sha256(core.canonical_json_bytes(CONTRACT)).hexdigest()


def digest(value):
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def array_hash(a):
    return hashlib.sha256(memoryview(a).cast("B")).hexdigest()


def immutable(a):
    return np.frombuffer(a.tobytes(order="C"), dtype=a.dtype).reshape(a.shape)


def integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(label + " must be an integer >= " + str(minimum))
    return value


def memory_bound(rows, channels):
    """Conservative adapter-owned ndarray bound, not process RSS or reader RAM.

    Two source/cache payloads plus immutable-copy staging (three matrices),
    96 bytes/native channel for row/filter/hash temporaries, 4 MiB block scratch.
    Caller-held raw matrices, other caches, transport and OS caches excluded.
    """
    integer(rows, "rows"); integer(channels, "channels")
    return 3 * rows * channels * 4 + 96 * channels + 4 * 1024**2


@dataclass(frozen=True)
class SyntheticSource:
    geometry: core.NativeFrequencyGeometry
    integration_count: int
    scope_json: str
    raw_sha256: str
    normalized_sha256: str
    identity: str
    values: np.ndarray


@dataclass(frozen=True)
class SyntheticCache:
    source: SyntheticSource
    width: int
    grid: core.ProxyCarrierGrid
    factors: np.ndarray
    bank_sha256: str
    identity: str
    payload_sha256: str
    values: np.ndarray


def normalize_synthetic_rows(reader, geometry, integration_count, *,
                             input_orientation, scope):
    """Read one complete integration at a time; reader returns native <f4 row.

    Archive-descending rows reverse before fixed NEW-extraction block alignment.
    The reader is a synthetic fixture callback, not a remote transport adapter.
    """
    integer(integration_count, "integration count")
    if input_orientation not in ("ascending", "descending"):
        raise ValueError("explicit input orientation required")
    if scope.get("kind") != "synthetic":
        raise ValueError("M43G only accepts explicitly synthetic source scope")
    if memory_bound(integration_count, geometry.channel_count) > CONTRACT["memory_cap_bytes"]:
        raise core.V0P6CapacityError("M43G source memory bound exceeds cap")
    out = np.empty((integration_count, geometry.channel_count), dtype="<f4")
    raw_hash = hashlib.sha256()
    for row in range(integration_count):
        supplied = reader(row)
        if not isinstance(supplied, np.ndarray) or supplied.dtype != np.dtype("<f4") or supplied.shape != (geometry.channel_count,):
            raise ValueError("reader must return one complete native float32 row")
        canonical = np.ascontiguousarray(supplied if input_orientation == "ascending" else supplied[::-1])
        if not np.isfinite(canonical).all():
            raise ValueError("nonfinite synthetic input")
        raw_hash.update(memoryview(canonical).cast("B"))
        # Reuse the frozen small-block arithmetic, without its whole-scan cap.
        for start in range(0, geometry.channel_count, 4096):
            block = canonical[start:start+4096].reshape(1, -1)
            out[row, start:start+4096] = legacy.normalize_float32_blocks_v0p6(block)[0]
        del supplied, canonical
    normalized_hash = array_hash(out)
    scope_json = core.canonical_json_bytes(scope).decode()
    identity = digest({"contract": CONTRACT_SHA256, "geometry": asdict(geometry),
                       "rows": integration_count, "scope": scope,
                       "raw_sha256": raw_hash.hexdigest(), "normalized_sha256": normalized_hash})
    return SyntheticSource(geometry, integration_count, scope_json, raw_hash.hexdigest(),
                           normalized_hash, identity, immutable(out))


def validate_source(src):
    if not isinstance(src, SyntheticSource):
        raise ValueError("synthetic source type required")
    import json
    scope = json.loads(src.scope_json)
    expected = digest({"contract": CONTRACT_SHA256, "geometry": asdict(src.geometry),
                       "rows": src.integration_count, "scope": scope,
                       "raw_sha256": src.raw_sha256, "normalized_sha256": src.normalized_sha256})
    if (scope.get("kind") != "synthetic" or src.identity != expected
            or src.values.dtype != np.dtype("<f4") or src.values.flags.writeable
            or src.values.shape != (src.integration_count, src.geometry.channel_count)
            or array_hash(src.values) != src.normalized_sha256):
        raise ValueError("synthetic source identity or payload mismatch")


def build_synthetic_cache(src, factors, grid, width, *, bank_sha256):
    validate_source(src)
    integer(width, "width")
    if width not in core.M37_SPECTRAL_WIDTHS:
        raise ValueError("unsupported native filter width")
    core._frozen_sha256(bank_sha256, "bank")
    f = np.asarray(factors, dtype="<f8")
    if (f.ndim != 2 or not f.shape[0] or f.shape[1] != src.integration_count
            or not np.isfinite(f).all() or np.any(f <= 0) or np.any(f >= 2)):
        raise ValueError("finite factor matrix with 0 < F < 2 required")
    if not math.isclose(grid.channel_width_hz, src.geometry.channel_width_hz, rel_tol=1e-12):
        raise ValueError("native and proxy spacing differ")
    half = width // 2
    endpoints = core.nearest_native_indices(src.geometry, f[..., None] * grid.support_hz[[0, -1]])
    if endpoints.min() < half or endpoints.max() >= src.geometry.channel_count-half:
        raise core.V0P6CoverageError("new extraction does not cover whole bank")
    out = np.empty((src.integration_count, src.geometry.channel_count-2*half), dtype="<f4")
    for row in range(src.integration_count):
        for start in range(half, src.geometry.channel_count-half, CONTRACT["filter_chunk_channels"]):
            stop = min(start+CONTRACT["filter_chunk_channels"], src.geometry.channel_count-half)
            if width == 1:
                out[row, start:stop] = src.values[row, start:stop]
            else:
                section = src.values[row, start-half:stop+half]
                windows = np.lib.stride_tricks.sliding_window_view(section, width)
                out[row, start-half:stop-half] = np.sum(windows, axis=-1, dtype=np.float32) / np.sqrt(width)
    if not np.isfinite(out).all():
        raise ValueError("nonfinite filter output")
    payload_hash = array_hash(out)
    identity = digest({"contract": CONTRACT_SHA256, "source": src.identity,
                       "bank": bank_sha256, "factors": core.factor_table_sha256(f),
                       "grid": core.proxy_carrier_grid_sha256(grid), "width": width,
                       "payload": payload_hash})
    return SyntheticCache(src, width, grid, immutable(np.ascontiguousarray(f)), bank_sha256,
                          identity, payload_hash, immutable(out))


def gather_bank_slice(cache, start, stop, *, template_indices=None, chunk_bins=4096):
    """Integrate a contiguous proxy interval; default includes every template.

    Each output column is retained even where multiple columns share a native
    channel. Contiguous interval checks include mapping across chunk boundaries.
    Explicit slices are diagnostics, never substitutes for a full search.
    """
    if not isinstance(cache, SyntheticCache):
        raise ValueError("synthetic cache type required")
    validate_source(cache.source)
    if (type(cache.width) is not int or cache.width not in core.M37_SPECTRAL_WIDTHS
            or cache.values.dtype != np.dtype("<f4")
            or cache.values.shape != (cache.source.integration_count,
                                      cache.source.geometry.channel_count-2*(cache.width//2))
            or not cache.values.flags.c_contiguous
            or cache.factors.dtype != np.dtype("<f8")
            or cache.factors.ndim != 2 or not cache.factors.shape[0]
            or cache.factors.shape[1] != cache.source.integration_count
            or not cache.factors.flags.c_contiguous):
        raise ValueError("synthetic cache dtype, shape or layout mismatch")
    expected = digest({"contract": CONTRACT_SHA256, "source": cache.source.identity,
                       "bank": cache.bank_sha256, "factors": core.factor_table_sha256(cache.factors),
                       "grid": core.proxy_carrier_grid_sha256(cache.grid), "width": cache.width,
                       "payload": cache.payload_sha256})
    if (expected != cache.identity or cache.values.flags.writeable
            or cache.factors.flags.writeable or array_hash(cache.values) != cache.payload_sha256):
        raise ValueError("synthetic cache identity or payload mismatch")
    integer(start, "start", 0); integer(stop, "stop"); integer(chunk_bins, "chunk size")
    if stop <= start or stop > cache.grid.support_bin_count:
        raise ValueError("invalid proxy support slice")
    if template_indices is None:
        selection = np.arange(cache.factors.shape[0])
    else:
        selection = np.asarray(template_indices)
        if (selection.ndim != 1 or not selection.size or selection.dtype.kind not in "iu"
                or selection.min() < 0 or selection.max() >= cache.factors.shape[0]
                or len(np.unique(selection)) != len(selection)):
            raise ValueError("invalid template selection")
    # This is a synthetic helper, not a production attestation boundary.
    f = cache.factors[selection]
    output_bytes = len(selection) * (stop-start) * 4
    mapping_bytes = len(selection) * min(chunk_bins, stop-start) * 64
    if memory_bound(cache.source.integration_count, cache.source.geometry.channel_count) + output_bytes + mapping_bytes > CONTRACT["memory_cap_bytes"]:
        raise core.V0P6CapacityError("M43G gather memory bound exceeds cap")
    out = np.zeros((len(selection), stop-start), dtype="<f4")
    half = cache.width // 2
    for row in range(cache.source.integration_count):
        prior = None
        for left in range(start, stop, chunk_bins):
            right = min(left+chunk_bins, stop)
            q = cache.grid.support_hz[left:right]
            indices = core.nearest_native_indices(cache.source.geometry, f[:, row, None] * q)
            steps = np.diff(indices, axis=1)
            if np.any(steps < 0) or np.any(steps > 2):
                raise ValueError("mapping outside nondecreasing {0,1,2} contract")
            if prior is not None and (np.any(indices[:, 0]-prior < 0) or np.any(indices[:, 0]-prior > 2)):
                raise ValueError("mapping changed at chunk boundary")
            prior = indices[:, -1]
            if indices.min() < half or indices.max() >= cache.source.geometry.channel_count-half:
                raise core.V0P6CoverageError("filtered native range exceeded")
            out[:, left-start:right-start] += cache.values[row, indices-half]
    out /= np.float32(math.sqrt(cache.source.integration_count))
    return out
