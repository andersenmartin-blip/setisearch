#!/usr/bin/env python3
"""Extract preregistered Milestone 13 windows from remote fine HDF5 files.

The adapter writes the same NPZ contract as the existing SIGPROC extractor.
It changes only the source-container reader; detector v0.5.0 remains unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np


def json_value(value):
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def remote_identity(url: str) -> tuple[int, str | None]:
    request = Request(
        url,
        method="HEAD",
        headers={"User-Agent": "setisearch-m13-extract/1.0"},
    )
    with urlopen(request, timeout=90) as response:
        size = int(response.headers["Content-Length"])
        accepts = response.headers.get("Accept-Ranges", "")
        etag = response.headers.get("ETag")
    if "bytes" not in accepts.lower():
        raise RuntimeError(f"Remote file does not advertise byte ranges: {url}")
    return size, etag


def channel_bounds(
    fch1_mhz: float,
    foff_mhz: float,
    nchans: int,
    fmin_mhz: float,
    fmax_mhz: float,
) -> tuple[int, int]:
    low_index = int(np.ceil((fmin_mhz - fch1_mhz) / foff_mhz))
    high_index = int(np.floor((fmax_mhz - fch1_mhz) / foff_mhz))
    channel_start, channel_stop = sorted((low_index, high_index))
    channel_start = max(0, channel_start)
    channel_stop = min(nchans - 1, channel_stop) + 1
    if channel_start >= channel_stop:
        raise ValueError("Requested frequency window is outside the HDF5 file")
    return channel_start, channel_stop


def validate_geometry(scan: dict, attrs: dict, shape: tuple[int, ...], dtype) -> None:
    expected = scan["expected_header"]
    checks = {
        "source_name": str(attrs["source_name"]) == expected["source_name"],
        "tstart_mjd": abs(float(attrs["tstart"]) - expected["tstart_mjd"]) < 1e-9,
        "tsamp_s": abs(float(attrs["tsamp"]) - expected["tsamp_s"]) < 1e-12,
        "shape": list(shape) == expected["dataset_shape"],
        "dtype": str(dtype) == expected["dataset_dtype"],
        "fch1_mhz": abs(float(attrs["fch1"]) - expected["fch1_mhz"]) < 1e-12,
        "foff_mhz": abs(float(attrs["foff"]) - expected["foff_mhz"]) < 1e-18,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            f"Header geometry changed for {scan['label']}: {', '.join(failed)}"
        )


def extract_scan(scan: dict, windows: list[dict], data_dir: Path) -> None:
    import fsspec
    import h5py
    import hdf5plugin  # noqa: F401  Registers the archive's compression filter.

    remote_size, etag = remote_identity(scan["url"])
    if remote_size != scan["expected_remote_size_bytes"]:
        raise RuntimeError(
            f"Remote size changed for {scan['label']}: "
            f"{remote_size} != {scan['expected_remote_size_bytes']}"
        )
    if etag != scan["expected_etag"]:
        raise RuntimeError(
            f"Remote ETag changed for {scan['label']}: {etag} != {scan['expected_etag']}"
        )

    with fsspec.open(
        scan["url"],
        mode="rb",
        block_size=4_194_304,
        cache_type="blockcache",
    ) as remote:
        with h5py.File(remote, "r") as handle:
            dataset = handle["data"]
            attrs = {
                **{key: json_value(value) for key, value in handle.attrs.items()},
                **{key: json_value(value) for key, value in dataset.attrs.items()},
            }
            validate_geometry(scan, attrs, dataset.shape, dataset.dtype)
            fch1 = float(attrs["fch1"])
            foff = float(attrs["foff"])
            nchans = int(dataset.shape[-1])

            for window in windows:
                output = data_dir / window["id"] / f"{scan['label']}.npz"
                if output.exists():
                    print(f"cached {output}", flush=True)
                    continue
                start, stop = channel_bounds(
                    fch1,
                    foff,
                    nchans,
                    float(window["fmin_mhz"]),
                    float(window["fmax_mhz"]),
                )
                selected = np.arange(start, stop)
                frequencies = fch1 + selected * foff
                data = np.asarray(dataset[:, 0, start:stop], dtype=np.float32)
                if frequencies[0] > frequencies[-1]:
                    frequencies = frequencies[::-1].copy()
                    data = data[:, ::-1].copy()
                metadata = {
                    "format": "HDF5",
                    "url": scan["url"],
                    "remote_size": remote_size,
                    "etag": etag,
                    "header": {
                        "source_name": attrs["source_name"],
                        "tstart": float(attrs["tstart"]),
                        "tsamp": float(attrs["tsamp"]),
                        "fch1": fch1,
                        "foff": foff,
                        "nchans": nchans,
                        "nifs": int(dataset.shape[1]),
                        "nbits": 32,
                    },
                    "data_offset": None,
                    "ntime": int(dataset.shape[0]),
                    "channel_start": start,
                    "channel_stop": stop,
                    "fmin_requested_mhz": float(window["fmin_mhz"]),
                    "fmax_requested_mhz": float(window["fmax_mhz"]),
                    "source_adapter": "scripts/m13_hdf5_extract.py",
                }
                output.parent.mkdir(parents=True, exist_ok=True)
                temporary = output.with_suffix(output.suffix + ".tmp")
                with temporary.open("wb") as handle_out:
                    np.savez_compressed(
                        handle_out,
                        data=data,
                        frequency_mhz=frequencies,
                        metadata=json.dumps(metadata),
                    )
                os.replace(temporary, output)
                print(
                    f"wrote {output} ({data.shape[0]} x {data.shape[1]})",
                    flush=True,
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_m13"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config["project"]["detector_version_frozen"] != "0.5.0":
        raise RuntimeError("Milestone 13 must use frozen detector v0.5.0")
    for scan in config["scans"]:
        extract_scan(scan, config["windows"], args.data_dir)


if __name__ == "__main__":
    main()
