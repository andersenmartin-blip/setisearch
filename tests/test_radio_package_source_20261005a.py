"""Offline admission and bounded transport laws; no real network or wheels."""

import copy
from email.message import Message
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "radio_package_source", ROOT / "scripts/radio_package_source_20261005a.py")
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)


class Response:
    def __init__(self, data, url, length=None, status=200, fail_after=None):
        self.stream = io.BytesIO(data)
        self.url = url
        self.status = status
        self.fail_after = fail_after
        self.closed = False
        self.headers = Message()
        self.headers["Content-Length"] = str(len(data) if length is None else length)

    def read(self, amount):
        if self.fail_after is not None and self.stream.tell() >= self.fail_after:
            raise TimeoutError("PRIVATE TOKEN MUST NOT APPEAR IN RECEIPT")
        if self.fail_after is not None:
            amount = min(amount, self.fail_after - self.stream.tell())
        return self.stream.read(amount)

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


class Opener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, request.get_method(), timeout, dict(request.headers)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def synthetic_wheels():
    # Distinct inert byte strings, never unpacked or imported. hdf5plugin has
    # two parts under the deliberately tiny offline-test export limit.
    sizes = (7, 5, 19)
    return [dict(name=row["name"], version=row["version"], filename=row["filename"],
                 url=row["url"], bytes=size,
                 sha256=hashlib.sha256(bytes([index + 65]) * size).hexdigest())
            for index, (row, size) in enumerate(zip(SOURCE.WHEELS, sizes))]


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.output = Path(self.directory.name) / "output"
        self.wheels = synthetic_wheels()
        self.bodies = [bytes([index + 65]) * wheel["bytes"] for index, wheel in enumerate(self.wheels)]
        self.responses = [Response(body, wheel["url"]) for body, wheel in zip(self.bodies, self.wheels)]
        self.limits = dict(SOURCE.LIMITS, export_part_bytes=10, total_received_bytes=sum(map(len, self.bodies)))
        self.identity = {"run_id": "123", "run_attempt": 1, "identity": SOURCE.IDENTITY}

    def tearDown(self):
        self.directory.cleanup()

    def acquire(self, responses=None, **kwargs):
        opener = Opener(self.responses if responses is None else responses)
        result = SOURCE.acquire(self.output, self.wheels, self.identity,
                                {"scripts/example.py": b"inert source"}, opener=opener,
                                host_metadata={"observation_only": True}, limits=self.limits, **kwargs)
        return result, opener

    def test_success_exact_bytes_and_artifact_groups(self):
        result, opener = self.acquire()
        self.assertEqual(result["status"], "EXACT_THREE_ORIGINAL_ARCHIVES")
        self.assertEqual(result["received_bytes"], 31)
        self.assertEqual(len(opener.calls), 3)
        self.assertTrue(all(method == "GET" and 0 < timeout <= 30 for _, method, timeout, _ in opener.calls))
        groups = {part["artifact_group"] for part in result["artifacts"]}
        self.assertEqual(groups, {"numpy", "h5py", "hdf5plugin-part000", "hdf5plugin-part001"})
        for body, row in zip(self.bodies, result["requests"]):
            parts = [self.output / part["path"] for part in row["exports"]]
            self.assertEqual(b"".join(part.read_bytes() for part in parts), body)
            self.assertTrue(all(part.stat().st_size <= 10 for part in parts))
        self.assertFalse(result["runtime_qualified"])
        self.assertFalse(result["scientific_authority"])
        self.assertTrue((self.output / "exports/receipt/manifest.json").is_file())

    def test_spent_is_durable_before_first_request_and_second_use_refused(self):
        test = self
        class CheckingOpener(Opener):
            def open(self, request, timeout):
                test.assertTrue(json.loads((test.output / "spent.json").read_bytes())["spent"])
                return super().open(request, timeout)
        opener = CheckingOpener(self.responses)
        SOURCE.acquire(self.output, self.wheels, self.identity, {}, opener=opener,
                       limits=self.limits, host_metadata={})
        with self.assertRaisesRegex(SOURCE.Refusal, "existing_output_refused"):
            SOURCE.acquire(self.output, self.wheels, self.identity, {}, opener=opener,
                           limits=self.limits, host_metadata={})
        self.assertEqual(len(opener.calls), 3)

    def test_wrong_length_does_not_read_body_or_try_other_wheels(self):
        bad = Response(b"wrong", self.wheels[0]["url"], length=4)
        result, opener = self.acquire([bad])
        self.assertEqual(result["requests"][0]["error"], "content_length_mismatch")
        self.assertEqual(result["received_bytes"], 0)
        self.assertEqual(bad.stream.tell(), 0)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(len(result["skipped_wheels"]), 2)
        self.assertEqual(result["status"], "FAILED_CLOSED")

    def test_hash_failure_preserves_every_received_byte_once(self):
        bad = Response(b"Z" * 7, self.wheels[0]["url"])
        result, opener = self.acquire([bad])
        row = result["requests"][0]
        self.assertEqual(row["error"], "original_sha256_mismatch")
        self.assertEqual((self.output / row["raw_path"]).read_bytes(), b"Z" * 7)
        self.assertEqual((self.output / row["exports"][0]["path"]).read_bytes(), b"Z" * 7)
        self.assertEqual(len(opener.calls), 1)

    def test_overrun_byte_preserved_and_acquisition_closed(self):
        bad = Response(b"A" * 8, self.wheels[0]["url"], length=7)
        result, opener = self.acquire([bad])
        row = result["requests"][0]
        self.assertEqual(row["error"], "original_length_overrun")
        self.assertEqual(row["received_bytes"], 8)
        self.assertEqual((self.output / row["raw_path"]).read_bytes(), b"A" * 8)
        self.assertEqual(len(opener.calls), 1)

    def test_timeout_partial_retained_and_error_secret_not_logged(self):
        bad = Response(b"A" * 7, self.wheels[0]["url"], fail_after=3)
        result, opener = self.acquire([bad])
        row = result["requests"][0]
        self.assertEqual(row["received_bytes"], 3)
        self.assertEqual(row["error"], "transport_or_io_TimeoutError")
        self.assertEqual((self.output / row["exports"][0]["path"]).read_bytes(), b"AAA")
        self.assertNotIn("PRIVATE", (self.output / "manifest.json").read_text())
        self.assertEqual(len(opener.calls), 1)

    def test_non_200_or_changed_url_denied_without_archive_read(self):
        for url, status, error in ((self.wheels[0]["url"], 302, "non_200_response"),
                                   ("https://attacker.invalid/file", 200, "changed_response_url_refused")):
            self.output = Path(self.directory.name) / ("output" + str(status))
            response = Response(b"A" * 7, url, status=status)
            result, opener = self.acquire([response])
            self.assertEqual(result["requests"][0]["error"], error)
            self.assertEqual(response.stream.tell(), 0)
            self.assertEqual(len(opener.calls), 1)

    def test_http_error_recorded_once(self):
        bad = urllib.error.HTTPError(self.wheels[0]["url"], 503,
                                     "PRIVATE MESSAGE", {}, io.BytesIO(b"error"))
        result, opener = self.acquire([bad])
        self.assertEqual(result["requests"][0]["error"], "http_error_503")
        self.assertEqual(result["requests"][0]["http_status"], 503)
        self.assertEqual(len(opener.calls), 1)

    def test_no_redirect_handler_never_reissues_request(self):
        handler = SOURCE.NoRedirect()
        with self.assertRaisesRegex(SOURCE.Refusal, "redirect_refused"):
            handler.redirect_request(urllib.request.Request(self.wheels[0]["url"]),
                                     None, 302, "found", {}, self.wheels[1]["url"])

    def test_total_bound_stops_before_later_request(self):
        self.limits["total_received_bytes"] = 6
        result, opener = self.acquire([self.responses[0]])
        row = result["requests"][0]
        self.assertEqual(result["received_bytes"], 6)
        self.assertEqual(row["error"], "total_received_limit")
        self.assertEqual(len(opener.calls), 1)

    def test_deadline_before_request_still_has_spent_and_receipt(self):
        ticks = iter([0, 181, 181, 181])
        result, opener = self.acquire([], clock=lambda: next(ticks, 181))
        self.assertEqual(len(opener.calls), 0)
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertTrue((self.output / "spent.json").is_file())
        self.assertEqual(result["requests"][0]["error"], "download_deadline_before_request")

    def test_encoded_response_and_duplicate_length_denied(self):
        for index, mutator in enumerate((lambda h: h.add_header("Content-Encoding", "gzip"),
                                         lambda h: h.add_header("Content-Length", "7"))):
            self.output = Path(self.directory.name) / ("output%d" % index)
            response = Response(b"A" * 7, self.wheels[0]["url"])
            mutator(response.headers)
            result, opener = self.acquire([response])
            self.assertEqual(result["received_bytes"], 0)
            self.assertEqual(result["status"], "FAILED_CLOSED")
            self.assertEqual(len(opener.calls), 1)

    def test_complete_files_without_second_plugin_group_are_not_success(self):
        self.limits["export_part_bytes"] = 100
        result, _ = self.acquire()
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["finalization_error"], "complete_export_groups_required")

    def test_path_and_receipt_bound_refused_before_opener(self):
        with self.assertRaisesRegex(SOURCE.Refusal, "new_absolute_output_required"):
            SOURCE.acquire(Path("relative"), self.wheels, self.identity, {}, opener=Opener([]))
        with self.assertRaisesRegex(SOURCE.Refusal, "source_receipt_size_limit"):
            SOURCE.acquire(self.output, self.wheels, self.identity,
                           {"large": b"x" * (1024 * 1024 + 1)}, opener=Opener([]))
        self.assertFalse(self.output.exists())

    def test_preservation_deadline_keeps_raw_archives_and_refuses_success(self):
        current = [0]
        def close_network():
            current[0] = 61
        result, opener = self.acquire(clock=lambda: current[0], network_closed=close_network)
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(result["finalization_error"], "preservation_wall_deadline")
        self.assertEqual(len(opener.calls), 3)
        for row, body in zip(result["requests"], self.bodies):
            self.assertEqual((self.output / row["raw_path"]).read_bytes(), body)

    def test_later_manifest_write_failure_repairs_success_copy_to_failed(self):
        original_write = SOURCE.exclusive_write
        def fail_root_manifest(path, payload):
            if path == self.output / "manifest.json":
                raise OSError("INERT INJECTED DISK ERROR")
            return original_write(path, payload)
        with mock.patch.object(SOURCE, "exclusive_write", side_effect=fail_root_manifest):
            result, _ = self.acquire()
        self.assertEqual(result["status"], "FAILED_CLOSED")
        for path in (self.output / "manifest.json", self.output / "exports/receipt/manifest.json"):
            self.assertEqual(json.loads(path.read_bytes())["status"], "FAILED_CLOSED")

    def test_retained_original_hash_failure_still_exports_bound_raw_path(self):
        with mock.patch.object(SOURCE, "hash_file", side_effect=OSError("INERT HASH READ FAILURE")):
            result, opener = self.acquire([self.responses[0]])
        self.assertEqual(result["status"], "FAILED_CLOSED")
        self.assertEqual(len(opener.calls), 1)
        row = result["requests"][0]
        self.assertEqual(row["error"], "retained_original_validation_OSError")
        self.assertEqual((self.output / row["raw_path"]).read_bytes(), self.bodies[0])
        self.assertEqual((self.output / row["exports"][0]["path"]).read_bytes(), self.bodies[0])
        self.assertEqual(row["retained_bytes"], len(self.bodies[0]))
        self.assertIsNone(row["retained_sha256"])


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Offline Fixture")
        self.git("config", "user.email", "offline@example.invalid")
        self.sources = {}
        for relative in SOURCE.SOURCE_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / relative).read_bytes() if (ROOT / relative).is_file() else b"inert offline source\n"
            path.write_bytes(raw)
            self.sources[relative] = SOURCE.sha256(raw)
        self.freeze = {"schema": SOURCE.FREEZE_SCHEMA, "identity": SOURCE.IDENTITY,
                       "marker_path": SOURCE.MARKER_PATH, "sources": self.sources,
                       "original_plan_path": SOURCE.ORIGINAL_PATH,
                       "original_plan_sha256": SOURCE.ORIGINAL_SHA256,
                       "wheels": list(SOURCE.WHEELS), "limits": SOURCE.LIMITS}
        self.write(SOURCE.FREEZE_PATH, SOURCE.json_bytes(self.freeze))
        self.write(SOURCE.MARKER_PATH, b'{"active":false}\n')
        self.commit("prepared")
        self.prepared = self.git("rev-parse", "HEAD").decode().strip()
        self.tree = self.git("rev-parse", "HEAD^{tree}").decode().strip()
        self.marker = {"schema": SOURCE.MARKER_SCHEMA, "identity": SOURCE.IDENTITY,
                       "single_use": True, "package_only": True, "automatic_successor": False,
                       "prepared_commit": self.prepared, "prepared_tree": self.tree,
                       "freeze_sha256": SOURCE.sha256((self.root / SOURCE.FREEZE_PATH).read_bytes())}
        self.write(SOURCE.MARKER_PATH, SOURCE.json_bytes(self.marker))
        self.commit("activation marker only")
        self.env = {"GITHUB_RUN_ID": "123456789", "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_SHA": self.git("rev-parse", "HEAD").decode().strip(),
                    "GITHUB_REPOSITORY": SOURCE.REPOSITORY}

    def tearDown(self):
        self.directory.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-qm", message)

    def admit(self):
        def fixture_git(_root, *args):
            return self.git(*args)
        return SOURCE.admit(self.root / SOURCE.FREEZE_PATH, self.root / SOURCE.MARKER_PATH,
                            self.env, git_call=fixture_git)

    def test_exact_frozen_marker_only_child_admitted_offline(self):
        freeze, identity, snapshots = self.admit()
        self.assertEqual(freeze, self.freeze)
        self.assertEqual(identity["prepared_commit"], self.prepared)
        self.assertEqual(set(snapshots), SOURCE.SOURCE_PATHS | {SOURCE.FREEZE_PATH, SOURCE.MARKER_PATH})

    def test_run_attempt_repository_and_sha_denied(self):
        original = dict(self.env)
        for key, value, reason in (("GITHUB_RUN_ATTEMPT", "2", "rerun_refused"),
                                    ("GITHUB_REPOSITORY", "other/repo", "repository_mismatch"),
                                    ("GITHUB_SHA", "0" * 40, "checkout_head_mismatch")):
            self.env = dict(original, **{key: value})
            with self.assertRaisesRegex(SOURCE.Refusal, reason):
                self.admit()

    def test_source_worktree_changed_refused(self):
        self.write("scripts/radio_package_source_20261005a.py", b"tampered\n")
        with self.assertRaisesRegex(SOURCE.Refusal, "source_hash_mismatch"):
            self.admit()

    def test_extra_activation_change_refused(self):
        self.git("reset", "--soft", self.prepared)
        self.write("unexpected.txt", b"extra change")
        self.commit("marker plus unexpected change")
        self.env["GITHUB_SHA"] = self.git("rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(SOURCE.Refusal, "activation_must_change_marker_only"):
            self.admit()

    def test_marker_pin_and_safety_flags_denied(self):
        for key, value, reason in (("freeze_sha256", "0" * 64, "freeze_sha_mismatch"),
                                    ("package_only", False, "inactive_or_invalid_marker"),
                                    ("single_use", False, "inactive_or_invalid_marker"),
                                    ("automatic_successor", True, "inactive_or_invalid_marker")):
            marker = dict(self.marker, **{key: value})
            self.write(SOURCE.MARKER_PATH, SOURCE.json_bytes(marker))
            with self.assertRaisesRegex(SOURCE.Refusal, reason):
                self.admit()

    def test_parent_and_tree_mismatch_denied(self):
        marker = dict(self.marker, prepared_commit="0" * 40)
        self.write(SOURCE.MARKER_PATH, SOURCE.json_bytes(marker))
        with self.assertRaisesRegex(SOURCE.Refusal, "sole_prepared_parent_required"):
            self.admit()
        marker = dict(self.marker, prepared_tree="0" * 40)
        self.write(SOURCE.MARKER_PATH, SOURCE.json_bytes(marker))
        with self.assertRaisesRegex(SOURCE.Refusal, "prepared_tree_mismatch"):
            self.admit()

    def test_symlink_source_denied(self):
        path = self.root / "scripts/radio_package_source_20261005a.py"
        path.unlink()
        path.symlink_to(self.root / SOURCE.ORIGINAL_PATH)
        with self.assertRaisesRegex(SOURCE.Refusal, "symlink_source_refused"):
            self.admit()

    def test_cohort_and_limits_cannot_be_promoted_by_mutating_freeze(self):
        original = (self.root / SOURCE.ORIGINAL_PATH).read_bytes()
        for mutation, reason in ((lambda d: d["wheels"][0].update(bytes=1), "original_wheel_cohort_mismatch"),
                                 (lambda d: d["limits"].update(download_wall_seconds=181), "limits_mismatch"),
                                 (lambda d: d["sources"].update(extra="0" * 64), "exact_source_set_required")):
            freeze = copy.deepcopy(self.freeze)
            mutation(freeze)
            with self.assertRaisesRegex(SOURCE.Refusal, reason):
                SOURCE.validate_freeze(freeze, original)

    def test_original_plan_remains_exact_and_duplicates_refused(self):
        original = (self.root / SOURCE.ORIGINAL_PATH).read_bytes()
        with self.assertRaisesRegex(SOURCE.Refusal, "original_plan_bytes_mismatch"):
            SOURCE.validate_freeze(self.freeze, original + b"\n")
        with self.assertRaisesRegex(SOURCE.Refusal, "duplicate_json_key"):
            SOURCE.json_object(b'{"a":1,"a":2}')

    def test_url_allowlist_refuses_credentials_fallback_http_and_query(self):
        filename = SOURCE.WHEELS[0]["filename"]
        for url in ("http://files.pythonhosted.org/packages/x/" + filename,
                    "https://user:secret@files.pythonhosted.org/packages/x/" + filename,
                    "https://files.pythonhosted.org:443/packages/x/" + filename,
                    "https://files.pythonhosted.org.evil.invalid/packages/x/" + filename,
                    SOURCE.WHEELS[0]["url"] + "?token=secret"):
            with self.assertRaisesRegex(SOURCE.Refusal, "nonofficial_url_refused"):
                SOURCE.validate_url(url, filename)


if __name__ == "__main__":
    unittest.main()
