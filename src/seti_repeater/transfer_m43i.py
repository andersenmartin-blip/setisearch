"""M43I telescope score adapter, bound to independently retained M43H receipts.

The arithmetic is a frozen copy of M43G v2; no telescope product is represented
as synthetic. The receipt trust anchor is supplied by the calling protocol.
This is a numerical qualification boundary, not a calibrated detector.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from . import search_v0p6 as core
from . import source_m43h as sources
from .transfer_m43g import immutable, integer, memory_bound, array_hash, digest

CONTRACT = {
    "version": "m43i-telescope-transfer-v1",
    "source": "M43H rehydrate with independently retained telescope receipt SHA",
    "normalization": "M43H ascending new-extraction float32 median/MAD blocks 4096",
    "filter": "native float32 window sum / float64 sqrt(width), cast float32",
    "mapping": "nearest-even binary64 affine coordinate; steps 0,1,2",
    "duplicates": "retain every proxy cell; no deduplication or reweighting",
    "integration": "ascending row order float32 sum / float32 sqrt(n)",
    "memory_cap_bytes": 512 * 1024**2,
    "filter_chunk_channels": 16384,
    "validation": "receipt, source row hashes, dtype, shape, C layout, readonly arrays, cache identity and payload",
}
CONTRACT_SHA256 = digest(CONTRACT)


@dataclass(frozen=True)
class TelescopeSource:
    geometry: core.NativeFrequencyGeometry
    integration_count: int
    receipt_json: str
    trusted_receipt_sha256: str
    normalized_sha256: str
    identity: str
    values: np.ndarray


@dataclass(frozen=True)
class TelescopeCache:
    source: TelescopeSource
    width: int
    grid: core.ProxyCarrierGrid
    factors: np.ndarray
    bank_sha256: str
    identity: str
    payload_sha256: str
    values: np.ndarray


def source_identity(geometry, rows, receipt_sha256, normalized_sha256):
    return digest({"contract": CONTRACT_SHA256, "geometry": asdict(geometry),
                   "rows": rows, "receipt": receipt_sha256,
                   "normalized_sha256": normalized_sha256})


def load_telescope_source(directory, *, trusted_receipt_sha256):
    """Verify stored native and normalized rows before loading immutable values.

    Rehash each loaded normalized row as well, so changes between rehydration
    and loading cannot silently enter the cache. No remote requests are made.
    """
    receipt = sources.rehydrate(directory, trusted_receipt_sha256,
                                required_kind="telescope-remote")
    geometry = core.NativeFrequencyGeometry(**receipt["scope"]["geometry"])
    rows = len(receipt["rows"])
    if memory_bound(rows, geometry.channel_count) > CONTRACT["memory_cap_bytes"]:
        raise core.V0P6CapacityError("M43I source memory bound exceeds cap")
    out = np.empty((rows, geometry.channel_count), dtype="<f4")
    for row, evidence in enumerate(receipt["rows"]):
        value = np.load(Path(directory)/f"row{row:02d}.normalized.npy", allow_pickle=False)
        if (value.dtype != np.dtype("<f4") or value.shape != (geometry.channel_count,)
                or not value.flags.c_contiguous or not np.isfinite(value).all()
                or array_hash(value) != evidence["normalized_sha256"]):
            raise ValueError("loaded row differs from trusted receipt")
        out[row] = value
    normalized_sha256 = array_hash(out)
    src = TelescopeSource(geometry, rows, core.canonical_json_bytes(receipt).decode(),
            trusted_receipt_sha256, normalized_sha256,
            source_identity(geometry, rows, trusted_receipt_sha256, normalized_sha256), immutable(out))
    validate_source(src)
    return src


def validate_source(src):
    if type(src) is not TelescopeSource:
        raise ValueError("telescope source type required")
    integer(src.integration_count, "integration count")
    if memory_bound(src.integration_count, src.geometry.channel_count) > CONTRACT["memory_cap_bytes"]:
        raise core.V0P6CapacityError("M43I source memory bound exceeds cap")
    receipt = sources.verify(json.loads(src.receipt_json))
    scope = receipt["scope"]
    if (receipt["receipt_sha256"] != src.trusted_receipt_sha256
            or scope["kind"] != "telescope-remote" or receipt["complete"] is not True
            or scope["geometry"] != asdict(src.geometry)
            or len(receipt["rows"]) != src.integration_count
            or src.values.dtype != np.dtype("<f4")
            or src.values.shape != (src.integration_count, src.geometry.channel_count)
            or not src.values.flags.c_contiguous or src.values.flags.writeable
            or array_hash(src.values) != src.normalized_sha256
            or src.identity != source_identity(src.geometry, src.integration_count,
                    src.trusted_receipt_sha256, src.normalized_sha256)):
        raise ValueError("telescope source identity, receipt or payload mismatch")
    for row, evidence in enumerate(receipt["rows"]):
        if evidence["row"] != row or array_hash(src.values[row]) != evidence["normalized_sha256"]:
            raise ValueError("telescope row differs from receipt")


def build_telescope_cache(src, factors, grid, width, *, bank_sha256):
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
    return TelescopeCache(src, width, grid, immutable(np.ascontiguousarray(f)), bank_sha256,
                          identity, payload_hash, immutable(out))


def gather_bank_slice(cache, start, stop, *, template_indices=None, chunk_bins=4096):
    """Integrate a contiguous proxy interval; default includes every template.

    Each output column is retained even where multiple columns share a native
    channel. Contiguous interval checks include mapping across chunk boundaries.
    Explicit slices are diagnostics, never substitutes for a full search.
    """
    if not isinstance(cache, TelescopeCache):
        raise ValueError("telescope cache type required")
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
        raise ValueError("telescope cache dtype, shape or layout mismatch")
    expected = digest({"contract": CONTRACT_SHA256, "source": cache.source.identity,
                       "bank": cache.bank_sha256, "factors": core.factor_table_sha256(cache.factors),
                       "grid": core.proxy_carrier_grid_sha256(cache.grid), "width": cache.width,
                       "payload": cache.payload_sha256})
    if (expected != cache.identity or cache.values.flags.writeable
            or cache.factors.flags.writeable or array_hash(cache.values) != cache.payload_sha256):
        raise ValueError("telescope cache identity or payload mismatch")
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
    # The source identity is tied to the caller-supplied M43H receipt.
    f = cache.factors[selection]
    output_bytes = len(selection) * (stop-start) * 4
    mapping_bytes = len(selection) * min(chunk_bins, stop-start) * 64
    if memory_bound(cache.source.integration_count, cache.source.geometry.channel_count) + output_bytes + mapping_bytes > CONTRACT["memory_cap_bytes"]:
        raise core.V0P6CapacityError("M43I gather memory bound exceeds cap")
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
