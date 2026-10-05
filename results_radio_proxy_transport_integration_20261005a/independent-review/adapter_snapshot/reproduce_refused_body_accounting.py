"""Synthetic post-receive timeout evidence/accounting; no network binding."""
import base64
import proxy_opener as p
from wheel_io import WheelIOError

expired = False
class Budget:
    received = 0
    def check(self): pass
    def record_received(self, n, kind): self.received += n

class FakeSocket:
    def settimeout(self, n): pass
    def recv(self, n):
        global expired
        expired = True
        return b"abc"
    def close(self): pass

budget = Budget()
receipt = {}
resources = p._Resources(receipt)
sock = resources.register(FakeSocket())
clock = p._Clock(budget, lambda: 0 if expired else 10, 5)
response = resources.register(p._RawResponse(p._Stream(sock, clock, budget), "synthetic"))
handle = p._Handle(response, resources, receipt)
try:
    handle.read(3)
except WheelIOError as exc:
    print("retained refused body:", base64.b64decode(exc.receipt["refused_body_receive_base64"]))
    print("observed bytes in receipt:", exc.receipt["refused_body_receive_bytes"])
    print("observed bytes recorded in budget:", budget.received)
