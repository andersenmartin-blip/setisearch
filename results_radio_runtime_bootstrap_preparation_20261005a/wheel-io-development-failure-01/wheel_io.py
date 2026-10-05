"""Bounded wheel acquisition and static preflight; never installs or imports wheels.

The caller supplies an already pinned wheel spec and a held destination directory.
Budget read/network debit methods precharge requested bytes, including EOF probes;
returned counters separately describe actual bytes made visible to this module.
TLS bootstrap, kernel buffering and provider resource peaks remain unqualified.
"""
import base64
import csv
import email.parser
import hashlib
import io
import itertools
import os
import re
import stat
import struct
import unicodedata
import urllib.parse
import zipfile
import zlib

CHUNK = 1024 * 1024
HEADER_MAX = 16384
HEADER_LINE_MAX = 8192
HEADER_COUNT_MAX = 128
CENTRAL_MAX = 2 * 1024 * 1024
ENTRY_MAX = 8192
MEMBER_MAX = 128 * 1024 * 1024
PAYLOAD_MAX = 512 * 1024 * 1024
METADATA_MAX = 2 * 1024 * 1024
SUPPORTED_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


class WheelIOError(RuntimeError):
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt or {}


def _fail(message):
    raise WheelIOError(message)


def _tick(budget, deadline_callback):
    budget.check()
    return deadline_callback()


def _received(budget, n, kind):
    record = getattr(budget, "record_received", None)
    if record is not None:
        record(n, kind=kind)


def _identity(st):
    return {"dev": st.st_dev, "ino": st.st_ino, "mode": stat.S_IMODE(st.st_mode),
            "nlink": st.st_nlink, "bytes": st.st_size}


def _directory(fd, initial, budget, deadline_callback):
    _tick(budget, deadline_callback)
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode) or (st.st_dev, st.st_ino) != initial:
        _fail("held wheelhouse directory identity changed")
    check = getattr(budget, "check_directory", None)
    if check is not None:
        check(fd)


def _safe_path(name, directory=False):
    if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 4096:
        _fail("invalid or oversized archive path")
    if any(ord(c) < 32 or ord(c) == 127 for c in name) or "\\" in name or ":" in name:
        _fail("archive path contains control, backslash or drive separator")
    if unicodedata.normalize("NFC", name) != name or name.startswith("/"):
        _fail("archive path is absolute or has a normalization alias")
    stripped = name[:-1] if directory and name.endswith("/") else name
    if not stripped or (not directory and name.endswith("/")):
        _fail("invalid directory/file path spelling")
    for part in stripped.split("/"):
        if not part or part in (".", "..") or part.endswith((".", " ")):
            _fail("archive path has unsafe component")
        if re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part):
            _fail("archive path has reserved portable component")
    return stripped


