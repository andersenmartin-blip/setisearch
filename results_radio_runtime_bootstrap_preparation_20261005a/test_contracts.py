"""Pure-data fixtures only: no gate, live process, native source or installer."""

import builtins
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("build_contracts.py")
SPEC = importlib.util.spec_from_file_location("pure_bootstrap_builder", MODULE_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def source_row(path, size=0, mode="0644"):
    return {"path": path, "bytes": size, "sha256": "1" * 64,
            "mode": "100755" if mode == "0755" else "100644", "filesystem_mode": mode,
            "git_blob": "2" * 40,
            "source_identity": {"st_dev": 1, "st_ino": 2, "st_mode": 0o100000 | int(mode, 8),
                                "st_size": size, "st_nlink": 1, "st_mtime_ns": 3, "st_ctime_ns": 4}}


def fixtures():
    wheels = []
    for name, version, size, sha in (("numpy", "2.3.5", 16606086, "3"),
                                    ("h5py", "3.16.0", 5405250, "4"),
                                    ("hdf5plugin", "7.1.0", 46397731, "5")):
        filename = name + "-" + version + "-cp312-cp312-manylinux_2_28_x86_64.whl"
        wheels.append({"name": name, "version": version, "bytes": size, "sha256": sha * 64,
                       "filename": filename, "url": "https://files.pythonhosted.org/packages/fixture/" + filename,
                       "tags": ["cp312-cp312-manylinux_2_28_x86_64"]})
    plan = {"authority": {"scientific_execution_authorized": False, "download_authorized": False},
            "remaining_authentic_receipt_requirements": {"all_eleven_fields_still_pending": list(BUILDER.PENDING_FIELDS)},
            "materialization": {"official_wheels": wheels,
                                "offline_hash_lock_utf8": "".join(row["name"] + "==" + row["version"] + " --hash=sha256:" + row["sha256"] + "\n" for row in wheels),
                                "wheel_file_bytes": 68409067,
                                "bootstrap_resources": {"wheel_bytes_only": 68409067}}}
    python = "/fixture/python3.12"
    runtime = [source_row(python, 0, "0755")] + [source_row("/fixture/runtime/" + str(i).zfill(4) + ".py") for i in range(764)]
    runtime[-1]["bytes"] = 53792770
    runtime[-1]["source_identity"]["st_size"] = 53792770
    runtime.sort(key=lambda row: row["path"])
    names = ["pip/__init__.py", "pip/__main__.py", "pip-26.2.1.dist-info/METADATA",
             "pip-26.2.1.dist-info/WHEEL", "pip-26.2.1.dist-info/RECORD"]
    names += ["pip/data/" + str(i).zfill(4) + ".txt" for i in range(474)]
    installer = []
    for name in sorted(names):
        row = source_row(BUILDER.SITE + "/" + name)
        row.update({"relative_path": name, "seed_relative_path": name})
        installer.append(row)
    installer[-1]["bytes"] = 5690699
    installer[-1]["source_identity"]["st_size"] = 5690699
    preread = {"schema": "radio-runtime-bootstrap-installer-preread-v1",
               "status": "PREPARED_STATIC_SOURCE_SNAPSHOT_ONLY", "scientific_authority": False,
               "new_live_reservation": False, "scientific_fields_pending": 11,
               "genuine_bootstrap_invocations": 0, "genuine_installer_invocations": 0,
               "genuine_capture_invocations": 0,
               "runtime_comparison": {"same_exact_765_cohort": True, "changed_rows": [], "added_paths": [], "removed_paths": []},
               "runtime_selected_files": runtime, "runtime_selected_file_count": 765,
               "runtime_selected_file_bytes": 53792770,
               "installer_source_files": installer, "installer_source_file_count": 479,
               "installer_source_raw_bytes": 5690699, "pip_source_root": BUILDER.SITE,
               "pip_version_static": "26.2.1", "pip_distribution": "pip-26.2.1.dist-info"}
    kwargs = {"bootstrap_identity": "b" * 64, "output_root": "/fixture/fresh-bootstrap-output",
              "output_root_identity": {"device": 1, "inode": 2, "mode": "0700"},
              "python_executable": python, "gate_path": "/fixture/bootstrap/bootstrap_gate.py",
              "attribution_basis_path": "/fixture/bootstrap/capture_basis.py",
              "wheel_io_path": "/fixture/bootstrap/wheel_io.py",
              "activation_path": "/fixture/repo/" + BUILDER.ACTIVATION_REPOSITORY_PATH}
    return plan, preread, kwargs


def invoke(plan, preread, kwargs, transform_source=None, transform_raw=None):
    plan_raw = BUILDER.canonical(plan)
    preread_raw = BUILDER.canonical(preread)
    plan_sha = BUILDER.digest(plan_raw)
    preread_sha = BUILDER.digest(preread_raw)
    source = [
        {"path": kwargs["gate_path"], "bytes": 5, "sha256": "6" * 64, "mode": "100644"},
        {"path": kwargs["attribution_basis_path"], "bytes": 6, "sha256": BUILDER.BASIS_SHA256, "mode": "0644"},
        {"path": kwargs["wheel_io_path"], "bytes": 7, "sha256": "8" * 64, "mode": "0644"},
        {"path": BUILDER.PLAN_PATH, "bytes": len(plan_raw), "sha256": plan_sha, "mode": "0644"},
        {"path": BUILDER.PREREAD_PATH, "bytes": len(preread_raw), "sha256": preread_sha, "mode": "0644"},
    ]
    if transform_source:
        transform_source(source)
    if transform_raw:
        plan_raw, preread_raw = transform_raw(plan_raw, preread_raw)
    # Fixture-only substitution: production builder exposes no pin override.
    with patch.object(BUILDER, "PLAN_SHA256", plan_sha), patch.object(BUILDER, "PREREAD_SHA256", preread_sha):
        return BUILDER.build_contracts(plan_raw, preread_raw, source, **kwargs)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.preread, self.kwargs = fixtures()

    def reject(self, plan=None, preread=None, kwargs=None, **options):
        with self.assertRaises(BUILDER.PreparationError):
            invoke(self.plan if plan is None else plan, self.preread if preread is None else preread,
                   self.kwargs if kwargs is None else kwargs, **options)

    def test_valid_exact_schema_canonical_and_authority(self):
        result = invoke(self.plan, self.preread, self.kwargs)
        contract = result["contract"]
        self.assertEqual(set(contract), BUILDER.CONTRACT_KEYS)
        self.assertEqual(result["freeze_raw"], BUILDER.canonical(contract))
        self.assertEqual(result["freeze_sha256"], hashlib.sha256(result["freeze_raw"]).hexdigest())
        self.assertEqual(json.loads(result["freeze_raw"]), contract)
        self.assertEqual(contract["limits"], BUILDER.FINAL_LIMITS)
        self.assertEqual(len(contract["runtime_pins"]), 1244)
        self.assertEqual(len(contract["seed_pins"]), 479)
        self.assertEqual(sum(row["bytes"] for row in contract["runtime_pins"]), 59483469)
        self.assertTrue(all(row["mode"] in ("0644", "0755") for row in contract["source_pins"] + contract["runtime_pins"]))
        self.assertTrue(all(value is False for value in result["preparation"]["authority"].values()))
        self.assertEqual(result["preparation"]["scientific_fields_pending"], BUILDER.PENDING_FIELDS)

    def test_repeat_is_deterministic_and_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.plan, self.preread, self.kwargs))
        first = invoke(self.plan, self.preread, self.kwargs)
        second = invoke(self.plan, self.preread, self.kwargs)
        self.assertEqual(first, second)
        self.assertEqual((self.plan, self.preread, self.kwargs), before)

    def test_primary_build_has_no_io_or_gate_import(self):
        import os
        import subprocess
        import socket
        with patch.object(builtins, "open", side_effect=AssertionError("I/O forbidden")), \
             patch.object(os, "open", side_effect=AssertionError("I/O forbidden")), \
             patch.object(os, "stat", side_effect=AssertionError("I/O forbidden")), \
             patch.object(os, "scandir", side_effect=AssertionError("I/O forbidden")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")), \
             patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            result = invoke(self.plan, self.preread, self.kwargs)
        self.assertFalse(any(name.endswith("bootstrap_gate") for name in sys.modules))
        self.assertEqual(result["contract"]["evidence_domain"], "package-bootstrap-only")

    def test_changed_raw_plan_is_rejected_before_parse(self):
        self.reject(transform_raw=lambda plan, preread: (plan + b" ", preread))

    def test_changed_raw_preread_is_rejected_before_parse(self):
        self.reject(transform_raw=lambda plan, preread: (plan, preread + b" "))

    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(BUILDER.PreparationError):
                BUILDER.pinned_json(raw, BUILDER.digest(raw), 1024)

    def test_changed_plan_authority_or_pending_fields(self):
        self.plan["authority"]["scientific_execution_authorized"] = True
        self.reject()
        self.plan["authority"]["scientific_execution_authorized"] = False
        self.plan["remaining_authentic_receipt_requirements"]["all_eleven_fields_still_pending"].pop()
        self.reject()

    def test_changed_wheel_total_version_and_lock(self):
        for field, value in (("bytes", 1), ("version", "2.4.0")):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                plan["materialization"]["official_wheels"][0][field] = value
                self.reject(plan=plan)
        self.plan["materialization"]["offline_hash_lock_utf8"] += "--extra-index-url https://example.invalid\n"
        self.reject()

    def test_duplicate_wheel_or_nonofficial_url(self):
        self.plan["materialization"]["official_wheels"][1] = copy.deepcopy(self.plan["materialization"]["official_wheels"][0])
        self.reject()
        self.plan, _, _ = fixtures()
        self.plan["materialization"]["official_wheels"][0]["url"] = "https://example.invalid/a.whl"
        self.reject()

    def test_runtime_duplicate_path_or_drift(self):
        self.preread["runtime_selected_files"][1]["path"] = self.preread["runtime_selected_files"][0]["path"]
        self.reject()
        _, self.preread, _ = fixtures()
        self.preread["runtime_comparison"]["changed_rows"] = ["one"]
        self.reject()

    def test_seed_changed_mapping_or_byte_count(self):
        self.preread["installer_source_files"][0]["relative_path"] = "pip/other.py"
        self.reject()
        _, self.preread, _ = fixtures()
        self.preread["installer_source_files"][-1]["bytes"] += 1
        self.reject()

    def test_missing_pip_entry_point_or_distinfo(self):
        for original in ("pip/__main__.py", "pip-26.2.1.dist-info/METADATA"):
            with self.subTest(original=original):
                preread = copy.deepcopy(self.preread)
                row = next(row for row in preread["installer_source_files"] if row["relative_path"] == original)
                replacement = "pip/replacement.py"
                row.update(path=BUILDER.SITE + "/" + replacement, relative_path=replacement, seed_relative_path=replacement)
                preread["installer_source_files"].sort(key=lambda row: row["path"])
                self.reject(preread=preread)

    def test_foreign_distinfo_and_ambient_bytecode(self):
        for target in ("pip-99.dist-info/METADATA", "pip/__pycache__/foo.py", "pip/data/foo.pyc", "pip/data/foo.pyo"):
            with self.subTest(target=target):
                preread = copy.deepcopy(self.preread)
                row = preread["installer_source_files"][0]
                row.update(path=BUILDER.SITE + "/" + target, relative_path=target, seed_relative_path=target)
                preread["installer_source_files"].sort(key=lambda row: row["path"])
                self.reject(preread=preread)

    def test_noncanonical_and_duplicate_source_paths(self):
        self.reject(transform_source=lambda rows: rows.append(copy.deepcopy(rows[0])))
        self.reject(transform_source=lambda rows: rows[0].update(path="/fixture/bootstrap/../bootstrap_gate.py"))

    def test_source_runtime_overlap_and_output_overlap(self):
        runtime = self.preread["runtime_selected_files"][0]
        self.reject(transform_source=lambda rows: rows.append({key: runtime[key] for key in BUILDER.PIN_KEYS}))
        self.kwargs["output_root"] = "/fixture/runtime"
        self.reject()

    def test_missing_required_source_or_external_source_drift(self):
        self.reject(transform_source=lambda rows: rows.pop())
        self.reject(transform_source=lambda rows: rows[-1].update(sha256="f" * 64))
        self.reject(transform_source=lambda rows: rows[1].update(sha256="f" * 64))

    def test_bool_or_oversized_or_lower_cap(self):
        for value in (True, 301, 299):
            with self.subTest(value=value):
                kwargs = copy.deepcopy(self.kwargs)
                kwargs["limits"] = dict(BUILDER.FINAL_LIMITS, wall_seconds=value)
                self.reject(kwargs=kwargs)

    def test_root_identity_and_retired_identity(self):
        for change in ({"output_root_identity": {"device": True, "inode": 2, "mode": "0700"}},
                       {"output_root_identity": {"device": 1, "inode": 0, "mode": "0700"}},
                       {"bootstrap_identity": next(iter(BUILDER.RETIRED_IDENTITIES))},
                       {"bootstrap_identity": "0" * 64}):
            with self.subTest(change=change):
                self.reject(kwargs=dict(self.kwargs, **change))

    def test_source_identity_hardlink_mode_and_bool_bytes(self):
        for key, value in (("st_nlink", 2), ("st_mode", 0o120644), ("st_size", True)):
            with self.subTest(key=key):
                preread = copy.deepcopy(self.preread)
                preread["installer_source_files"][0]["source_identity"][key] = value
                self.reject(preread=preread)
        self.preread["installer_source_files"][0]["bytes"] = False
        self.reject()

    def test_static_authority_and_nonzero_invocation(self):
        self.preread["scientific_authority"] = True
        self.reject()
        self.preread["scientific_authority"] = False
        self.preread["genuine_installer_invocations"] = 1
        self.reject()

    def test_gate_pin_schema_and_fixed_activation(self):
        self.reject(transform_source=lambda rows: rows[0].update(repository_path="extra-field"))
        self.kwargs["activation_path"] = "/fixture/repo/config/old.activate.json"
        self.reject()

    def test_extra_representation_sources_are_admitted_separately(self):
        def extra(rows):
            rows.append({"path": "/fixture/repo/installer-basis/resource.base64", "bytes": 123,
                         "sha256": "c" * 64, "mode": "100644"})
        result = invoke(self.plan, self.preread, self.kwargs, transform_source=extra)
        self.assertEqual(result["preparation"]["source_files"], 6)
        self.assertEqual(len(result["contract"]["runtime_pins"]), 1244)


if __name__ == "__main__":
    unittest.main(verbosity=2)
