"""Inert prospective CONNECT planning and bounded transcript parsing.

No environment lookup, socket, DNS, TLS, package fetch or installer is provided.
Accepted synthetic transcripts never qualify an actual service or runtime.
"""
import hashlib
import json
import re

ORIGINAL_PLAN_SHA256 = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
SPENT_BOOTSTRAP_A = "7e4a63f99adcb7a9725211960b368db972e92b16c60bdf1a3d5220e49df2d52b"
HEADER_BYTES = 16_384
LINE_BYTES = 4_096
HEADER_COUNT = 64


class Refusal(ValueError):
    def __init__(self, reason, raw=b""):
        super().__init__(reason)
        self.raw = raw


def endpoint(proxy_url):
    if not isinstance(proxy_url, str):
        raise Refusal("explicit proxy must be text")
    match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{3,4})", proxy_url, flags=re.ASCII)
    if not match or not 1024 <= int(match.group(1)) <= 65535:
        raise Refusal("only explicit canonical credential-free local HTTP proxy is supported")
    return {"host": "127.0.0.1", "port": int(match.group(1)), "scheme": "http"}


def prepare(original_plan_raw, proxy_url, trust_binding):
    if type(original_plan_raw) is not bytes or hashlib.sha256(original_plan_raw).hexdigest() != ORIGINAL_PLAN_SHA256:
        raise Refusal("unchanged original plan raw hash required")
    if not isinstance(trust_binding, dict) or set(trust_binding) != {"path", "bytes", "sha256"}:
        raise Refusal("external prospective trust binding required")
    if (type(trust_binding["bytes"]) is not int or not 0 < trust_binding["bytes"] <= 1_048_576
            or not isinstance(trust_binding["path"], str)
            or re.fullmatch(r"/(?:[A-Za-z0-9_+.-]+/)*[A-Za-z0-9_+.-]+", trust_binding["path"]) is None
            or any(component in (".", "..") for component in trust_binding["path"].split("/"))
            or not isinstance(trust_binding["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", trust_binding["sha256"]) is None):
        raise Refusal("invalid trust binding")
    # Authenticate the complete raw plan. This preparation receipt only names
    # its hash; the later adapter must separately retain/extract pinned wheels.
    json.loads(original_plan_raw)
    return {
        "schema": "radio-proxy-transport-inert-preparation-v1",
        "status": "PENDING_IMPLEMENTATION_AND_FRESH_ADMISSION",
        "original_plan_sha256": ORIGINAL_PLAN_SHA256,
        "proxy": endpoint(proxy_url), "trust_binding": dict(trust_binding),
        "trust_bytes_observed": False, "trust_runtime_qualified": False,
        "tunnel_destination": {"host": "files.pythonhosted.org", "port": 443},
        "request_bytes": "CONNECT files.pythonhosted.org:443 HTTP/1.1\r\nHost: files.pythonhosted.org:443\r\n\r\n",
        "limits": {"response_header_bytes": HEADER_BYTES, "line_bytes": LINE_BYTES,
                   "header_count": HEADER_COUNT, "oversize_probe_bytes": 1},
        "ambient_environment_adopted": False, "authentication_headers": [],
        "direct_fallback": False, "socks_fallback": False, "redirect": False,
        "retry": False, "resume": False, "activation": None, "allocation": None,
        "retired_bootstrap_identity": SPENT_BOOTSTRAP_A,
        "old_bootstrap_reuse_authorized": False, "scientific_authority": False,
        "runtime_qualification": "PENDING", "eleven_scientific_fields": "PENDING",
        "unimplemented_gates": [
            "complete source/runtime/loader freeze and immutable publication readback",
            "externally authenticated current proxy/trust and fresh original root",
            "socket/TLS lifecycle and raw bounded CONNECT integration",
            "peer hostname verification and pinned trust bytes",
            "whole attempt clock, CONNECT/TLS reads and directory-inclusive accounting",
            "sole future allocation/activation and original wheel-body/custody guards"
        ]
    }


def parse_connect(readline, debit_network, check_deadline):
    """Parse injected bounded raw lines; do not initiate a connection.

    Precharge the full request including the possible +1 probe. Preserve every
    returned byte on refusal, and never retry a failed receive. The injectable
    caller must supply actual bounded socket reads in a separately frozen scope.
    """
    raw = bytearray()
    lines = []
    while True:
        request = min(LINE_BYTES + 1, HEADER_BYTES - len(raw) + 1)
        if request <= 0:
            raise Refusal("CONNECT header cap exceeded", bytes(raw))
        try:
            check_deadline()
            debit_network(request)
            line = readline(request)
        except Exception as exc:
            raise Refusal("CONNECT receive refused: " + type(exc).__name__, bytes(raw)) from exc
        if type(line) is not bytes:
            raise Refusal("CONNECT receive returned non-bytes", bytes(raw))
        raw.extend(line)
        # Preserve bytes returned across the deadline before refusing them.
        try:
            check_deadline()
        except Exception as exc:
            raise Refusal("CONNECT post-receive deadline refused: " + type(exc).__name__, bytes(raw)) from exc
        if len(line) > request:
            raise Refusal("injected receive violated requested bound", bytes(raw))
        if len(raw) > HEADER_BYTES or len(line) > LINE_BYTES:
            raise Refusal("CONNECT retained oversize probe", bytes(raw))
        if not line.endswith(b"\r\n") or b"\r" in line[:-2] or b"\n" in line[:-2]:
            raise Refusal("CONNECT truncated or noncanonical line", bytes(raw))
        if any(c < 32 or c > 126 for c in line[:-2]):
            raise Refusal("CONNECT control/non-ASCII byte", bytes(raw))
        lines.append(line)
        if line == b"\r\n":
            break
        if len(lines) > HEADER_COUNT + 1:
            raise Refusal("CONNECT header count exceeded", bytes(raw))
    if not re.fullmatch(rb"HTTP/1\.[01] 200 [\x20-\x7e]*\r\n", lines[0]):
        raise Refusal("CONNECT exact success required; no authentication or redirect fallback", bytes(raw))
    headers = []
    for line in lines[1:-1]:
        if b":" not in line or line[:1] in b" \t":
            raise Refusal("CONNECT malformed/folded header", bytes(raw))
        name, value = line[:-2].split(b":", 1)
        if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
            raise Refusal("CONNECT invalid header name", bytes(raw))
        if name.lower() in (b"content-length", b"transfer-encoding"):
            raise Refusal("CONNECT framed body refused by prospective law", bytes(raw))
        headers.append([name.decode("ascii"), value.decode("ascii")])
    return {"raw": bytes(raw), "headers": headers, "status": "PARSED_INJECTED_CONNECT_ONLY",
            "service_qualified": False, "tls_qualified": False, "scientific_authority": False}
