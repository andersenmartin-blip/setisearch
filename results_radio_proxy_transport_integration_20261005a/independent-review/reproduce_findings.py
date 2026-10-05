"""Pure synthetic review reproductions; no sockets/environment/network used."""
import io
from pathlib import Path
import proxy_contract as p

calls = []
expired = False
stream = io.BytesIO(b"HTTP/1.1 200 OK\r\n\r\n")

def clock():
    calls.append("clock")
    if expired:
        raise TimeoutError("synthetic deadline exceeded")

def read(n):
    global expired
    line = stream.readline(n)
    calls.append("read")
    if line == b"\r\n":
        expired = True
    return line

result = p.parse_connect(read, lambda n: calls.append(("debit", n)), clock)
print("late final read accepted:", result["status"], "expired:", expired, "calls:", calls)

raw = Path(__file__).with_name("original-plan.json").read_bytes()
plan = p.prepare(raw, "http://127.0.0.1:12345", {"path": "/prospective/trust.crt", "bytes": 1310, "sha256": "a" * 64})
print("raw plan returned:", any(v is raw for v in plan.values()))
print("returned plan-bearing keys:", [k for k in plan if "plan" in k])

result = p.parse_connect(io.BytesIO(b"HTTP/1.1 200\r\n\r\n").readline, lambda n: None, lambda: None)
print("status line with missing required post-code SP accepted:", result["status"])
