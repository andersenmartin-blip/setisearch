#!/usr/bin/env python3
"""Prospective native-order HDF5 extraction adapter for detector-v0.6/M37.

Unlike the legacy Milestone-13 adapter, this module does **not** reverse or
normalize caller-visible arrays before source attestation.  It reads the exact
``data[:, 0, channel_start:channel_stop]`` HDF5 hyperslab in header-native
(descending-frequency) order, derives the matching float64 axis from the
validated header, and immediately passes both to ``source_v0p6``.  That source
factory owns the one canonical ascending-axis reversal and 4096-channel robust
normalization.

Importing this module performs no network or telescope I/O.  The iterator
requires an explicit spectral-access authorization boolean before even the
remote HEAD request.  Authorized reads use the identity-bound, restartable
sparse range transport rather than a volatile generic block cache.
"""

from __future__ import annotations

import gc
import hashlib
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import numpy as np

from seti_repeater import http_range_v0p6 as transport
from seti_repeater import source_v0p6 as source


M37_V0P6_EXTRACTOR_USER_AGENT = "setisearch-m37-v0p6-extract/1.0"


def _require_frozen_implementation() -> None:
    observed = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if observed != source.M37_HDF5_EXTRACTOR_SOURCE_SHA256:
        raise source.core.V0P6ContractError(
            "M37 v0.6 extractor source differs from its frozen engine identity"
        )


def _remote_identity(url: str) -> tuple[int, str]:
    identity = transport.remote_identity(url)
    return identity.size, identity.etag


