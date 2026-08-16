"""Byte-range extraction of small windows from remote SIGPROC filterbanks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen
import json
import struct

import numpy as np


HEADER_TYPES = {
    "telescope_id": "<i", "machine_id": "<i", "data_type": "<i",
    "barycentric": "<i", "pulsarcentric": "<i", "nbits": "<i",
    "nsamples": "<i", "nchans": "<i", "nifs": "<i",
    "nbeams": "<i", "ibeam": "<i", "rawdatafile": "str",
    "source_name": "str", "az_start": "<d", "za_start": "<d",
    "tstart": "<d", "tsamp": "<d", "fch1": "<d", "foff": "<d",
    "refdm": "<d", "period": "<d", "src_raj": "<d", "src_dej": "<d",
}


def fetch_range(url: str, start: int, stop: int, timeout: int = 90) -> bytes:
    """Fetch byte interval [start, stop) and reject silent full-file replies."""
    request = Request(url, headers={"Range": f"bytes={start}-{stop - 1}"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read(stop - start + 1)
        status = getattr(response, "status", response.getcode())
        content_range = response.headers.get("Content-Range")
    if status != 206 or not content_range:
        raise RuntimeError(f"Server ignored Range request: status={status}, range={content_range}")
    if len(payload) != stop - start:
        raise RuntimeError(f"Short range read: wanted {stop-start}, received {len(payload)}")
    return payload


def remote_size(url: str, timeout: int = 90) -> int:
    request = Request(url, method="HEAD")
    with urlopen(request, timeout=timeout) as response:
        size = response.headers.get("Content-Length")
        accepts = response.headers.get("Accept-Ranges", "")
    if size is None or "bytes" not in accepts.lower():
        raise RuntimeError("Remote file does not advertise byte ranges and a content length")
    return int(size)


def parse_sigproc_header_bytes(raw: bytes) -> tuple[dict, int]:
    header: dict = {}
    cursor = 0
    while True:
        if cursor + 4 > len(raw):
            raise EOFError("HEADER_END was not found in fetched prefix")
        keyword_length = struct.unpack_from("<I", raw, cursor)[0]
        cursor += 4
        keyword = raw[cursor:cursor + keyword_length].decode("ascii")
        cursor += keyword_length
        if keyword == "HEADER_START":
            continue
        if keyword == "HEADER_END":
            return header, cursor
        kind = HEADER_TYPES[keyword]
        if kind == "str":
            length = struct.unpack_from("<I", raw, cursor)[0]
            cursor += 4
            value = raw[cursor:cursor + length].decode("ascii")
            cursor += length
        else:
            value = struct.unpack_from(kind, raw, cursor)[0]
            cursor += struct.calcsize(kind)
        header[keyword] = value


def remote_header(url: str) -> tuple[dict, int, int, int]:
    raw = fetch_range(url, 0, 65536)
    header, data_offset = parse_sigproc_header_bytes(raw)
    if header["nbits"] != 32 or header["nifs"] != 1:
        raise NotImplementedError("The extractor expects one IF of 32-bit floats")
    size = remote_size(url)
    row_bytes = header["nchans"] * 4
    payload = size - data_offset
    if payload % row_bytes:
        raise RuntimeError("Remote payload is not an integer number of integrations")
    return header, data_offset, size, payload // row_bytes


def extract_frequency_window(
    url: str,
    fmin_mhz: float,
    fmax_mhz: float,
    output: str | Path,
    workers: int = 8,
) -> Path:
    """Extract one frequency slice, caching the result as compressed NPZ."""
    output = Path(output)
    if output.exists():
        return output
    header, data_offset, size, ntime = remote_header(url)
    low_index = int(np.ceil((fmin_mhz - header["fch1"]) / header["foff"]))
    high_index = int(np.floor((fmax_mhz - header["fch1"]) / header["foff"]))
    channel_start, channel_stop = sorted((low_index, high_index))
    channel_start = max(0, channel_start)
    channel_stop = min(header["nchans"] - 1, channel_stop) + 1
    if channel_start >= channel_stop:
        raise ValueError("Requested frequency window is outside the file")
    selected = np.arange(channel_start, channel_stop)
    frequencies = header["fch1"] + selected * header["foff"]
    nfreq = selected.size
    row_bytes = header["nchans"] * 4
    window_bytes = nfreq * 4
    data = np.empty((ntime, nfreq), dtype="<f4")

    def get_row(row: int) -> tuple[int, bytes]:
        start = data_offset + row * row_bytes + channel_start * 4
        return row, fetch_range(url, start, start + window_bytes)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(get_row, row) for row in range(ntime)]
        for future in as_completed(futures):
            row, payload = future.result()
            data[row] = np.frombuffer(payload, dtype="<f4", count=nfreq)

    if frequencies[0] > frequencies[-1]:
        frequencies = frequencies[::-1].copy()
        data = data[:, ::-1].copy()
    metadata = {
        "url": url, "remote_size": size, "header": header,
        "data_offset": data_offset, "ntime": ntime,
        "channel_start": channel_start, "channel_stop": channel_stop,
        "fmin_requested_mhz": fmin_mhz, "fmax_requested_mhz": fmax_mhz,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output, data=data, frequency_mhz=frequencies, metadata=json.dumps(metadata))
    return output

