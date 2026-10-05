import base64
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from build_fixture import build
import proxy_contract
import proxy_opener as adapter
import wheel_io

ROOT = Path(__file__).parent
ORIGINAL = (ROOT / "original-plan.json").read_bytes()
BODY, SPEC, FIXTURE = build()
TRUST = b"synthetic trust bytes; not a certificate\n"
TRUST_BINDING = {"path": "/synthetic/trust.pem", "bytes": len(TRUST),
                 "sha256": hashlib.sha256(TRUST).hexdigest()}
SUCCESS_CONNECT = b"HTTP/1.1 200 Connection established\r\n\r\n"


class Budget:
    def __init__(self):
        self.network, self.reads, self.received, self.writes = [], [], [], []
        self.refuse = False
    def check(self):
        if self.refuse:
            raise RuntimeError("budget exhausted")
    def debit_network(self, count):
        self.check()
        self.network.append(count)
    def debit_read(self, count):
        self.check()
        self.reads.append(count)
    def record_received(self, count, *, kind):
        self.received.append((kind, count))
    def before_write(self, count):
        self.writes.append(count)
    def after_write(self): pass
    def check_directory(self, fd): pass


class Socket:
    def __init__(self, raw=b"", fragments=None):
        self.raw = bytearray(raw)
        self.fragments = list(fragments or [])
        self.timeouts, self.recv_requests, self.send_requests = [], [], []
        self.sent, self.close_count = bytearray(), 0
        self.fail_send = self.fail_recv = self.fail_close = False
        self.overreturn = False
        self.send_limit = None
        self.after_receive = None
    def settimeout(self, timeout):
        if not math.isfinite(timeout) or not timeout > 0:
            raise AssertionError("nonfinite timeout")
        self.timeouts.append(timeout)
    def send(self, view):
        self.send_requests.append(len(view))
        if self.fail_send:
            raise OSError("synthetic send failure")
        count = min(len(view), self.send_limit) if self.send_limit is not None else len(view)
        self.sent.extend(view[:max(0, count)])
        return count
    def recv(self, count):
        self.recv_requests.append(count)
        if self.fail_recv:
            raise OSError("synthetic receive failure")
        maximum = min(count, self.fragments.pop(0)) if self.fragments else count
        if self.overreturn:
            maximum = count + 1
        result = bytes(self.raw[:maximum])
        del self.raw[:maximum]
        if self.after_receive:
            self.after_receive(result)
        return result
    def close(self):
        self.close_count += 1
        if self.fail_close:
            raise OSError("synthetic close failure")


class Harness:
    def __init__(self, connect_raw=SUCCESS_CONNECT, body=BODY, headers=None, status="200 OK"):
        self.raw = Socket(connect_raw)
        self.tls = Socket(("HTTP/1.1 " + status + "\r\n" +
                           (headers if headers is not None else "Content-Length: " + str(len(body)) + "\r\n") +
                           "\r\n").encode() + body, fragments=[1, 2, 3, 5, 7, 11])
        self.budget = Budget()
        self.remaining = 5.0
        self.clock_calls = 0
        self.connect_calls, self.tls_calls = [], []
        self.trust_calls = []
        self.trust_raw = TRUST
        self.connect_failure = self.tls_failure = self.http_failure = False
        self.open = self.make()
    def deadline(self):
        self.clock_calls += 1
        return self.remaining
    def trust_read(self, path, maximum):
        self.trust_calls.append((path, maximum))
        return self.trust_raw
    def connect(self, host, port, *, timeout, register):
        self.connect_calls.append((host, port, timeout))
        register(self.raw)
        if self.connect_failure:
            raise OSError("synthetic connect failure after registration")
        return self.raw
    def tls_wrap(self, raw, *, configuration, timeout, register):
        self.tls_calls.append((raw, configuration, timeout))
        register(self.tls)
        if self.tls_failure:
            raise OSError("synthetic TLS verification failure")
        return self.tls
    def http(self, stream, **kwargs):
        if self.http_failure:
            response = kwargs["register"](adapter._RawResponse(stream, kwargs["url"]))
            raise OSError("synthetic HTTP failure after response registration")
        return adapter.bounded_http_binding(stream, **kwargs)
    def make(self, original=False):
        bindings = dict(trust_read=self.trust_read, connect=self.connect, tls_wrap=self.tls_wrap,
                        http_binding=self.http, budget=self.budget, deadline_callback=self.deadline)
        if original:
            return adapter.make_opener(ORIGINAL, "http://127.0.0.1:8080", TRUST_BINDING, **bindings)
        return adapter.make_simulation_opener(FIXTURE, ORIGINAL, "http://127.0.0.1:8080",
                                              TRUST_BINDING, **bindings)
    def acquire(self, spec=SPEC):
        with tempfile.TemporaryDirectory() as directory:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                result = wheel_io.acquire_wheel(spec, fd, self.budget, self.deadline, opener=self.open)
                payload = Path(directory, spec["filename"]).read_bytes()
                return result, payload
            finally:
                os.close(fd)


