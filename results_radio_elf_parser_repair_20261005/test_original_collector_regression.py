"""Offline tests: stdlib plus fake module/HDF5 interfaces; no real imports."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).with_name("collect_runtime_identity_repaired.py")
spec = importlib.util.spec_from_file_location("collector_under_test", SOURCE)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def elf_fixture(bits=64, endian="<"):
    """Small ELF metadata fixture. Never executable or loaded as native code."""
    size, phsize, dynwidth = (64, 56, 16) if bits == 64 else (52, 32, 8)
    raw = bytearray(512)
    raw[:16] = b"\x7fELF" + bytes([2 if bits == 64 else 1, 1 if endian == "<" else 2, 1]) + bytes(9)
    fmt = endian + ("HHIQQQIHHHHHH" if bits == 64 else "HHIIIIIHHHHHH")
    struct.pack_into(fmt, raw, 16, 3, 62 if bits == 64 else 3, 1, 0, size, 0, 0,
                     size, phsize, 2, 0, 0, 0)
    def ph(index, typ, off, va, length):
        if bits == 64:
            struct.pack_into(endian + "IIQQQQQQ", raw, size + index * phsize,
                             typ, 4, off, va, 0, length, length, 8)
        else:
            struct.pack_into(endian + "IIIIIIII", raw, size + index * phsize,
                             typ, off, va, 0, length, length, 4, 4)
    ph(0, 1, 0, 0x1000, len(raw))
    ph(1, 2, 200, 0x1000 + 200, 6 * dynwidth)
    table = b"\0libfoo.so\0$ORIGIN\0/locked/lib\0"
    raw[400:400 + len(table)] = table
    for i, (tag, val) in enumerate([(5, 0x1000 + 400), (10, len(table)),
                                     (1, 1), (15, 11), (29, 19), (0, 0)]):
        struct.pack_into(endian + ("qQ" if bits == 64 else "iI"), raw, 200 + i * dynwidth, tag, val)
    return bytes(raw)


class ElfTests(unittest.TestCase):
    def test_exact_needed_rpath_runpath_in_32_and_64_endian_variants(self):
        for bits in (32, 64):
            for endian in ("<", ">"):
                info = collector.elf_dynamic(elf_fixture(bits, endian))
                self.assertEqual(info["needed"], ["libfoo.so"])
                self.assertEqual(info["rpath"], ["$ORIGIN"])
                self.assertEqual(info["runpath"], ["/locked/lib"])
                self.assertEqual(info["class_bits"], bits)

    def test_missing_dynamic_terminator_refused(self):
        raw = bytearray(elf_fixture())
        struct.pack_into("<qQ", raw, 200 + 5 * 16, 1, 1)
        with self.assertRaisesRegex(collector.Refusal, "unterminated"):
            collector.elf_dynamic(raw)

    def test_out_of_file_program_header_refused(self):
        with self.assertRaises(collector.Refusal):
            collector.elf_dynamic(elf_fixture()[:80])

    def test_unterminated_dynamic_string_refused(self):
        raw = bytearray(elf_fixture())
        raw[400:431] = b"x" * 31
        with self.assertRaisesRegex(collector.Refusal, "unterminated dynamic string"):
            collector.elf_dynamic(raw)


class ReadTests(unittest.TestCase):
    def test_full_hash_at_exact_budget_and_honest_cache_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "native.so"
            raw = elf_fixture(); p.write_bytes(raw)
            reader = collector.BoundedReader(limit=len(raw))
            a = reader.native(p); b = reader.native(p)
            self.assertEqual(a["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(reader.charged_bytes, len(raw))
            self.assertFalse(a["hash_reused_after_identity_recheck"])
            self.assertTrue(b["hash_reused_after_identity_recheck"])

    def test_budget_refusal_before_native_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "native.so"; p.write_bytes(elf_fixture())
            reader = collector.BoundedReader(limit=20)
            with self.assertRaisesRegex(collector.Refusal, "cannot fit"):
                reader.native(p)
            self.assertEqual(reader.charged_bytes, 0)

    def test_nonelf_mapped_file_retained_but_cannot_be_native_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "locale"; p.write_bytes(b"metadata")
            reader = collector.BoundedReader()
            self.assertIsNone(reader.native(p, require_elf=False)["elf"])
            with self.assertRaises(collector.Refusal):
                reader.native(p)

    def test_deleted_mapping_refused_and_path_spaces_preserved(self):
        raw = b"1000-2000 r-xp 00000000 08:01 42 /a/path with spaces.so\n"
        records, paths = collector.parse_maps(raw)
        self.assertEqual(paths, ["/a/path with spaces.so"])
        self.assertEqual(records[0]["inode"], "42")
        with self.assertRaisesRegex(collector.Refusal, "deleted"):
            collector.parse_maps(raw.replace(b".so\n", b".so (deleted)\n"))


class FakeH5Z:
    def __init__(self):
        self.registered = False
        self.calls = []

    def filter_avail(self, number):
        self.calls.append(("filter_avail", number))
        return self.registered

    def get_filter_info(self, number):
        self.calls.append(("get_filter_info", number))
        return 3

    def __getattr__(self, name):
        raise AssertionError("forbidden native operation requested: " + name)


class OrchestrationTests(unittest.TestCase):
    def setup_fakes(self, *, wrong_version=False, wrong_filters=False):
        events = []; h5z = FakeH5Z()
        modules = {
            "numpy": SimpleNamespace(__version__="2.3.5"),
            "h5py": SimpleNamespace(__version__="3.16.0", h5z=h5z,
                                     version=SimpleNamespace(hdf5_version="2.0.0",
                                     hdf5_version_tuple=(2, 0, 0), hdf5_built_version_tuple=(2, 0, 0))),
            "hdf5plugin": SimpleNamespace(version="7.1.0", FILTERS={"test": 32001}, PLUGIN_PATH="/fake/plugins")}
        if wrong_filters:
            modules["hdf5plugin"].FILTERS = {"wrong": 32002}
        def importer(name):
            events.append("import:" + name)
            if name == "hdf5plugin":
                h5z.registered = True
            return modules[name]
        def distribution(name):
            events.append("distribution:" + name)
            version = "9.0.0" if wrong_version else collector.COHORT[name]
            return SimpleNamespace(version=version)
        def snapshot():
            events.append("maps")
            return {"fake_snapshot_index": len(events)}
        return events, h5z, dict(importer=importer, distribution_getter=distribution,
                 snapshotter=snapshot, inventory=lambda n,d: {"files": [{"name": n}]},
                 module_observer=lambda m: {"fake_module": True})

    def test_before_after_filter_registration_and_zero_authority(self):
        events, h5z, kwargs = self.setup_fakes()
        out = collector.collect("/fake", {"test": 32001}, **kwargs)
        self.assertFalse(out["filters_before_plugin"][0]["available"])
        self.assertTrue(out["filters_after_plugin"][0]["available"])
        self.assertEqual(h5z.calls, [("filter_avail",32001), ("filter_avail",32001), ("get_filter_info",32001)])
        self.assertEqual([x for x in events if x.startswith("import:")],
                         ["import:numpy", "import:h5py", "import:hdf5plugin"])
        self.assertTrue(all(value is False for value in out["authority"].values()))
        self.assertEqual(out["status"], "COLLECTED_IDENTITY_INPUTS_ONLY")

    def test_wrong_distribution_version_refused_before_any_native_import(self):
        events, _, kwargs = self.setup_fakes(wrong_version=True)
        with self.assertRaisesRegex(collector.Refusal, "distribution version"):
            collector.collect("/fake", {"test":32001}, **kwargs)
        self.assertFalse(any(x.startswith("import:") for x in events))

    def test_source_filter_mismatch_never_claims_complete(self):
        _, _, kwargs = self.setup_fakes(wrong_filters=True)
        with self.assertRaisesRegex(collector.Refusal, "FILTERS differs"):
            collector.collect("/fake", {"test":32001}, **kwargs)

    def test_unexpected_hdf5_runtime_refused(self):
        _, _, kwargs = self.setup_fakes()
        original = kwargs["importer"]
        def importer(name):
            module = original(name)
            if name == "h5py":
                module.version.hdf5_version = "1.14.6"
            return module
        kwargs["importer"] = importer
        with self.assertRaisesRegex(collector.Refusal, "HDF5 runtime/build"):
            collector.collect("/fake", {"test":32001}, **kwargs)

    def test_source_imports_are_stdlib_and_forbidden_science_entrypoints_absent(self):
        tree = ast.parse(SOURCE.read_text())
        native = set(collector.COHORT)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse({a.name.split(".")[0] for a in node.names} & native)
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or "").split(".")[0], native)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, {"File", "Dataset", "create_dataset", "random", "default_rng", "seed"})


if __name__ == "__main__":
    unittest.main()
