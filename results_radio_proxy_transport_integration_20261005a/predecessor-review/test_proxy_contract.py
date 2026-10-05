import io
import unittest
from pathlib import Path
from unittest.mock import patch
import proxy_contract as p


class Tests(unittest.TestCase):
    def parse(self, raw, budget=None, clock=None):
        stream = io.BytesIO(raw)
        return p.parse_connect(stream.readline, budget or (lambda n: None), clock or (lambda: None))

    def test_canonical_loopback(self):
        self.assertEqual(p.endpoint("http://127.0.0.1:12345")["port"], 12345)

    def test_proxy_rejects_credentials_aliases_unicode_and_paths(self):
        for value in ["http://u:p@127.0.0.1:12345", "http://localhost:12345", "http://[::1]:12345",
                      "http://127.0.0.1:01234", "http://127.0.0.1:65536", "http://127.0.0.1:1023",
                      "http://127.0.0.1:12345/", "http://127.0.0.1:12345?x", "http://127.0.0.1:１２３４５",
                      "socks5h://127.0.0.1:12345", "https://127.0.0.1:12345", None]:
            with self.subTest(value=value), self.assertRaises(p.Refusal): p.endpoint(value)

    def test_original_plan_cannot_change(self):
        with self.assertRaises(p.Refusal): p.prepare(b"{}", "http://127.0.0.1:12345", {})

    def test_actual_pinned_plan_inert_construction(self):
        raw = Path(__file__).with_name("original-plan.json").read_bytes()
        trust = {"path": "/prospective/trust.crt", "bytes": 1310, "sha256": "a" * 64}
        with patch("socket.socket", side_effect=AssertionError("no socket")), patch("os.getenv", side_effect=AssertionError("no ambient environment")):
            result = p.prepare(raw, "http://127.0.0.1:12345", trust)
        self.assertEqual(result["original_plan_sha256"], p.ORIGINAL_PLAN_SHA256)
        self.assertIsNone(result["activation"])
        self.assertIsNone(result["allocation"])
        self.assertFalse(result["old_bootstrap_reuse_authorized"])
        self.assertFalse(result["trust_bytes_observed"])
        trust["path"] = "/changed.crt"
        self.assertEqual(result["trust_binding"]["path"], "/prospective/trust.crt")

    def test_trust_descriptor_refuses_unsafe_paths_boolean_and_overflow(self):
        raw = Path(__file__).with_name("original-plan.json").read_bytes()
        for value in [{"path": "/x/../trust.crt", "bytes": 1, "sha256": "a" * 64},
                      {"path": "/trust\n.crt", "bytes": 1, "sha256": "a" * 64},
                      {"path": "/trust.crt", "bytes": True, "sha256": "a" * 64},
                      {"path": "/trust.crt", "bytes": 1048577, "sha256": "a" * 64},
                      {"path": "/trust.crt", "bytes": 1, "sha256": "bad"}]:
            with self.subTest(value=value), self.assertRaises(p.Refusal):
                p.prepare(raw, "http://127.0.0.1:12345", value)

    def test_expired_clock_prevents_budget_and_receive(self):
        calls = []
        def clock(): raise TimeoutError("synthetic expired clock")
        with self.assertRaises(p.Refusal):
            p.parse_connect(lambda n: calls.append("read"), lambda n: calls.append("debit"), clock)
        self.assertEqual(calls, [])

    def test_success_only_parses_transcript(self):
        raw = b"HTTP/1.1 200 Connection established\r\nX-Proxy: synthetic\r\n\r\n"
        with patch("socket.socket", side_effect=AssertionError("no sockets")):
            result = self.parse(raw)
        self.assertEqual(result["raw"], raw)
        self.assertFalse(result["service_qualified"])
        self.assertFalse(result["tls_qualified"])

    def test_non200_preserves_complete_received_header_without_fallback(self):
        for code in [b"301", b"407", b"500"]:
            raw = b"HTTP/1.1 " + code + b" Refused\r\nX-Error: synthetic\r\n\r\n"
            with self.assertRaises(p.Refusal) as caught: self.parse(raw)
            self.assertEqual(caught.exception.raw, raw)

    def test_line_overflow_retains_plus_one(self):
        raw = b"a" * (p.LINE_BYTES + 2)
        with self.assertRaises(p.Refusal) as caught: self.parse(raw)
        self.assertEqual(len(caught.exception.raw), p.LINE_BYTES + 1)

    def test_total_header_overflow_retains_plus_one(self):
        raw = b"HTTP/1.1 200 OK\r\n" + (b"X: " + b"a" * 3990 + b"\r\n") * 6
        with self.assertRaises(p.Refusal) as caught: self.parse(raw)
        self.assertEqual(len(caught.exception.raw), p.HEADER_BYTES + 1)

    def test_header_count_limit(self):
        with self.assertRaises(p.Refusal): self.parse(b"HTTP/1.1 200 OK\r\n" + b"X: a\r\n" * 65 + b"\r\n")

    def test_truncation_lf_control_folding_invalid_name(self):
        for raw in [b"HTTP/1.1 200 OK\n", b"HTTP/1.1 200 OK\r\nX: a\x00b\r\n",
                    b"HTTP/1.1 200 OK\r\n X: a\r\n\r\n", b"HTTP/1.1 200 OK\r\nX Y: a\r\n\r\n",
                    b"HTTP/1.1 200 OK\r\n"]:
            with self.subTest(raw=raw), self.assertRaises(p.Refusal): self.parse(raw)

    def test_body_framing_is_refused(self):
        for header in [b"Content-Length: 0", b"Transfer-Encoding: chunked"]:
            with self.assertRaises(p.Refusal): self.parse(b"HTTP/1.1 200 OK\r\n" + header + b"\r\n\r\n")

    def test_budget_refusal_precedes_read(self):
        reads = []
        def debit(n): raise RuntimeError("spent")
        with self.assertRaises(p.Refusal) as caught:
            p.parse_connect(lambda n: reads.append(n), debit, lambda: None)
        self.assertEqual(reads, [])
        self.assertEqual(caught.exception.raw, b"")

    def test_receive_failure_no_retry_retains_previous_bytes(self):
        calls = []
        def read(n):
            calls.append(n)
            if len(calls) == 1: return b"HTTP/1.1 200 OK\r\n"
            raise OSError("synthetic receive failure")
        with self.assertRaises(p.Refusal) as caught: p.parse_connect(read, lambda n: None, lambda: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual(caught.exception.raw, b"HTTP/1.1 200 OK\r\n")

    def test_every_receive_precharged_and_clock_checked(self):
        events = []
        stream = io.BytesIO(b"HTTP/1.1 200 OK\r\n\r\n")
        p.parse_connect(lambda n: (events.append("read"), stream.readline(n))[1],
                        lambda n: events.append(("debit", n)), lambda: events.append("clock"))
        self.assertEqual([events[i] for i in (0, 2, 3, 5)], ["clock", "read", "clock", "read"])
        self.assertTrue(all(events[i][0] == "debit" for i in (1, 4)))


if __name__ == "__main__": unittest.main()