def _spec(wheel):
    required = ("filename", "url", "bytes", "sha256", "name", "version", "tags")
    if not isinstance(wheel, dict) or any(k not in wheel for k in required):
        _fail("wheel spec is incomplete")
    filename = _safe_path(wheel["filename"])
    if "/" in filename or not filename.endswith(".whl"):
        _fail("wheel output must be one fixed .whl filename")
    if type(wheel["bytes"]) is not int or not 0 < wheel["bytes"] <= PAYLOAD_MAX:
        _fail("wheel expected byte length is outside cap")
    if not isinstance(wheel["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", wheel["sha256"]):
        _fail("wheel SHA256 is not canonical")
    u = urllib.parse.urlsplit(wheel["url"])
    if (u.scheme != "https" or u.netloc != "files.pythonhosted.org" or
            u.username is not None or u.password is not None or u.port is not None or
            u.query or u.fragment or not u.path.startswith("/packages/") or
            u.path.rsplit("/", 1)[-1] != filename or urllib.parse.unquote(u.path) != u.path):
        _fail("wheel URL is not the exact pinned HTTPS files.pythonhosted.org URL")
    _safe_path(u.path[1:])
    parts = filename[:-4].split("-")
    if len(parts) not in (5, 6):
        _fail("wheel filename has unsupported fields")
    if len(parts) == 6 and not re.fullmatch(r"[0-9][A-Za-z0-9_]*", parts[2]):
        _fail("wheel build tag is invalid")
    norm = lambda s: re.sub(r"[-_.]+", "_", s).lower()
    if norm(parts[0]) != norm(wheel["name"]) or parts[1] != wheel["version"]:
        _fail("wheel filename distribution/version differs from pinned spec")
    expanded = sorted("-".join(x) for x in itertools.product(*(p.split(".") for p in parts[-3:])))
    if (not isinstance(wheel["tags"], list) or sorted(wheel["tags"]) != expanded or
            len(set(wheel["tags"])) != len(expanded) or
            any(not re.fullmatch(r"[A-Za-z0-9_]+-[A-Za-z0-9_]+-[A-Za-z0-9_]+", x) for x in expanded)):
        _fail("wheel filename tags differ from pinned expanded tags")
    return wheel


class _StrictResponse:
    """One bounded status/header block; no interim, redirect or transfer coding."""
    budget = None
    deadline_callback = None

    def begin(self):
        import http.client
        if self.headers is not None:
            return
        raw = []
        total = 0
        for index in range(HEADER_COUNT_MAX + 2):
            _tick(self.budget, self.deadline_callback)
            request = min(HEADER_LINE_MAX + 1, HEADER_MAX - total + 1)
            if request <= 0:
                _fail("received HTTP headers exceed bounded total")
            self.budget.debit_network(request)
            line = self.fp.readline(request)
            _received(self.budget, len(line), "network")
            total += len(line)
            raw.append(line)
            self.raw_header_prefix = b"".join(raw)
            if len(line) > HEADER_LINE_MAX or total > HEADER_MAX:
                _fail("received HTTP headers exceed bounded line or total")
            if not line.endswith(b"\r\n"):
                _fail("HTTP header/status line is missing CRLF")
            if index == 0:
                m = re.fullmatch(rb"HTTP/(1\.[01]) ([0-9]{3}) ([^\r\n]*)\r\n", line)
                if not m:
                    _fail("unsupported or malformed HTTP status line")
                self.version = 10 if m[1] == b"1.0" else 11
                self.status = self.code = int(m[2])
                self.reason = m[3].decode("latin1")
            elif line == b"\r\n":
                break
            elif line[:1] in b" \t" or b":" not in line:
                _fail("HTTP folded or malformed header is refused")
            if index > HEADER_COUNT_MAX:
                _fail("received HTTP header count exceeds cap")
        else:
            _fail("received HTTP header block exceeds cap")
        self.headers = self.msg = email.parser.BytesParser(_class=http.client.HTTPMessage).parsebytes(b"".join(raw[1:]))
        self.chunked = False
        self.chunk_left = None
        # Read to connection close, even beyond declared length, to expose the
        # single bounded +1 oversize probe rather than hide it behind HTTPResponse.
        self.length = None
        self.will_close = True


class _ResponseHandle:
    def __init__(self, response, connection):
        self.response = response
        self.connection = connection
    def __getattr__(self, name):
        return getattr(self.response, name)
    def close(self):
        try:
            self.response.close()
        finally:
            self.connection.close()


def _open_https(url, budget, deadline_callback):
    # This genuine TLS loader path is deliberately not taken by synthetic tests.
    import http.client
    import ssl
    remaining = _tick(budget, deadline_callback)
    timeout = min(5.0, remaining) if type(remaining) in (int, float) else 5.0
    if timeout <= 0:
        _fail("HTTPS deadline has expired")
    response_class = type("BoundedResponse", (_StrictResponse, http.client.HTTPResponse),
                          {"budget": budget, "deadline_callback": staticmethod(deadline_callback)})
    conn = http.client.HTTPSConnection("files.pythonhosted.org", timeout=timeout,
                                       context=ssl.create_default_context())
    conn.response_class = response_class
    try:
        conn.request("GET", urllib.parse.urlsplit(url).path,
                     headers={"Accept-Encoding": "identity", "Connection": "close",
                              "User-Agent": "setisearch-static-wheel-bootstrap/1"})
        return _ResponseHandle(conn.getresponse(), conn)
    except BaseException:
        conn.close()
        raise


def _headers(response):
    source = response.headers
    iterator = source.raw_items() if hasattr(source, "raw_items") else iter(source.items())
    items = []
    total = 0
    for k, v in iterator:
        if not isinstance(k, str) or not isinstance(v, str):
            _fail("non-text HTTP header")
        encoded = (k + ": " + v + "\r\n").encode("latin1", "strict")
        total += len(encoded)
        if len(items) >= HEADER_COUNT_MAX or len(encoded) > HEADER_LINE_MAX or total > HEADER_MAX:
            _fail("received HTTP headers exceed bounded representation")
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", k) or "\r" in v or "\n" in v:
            _fail("malformed HTTP header name or value")
        items.append([k, v])
    return items


def acquire_wheel(wheel, held_wheelhouse_fd, budget, deadline_callback, opener=None):
    """Exactly one GET, one exclusive output and no retry; failure retains raw bytes."""
    _spec(wheel)
    st = os.fstat(held_wheelhouse_fd)
    if not stat.S_ISDIR(st.st_mode):
        _fail("wheelhouse descriptor is not a directory")
    directory_identity = (st.st_dev, st.st_ino)
    receipt = {"schema": "setisearch-wheel-acquisition-v1", "filename": wheel["filename"],
               "url": wheel["url"], "expected_bytes": wheel["bytes"], "expected_sha256": wheel["sha256"],
               "status": "STARTING", "requests": 0, "http_status": None, "headers": [],
               "received_body_bytes": 0, "written_bytes": 0, "charged_body_reads": 0,
               "sha256": hashlib.sha256(b"").hexdigest(), "implicit_tls_loader_io_qualified": False}
    fd = None
    response = None
    digest = hashlib.sha256()
    try:
        _directory(held_wheelhouse_fd, directory_identity, budget, deadline_callback)
        budget.before_write(0)
        fd = os.open(wheel["filename"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=held_wheelhouse_fd)
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode) or fst.st_nlink != 1:
            _fail("exclusive wheel output is not a sole regular file")
        initial_file = (fst.st_dev, fst.st_ino)
        budget.after_write()
        receipt["requests"] = 1
        if opener is None:
            response = _open_https(wheel["url"], budget, deadline_callback)
        else:
            remaining = _tick(budget, deadline_callback)
            timeout = min(5.0, remaining) if type(remaining) in (int, float) else 5.0
            response = opener(wheel["url"], timeout=timeout)
        receipt["http_status"] = response.status
        receipt["headers"] = _headers(response)
        fields = {}
        for k, v in receipt["headers"]:
            fields.setdefault(k.lower(), []).append(v)
        if response.status != 200:
            _fail("HTTP status is not 200; redirect/retry is forbidden")
        lengths = fields.get("content-length", [])
        if len(lengths) != 1 or not re.fullmatch(r"0|[1-9][0-9]*", lengths[0]):
            _fail("exact sole Content-Length is required")
        if int(lengths[0]) != wheel["bytes"]:
            _fail("received Content-Length differs from pinned wheel length")
        if "transfer-encoding" in fields or fields.get("content-encoding", ["identity"]) != ["identity"]:
            _fail("HTTP transfer/content encoding is refused")
        if hasattr(response, "geturl") and response.geturl() != wheel["url"]:
            _fail("opener redirected away from exact pinned URL")
        while True:
            _directory(held_wheelhouse_fd, directory_identity, budget, deadline_callback)
            request = min(CHUNK, wheel["bytes"] - receipt["received_body_bytes"] + 1)
            if request <= 0:
                _fail("wheel body exceeds pinned length")
            budget.debit_network(request)
            receipt["charged_body_reads"] += request
            chunk = response.read(request)
            if not isinstance(chunk, bytes) or len(chunk) > request:
                _fail("HTTP opener violated bounded bytes read")
            _received(budget, len(chunk), "network")
            if not chunk:
                break
            receipt["received_body_bytes"] += len(chunk)
            budget.before_write(len(chunk))
            view = memoryview(chunk)
            while view:
                _tick(budget, deadline_callback)
                n = os.write(fd, view)
                if n <= 0:
                    _fail("wheel output write made no progress")
                digest.update(view[:n])
                receipt["written_bytes"] += n
                receipt["sha256"] = digest.hexdigest()
                view = view[n:]
            budget.after_write()
            if receipt["received_body_bytes"] > wheel["bytes"]:
                _fail("wheel body exceeds pinned length by preserved +1 probe")
        if receipt["written_bytes"] != wheel["bytes"] or digest.hexdigest() != wheel["sha256"]:
            _fail("wheel received length or streamed SHA256 differs from pinned spec")
        _directory(held_wheelhouse_fd, directory_identity, budget, deadline_callback)
        fst = os.fstat(fd)
        if (fst.st_dev, fst.st_ino) != initial_file or fst.st_nlink != 1 or fst.st_size != receipt["written_bytes"]:
            _fail("wheel output identity/length changed")
        receipt["status"] = "ACQUIRED_HASH_MATCH"
        receipt["file_identity"] = _identity(fst)
        return receipt
    except Exception as exc:
        receipt["status"] = "CLOSED_FAILED"
        receipt["failure_type"] = type(exc).__name__
        receipt["failure"] = str(exc)[:4096]
        if fd is not None:
            receipt["file_identity"] = _identity(os.fstat(fd))
        raise WheelIOError("wheel acquisition failed: " + str(exc), receipt) from exc
    finally:
        cleanup = []
        if response is not None:
            try:
                response.close()
            except Exception as exc:
                cleanup.append({"operation": "response.close", "type": type(exc).__name__, "detail": str(exc)[:1024]})
        if fd is not None:
            try:
                os.close(fd)
            except Exception as exc:
                cleanup.append({"operation": "os.close(output)", "type": type(exc).__name__, "detail": str(exc)[:1024]})
        if cleanup:
            receipt["cleanup_failures"] = cleanup
            receipt["status"] = "CLOSED_FAILED"
            raise WheelIOError("wheel acquisition cleanup failed", receipt)


class _ArchiveReader(io.RawIOBase):
    def __init__(self, fd, budget, deadline_callback):
        self.fd, self.budget, self.deadline_callback = fd, budget, deadline_callback
        self.position = 0
        self.initial = os.fstat(fd)
        self.size = self.initial.st_size
        self.actual_reads = 0
        self.charged_reads = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if self.position < 0 or self.position > self.size:
            _fail("archive seek is outside held file")
        return self.position
    def check_identity(self):
        _tick(self.budget, self.deadline_callback)
        st = os.fstat(self.fd)
        a, b = self.initial, st
        if (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns, a.st_nlink) != (
                b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns, b.st_nlink):
            _fail("held wheel archive changed during static preflight")
    def read(self, size=-1):
        if size < 0: size = self.size - self.position
        if size > CENTRAL_MAX or size < 0:
            _fail("archive read exceeds per-operation bound")
        self.check_identity()
        self.budget.debit_read(size)
        self.charged_reads += size
        result = os.pread(self.fd, size, self.position)
        _received(self.budget, len(result), "zip")
        self.actual_reads += len(result)
        self.position += len(result)
        return result
    def at(self, offset, count):
        self.seek(offset)
        result = self.read(count)
        if len(result) != count:
            _fail("truncated held wheel archive")
        return result


def _extras(raw):
    cursor = 0
    while cursor < len(raw):
        if len(raw) - cursor < 4:
            _fail("truncated ZIP extra-field header")
        kind, length = struct.unpack_from("<HH", raw, cursor)
        cursor += 4
        if cursor + length > len(raw):
            _fail("truncated ZIP extra-field value")
        if kind in (0x0001, 0x7075, 0x6375):
            _fail("ZIP64 or Unicode path/comment alias extra is refused")
        cursor += length


def _structure(reader):
    if reader.size < 22:
        _fail("archive has no bounded EOCD")
    tail_start = max(0, reader.size - 65557)
    tail = reader.at(tail_start, reader.size - tail_start)
    candidates = []
    for i in range(len(tail) - 21):
        if tail[i:i+4] == b"PK\x05\x06":
            fields = struct.unpack_from("<4s4H2IH", tail, i)
            if i + 22 + fields[-1] == len(tail):
                candidates.append((tail_start + i, fields))
    if len(candidates) != 1:
        _fail("archive lacks one unambiguous terminal EOCD")
    eocd, f = candidates[0]
    _, disk, cd_disk, disk_count, count, cd_size, cd_offset, _ = f
    if disk or cd_disk or count != disk_count or count == 65535 or cd_size == 0xffffffff or cd_offset == 0xffffffff:
        _fail("ZIP64/multidisk archive is refused")
    if not 0 < count <= ENTRY_MAX or not 0 < cd_size <= CENTRAL_MAX:
        _fail("ZIP central directory count/bytes exceeds bound")
    if cd_offset + cd_size != eocd:
        _fail("central directory does not end at terminal EOCD")
    central = reader.at(cd_offset, cd_size)
    entries = []
    cursor = 0
    aliases = {}
    names = {}
    payload = 0
    for _ in range(count):
        if cursor + 46 > len(central):
            _fail("truncated central directory entry")
        f = struct.unpack_from("<4s6H3I5H2I", central, cursor)
        if f[0] != b"PK\x01\x02":
            _fail("bad central directory signature")
        (_, made, needed, flags, method, mtime, mdate, crc, compressed, size,
         name_len, extra_len, comment_len, start_disk, internal, external, local) = f
        end = cursor + 46 + name_len + extra_len + comment_len
        if end > len(central) or not name_len:
            _fail("central directory variable fields exceed declared span")
        raw_name = central[cursor+46:cursor+46+name_len]
        extra = central[cursor+46+name_len:cursor+46+name_len+extra_len]
        _extras(extra)
        if start_disk or 0xffffffff in (compressed, size, local) or needed > 20:
            _fail("ZIP64/multidisk/new ZIP feature is refused")
        if flags & ~(0x800 | 8) or method not in SUPPORTED_METHODS:
            _fail("encrypted/unsupported ZIP flags or compression")
        if method == zipfile.ZIP_STORED and compressed != size:
            _fail("stored ZIP member has differing compressed/uncompressed lengths")
        try:
            name = raw_name.decode("utf-8" if flags & 0x800 else "ascii")
        except UnicodeDecodeError:
            _fail("noncanonical archive filename encoding")
        directory = name.endswith("/")
        clean = _safe_path(name, directory)
        alias = clean.casefold()
        if name in names or alias in aliases:
            _fail("duplicate or aliased archive path")
        names[name] = directory
        aliases[alias] = directory
        mode = external >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (kind == stat.S_IFDIR) != directory and kind != 0:
            _fail("archive symlink/special file or inconsistent directory kind")
        if external & 0x10 and not directory:
            _fail("DOS directory flag differs from path")
        if size > MEMBER_MAX or directory and size != 0:
            _fail("archive member declared size exceeds cap or directory is nonempty")
        payload += size
        if payload > PAYLOAD_MAX:
            _fail("archive declared aggregate payload exceeds cap")
        if clean.endswith((".dist-info/RECORD.jws", ".dist-info/RECORD.p7s")):
            _fail("deprecated wheel RECORD signatures are refused")
        entries.append({"path": name, "kind": "directory" if directory else "file", "bytes": size,
                        "compressed_bytes": compressed, "crc32": crc, "local_offset": local,
                        "flags": flags, "method": method, "needed": needed,
                        "mtime": mtime, "mdate": mdate, "raw_name": raw_name})
        cursor = end
    if cursor != len(central):
        _fail("central directory has unparsed records or count disagreement")
    for name, directory in names.items():
        clean = name.rstrip("/")
        parts = clean.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i]).casefold()
            if prefix in aliases and aliases[prefix] is False:
                _fail("archive file/directory prefix collision")
    regions = []
    for row in entries:
        local = row["local_offset"]
        if local + 30 > cd_offset:
            _fail("local header overlaps central directory")
        f = struct.unpack("<4s5H3I2H", reader.at(local, 30))
        sig, needed, flags, method, mtime, mdate, crc, compressed, size, name_len, extra_len = f
        if (sig != b"PK\x03\x04" or (needed, flags, method, mtime, mdate) !=
                (row["needed"], row["flags"], row["method"], row["mtime"], row["mdate"])):
            _fail("local and central ZIP header metadata differs")
        variable_end = local + 30 + name_len + extra_len
        if variable_end > cd_offset:
            _fail("local variable header overlaps central directory")
        variable = reader.at(local + 30, name_len + extra_len)
        if variable[:name_len] != row["raw_name"]:
            _fail("local and central filenames differ")
        _extras(variable[name_len:])
        expected = (row["crc32"], row["compressed_bytes"], row["bytes"])
        if flags & 8:
            if any(got not in (0, want) for got, want in zip((crc, compressed, size), expected)):
                _fail("local descriptor placeholders differ from central values")
        elif (crc, compressed, size) != expected:
            _fail("local and central CRC/length differs")
        data_end = variable_end + row["compressed_bytes"]
        if data_end > cd_offset:
            _fail("compressed member overlaps central directory")
        end = data_end
        if flags & 8:
            if data_end + 12 > cd_offset:
                _fail("truncated ZIP data descriptor")
            probe = reader.at(data_end, 4)
            signed = probe == b"PK\x07\x08"
            descriptor = reader.at(data_end + (4 if signed else 0), 12)
            if struct.unpack("<3I", descriptor) != expected:
                _fail("ZIP data descriptor disagrees with central values")
            end += 16 if signed else 12
            if end > cd_offset:
                _fail("ZIP data descriptor overlaps central directory")
        row["data_offset"] = variable_end
        row["region_end"] = end
        regions.append((local, end))
    cursor = 0
    for start, end in sorted(regions):
        if start != cursor:
            _fail("archive local regions overlap or leave an unparsed gap/preamble")
        cursor = end
    if cursor != cd_offset:
        _fail("archive local regions do not meet central directory")
    return entries, payload