def _json_scalar(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    if isinstance(value, np.generic):
        return value.item()
    return value


def _observed_header(dataset: Any, attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Translate exact HDF5 attributes to the published M37 header schema."""
    return {
        "source_name": str(_json_scalar(attributes["source_name"])),
        "src_raj_hours": float(_json_scalar(attributes["src_raj"])),
        "src_dej_deg": float(_json_scalar(attributes["src_dej"])),
        "tstart_mjd": float(_json_scalar(attributes["tstart"])),
        "tsamp_s": float(_json_scalar(attributes["tsamp"])),
        "dataset_shape": [int(item) for item in dataset.shape],
        "dataset_dtype": str(dataset.dtype),
        "fch1_mhz": float(_json_scalar(attributes["fch1"])),
        "foff_mhz": float(_json_scalar(attributes["foff"])),
    }


def _validated_dataset(handle: Any, definition: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    dataset = handle["data"]
    attributes = {
        **{key: _json_scalar(value) for key, value in handle.attrs.items()},
        **{key: _json_scalar(value) for key, value in dataset.attrs.items()},
    }
    header = _observed_header(dataset, attributes)
    if header != dict(definition["expected_header"]):
        raise source.core.V0P6ContractError(
            "M37 HDF5 header differs from the published scan identity"
        )
    return dataset, header


def _iter_handle_products(
    handle: Any,
    *,
    definition: Mapping[str, Any],
    scan_definitions: Sequence[Mapping[str, Any]],
    scan_label: str,
    requested_windows: Sequence[str],
    remote_size: int,
    etag: str,
) -> Iterator[source.M37NormalizedScanProduct]:
    dataset, header = _validated_dataset(handle, definition)
    for window_id in requested_windows:
        start, stop = source.m37_extraction_interval(window_id)
        raw_native = np.ascontiguousarray(dataset[:, 0, start:stop], dtype="<f4")
        frequency_native = np.ascontiguousarray(
            float(header["fch1_mhz"])
            + np.arange(start, stop, dtype=np.float64)
            * float(header["foff_mhz"]),
            dtype="<f8",
        )
        extracted = source.attest_m37_extracted_scan(
            raw_native,
            frequency_native,
            scan_definitions,
            window_id=window_id,
            scan_label=scan_label,
            observed_url=str(definition["url"]),
            observed_remote_size_bytes=remote_size,
            observed_etag=etag,
            observed_header=header,
            channel_start=start,
            channel_stop=stop,
        )
        product = source.normalize_m37_extracted_scan(extracted)
        del raw_native, frequency_native, extracted
        gc.collect()
        yield product
        del product
        gc.collect()


def iter_m37_normalized_scan_products(
    scan_definitions: Sequence[Mapping[str, Any]],
    *,
    scan_label: str,
    window_ids: Sequence[str] = source.core.M37_WINDOW_IDS,
    spectral_access_authorized: bool = False,
    range_mirror_root: str | Path | None = None,
    range_workers: int = transport.DEFAULT_WORKERS,
) -> Iterator[source.M37NormalizedScanProduct]:
    """Yield exact products one window at a time from one authorized HDF5 scan.

    The caller must finish consuming and release each yielded product before
    requesting the next if its downstream buffers would otherwise exceed the
    frozen live-ndarray cap.  No cache, roll, or multi-scan array is retained by
    this iterator.
    """
    if spectral_access_authorized is not True:
        raise RuntimeError(
            "M37 spectral access is not authorized; no remote request made"
        )
    _require_frozen_implementation()
    source.validate_m37_source_scan_definitions(scan_definitions)
    definitions = [
        item for item in scan_definitions if str(item["label"]) == scan_label
    ]
    if len(definitions) != 1:
        raise source.core.V0P6ContractError(
            "M37 extractor requires exactly one known scan label"
        )
    definition = definitions[0]
    requested_windows = tuple(str(item) for item in window_ids)
    if (
        not requested_windows
        or len(set(requested_windows)) != len(requested_windows)
        or any(item not in source.core.M37_WINDOW_IDS for item in requested_windows)
    ):
        raise source.core.V0P6ContractError(
            "M37 extractor window inventory is empty, duplicated, or unknown"
        )
    if range_mirror_root is None:
        raise source.core.V0P6ContractError(
            "M37 extractor requires a persistent sparse range-mirror root"
        )
    mirror_root = Path(range_mirror_root)
    if not mirror_root.is_dir():
        raise source.core.V0P6ContractError(
            "M37 sparse range-mirror root does not exist"
        )
    remote_size, etag = _remote_identity(str(definition["url"]))
    if (
        remote_size != int(definition["expected_remote_size_bytes"])
        or etag != str(definition["expected_etag"])
    ):
        raise source.core.V0P6ContractError(
            "M37 remote size/ETag differs from the published scan identity"
        )

    # Optional extraction dependencies remain isolated from package import.
    import h5py
    import hdf5plugin  # noqa: F401  Registers the archive compression filter.

    identity = transport.RemoteIdentity(
        str(definition["url"]), remote_size, etag
    )
    mirror_path = mirror_root / f"{scan_label}.h5.sparse"
    intervals = tuple(
        source.m37_extraction_interval(window_id)
        for window_id in requested_windows
    )
    with transport.SparseRangeMirror(
        mirror_path,
        identity,
        workers=range_workers,
    ) as mirror:
        mirror.prefetch(
            (
                transport.ByteRange(
                    0,
                    min(remote_size, transport.HDF5_METADATA_PREFIX_BYTES),
                ),
            )
        )
        mirror.seek(0)
        with h5py.File(mirror, "r") as handle:
            dataset, _ = _validated_dataset(handle, definition)
            ranges = transport.discover_hdf5_chunk_ranges(dataset, intervals)
            plan = transport.range_plan_record(
                identity,
                dataset_shape=dataset.shape,
                dataset_chunks=dataset.chunks,
                channel_intervals=intervals,
                ranges=ranges,
            )
        transport.publish_range_plan(
            mirror_root / f"{scan_label}.range-plan.json", plan
        )
        mirror.prefetch(ranges)
        mirror.seek(0)
        with h5py.File(mirror, "r") as handle:
            yield from _iter_handle_products(
                handle,
                definition=definition,
                scan_definitions=scan_definitions,
                scan_label=scan_label,
                requested_windows=requested_windows,
                remote_size=remote_size,
                etag=etag,
            )


def main() -> None:
    raise SystemExit(
        "This prospective adapter is a library entry point. Publish the final "
        "M37 authorization/orchestration receipt before invoking it."
    )


if __name__ == "__main__":
    main()
