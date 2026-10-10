"""Integrity-check a complete PNG buffer before atomic display publication.

Only image bytes are checked. No scientific arrays, selection, or scores are
calculated. The temporary filename has no PNG extension and is fully written,
fsynced, checked, then replaced into its public filename.
"""
from io import BytesIO
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import zlib

MAX_PNG_BYTES = 32 * 1024**2
MAX_PIXELS = 40_000_000


def validate_png_bytes(raw, expected_dimensions=None):
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= MAX_PNG_BYTES:
        raise ValueError("PNG byte buffer outside the finite display limit")
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    position, chunks, dimensions, idat_count, saw_end = 8, [], None, 0, False
    while position < len(raw):
        if position + 12 > len(raw):
            raise ValueError("Incomplete PNG chunk header/checksum")
        length = struct.unpack(">I", raw[position:position + 4])[0]
        kind = raw[position + 4:position + 8]
        end = position + 8 + length
        if end + 4 > len(raw):
            raise ValueError("Incomplete PNG chunk payload/checksum")
        stored = struct.unpack(">I", raw[end:end + 4])[0]
        actual = zlib.crc32(raw[position + 4:end]) & 0xffffffff
        if stored != actual:
            raise ValueError("PNG chunk CRC mismatch")
        if not chunks:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG must begin with one valid IHDR")
            dimensions = struct.unpack(">II", raw[position + 8:position + 16])
            if not all(0 < x <= 20000 for x in dimensions) or dimensions[0] * dimensions[1] > MAX_PIXELS:
                raise ValueError("PNG decoded dimensions outside the finite display limit")
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG IHDR")
        chunks.append(kind.decode("ascii"))
        if kind == b"IDAT":
            idat_count += 1
        position = end + 4
        if kind == b"IEND":
            if length != 0 or position != len(raw):
                raise ValueError("PNG IEND must end the complete buffer")
            saw_end = True
            break
    if not saw_end or not idat_count:
        raise ValueError("PNG has no complete image data/end marker")
    if expected_dimensions is not None and tuple(expected_dimensions) != dimensions:
        raise ValueError("PNG dimensions differ from the exact intended display")
    from PIL import Image
    with Image.open(BytesIO(raw)) as decoded:
        if decoded.format != "PNG" or decoded.size != dimensions:
            raise ValueError("PNG decoder/header disagreement")
        decoded.load()
        mode = decoded.mode
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "dimensions_pixels": list(dimensions), "chunk_count": len(chunks),
            "IDAT_chunk_count": idat_count, "all_chunk_CRCs_passed": True,
            "IEND_at_exact_EOF": True, "full_PIL_decode_passed": True, "decoded_mode": mode}


def publish_png_atomic(path, raw, overwrite=False, expected_dimensions=None):
    path = Path(path)
    verified = validate_png_bytes(raw, expected_dimensions)
    if path.exists() and not overwrite:
        raise ValueError("Existing image publication is preserved")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".png-publication-", suffix=".pending",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != verified["sha256"]:
            raise ValueError("Complete temporary PNG differs from validated buffer")
        if path.exists() and not overwrite:
            raise ValueError("Image appeared during publication; preserve it")
        os.replace(temporary, path)
        temporary = None
        if hashlib.sha256(path.read_bytes()).hexdigest() != verified["sha256"]:
            raise ValueError("Atomically published PNG differs from validated buffer")
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {**verified, "buffer_validated_before_publication": True,
            "complete_non_PNG_temporary_fsynced": True, "atomic_replace_used": True,
            "published_bytes_match_validated_buffer": True}


def save_figure_atomic(figure, path, **kwargs):
    if "format" in kwargs:
        raise ValueError("The saved-figure format is fixed to PNG")
    buffer = BytesIO()
    figure.savefig(buffer, format="png", **kwargs)
    return publish_png_atomic(path, buffer.getvalue())
