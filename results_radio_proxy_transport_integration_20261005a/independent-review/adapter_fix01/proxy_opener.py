"""Inert CONNECT/socket/TLS integration: no network-capable default bindings.

Injected bindings must register resources before operations that can fail and
must honor their timeout/configuration contract. Their native custody, TLS
ciphertext, DNS behavior and certificate verification cannot be certified here.
"""
import base64
import email.parser
import hashlib
import json
import math
import re
import types
import urllib.parse

import proxy_contract
from wheel_io import WheelIOError, _spec

HOST = "files.pythonhosted.org"
CONNECT = b"CONNECT files.pythonhosted.org:443 HTTP/1.1\r\nHost: files.pythonhosted.org:443\r\n\r\n"


def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def _positive(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise WheelIOError("positive finite remaining deadline/timeout required")
    return float(value)


class _Clock:
    def __init__(self, budget, deadline, cap):
        self.budget, self.deadline = budget, deadline
        self.cap = min(5.0, _positive(cap))

    def timeout(self):
        self.budget.check()
        return min(self.cap, _positive(self.deadline()))


class _Resources:
    def __init__(self, receipt):
        self.items, self.closed, self.receipt = [], False, receipt

    def register(self, resource):
        if self.closed or not callable(getattr(resource, "close", None)):
            raise WheelIOError("binding must register a closable resource before IO")
        if not any(item is resource for item in self.items):
            self.items.append(resource)
        return resource

    def require_registered(self, resource):
        if not any(item is resource for item in self.items):
            self.register(resource)
            raise WheelIOError("binding returned an unregistered resource")
        return resource

    def close(self):
        if self.closed:
            return
        self.closed = True
        errors = []
        for item in reversed(self.items):
            try:
                item.close()
            except Exception as exc:
                errors.append({"type": type(exc).__name__, "detail": str(exc)[:1024]})
        self.receipt["registered_resource_count"] = len(self.items)
        self.receipt["cleanup_attempt_count"] = len(self.items)
        if errors:
            self.receipt["cleanup_failures"] = errors
            self.receipt["status"] = "CLOSED_FAILED"
            raise WheelIOError("injected resource cleanup failed", self.receipt)


class _Stream:
    """Every syscall refreshes timeout; line reads use recv(1), never makefile."""
    def __init__(self, socket, clock, budget):
        self.socket, self.clock, self.budget = socket, clock, budget

    def send(self, raw):
        if type(raw) is not bytes:
            raise WheelIOError("send bytes required")
        self.budget.debit_network(len(raw))
        view = memoryview(raw)
        while view:
            self.socket.settimeout(self.clock.timeout())
            count = self.socket.send(view)
            self.clock.timeout()
            if type(count) is not int or not 0 < count <= len(view):
                raise WheelIOError("injected send violated positive bounded progress")
            view = view[count:]

    def recv(self, maximum, retain, *, record=False):
        if type(maximum) is not int or maximum <= 0:
            raise WheelIOError("positive bounded receive required")
        self.socket.settimeout(self.clock.timeout())
        raw = self.socket.recv(maximum)
        if type(raw) is not bytes:
            raise WheelIOError("injected receive returned non-bytes")
        retain(raw)  # Retain bytes before any post-receive refusal.
        if record and callable(getattr(self.budget, "record_received", None)):
            self.budget.record_received(len(raw), kind="network")
        self.clock.timeout()
        if len(raw) > maximum:
            raise WheelIOError("injected receive exceeded requested bound")
        return raw

    def readline(self, maximum, raw_prefix):
        result = bytearray()
        while len(result) < maximum:
            chunk = self.recv(1, lambda raw: (result.extend(raw), raw_prefix.extend(raw)), record=True)
            if not chunk or result.endswith(b"\n"):
                break
        return bytes(result)


class _RawResponse:
    def __init__(self, stream, url):
        self.stream, self.url = stream, url
        self.status, self.headers = None, None
        self.raw_header_prefix = b""
        self.pending_body = b""
        self.closed = False

    def begin(self):
        prefix, lines = bytearray(), []
        try:
            while True:
                cap = min(4097, 16384 - len(prefix) + 1)
                self.stream.clock.timeout()
                self.stream.budget.debit_network(cap)
                line = self.stream.readline(cap, prefix)
                if len(line) > 4096 or len(prefix) > 16384:
                    raise WheelIOError("bounded HTTP header line/total exceeded")
                if (not line.endswith(b"\r\n") or b"\r" in line[:-2] or b"\n" in line[:-2]
                        or any(c < 32 or c > 126 for c in line[:-2])):
                    raise WheelIOError("HTTP line is truncated, noncanonical or non-ASCII")
                lines.append(line)
                if line == b"\r\n":
                    break
                if len(lines) > 65:
                    raise WheelIOError("bounded HTTP header count exceeded")
            match = re.fullmatch(rb"HTTP/1\.[01] ([0-9]{3}) [\x20-\x7e]*\r\n", lines[0])
            if not match:
                raise WheelIOError("malformed HTTP status line")
            self.status = int(match[1])
            for line in lines[1:-1]:
                if line[:1] in b" \t" or b":" not in line:
                    raise WheelIOError("folded/malformed HTTP header")
                name = line.split(b":", 1)[0]
                if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                    raise WheelIOError("invalid HTTP header name")
            self.headers = email.parser.BytesParser().parsebytes(b"".join(lines[1:]))
        finally:
            self.raw_header_prefix = bytes(prefix)

    def read(self, maximum):
        if self.closed:
            raise WheelIOError("response already closed")
        # acquire_wheel precharges each body request, including its +1 probe.
        raw = self.stream.recv(maximum, lambda chunk: setattr(self, "pending_body", chunk))
        self.pending_body = b""
        return raw

    def geturl(self):
        return self.url

    def close(self):
        self.closed = True


def bounded_http_binding(stream, *, url, register, timeout):
    """Pure HTTP/1.1 binding, explicitly injected; uses only supplied stream."""
    _positive(timeout)
    response = register(_RawResponse(stream, url))
    request = ("GET " + urllib.parse.urlsplit(url).path + " HTTP/1.1\r\nHost: " + HOST +
               "\r\nAccept-Encoding: identity\r\nConnection: close\r\n"
               "User-Agent: setisearch-inert-proxy-adapter/1\r\n\r\n").encode("ascii")
    stream.send(request)
    response.begin()
    return response


class _Handle:
    def __init__(self, response, resources, receipt):
        self.response, self.resources, self.transport_receipt = response, resources, receipt

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read(self, maximum):
        try:
            return self.response.read(maximum)
        except Exception as exc:
            receipt = self.transport_receipt
            receipt["status"] = "CLOSED_FAILED"
            raw = getattr(self.response, "pending_body", b"")
            receipt["refused_body_receive_base64"] = _b64(raw)
            receipt["refused_body_receive_bytes"] = len(raw)
            # Successful reads are counted by unchanged acquire_wheel. A
            # refusal after recv bypasses that path, so count observed bytes
            # here exactly once without double-counting successful returns.
            record = getattr(self.response.stream.budget, "record_received", None)
            if raw and callable(record):
                try:
                    record(len(raw), kind="network")
                except Exception as record_error:
                    receipt["received_counter_failure"] = type(record_error).__name__
            receipt["failure_type"] = type(exc).__name__
            receipt["failure"] = str(exc)[:4096]
            try:
                self.resources.close()
            except WheelIOError:
                pass
            raise WheelIOError("bounded body receive refused: " + str(exc), receipt) from exc

    def close(self):
        try:
            self.resources.close()
        except WheelIOError as exc:
            raise exc


def _build(raw_plan, prepared, wheels, *, trust_read, connect, tls_wrap, http_binding,
           budget, deadline_callback):
    for binding in (trust_read, connect, tls_wrap, http_binding, deadline_callback):
        if not callable(binding):
            raise WheelIOError("explicit trust/connect/TLS/HTTP/deadline bindings required")
    allowlist = {wheel["url"] for wheel in wheels}
    if not allowlist or len(allowlist) != len(wheels):
        raise WheelIOError("nonempty unique pinned URL allowlist required")
    for wheel in wheels:
        _spec(wheel)
    trust = dict(prepared["trust_binding"])
    proxy = dict(prepared["proxy"])
    receipt = {"schema": "radio-proxy-injected-integration-v1", "status": "PENDING",
               "evidence_domain": "SIMULATION_ONLY", "runtime_qualification": "PENDING_ACTUAL_NATIVE_CUSTODY",
               "plan_sha256": hashlib.sha256(raw_plan).hexdigest(),
               "original_plan_sha256": proxy_contract.ORIGINAL_PLAN_SHA256,
               "plan_binding_kind": prepared["plan_binding_kind"],
               "trust_bytes_pin_observed": False, "peer_verification_native_qualified": False,
               "tls_resource_custody_qualified": False, "scientific_authority": False,
               "old_bootstrap_status": "CLOSED_FAILED", "old_bootstrap_reuse_authorized": False,
               "direct_fallback": False, "retry": False, "allocation": None, "activation": None,
               "received_connect_prefix_base64": "", "received_connect_prefix_bytes": 0}
    resources = _Resources(receipt)
    used = False

    def opener(url, *, timeout):
        nonlocal used
        if used:
            # A repeat/reentrant refusal cannot replace or close the original
            # attempt's raw evidence or resources.
            raise WheelIOError("single-use opener refuses retry or reentrancy", {
                "status": "CLOSED_FAILED", "evidence_domain": "SIMULATION_ONLY",
                "refusal_kind": "SEPARATE_SPENT_OR_REENTRANT_CALL",
                "original_attempt_evidence_preserved": True})
        used = True
        prefix = bytearray()
        try:
            if type(url) is not str or url not in allowlist:
                raise WheelIOError("URL is not an exact member of the bound plan")
            clock = _Clock(budget, deadline_callback, timeout)
            clock.timeout()
            budget.debit_read(trust["bytes"] + 1)
            trust_raw = trust_read(trust["path"], trust["bytes"] + 1)
            if type(trust_raw) is bytes:
                receipt["trust_observed_bytes"] = len(trust_raw)
                receipt["trust_observed_sha256"] = hashlib.sha256(trust_raw).hexdigest()
            clock.timeout()
            if (type(trust_raw) is not bytes or len(trust_raw) != trust["bytes"] or
                    hashlib.sha256(trust_raw).hexdigest() != trust["sha256"]):
                raise WheelIOError("trust bytes differ from exact prospective pin")
            receipt["trust_bytes_pin_observed"] = True
            raw_socket = resources.require_registered(connect(
                proxy["host"], proxy["port"], timeout=clock.timeout(), register=resources.register))
            clock.timeout()
            stream = _Stream(raw_socket, clock, budget)
            stream.send(CONNECT)
            proxy_contract.parse_connect(lambda cap: stream.readline(cap, prefix),
                                         budget.debit_network, clock.timeout)
            configuration = types.MappingProxyType({"server_hostname": HOST, "check_hostname": True,
                             "verify_mode": "CERT_REQUIRED", "minimum_version": "TLSv1.2",
                             "alpn_protocols": ("http/1.1",), "trust_bytes": trust_raw,
                             "trust_sha256": trust["sha256"], "default_trust": False,
                             "do_handshake_on_connect": True})
            tls_socket = resources.require_registered(tls_wrap(
                raw_socket, configuration=configuration, timeout=clock.timeout(),
                register=resources.register))
            clock.timeout()
            response = resources.require_registered(http_binding(
                _Stream(tls_socket, clock, budget), url=url,
                register=resources.register, timeout=clock.timeout()))
            clock.timeout()
            receipt["status"] = "SIMULATION_ONLY"
            receipt["binding_returned"] = True
            return _Handle(response, resources, receipt)
        except Exception as exc:
            receipt["status"] = "CLOSED_FAILED"
            receipt["failure_type"] = type(exc).__name__
            receipt["failure"] = str(exc)[:4096]
            for item in resources.items:
                if hasattr(item, "raw_header_prefix"):
                    header = item.raw_header_prefix
                    receipt["received_http_header_prefix_base64"] = _b64(header)
                    receipt["received_http_header_prefix_bytes"] = len(header)
                if getattr(item, "pending_body", b""):
                    body = item.pending_body
                    receipt["deadline_refused_body_base64"] = _b64(body)
                    receipt["deadline_refused_body_bytes"] = len(body)
            try:
                resources.close()
            except WheelIOError:
                pass  # All close attempts recorded; preserve the primary refusal.
            raise WheelIOError("inert proxy integration refused: " + str(exc), receipt) from exc
        finally:
            receipt["received_connect_prefix_base64"] = _b64(prefix)
            receipt["received_connect_prefix_bytes"] = len(prefix)

    opener.receipt = receipt
    return opener


def make_opener(original_plan_raw, proxy_url, trust_binding, **bindings):
    """Production plan binding; complete original raw plan and URL list required."""
    prepared = proxy_contract.prepare(original_plan_raw, proxy_url, trust_binding)
    prepared["plan_binding_kind"] = "AUTHENTICATED_ORIGINAL_PLAN"
    wheels = json.loads(original_plan_raw)["materialization"]["official_wheels"]
    return _build(original_plan_raw, prepared, wheels, **bindings)


def make_simulation_opener(test_plan_raw, original_plan_raw, proxy_url, trust_binding, **bindings):
    """Distinct synthetic fixture only; never substitutes for original plan binding."""
    prepared = proxy_contract.prepare(original_plan_raw, proxy_url, trust_binding)
    fixture = json.loads(test_plan_raw)
    if (fixture.get("schema") != "radio-proxy-separate-synthetic-wheel-fixture-v1" or
            fixture.get("evidence_domain") != "SIMULATION_ONLY" or
            fixture.get("original_plan_sha256") != proxy_contract.ORIGINAL_PLAN_SHA256):
        raise WheelIOError("explicitly separate synthetic fixture required")
    prepared["plan_binding_kind"] = "SEPARATE_SYNTHETIC_FIXTURE"
    return _build(test_plan_raw, prepared, fixture["wheels"], **bindings)