def _payload_chunks(reader, row):
    """Checks actual raw DEFLATE end/consumption; ZipExtFile trims declared size."""
    remaining = row["compressed_bytes"]
    offset = row["data_offset"]
    produced = 0
    decompressor = zlib.decompressobj(-15) if row["method"] == zipfile.ZIP_DEFLATED else None
    while remaining:
        raw = reader.at(offset, min(CHUNK, remaining))
        remaining -= len(raw)
        offset += len(raw)
        if decompressor is None:
            produced += len(raw)
            if produced > row["bytes"]:
                _fail("stored payload exceeds declared length")
            yield raw
            continue
        pending = raw
        while pending:
            _tick(reader.budget, reader.deadline_callback)
            limit = min(CHUNK, row["bytes"] - produced + 1)
            chunk = decompressor.decompress(pending, limit)
            produced += len(chunk)
            if produced > row["bytes"]:
                _fail("DEFLATE payload exceeds declared length by bounded +1")
            if decompressor.unused_data or decompressor.eof and remaining:
                _fail("DEFLATE stream has trailing declared compressed bytes")
            next_pending = decompressor.unconsumed_tail
            if not chunk and next_pending == pending:
                _fail("DEFLATE stream made no progress")
            pending = next_pending
            if chunk:
                yield chunk
    if decompressor is not None:
        while not decompressor.eof:
            _tick(reader.budget, reader.deadline_callback)
            chunk = decompressor.decompress(b"", min(CHUNK, row["bytes"] - produced + 1))
            produced += len(chunk)
            if produced > row["bytes"]:
                _fail("DEFLATE payload exceeds declared length by bounded +1")
            if not chunk:
                _fail("DEFLATE stream lacks exact end marker")
            yield chunk
        if decompressor.unused_data or decompressor.unconsumed_tail:
            _fail("DEFLATE stream did not consume its exact compressed span")
    if produced != row["bytes"]:
        _fail("streamed archive member length differs from declaration")


