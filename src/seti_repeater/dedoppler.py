"""Robust normalization and transparent CPU dedoppler helpers."""

from __future__ import annotations

from ctypes import CDLL, POINTER, c_float, c_int, c_int32
from pathlib import Path
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "dedoppler_max.c"
LIBRARY = ROOT / "_dedoppler_max.so"


def compile_library() -> Path:
    """Compile the small OpenMP kernel on first use."""
    if not LIBRARY.exists() or LIBRARY.stat().st_mtime < SOURCE.stat().st_mtime:
        subprocess.run(
            [
                "gcc", "-O3", "-march=native", "-fopenmp", "-shared", "-fPIC",
                str(SOURCE), "-o", str(LIBRARY), "-lm",
            ],
            check=True,
        )
    return LIBRARY


def robust_block_normalize(data: np.ndarray, block: int = 4096) -> np.ndarray:
    """Flatten each time row in blocks while retaining narrow spectral lines."""
    data = np.asarray(data, dtype=np.float32)
    normalized = np.empty_like(data)
    for start in range(0, data.shape[1], block):
        stop = min(start + block, data.shape[1])
        section = data[:, start:stop]
        center = np.median(section, axis=1, keepdims=True)
        mad = np.median(np.abs(section - center), axis=1, keepdims=True)
        scale = np.maximum(1.4826 * mad, np.finfo(np.float32).tiny)
        normalized[:, start:stop] = (section - center) / scale
    return np.ascontiguousarray(normalized, dtype=np.float32)


def dedoppler_max(
    normalized: np.ndarray,
    tsamp_seconds: float,
    channel_width_hz: float,
    max_drift_hz_s: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return the best straight-line path at each safe frequency bin."""
    normalized = np.ascontiguousarray(normalized, dtype=np.float32)
    ntime, nfreq = normalized.shape
    duration = (ntime - 1) * tsamp_seconds
    max_shift = int(np.ceil(max_drift_hz_s * duration / abs(channel_width_hz)))
    best_snr = np.full(nfreq, np.nan, dtype=np.float32)
    best_shift = np.zeros(nfreq, dtype=np.int32)

    lib = CDLL(str(compile_library()))
    function = lib.dedoppler_max
    function.argtypes = [
        POINTER(c_float), c_int, c_int, c_int,
        POINTER(c_float), POINTER(c_int32),
    ]
    function.restype = c_int
    status = function(
        normalized.ctypes.data_as(POINTER(c_float)), ntime, nfreq, max_shift,
        best_snr.ctypes.data_as(POINTER(c_float)),
        best_shift.ctypes.data_as(POINTER(c_int32)),
    )
    if status:
        raise RuntimeError(f"dedoppler_max failed with status {status}")
    drift = best_shift.astype(float) * channel_width_hz / duration
    return best_snr, drift, max_shift


def dedoppler_shifts(normalized: np.ndarray, shifts: np.ndarray) -> tuple[np.ndarray, int]:
    """Integrate an arbitrary integer-bin Doppler path."""
    normalized = np.asarray(normalized, dtype=np.float32)
    shifts = np.asarray(shifts, dtype=int)
    ntime, nfreq = normalized.shape
    if shifts.shape != (ntime,):
        raise ValueError("shifts must have one value per time integration")
    margin = int(np.max(np.abs(shifts)))
    spectrum = np.full(nfreq, np.nan, dtype=np.float32)
    valid = np.arange(margin, nfreq - margin)
    accumulated = np.zeros(valid.size, dtype=np.float32)
    for row, shift in zip(normalized, shifts):
        accumulated += row[valid + shift]
    spectrum[valid] = accumulated / np.sqrt(ntime)
    return spectrum, margin

