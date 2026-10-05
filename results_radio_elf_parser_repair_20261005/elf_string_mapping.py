"""Pure byte mapping repair; never loads or executes an ELF file."""


class Refusal(Exception):
    pass


def file_backed_virtual_bytes(raw, loads, address, length):
    """Resolve one contiguous virtual interval through exact file-backed spans.

    PT_LOAD boundaries need not coincide with a dynamic string-table boundary.
    Every virtual byte must have exactly one file-offset translation. Overlapping
    headers are allowed only when those translations are identical; equal bytes
    at different offsets do not remove an ambiguity. Zero-filled memory is not
    a source of file bytes. The caller already validated all segment bounds.
    """
    if (type(address) is not int or type(length) is not int or address < 0 or
            length <= 0 or length > len(raw)):
        raise Refusal("dynamic string table interval outside finite file bound")
    end = address + length
    boundaries = {address, end}
    for va, file_size, file_offset in loads:
        if (type(va) is not int or type(file_size) is not int or
                type(file_offset) is not int or min(va, file_size, file_offset) < 0 or
                file_offset + file_size > len(raw)):
            raise Refusal("ELF file-backed load bounds invalid")
        for value in (va, va + file_size):
            if address < value < end:
                boundaries.add(value)
    chunks = []
    ordered = sorted(boundaries)
    for left, right in zip(ordered, ordered[1:]):
        locations = {file_offset + left - va for va, file_size, file_offset in loads
                     if va <= left and right <= va + file_size}
        if not locations:
            raise Refusal("dynamic string table has a non-file-backed virtual gap")
        if len(locations) != 1:
            raise Refusal("dynamic string table has conflicting file-offset translations")
        location = locations.pop()
        count = right - left
        if location < 0 or location + count > len(raw):
            raise Refusal("dynamic string span outside complete file bytes")
        chunks.append(raw[location:location + count])
    table = b"".join(chunks)
    if len(table) != length:
        raise Refusal("dynamic string table exact byte coverage failed")
    return table
