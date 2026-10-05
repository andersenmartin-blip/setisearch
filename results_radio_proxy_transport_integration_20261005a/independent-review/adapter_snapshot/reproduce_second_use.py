"""Synthetic reproduction of repeated-call mutation; no network bindings."""
import base64
import hashlib
import io
import json
from pathlib import Path
import proxy_opener as p
from wheel_io import WheelIOError

class Budget:
    def check(self): pass
    def debit_read(self, n): pass
    def debit_network(self, n): pass
    def record_received(self, n, kind): pass

class FakeSocket:
    def __init__(self):
        self.raw = io.BytesIO(b"HTTP/1.1 407 Refused\r\nX-Reason: original\r\n\r\n")
        self.close_count = 0
    def settimeout(self, n): pass
    def send(self, view): return len(view)
    def recv(self, n): return self.raw.read(n)
    def close(self): self.close_count += 1

raw = Path(__file__).with_name("original-plan.json").read_bytes()
url = json.loads(raw)["materialization"]["official_wheels"][0]["url"]
sock = FakeSocket()
def connect(host, port, *, register, timeout): return register(sock)
def unreachable(*args, **kwargs): raise AssertionError("must not reach TLS/HTTP")
trust = b"test"
opener = p.make_opener(raw, "http://127.0.0.1:12345", {
    "path": "/prospective/trust.crt", "bytes": len(trust),
    "sha256": hashlib.sha256(trust).hexdigest()},
    trust_read=lambda path, maximum: trust, connect=connect,
    tls_wrap=unreachable, http_binding=unreachable, budget=Budget(),
    deadline_callback=lambda: 10)

for call in (1, 2):
    try: opener(url, timeout=5)
    except WheelIOError as exc:
        print("call", call, "prefix:", base64.b64decode(exc.receipt["received_connect_prefix_base64"]),
              "failure:", exc.receipt["failure"], "close_count:", sock.close_count)