class AdapterTests(unittest.TestCase):
    def refusal(self, harness, url=SPEC["url"], timeout=5):
        with self.assertRaises(wheel_io.WheelIOError) as caught:
            harness.open(url, timeout=timeout)
        return caught.exception.receipt

    def test_deterministic_fixture_does_not_replace_original(self):
        self.assertEqual(build(), (BODY, SPEC, FIXTURE))
        self.assertEqual(hashlib.sha256(ORIGINAL).hexdigest(), proxy_contract.ORIGINAL_PLAN_SHA256)
        original = json.loads(ORIGINAL)["materialization"]["official_wheels"]
        self.assertEqual(len(original), 3)
        self.assertNotIn(SPEC["url"], {row["url"] for row in original})

    def test_exact_fixture_body_hash_static_preflight_and_plus_one_charge(self):
        h = Harness()
        with tempfile.TemporaryDirectory() as directory:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                receipt = wheel_io.acquire_wheel(SPEC, fd, h.budget, h.deadline, opener=h.open)
                held = os.open(SPEC["filename"], os.O_RDONLY, dir_fd=fd)
                try:
                    static = wheel_io.inspect_wheel(held, SPEC, h.budget, h.deadline)
                finally:
                    os.close(held)
                self.assertEqual(receipt["status"], "ACQUIRED_HASH_MATCH")
                self.assertEqual(static["status"], "STATIC_WHEEL_PREFLIGHT_VERIFIED")
                self.assertEqual(Path(directory, SPEC["filename"]).read_bytes(), BODY)
                self.assertEqual(receipt["charged_body_reads"], len(BODY) + 2)
                self.assertEqual(receipt["file_identity"]["mode"], 0o600)
                self.assertEqual(receipt["file_identity"]["nlink"], 1)
            finally:
                os.close(fd)
        self.assertEqual(h.raw.close_count, 1)
        self.assertEqual(h.tls.close_count, 1)
        self.assertEqual(h.open.receipt["evidence_domain"], "SIMULATION_ONLY")
        self.assertFalse(h.open.receipt["tls_resource_custody_qualified"])

    def test_original_plan_allowlist_rejects_synthetic_url_before_trust(self):
        h = Harness()
        h.open = h.make(original=True)
        self.refusal(h)
        self.assertEqual(h.trust_calls, [])
        self.assertEqual(h.connect_calls, [])

    def test_original_plan_url_only_can_reach_injected_bindings(self):
        h = Harness()
        h.open = h.make(original=True)
        url = json.loads(ORIGINAL)["materialization"]["official_wheels"][0]["url"]
        response = h.open(url, timeout=5)
        self.assertEqual(response.geturl(), url)
        response.close()
        self.assertEqual(h.connect_calls[0][:2], ("127.0.0.1", 8080))

    def test_changed_original_plan_refused_before_io(self):
        h = Harness()
        with self.assertRaises(proxy_contract.Refusal):
            adapter.make_opener(ORIGINAL + b" ", "http://127.0.0.1:8080", TRUST_BINDING,
                                trust_read=h.trust_read, connect=h.connect, tls_wrap=h.tls_wrap,
                                http_binding=h.http, budget=h.budget, deadline_callback=h.deadline)
        self.assertEqual(h.connect_calls, [])

    def test_noncanonical_proxy_refused(self):
        for proxy in ("http://localhost:8080", "http://127.0.0.1:08080", "http://127.0.0.1:8080/",
                      "https://127.0.0.1:8080", "http://user@127.0.0.1:8080"):
            with self.subTest(proxy=proxy), self.assertRaises(proxy_contract.Refusal):
                adapter.make_opener(ORIGINAL, proxy, TRUST_BINDING)

    def test_url_substitution_refused_before_io(self):
        for url in (SPEC["url"] + "?a=1", SPEC["url"].replace("https:", "http:"),
                    SPEC["url"].replace("files.pythonhosted.org", "evil.example")):
            h = Harness()
            self.refusal(h, url)
            self.assertEqual(h.connect_calls, [])
            self.assertEqual(h.trust_calls, [])

    def test_trust_mismatch_or_oversize_before_connect(self):
        for trust in (TRUST[:-1], TRUST + b"x", b"x" * len(TRUST), "not bytes"):
            h = Harness()
            h.trust_raw = trust
            self.refusal(h)
            self.assertEqual(h.connect_calls, [])
            self.assertEqual(h.budget.reads, [len(TRUST) + 1])

    def test_required_bindings_no_default(self):
        h = Harness()
        with self.assertRaises(TypeError):
            adapter.make_opener(ORIGINAL, "http://127.0.0.1:8080", TRUST_BINDING)
        with self.assertRaises(wheel_io.WheelIOError):
            adapter.make_opener(ORIGINAL, "http://127.0.0.1:8080", TRUST_BINDING,
                                trust_read=h.trust_read, connect=None, tls_wrap=h.tls_wrap,
                                http_binding=h.http, budget=h.budget, deadline_callback=h.deadline)

    def test_bad_deadline_and_timeout_zero_io(self):
        for value in (0, -1, float("nan"), float("inf"), True, None, "5"):
            for kind in ("deadline", "timeout"):
                h = Harness()
                if kind == "deadline":
                    h.remaining = value
                self.refusal(h, timeout=value if kind == "timeout" else 5)
                self.assertEqual(h.trust_calls, [])
                self.assertEqual(h.connect_calls, [])

    def test_budget_refusal_zero_io(self):
        h = Harness()
        h.budget.refuse = True
        self.refusal(h)
        self.assertEqual(h.connect_calls, [])

    def test_fragmented_connect_no_tunnel_read_ahead(self):
        sentinel = b"unread tunnel sentinel"
        h = Harness(connect_raw=SUCCESS_CONNECT + sentinel)
        response = h.open(SPEC["url"], timeout=5)
        self.assertEqual(bytes(h.raw.raw), sentinel)
        self.assertTrue(all(n == 1 for n in h.raw.recv_requests))
        self.assertEqual(base64.b64decode(h.open.receipt["received_connect_prefix_base64"]), SUCCESS_CONNECT)
        response.close()

    def test_timeout_refreshed_each_syscall(self):
        h = Harness()
        h.remaining = 2.5
        def advance(raw):
            h.remaining -= 0.001
        h.raw.after_receive = advance
        response = h.open(SPEC["url"], timeout=4)
        self.assertEqual(len(h.raw.timeouts), len(h.raw.send_requests) + len(h.raw.recv_requests))
        self.assertGreater(h.raw.timeouts[1], h.raw.timeouts[-1])
        self.assertTrue(all(0 < t <= 2.5 for t in h.tls.timeouts))
        response.close()

    def test_connect_last_receive_deadline_preserves_full_raw(self):
        h = Harness()
        h.raw.after_receive = lambda raw: setattr(h, "remaining", 0) if not h.raw.raw else None
        receipt = self.refusal(h)
        self.assertEqual(base64.b64decode(receipt["received_connect_prefix_base64"]), SUCCESS_CONNECT)
        self.assertEqual(h.tls_calls, [])
        self.assertEqual(h.raw.close_count, 1)

    def test_connect_truncation_preserves_partial_line(self):
        h = Harness(connect_raw=b"HTTP/1.1 200 OK\r\nX-Part: incom")
        receipt = self.refusal(h)
        self.assertEqual(base64.b64decode(receipt["received_connect_prefix_base64"]), b"HTTP/1.1 200 OK\r\nX-Part: incom")
        self.assertEqual(h.tls_calls, [])

    def test_connect_failure_status_framing_and_missing_reason_space(self):
        for raw in (b"HTTP/1.1 407 Authentication\r\n\r\n", b"HTTP/1.1 301 Redirect\r\n\r\n",
                    b"HTTP/1.1 100 Continue\r\n\r\n", b"HTTP/1.1 200\r\n\r\n",
                    b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n",
                    b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"):
            h = Harness(connect_raw=raw)
            receipt = self.refusal(h)
            self.assertEqual(base64.b64decode(receipt["received_connect_prefix_base64"]), raw)
            self.assertEqual(h.tls_calls, [])
            self.assertEqual(h.raw.close_count, 1)

    def test_connect_oversize_and_count_limits(self):
        cases = [b"HTTP/1.1 200 OK\r\nX: " + b"a" * 5000 + b"\r\n\r\n",
                 b"HTTP/1.1 200 OK\r\n" + b"X: a\r\n" * 65 + b"\r\n",
                 b"HTTP/1.1 200 OK\r\n" + (b"X: " + b"a" * 3990 + b"\r\n") * 5 + b"\r\n"]
        for raw in cases:
            h = Harness(connect_raw=raw)
            receipt = self.refusal(h)
            self.assertLessEqual(receipt["received_connect_prefix_bytes"], 16385)
            self.assertEqual(h.tls_calls, [])

    def test_connect_overreturn_retained_and_closed(self):
        h = Harness()
        h.raw.overreturn = True
        receipt = self.refusal(h)
        self.assertEqual(base64.b64decode(receipt["received_connect_prefix_base64"]), SUCCESS_CONNECT[:2])
        self.assertEqual(h.raw.close_count, 1)

    def test_connect_send_fragmentation_and_zero_progress(self):
        h = Harness()
        h.raw.send_limit = 3
        response = h.open(SPEC["url"], timeout=5)
        self.assertEqual(bytes(h.raw.sent), adapter.CONNECT)
        response.close()
        h = Harness()
        h.raw.send_limit = 0
        self.refusal(h)
        self.assertEqual(h.raw.recv_requests, [])
        self.assertEqual(h.raw.close_count, 1)

    def test_connect_send_overreport_refused(self):
        h = Harness()
        h.raw.send = lambda view: len(view) + 1
        self.refusal(h)
        self.assertEqual(h.raw.close_count, 1)

    def test_connect_send_and_recv_exceptions_no_retry(self):
        for kind in ("send", "recv"):
            h = Harness()
            setattr(h.raw, "fail_" + kind, True)
            self.refusal(h)
            self.assertEqual(h.raw.close_count, 1)
            self.assertEqual(len(h.connect_calls), 1)

    def test_registered_partial_connect_tls_http_cleanup(self):
        for kind, count in (("connect", 1), ("tls", 2), ("http", 3)):
            h = Harness()
            setattr(h, kind + "_failure", True)
            receipt = self.refusal(h)
            self.assertEqual(receipt["cleanup_attempt_count"], count)
            self.assertEqual(h.raw.close_count, 1)
            self.assertEqual(h.tls.close_count, int(kind != "connect"))

    def test_unregistered_binding_result_closed_and_refused(self):
        h = Harness()
        h.connect = lambda host, port, **kwargs: h.raw
        h.open = h.make()
        self.refusal(h)
        self.assertEqual(h.raw.close_count, 1)

    def test_tls_exact_immutable_configuration_contract(self):
        h = Harness()
        response = h.open(SPEC["url"], timeout=5)
        configuration = h.tls_calls[0][1]
        self.assertEqual(configuration["server_hostname"], "files.pythonhosted.org")
        self.assertIs(configuration["check_hostname"], True)
        self.assertEqual(configuration["verify_mode"], "CERT_REQUIRED")
        self.assertEqual(configuration["trust_bytes"], TRUST)
        self.assertIs(configuration["default_trust"], False)
        with self.assertRaises(TypeError):
            configuration["check_hostname"] = False
        response.close()

    def test_http_truncation_raw_prefix_and_cleanup(self):
        h = Harness()
        raw = b"HTTP/1.1 200 OK\r\nContent-Length: "
        h.tls.raw = bytearray(raw)
        receipt = self.refusal(h)
        self.assertEqual(base64.b64decode(receipt["received_http_header_prefix_base64"]), raw)
        self.assertEqual(h.raw.close_count, 1)
        self.assertEqual(h.tls.close_count, 1)

    def test_http_header_deadline_retains_last_byte(self):
        h = Harness()
        raw = b"HTTP/1.1 200 OK\r\nX: partial"
        h.tls.raw = bytearray(raw)
        h.tls.after_receive = lambda chunk: setattr(h, "remaining", 0) if not h.tls.raw else None
        receipt = self.refusal(h)
        self.assertEqual(base64.b64decode(receipt["received_http_header_prefix_base64"]), raw)

    def test_body_exact_hash_mismatch_and_short_body_custody(self):
        for body in (BODY[:-1], bytes([BODY[0] ^ 1]) + BODY[1:]):
            h = Harness(body=body, headers="Content-Length: " + str(len(BODY)) + "\r\n")
            with tempfile.TemporaryDirectory() as directory:
                fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    with self.assertRaises(wheel_io.WheelIOError) as caught:
                        wheel_io.acquire_wheel(SPEC, fd, h.budget, h.deadline, opener=h.open)
                    self.assertEqual(caught.exception.receipt["status"], "CLOSED_FAILED")
                    self.assertEqual(Path(directory, SPEC["filename"]).read_bytes(), body)
                finally:
                    os.close(fd)
            self.assertEqual(h.raw.close_count, 1)
            self.assertEqual(h.tls.close_count, 1)

    def test_body_plus_one_preserved_without_further_receive(self):
        h = Harness(body=BODY + b"xy", headers="Content-Length: " + str(len(BODY)) + "\r\n")
        with tempfile.TemporaryDirectory() as directory:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(wheel_io.WheelIOError) as caught:
                    wheel_io.acquire_wheel(SPEC, fd, h.budget, h.deadline, opener=h.open)
                self.assertEqual(caught.exception.receipt["received_body_bytes"], len(BODY) + 1)
                self.assertEqual(Path(directory, SPEC["filename"]).read_bytes(), BODY + b"x")
                self.assertEqual(bytes(h.tls.raw), b"y")
            finally:
                os.close(fd)

    def test_body_deadline_crossing_has_separate_raw_failure_custody(self):
        h = Harness()
        response = h.open(SPEC["url"], timeout=5)
        h.tls.after_receive = lambda chunk: setattr(h, "remaining", 0)
        with self.assertRaises(wheel_io.WheelIOError) as caught:
            response.read(7)
        receipt = caught.exception.receipt
        self.assertEqual(base64.b64decode(receipt["refused_body_receive_base64"]), BODY[:7])
        self.assertEqual(h.tls.close_count, 1)
        response.close()
        self.assertEqual(h.tls.close_count, 1)

    def test_wheel_http_status_length_encoding_guards_inherited(self):
        cases = [dict(status="302 Found"), dict(headers="Content-Length: 1\r\n"),
                 dict(headers="Content-Length: " + str(len(BODY)) + "\r\nContent-Length: " + str(len(BODY)) + "\r\n"),
                 dict(headers="Content-Length: " + str(len(BODY)) + "\r\nTransfer-Encoding: chunked\r\n"),
                 dict(headers="Content-Length: " + str(len(BODY)) + "\r\nContent-Encoding: gzip\r\n")]
        for kwargs in cases:
            h = Harness(**kwargs)
            with self.assertRaises(wheel_io.WheelIOError):
                h.acquire()
            self.assertEqual(h.tls.close_count, 1)

    def test_cleanup_failure_changes_success_and_attempts_every_close(self):
        h = Harness()
        h.tls.fail_close = True
        h.raw.fail_close = True
        with self.assertRaises(wheel_io.WheelIOError) as caught:
            h.acquire()
        self.assertEqual(caught.exception.receipt["status"], "CLOSED_FAILED")
        self.assertEqual(h.raw.close_count, 1)
        self.assertEqual(h.tls.close_count, 1)
        self.assertEqual(len(h.open.receipt["cleanup_failures"]), 2)

    def test_second_use_refused_no_second_connect(self):
        h = Harness()
        response = h.open(SPEC["url"], timeout=5)
        response.close()
        self.refusal(h)
        self.assertEqual(len(h.connect_calls), 1)

    def test_no_network_or_environment_defaults_exercised(self):
        h = Harness()
        with mock.patch("socket.socket", side_effect=AssertionError("socket blocked")), \
             mock.patch("socket.getaddrinfo", side_effect=AssertionError("DNS blocked")), \
             mock.patch("ssl.create_default_context", side_effect=AssertionError("SSL defaults blocked")), \
             mock.patch("os.getenv", side_effect=AssertionError("environment blocked")), \
             mock.patch.object(wheel_io, "_open_https", side_effect=AssertionError("fallback blocked")):
            receipt, body = h.acquire()
        self.assertEqual(body, BODY)
        self.assertEqual(receipt["status"], "ACQUIRED_HASH_MATCH")

    def test_corrected_parser_post_deadline_and_reason_space(self):
        lines = iter([b"HTTP/1.1 200 OK\r\n", b"\r\n"])
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 4:
                raise RuntimeError("past deadline")
        with self.assertRaises(proxy_contract.Refusal) as caught:
            proxy_contract.parse_connect(lambda cap: next(lines), lambda cap: None, check)
        self.assertEqual(caught.exception.raw, b"HTTP/1.1 200 OK\r\n\r\n")
        lines = iter([b"HTTP/1.1 200\r\n", b"\r\n"])
        with self.assertRaises(proxy_contract.Refusal):
            proxy_contract.parse_connect(lambda cap: next(lines), lambda cap: None, lambda: None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