def _metadata(content, wheel, entries):
    norm = lambda s: re.sub(r"[-_.]+", "_", s).lower()
    dist = norm(wheel["name"]) + "-" + wheel["version"] + ".dist-info"
    record = dist + "/RECORD"
    metadata = dist + "/METADATA"
    wheel_path = dist + "/WHEEL"
    regular = {r["path"]: r for r in entries if r["kind"] == "file"}
    if any(p not in regular for p in (record, metadata, wheel_path)):
        _fail("wheel lacks its one pinned METADATA/WHEEL/RECORD set")
    roots = {p.split("/", 1)[0] for p in regular if p.split("/", 1)[0].endswith(".dist-info")}
    if roots != {dist}:
        _fail("wheel has an additional or mismatched dist-info root")
    for path in regular:
        parts = path.split("/")
        if parts[0].endswith(".data"):
            if (parts[0] != dist[:-10] + ".data" or len(parts) < 3 or
                    parts[1] not in ("purelib", "platlib", "headers", "scripts", "data")):
                _fail("wheel .data path has wrong distribution root or scheme")
    parsed = email.parser.BytesParser().parsebytes(content[metadata])
    for field, expected in (("Name", wheel["name"]), ("Version", wheel["version"])):
        values = parsed.get_all(field, [])
        if len(values) != 1 or (norm(values[0]) != norm(expected) if field == "Name" else values[0] != expected):
            _fail("METADATA name/version differs from pinned spec")
    wh = email.parser.BytesParser().parsebytes(content[wheel_path])
    if wh.get_all("Wheel-Version", []) != ["1.0"]:
        _fail("only sole Wheel-Version 1.0 is supported")
    pure = wh.get_all("Root-Is-Purelib", [])
    if pure not in (["true"], ["false"]):
        _fail("Root-Is-Purelib must be one canonical boolean")
    tags = wh.get_all("Tag", [])
    if len(tags) != len(set(tags)) or sorted(tags) != sorted(wheel["tags"]):
        _fail("WHEEL expanded tags differ from pinned tags")
    if pure == ["true"] and any(t.split("-")[1:] != ["none", "any"] for t in tags):
        _fail("purelib wheel has non-pure pinned ABI/platform tags")
    try:
        rows = list(csv.reader(io.StringIO(content[record].decode("utf-8"), newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        _fail("RECORD is not strict UTF8 CSV: " + str(exc))
    seen = set()
    for row in rows:
        if len(row) != 3:
            _fail("RECORD row must contain exactly three columns")
        path, encoded, size = row
        _safe_path(path)
        if path in seen or path not in regular:
            _fail("RECORD duplicates or names a missing/nonregular member")
        seen.add(path)
        if path == record:
            if encoded or size:
                _fail("RECORD self row must have blank hash and size")
            continue
        if not re.fullmatch(r"sha256=[A-Za-z0-9_-]{43}", encoded):
            _fail("RECORD hash must be canonical unpadded URL-safe SHA256")
        raw = base64.urlsafe_b64decode(encoded[7:] + "=")
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != encoded[7:]:
            _fail("RECORD hash has noncanonical trailing bits")
        if not re.fullmatch(r"0|[1-9][0-9]*", size):
            _fail("RECORD size is not canonical decimal")
        if int(size) != regular[path]["bytes"] or raw.hex() != regular[path]["sha256"]:
            _fail("RECORD member hash or length differs from streamed content")
    if seen != set(regular):
        _fail("RECORD does not cover exactly every regular archive member")
    entry_path = dist + "/entry_points.txt"
    entrypoints = content.get(entry_path)
    if entrypoints is not None:
        try:
            entrypoints = entrypoints.decode("utf-8")
        except UnicodeDecodeError:
            _fail("entry_points.txt is not UTF8")
    return {"name": parsed["Name"], "version": parsed["Version"],
            "requires_python": parsed.get_all("Requires-Python", []),
            "requires_dist": parsed.get_all("Requires-Dist", []),
            "metadata_version": parsed.get_all("Metadata-Version", []),
            "wheel_version": "1.0", "root_is_purelib": pure == ["true"],
            "tags": sorted(tags), "dist_info": dist, "entry_points_utf8": entrypoints,
            "data_paths_remapped": False}


def inspect_wheel(held_fd, wheel, budget, deadline_callback):
    """Statically verifies a held archive; no extraction, install, import or ELF parse."""
    _spec(wheel)
    st = os.fstat(held_fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size != wheel["bytes"]:
        _fail("held wheel is not a sole regular file with pinned length")
    reader = _ArchiveReader(held_fd, budget, deadline_callback)
    receipt = {"schema": "setisearch-wheel-static-preflight-v1", "filename": wheel["filename"],
               "status": "STARTING", "archive_bytes": st.st_size, "file_identity": _identity(st),
               "archive_sha256": None, "payload_bytes": None, "members": [],
               "native_elf_parsed": False, "installed": False, "packages_imported": False}
    try:
        digest = hashlib.sha256()
        while reader.tell() < reader.size:
            digest.update(reader.read(min(CHUNK, reader.size - reader.tell())))
        receipt["archive_sha256"] = digest.hexdigest()
        if receipt["archive_sha256"] != wheel["sha256"]:
            _fail("held archive SHA256 differs from pinned spec")
        entries, payload = _structure(reader)
        receipt["payload_bytes"] = payload
        contents = {}
        with zipfile.ZipFile(reader, "r", allowZip64=False) as archive:
            infos = archive.infolist()
            if len(infos) != len(entries) or [i.filename for i in infos] != [r["path"] for r in entries]:
                _fail("ZipFile view differs from bounded central directory preflight")
            actual_payload = 0
            for info, row in zip(infos, entries):
                if (info.CRC, info.file_size, info.compress_size, info.header_offset, info.flag_bits, info.compress_type) != (
                        row["crc32"], row["bytes"], row["compressed_bytes"], row["local_offset"], row["flags"], row["method"]):
                    _fail("ZipFile entry fields differ from bounded structural preflight")
                sha = hashlib.sha256()
                count = 0
                crc = 0
                capture = (row["path"].endswith((".dist-info/METADATA", ".dist-info/WHEEL",
                                                ".dist-info/RECORD", ".dist-info/entry_points.txt")))
                raw = bytearray()
                if capture and row["bytes"] > METADATA_MAX:
                    _fail("wheel metadata/RECORD/entrypoints exceeds bounded capture")
                for chunk in _payload_chunks(reader, row):
                    _tick(budget, deadline_callback)
                    count += len(chunk)
                    actual_payload += len(chunk)
                    if count > row["bytes"] or count > MEMBER_MAX or actual_payload > PAYLOAD_MAX:
                        _fail("streamed archive payload exceeds declared or scope cap")
                    sha.update(chunk)
                    crc = zlib.crc32(chunk, crc)
                    if capture:
                        raw.extend(chunk)
                if count != row["bytes"]:
                    _fail("streamed archive member length differs from declaration")
                if crc != row["crc32"]:
                    _fail("streamed archive member CRC32 differs from declaration")
                row["sha256"] = sha.hexdigest()
                if capture:
                    contents[row["path"]] = bytes(raw)
                receipt["members"].append({k: row[k] for k in ("path", "kind", "bytes", "sha256", "compressed_bytes", "crc32")})
            if actual_payload != payload:
                _fail("streamed aggregate payload differs from central declarations")
        receipt["metadata"] = _metadata(contents, wheel, entries)
        receipt["native_member_paths"] = [r["path"] for r in entries if r["kind"] == "file" and
                                           re.search(r"(?:\.so(?:\.[0-9]+)*|\.dll|\.dylib|\.pyd)$", r["path"], re.I)]
        reader.check_identity()
        receipt["status"] = "STATIC_WHEEL_PREFLIGHT_VERIFIED"
        return receipt
    except Exception as exc:
        receipt["status"] = "CLOSED_FAILED"
        receipt["failure_type"] = type(exc).__name__
        receipt["failure"] = str(exc)[:4096]
        raise WheelIOError("wheel static preflight failed: " + str(exc), receipt) from exc
    finally:
        receipt["actual_archive_read_bytes"] = reader.actual_reads
        receipt["charged_archive_read_bytes"] = reader.charged_reads
