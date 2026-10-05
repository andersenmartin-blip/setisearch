"""Independent targeted checks of reported fixes; all IO bindings synthetic."""
import base64
import hashlib
import io
import json
from pathlib import Path
import proxy_opener as p
import native_bindings as n
from wheel_io import WheelIOError

class Budget:
    def __init__(self): self.received = 0
    def check(self): pass
    def debit_read(self, size): pass
    def debit_network(self, size): pass
    def record_received(self, size, kind): self.received += size

class Socket:
    def __init__(self, raw=b"", expire=None):
        self.raw, self.expire = io.BytesIO(raw), expire
        self.closed = False
    def settimeout(self, timeout): pass
    def send(self, view): return len(view)
    def recv(self, size):
        raw = self.raw.read(size)
        if self.expire: self.expire()
        return raw
    def close(self): self.closed = True

raw = Path(__file__).with_name("original-plan.json").read_bytes()
url = json.loads(raw)["materialization"]["official_wheels"][0]["url"]
prefix = b"HTTP/1.1 407 Refused\r\nX-Reason: original\r\n\r\n"
sock = Socket(prefix)
def connect(host, port, *, register, timeout, refresh_timeout): return register(sock)
def unreachable(*args, **kwargs): raise AssertionError("must not reach TLS/HTTP")
trust = b"test"
opener = p.make_opener(raw, "http://127.0.0.1:12345", {
    "path": "/prospective/trust.crt", "bytes": len(trust),
    "sha256": hashlib.sha256(trust).hexdigest()},
    trust_read=lambda path, maximum: trust, connect=connect,
    tls_wrap=unreachable, http_binding=unreachable, budget=Budget(),
    deadline_callback=lambda: 10)
try: opener(url, timeout=5)
except WheelIOError: pass
before = json.dumps(opener.receipt, sort_keys=True)
try: opener(url, timeout=5)
except WheelIOError as exc:
    assert exc.receipt["refusal_kind"] == "SEPARATE_SPENT_OR_REENTRANT_CALL"
else: raise AssertionError("repeat accepted")
assert before == json.dumps(opener.receipt, sort_keys=True)
assert base64.b64decode(opener.receipt["received_connect_prefix_base64"]) == prefix
print("PASS: second-use refusal preserves primary receipt/prefix")

expired = False
def expire():
    global expired
    expired = True
budget, receipt = Budget(), {}
resources = p._Resources(receipt)
sock = resources.register(Socket(b"abc", expire))
clock = p._Clock(budget, lambda: 0 if expired else 10, 5)
response = resources.register(p._RawResponse(p._Stream(sock, clock, budget), "synthetic"))
handle = p._Handle(response, resources, receipt, budget)
try: handle.read(3)
except WheelIOError as exc:
    assert base64.b64decode(exc.receipt["refused_body_receive_base64"]) == b"abc"
    assert exc.receipt["refused_body_receive_bytes"] == budget.received == 3
    assert sock.closed
else: raise AssertionError("late read accepted")
print("PASS: late body bytes retained and actual-counter recorded once")

class ResponseWithoutStream:
    closed = False
    def read(self, maximum): raise OSError("original body failure")
    def close(self): self.closed = True
receipt, budget = {}, Budget()
resources = p._Resources(receipt)
response = resources.register(ResponseWithoutStream())
handle = p._Handle(response, resources, receipt, budget)
try: handle.read(3)
except WheelIOError as exc:
    assert exc.receipt["failure_type"] == "OSError"
    assert response.closed
else: raise AssertionError("failed response accepted")
print("PASS: custom response without stream preserves primary error and closes")

class Never:
    def __getattr__(self, name): raise AssertionError("builder accessed module: " + name)
connect_binding, tls_binding = n.build_native_bindings(socket_module=Never(), ssl_module=Never())
assert callable(connect_binding) and callable(tls_binding)
print("PASS: native builder construction touches no module attributes or IO")

for broken_property in (False, True):
    class ResponseBrokenOptionalEvidence:
        closed = False
        @property
        def pending_body(self):
            if broken_property:
                raise RuntimeError("optional property failed")
            return "optional raw wrong type"
        def read(self, maximum): raise OSError("primary body failure")
        def close(self): self.closed = True
    receipt, budget = {}, Budget()
    resources = p._Resources(receipt)
    response = resources.register(ResponseBrokenOptionalEvidence())
    handle = p._Handle(response, resources, receipt, budget)
    try: handle.read(3)
    except WheelIOError as exc:
        assert exc.receipt["failure_type"] == "OSError"
        assert response.closed
        assert exc.receipt["optional_evidence_failures"][0]["type"] == (
            "RuntimeError" if broken_property else "TypeError")
    else: raise AssertionError("failed response accepted")
print("PASS: wrong-type and raising optional pending_body preserve primary error/cleanup")
