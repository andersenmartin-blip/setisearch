"""Budgeted radio transport. One Budget is shared across an acquisition session.

No redirects, retries, credentials, or fallback object identities. A failed
request consumes its reservation. Checkpoints retain the proven M43H format.
"""
from dataclasses import dataclass, field
import time
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import http_range_v0p6 as old
from .transport_m43h import BoundedMirror as PreviousMirror, MAX_REQUEST, TIMEOUT


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("radio object redirect refused")


def open_response(request, timeout):
    return build_opener(NoRedirect()).open(request, timeout=timeout)


@dataclass
class Budget:
    max_requests: int
    max_bytes: int
    max_seconds: float
    started: float = field(default_factory=time.monotonic, init=False)
    attempts: int = field(default=0, init=False)
    reserved_bytes: int = field(default=0, init=False)
    accepted_bytes: int = field(default=0, init=False)

    def __post_init__(self):
        if (type(self.max_requests) is not int or not 0 < self.max_requests <= 1000
                or type(self.max_bytes) is not int or not 0 < self.max_bytes <= 2**30
                or not 0 < self.max_seconds <= 3600):
            raise ValueError("invalid acquisition session budget")

    def remaining_seconds(self):
        remaining = self.max_seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise ValueError("acquisition session time budget exhausted")
        return remaining

    def reserve(self, size):
        self.remaining_seconds()
        if (type(size) is not int or size < 0
                or self.attempts >= self.max_requests
                or self.reserved_bytes + size > self.max_bytes):
            raise ValueError("acquisition session request/byte budget exhausted")
        self.attempts += 1
        self.reserved_bytes += size

    def record(self):
        return {"attempts": self.attempts, "reserved_bytes": self.reserved_bytes,
                "accepted_bytes": self.accepted_bytes,
                "elapsed_seconds": time.monotonic() - self.started,
                "limits": {"max_requests": self.max_requests,
                           "max_bytes": self.max_bytes, "max_seconds": self.max_seconds}}


def live_identity(url, budget):
    budget.reserve(0)
    request = Request(url, method="HEAD", headers={
        "User-Agent": "setisearch-radio-source/1.0", "Accept-Encoding": "identity"})
    with open_response(request, min(TIMEOUT, budget.remaining_seconds())) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("radio HEAD status or URL changed")
        headers = response.headers
        if ("bytes" not in headers.get("Accept-Ranges", "").lower()
                or headers.get("Content-Encoding", "identity") not in ("", "identity")):
            raise ValueError("radio source lacks identity byte ranges")
        identity = old.RemoteIdentity(url, int(headers["Content-Length"]), headers["ETag"])
    budget.remaining_seconds()
    return identity


class RadioMirror(PreviousMirror):
    def __init__(self, path, identity, budget):
        self.budget = budget
        super().__init__(path, identity)

    def _ensure(self, interval):
        # Exact on-demand reads; the old large read-ahead is unnecessary for
        # metadata and could fetch payload outside the published chunk plan.
        self.prefetch((interval,))

    def _request(self, interval):
        if interval.length > MAX_REQUEST:
            raise ValueError("radio request exceeds bound")
        # Reserve the extra byte used to reject an overlong response too.
        self.budget.reserve(interval.length + 1)
        request = Request(self.identity.url, headers={
            "User-Agent": "setisearch-radio-source/1.0",
            "Range": f"bytes={interval.start}-{interval.stop-1}",
            "If-Match": self.identity.etag, "Accept-Encoding": "identity"})
        with open_response(request, min(TIMEOUT, self.budget.remaining_seconds())) as response:
            expected_range = f"bytes {interval.start}-{interval.stop-1}/{self.identity.size}"
            if (response.status != 206 or response.geturl() != self.identity.url
                    or response.headers.get("Content-Range") != expected_range
                    or response.headers.get("ETag") != self.identity.etag
                    or response.headers.get("Content-Encoding", "identity") not in ("", "identity")
                    or int(response.headers.get("Content-Length", -1)) != interval.length):
                raise ValueError("radio identity/range mismatch before body read")
            payload = response.read(interval.length + 1)
        if len(payload) != interval.length:
            raise ValueError("radio response length changed")
        self.budget.accepted_bytes += len(payload)
        self.budget.remaining_seconds()
        return payload
