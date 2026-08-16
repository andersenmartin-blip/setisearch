"""Unit-noise spectral matched filters for unresolved and smeared tones."""

from __future__ import annotations

import numpy as np


def validate_widths(widths: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    result = tuple(int(width) for width in widths)
    if not result or any(width < 1 or width % 2 == 0 for width in result):
        raise ValueError("spectral widths must be positive odd integers")
    if len(set(result)) != len(result):
        raise ValueError("spectral widths must be unique")
    return result


def normalized_boxcar(values: np.ndarray, width: int) -> np.ndarray:
    """Apply an odd-width boxcar with L2 norm one along the final axis."""
    width = validate_widths([width])[0]
    values = np.asarray(values, dtype=np.float32)
    if width == 1:
        return values.copy()
    half = width // 2
    windows = np.lib.stride_tricks.sliding_window_view(values, width, axis=-1)
    filtered = np.full(values.shape, np.nan, dtype=np.float32)
    filtered[..., half:-half] = np.sum(windows, axis=-1, dtype=np.float32) / np.sqrt(width)
    return filtered


def make_spectral_bank(vectors: np.ndarray, widths: list[int] | tuple[int, ...]) -> np.ndarray:
    """Return [spectral width, orbital template, epoch, frequency] vectors."""
    widths = validate_widths(widths)
    return np.stack([normalized_boxcar(vectors, width) for width in widths], axis=0)

