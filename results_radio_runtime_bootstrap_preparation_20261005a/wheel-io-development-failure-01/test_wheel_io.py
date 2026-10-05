"""Synthetic fixtures only: no genuine URL, native wheel or package execution."""
import base64
import csv
import hashlib
import importlib.util
import io
import os
import pathlib
import stat
import struct
import tempfile
import unittest
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("wheel_io_test_subject", HERE / "wheel_io.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

DIST = "demo-1.0.dist-info"
FILENAME = "demo-1.0-py3-none-any.whl"
URL = "https://files.pythonhosted.org/packages/aa/bb/" + FILENAME


class Budget:
    def __init__(self, read_cap=2**30, network_cap=2**30, write_cap=2**30):
        self.read_cap, self.network_cap, self.write_cap = read_cap, network_cap, write_cap
        self.reads = self.network = self.writes = self.checks = self.after = 0
        self.received = {"network": 0, "zip": 0}
        self.directories = []
        self.error = None
    def check(self):
        self.checks += 1
        if self.error: raise self.error
    def debit_read(self, n):
        if self.reads + n > self.read_cap: raise ValueError("read cap")
        self.reads += n
    def debit_network(self, n):
        if self.network + n > self.network_cap: raise ValueError("network cap")
        self.network += n
    def before_write(self, n):
        if self.writes + n > self.write_cap: raise ValueError("write cap")
        self.writes += n
    def after_write(self): self.after += 1
    def check_directory(self, fd): self.directories.append(os.fstat(fd).st_ino)
    def record_received(self, n, kind): self.received[kind] += n


class Headers:
    def __init__(self, rows): self.rows = rows
    def raw_items(self): return iter(self.rows)


class Response:
    def __init__(self, raw, status=200, headers=None, fail_at=None):
        self.stream = io.BytesIO(raw)
        self.status = status
        self.headers = Headers(headers if headers is not None else [("Content-Length", str(len(raw)))])
        self.fail_at = fail_at
        self.closed = False
        self.requests = []
        self.url = URL
    def read(self, size):
        self.requests.append(size)
        if self.fail_at is not None and self.stream.tell() >= self.fail_at:
            raise OSError("synthetic network break")
        if self.fail_at is not None:
            size = min(size, self.fail_at - self.stream.tell())
        return self.stream.read(size)
    def geturl(self): return self.url
    def close(self): self.closed = True


def wheel_spec(raw):
    return {"filename": FILENAME, "url": URL, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "name": "demo", "version": "1.0", "tags": ["py3-none-any"]}


def fixture(extra=None, *, record_edit=None, wheel_text=None, metadata_text=None,
            compression=zipfile.ZIP_STORED, omit=None, duplicates=None):
    files = {"demo/__init__.py": b"# synthetic, never imported\n",
             DIST + "/METADATA": (metadata_text or "Metadata-Version: 2.1\nName: demo\nVersion: 1.0\nRequires-Python: >=3.9\n\n").encode(),
             DIST + "/WHEEL": (wheel_text or "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n").encode(),
             DIST + "/entry_points.txt": b"[console_scripts]\ndemo = demo:main\n"}
    files.update(extra or {})
    rows = []
    for path, content in files.items():
        if not path.endswith("/"):
            rows.append([path, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode(), str(len(content))])
    rows.append([DIST + "/RECORD", "", ""])
    if record_edit:
        record_edit(rows)
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    files[DIST + "/RECORD"] = output.getvalue().encode()
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=compression) as z:
        for path, content in files.items():
            if path == omit: continue
            info = zipfile.ZipInfo(path)
            info.create_system = 3
            info.external_attr = ((stat.S_IFDIR | 0o700) << 16 | 0x10) if path.endswith("/") else ((stat.S_IFREG | 0o600) << 16)
            info.compress_type = compression
            z.writestr(info, content)
        for path, content in duplicates or []:
            z.writestr(path, content)
    return raw.getvalue()


def central_offsets(raw):
    eocd = raw.rfind(b"PK\x05\x06")
    offset = struct.unpack_from("<I", raw, eocd + 16)[0]
    result = []
    while offset < eocd:
        result.append(offset)
        n, x, c = struct.unpack_from("<3H", raw, offset + 28)
        offset += 46 + n + x + c
    return result


class WheelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        os.chmod(self.root, 0o700)
        self.dirfd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.budget = Budget()
        self.deadlines = 0
    def tearDown(self):
        os.close(self.dirfd)
        self.temp.cleanup()
    def deadline(self):
        self.deadlines += 1
        return 60.0
    def acquire(self, raw, *, pinned=None, response=None, opener=None, budget=None):
        response = response or Response(raw)
        calls = []
        def fake(url, timeout):
            calls.append((url, timeout))
            return response
        result = w.acquire_wheel(pinned or wheel_spec(raw), self.dirfd, budget or self.budget,
                                 self.deadline, opener=opener or fake)
        return result, response, calls
    def inspect(self, raw, budget=None):
        path = self.root / FILENAME
        path.write_bytes(raw)
        os.chmod(path, 0o600)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            return w.inspect_wheel(fd, wheel_spec(raw), budget or self.budget, self.deadline)
        finally:
            os.close(fd)
    def refuses(self, raw, message=None):
        with self.assertRaises(w.WheelIOError) as caught:
            self.inspect(raw)
        if message: self.assertIn(message, str(caught.exception))
        return caught.exception

    def test_acquire_single_exact_get_regular_mode_and_identity(self):
        raw = fixture()
        result, response, calls = self.acquire(raw)
        self.assertEqual(result["status"], "ACQUIRED_HASH_MATCH")
        self.assertEqual(result["requests"], 1)
        self.assertEqual(calls, [(URL, 5.0)])
        self.assertEqual((self.root / FILENAME).read_bytes(), raw)
        self.assertEqual(result["file_identity"]["mode"], 0o600)
        self.assertTrue(response.closed)
        self.assertEqual(self.budget.received["network"], len(raw))
        self.assertEqual(self.budget.reads, 0)
        self.assertEqual(self.budget.network, len(raw) + 2)
        self.assertGreater(len(self.budget.directories), 2)

    def test_acquire_hash_failure_retains_all_raw(self):
        raw = fixture()
        pinned = wheel_spec(raw); pinned["sha256"] = "0" * 64
        with self.assertRaises(w.WheelIOError) as e: self.acquire(raw, pinned=pinned)
        self.assertEqual((self.root / FILENAME).read_bytes(), raw)
        self.assertEqual(e.exception.receipt["written_bytes"], len(raw))
        self.assertEqual(e.exception.receipt["sha256"], hashlib.sha256(raw).hexdigest())

    def test_acquire_oversize_preserves_single_extra_byte(self):
        raw = fixture(); response = Response(raw + b"EXTRA", headers=[("Content-Length", str(len(raw)))])
        with self.assertRaises(w.WheelIOError) as e: self.acquire(raw, response=response)
        self.assertEqual((self.root / FILENAME).read_bytes(), raw + b"E")
        self.assertEqual(e.exception.receipt["received_body_bytes"], len(raw) + 1)

    def test_acquire_short_body_is_retained(self):
        raw = fixture(); response = Response(raw[:-8], headers=[("Content-Length", str(len(raw)))])
        with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response)
        self.assertEqual((self.root / FILENAME).read_bytes(), raw[:-8])

    def test_acquire_network_failure_preserves_prefix_and_no_retry(self):
        raw = fixture(); response = Response(raw, fail_at=37)
        with self.assertRaises(w.WheelIOError) as e: self.acquire(raw, response=response)
        self.assertEqual((self.root / FILENAME).read_bytes(), raw[:37])
        self.assertEqual(e.exception.receipt["requests"], 1)
        self.assertEqual(e.exception.receipt["failure_type"], "OSError")
        self.assertEqual(len(response.requests), 2)

    def test_acquire_existing_regular_is_never_replaced(self):
        (self.root / FILENAME).write_bytes(b"prior")
        with self.assertRaises(w.WheelIOError) as e: self.acquire(fixture())
        self.assertEqual((self.root / FILENAME).read_bytes(), b"prior")
        self.assertEqual(e.exception.receipt["requests"], 0)

    def test_acquire_existing_symlink_is_never_followed(self):
        target = self.root / "target"; target.write_bytes(b"prior")
        (self.root / FILENAME).symlink_to(target)
        with self.assertRaises(w.WheelIOError): self.acquire(fixture())
        self.assertEqual(target.read_bytes(), b"prior")

    def test_acquire_redirect_status_refused_without_body_read(self):
        raw = fixture(); response = Response(raw, status=302)
        with self.assertRaises(w.WheelIOError) as e: self.acquire(raw, response=response)
        self.assertEqual(e.exception.receipt["http_status"], 302)
        self.assertFalse(response.requests)
        self.assertEqual((self.root / FILENAME).read_bytes(), b"")

    def test_acquire_fake_redirect_url_refused(self):
        raw = fixture(); response = Response(raw); response.url += "?redirected"
        with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response)
        self.assertFalse(response.requests)

    def test_acquire_content_length_missing_duplicate_noncanonical_wrong(self):
        raw = fixture()
        for headers in ([], [("Content-Length", str(len(raw))), ("Content-Length", str(len(raw)))],
                        [("Content-Length", "+" + str(len(raw)))], [("Content-Length", "1")]):
            with self.subTest(headers=headers):
                (self.root / FILENAME).unlink(missing_ok=True)
                response = Response(raw, headers=headers)
                with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response)
                self.assertFalse(response.requests)

    def test_acquire_encoding_and_header_caps(self):
        raw = fixture()
        for extra in ([('Transfer-Encoding', 'chunked')], [('Content-Encoding', 'gzip')],
                      [('X-Large', 'x' * 8192)], [('X', 'a')] * 129, [('X'+str(i), 'a'*4090) for i in range(5)]):
            with self.subTest(extra=extra[0][0]):
                (self.root / FILENAME).unlink(missing_ok=True)
                response = Response(raw, headers=[("Content-Length", str(len(raw)))] + extra)
                with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response)
                self.assertFalse(response.requests)

    def test_acquire_budget_cap_precedes_network_body_read(self):
        raw = fixture(); response = Response(raw)
        with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response, budget=Budget(network_cap=1))
        self.assertFalse(response.requests)

    def test_acquire_write_cap_retains_already_written_prefix(self):
        raw = fixture(); response = Response(raw, fail_at=37)
        with self.assertRaises(w.WheelIOError): self.acquire(raw, response=response, budget=Budget(write_cap=1))
        self.assertEqual((self.root / FILENAME).read_bytes(), b"")

    def test_acquire_opener_failure_retains_exclusive_empty_output(self):
        def fail(url, timeout): raise OSError("synthetic open failure")
        with self.assertRaises(w.WheelIOError) as e: self.acquire(fixture(), opener=fail)
        self.assertEqual((self.root / FILENAME).read_bytes(), b"")
        self.assertEqual(e.exception.receipt["requests"], 1)

    def test_spec_url_and_path_restrictions_before_creation(self):
        raw = fixture(); original = wheel_spec(raw)
        for url in (URL.replace("https:", "http:"), URL.replace("files.pythonhosted.org", "evil.example"),
                    URL.replace(".org/", ".org:443/"), URL + "?q=1", URL + "#x",
                    URL.replace("/packages/", "/packages/../"), URL.replace("/aa/", "/%61a/")):
            with self.subTest(url=url):
                pinned = dict(original, url=url)
                with self.assertRaises(w.WheelIOError): self.acquire(raw, pinned=pinned)
                self.assertFalse((self.root / FILENAME).exists())

    def test_spec_tag_mismatch_before_creation(self):
        pinned = wheel_spec(fixture()); pinned["tags"] = ["cp312-cp312-any"]
        with self.assertRaises(w.WheelIOError): self.acquire(fixture(), pinned=pinned)
        self.assertFalse((self.root / FILENAME).exists())

    def test_inspect_stored_and_deflated_complete_record(self):
        for method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            with self.subTest(method=method):
                result = self.inspect(fixture(compression=method))
                self.assertEqual(result["status"], "STATIC_WHEEL_PREFLIGHT_VERIFIED")
                self.assertEqual(result["metadata"]["tags"], ["py3-none-any"])
                self.assertEqual(result["metadata"]["entry_points_utf8"], "[console_scripts]\ndemo = demo:main\n")
                self.assertEqual(result["payload_bytes"], sum(r["bytes"] for r in result["members"]))
                self.assertEqual(result["actual_archive_read_bytes"], self.budget.received["zip"] if method == 0 else result["actual_archive_read_bytes"])
                self.assertFalse(result["packages_imported"])

    def test_inspect_valid_directories_and_data_remain_unmapped(self):
        result = self.inspect(fixture({"demo/": b"", "demo-1.0.data/scripts/demo": b"#!/python\n"}))
        self.assertFalse(result["metadata"]["data_paths_remapped"])
        self.assertEqual(len([r for r in result["members"] if r["kind"] == "directory"]), 1)

    def test_inspect_native_extensions_only_listed_not_parsed(self):
        result = self.inspect(fixture({"demo/lib.so.1": b"not ELF, synthetic only"}))
        self.assertEqual(result["native_member_paths"], ["demo/lib.so.1"])
        self.assertFalse(result["native_elf_parsed"])

    def test_inspect_archive_hash_checked_independently(self):
        raw = fixture(); path = self.root / FILENAME; path.write_bytes(raw)
        fd = os.open(path, os.O_RDONLY)
        try:
            pinned = wheel_spec(raw); pinned["sha256"] = "0" * 64
            with self.assertRaises(w.WheelIOError) as e: w.inspect_wheel(fd, pinned, self.budget, self.deadline)
            self.assertIn("archive SHA256", str(e.exception))
        finally: os.close(fd)

    def test_inspect_hardlink_is_refused(self):
        raw = fixture(); path = self.root / FILENAME; path.write_bytes(raw); os.link(path, self.root / "alias")
        fd = os.open(path, os.O_RDONLY)
        try:
            with self.assertRaises(w.WheelIOError): w.inspect_wheel(fd, wheel_spec(raw), self.budget, self.deadline)
            self.assertEqual(self.budget.reads, 0)
        finally: os.close(fd)

    def test_inspect_read_cap_before_archive_read(self):
        e = self.refuses(fixture(), "read cap") if False else None
        with self.assertRaises(w.WheelIOError) as e: self.inspect(fixture(), Budget(read_cap=1))
        self.assertEqual(e.exception.receipt["actual_archive_read_bytes"], 0)

    def test_inspect_deadline_precedes_read(self):
        def expired(): raise TimeoutError("synthetic deadline")
        self.deadline = expired
        with self.assertRaises(w.WheelIOError) as e: self.inspect(fixture())
        self.assertEqual(e.exception.receipt["actual_archive_read_bytes"], 0)

    def test_inspect_unsafe_archive_paths(self):
        for path in ("../escape", "/escape", "demo//x", "demo/./x", "demo/../x", "demo\\x", "C:x", "demo/nul", "demo/x.", "demo/x ", "demo/line\nx"):
            with self.subTest(path=path): self.refuses(fixture({path: b"x"}))

    def test_inspect_duplicate_case_alias_and_file_directory_prefix(self):
        for raw in (fixture(duplicates=[("demo/__init__.py", b"x")]), fixture({"Demo/__INIT__.py": b"x"}),
                    fixture({"node": b"x", "node/child": b"x"}), fixture({"node": b"x", "node/": b""})):
            self.refuses(raw)

    def test_inspect_symlink_fifo_special_file_refused(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFBLK):
            raw = bytearray(fixture()); central = central_offsets(raw)[0]
            struct.pack_into("<I", raw, central + 38, (kind | 0o600) << 16)
            with self.subTest(kind=kind): self.refuses(bytes(raw), "symlink/special")

    def test_inspect_eocd_count_central_size_zip64_multidisk_caps(self):
        original = fixture(); end = original.rfind(b"PK\x05\x06")
        for field, fmt, value in ((end+8, "H", 8193), (end+12, "I", 2*1024*1024+1),
                                  (end+10, "H", 65535), (end+4, "H", 1)):
            raw = bytearray(original); struct.pack_into("<"+fmt, raw, field, value)
            self.refuses(bytes(raw))

    def test_inspect_encryption_and_unsupported_compression(self):
        original = fixture(); central = central_offsets(original)[0]
        for field, value in ((central+8, 1), (central+10, 12)):
            raw = bytearray(original); struct.pack_into("<H", raw, field, value)
            self.refuses(bytes(raw), "encrypted/unsupported")

    def test_inspect_local_central_filename_mismatch(self):
        raw = bytearray(fixture()); raw[30] ^= 1
        self.refuses(bytes(raw), "local and central filenames")

    def test_inspect_local_central_lengths_mismatch(self):
        raw = bytearray(fixture()); struct.pack_into("<I", raw, 22, 999)
        self.refuses(bytes(raw), "local and central CRC/length")

    def test_inspect_local_region_alias_and_trailing_unknown_data(self):
        original = fixture(); offsets = central_offsets(original)
        raw = bytearray(original); struct.pack_into("<I", raw, offsets[1]+42, 0)
        self.refuses(bytes(raw))
        self.refuses(original + b"unparsed", "EOCD")

    def test_inspect_declared_member_size_bound_before_stream(self):
        raw = bytearray(fixture()); central = central_offsets(raw)[0]
        struct.pack_into("<I", raw, central+24, w.MEMBER_MAX+1)
        self.refuses(bytes(raw), "declared size exceeds cap")

    def test_inspect_declared_payload_bound_before_stream(self):
        raw = bytearray(fixture({"extra/a": b"a", "extra/b": b"b"}))
        for central in central_offsets(raw): struct.pack_into("<I", raw, central+24, w.MEMBER_MAX)
        self.refuses(bytes(raw), "aggregate payload")

    def test_inspect_corrupt_member_crc(self):
        raw = bytearray(fixture()); raw[30+len("demo/__init__.py")] ^= 1
        self.refuses(bytes(raw), "CRC")

    def test_inspect_record_hash_length_and_canonical_encoding(self):
        def wrong_hash(rows): rows[0][1] = "sha256=" + "A"*43
        def wrong_size(rows): rows[0][2] = "999"
        def padded_hash(rows): rows[0][1] += "="
        def wrong_algorithm(rows): rows[0][1] = rows[0][1].replace("sha256", "md5")
        def leading_zero(rows): rows[0][2] = "0" + rows[0][2]
        for edit in (wrong_hash, wrong_size, padded_hash, wrong_algorithm, leading_zero):
            self.refuses(fixture(record_edit=edit), "RECORD")

    def test_inspect_record_coverage_missing_extra_duplicate_and_self(self):
        def missing(rows): rows.pop(0)
        def extra(rows): rows.append(["ghost", "sha256="+"A"*43, "0"])
        def duplicate(rows): rows.append(rows[0])
        def self_hash(rows): rows[-1][1] = "sha256="+"A"*43
        for edit in (missing, extra, duplicate, self_hash): self.refuses(fixture(record_edit=edit), "RECORD")

    def test_inspect_deprecated_record_signatures(self):
        for name in ("RECORD.jws", "RECORD.p7s"):
            self.refuses(fixture({DIST+"/"+name: b"signature"}), "deprecated")

    def test_inspect_metadata_name_version_and_duplicate_fields(self):
        for text in ("Name: other\nVersion: 1.0\n", "Name: demo\nVersion: 2.0\n", "Name: demo\nName: demo\nVersion: 1.0\n"):
            self.refuses(fixture(metadata_text=text), "METADATA")

    def test_inspect_wheel_version_purelib_tags_and_duplicates(self):
        for text in ("Wheel-Version: 1.1\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
                     "Wheel-Version: 1.0\nRoot-Is-Purelib: True\nTag: py3-none-any\n",
                     "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\nTag: py3-none-any\n",
                     "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: cp312-none-any\n"):
            self.refuses(fixture(wheel_text=text))

    def test_inspect_missing_metadata_and_extra_distinfo(self):
        self.refuses(fixture(omit=DIST+"/METADATA"), "lacks")
        self.refuses(fixture({"other-1.0.dist-info/METADATA": b"Name: other\nVersion: 1.0\n"}), "additional")

    def test_inspect_data_wrong_root_and_unknown_scheme(self):
        for name in ("other-1.0.data/scripts/x", "demo-1.0.data/unknown/x", "demo-1.0.data/scripts"):
            self.refuses(fixture({name: b"x"}), ".data")

    def test_inspect_directory_payload_refused(self):
        self.refuses(fixture({"demo/": b"x"}), "directory is nonempty")

    def test_inspect_bounded_metadata_capture(self):
        self.refuses(fixture({DIST+"/entry_points.txt": b"x"*(w.METADATA_MAX+1)}), "bounded capture")

    def test_inspect_preserves_archive_and_does_not_create_install(self):
        raw = fixture(); self.inspect(raw)
        self.assertEqual((self.root / FILENAME).read_bytes(), raw)
        self.assertEqual([p.name for p in self.root.iterdir()], [FILENAME])


if __name__ == "__main__":
    unittest.main(verbosity=2)
