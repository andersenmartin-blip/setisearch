"""Prospective stdlib-shaped bindings, all dependencies explicit and inert.

Building functions performs no socket/context/loader/trust operations. Calling
the returned functions with real modules would initiate native operations and
requires a separately admitted scope. Tests inject fake modules exclusively.
"""
import hashlib

from proxy_opener import HOST, _positive
from wheel_io import WheelIOError


def build_native_bindings(*, socket_module, ssl_module):
    if socket_module is None or ssl_module is None:
        raise WheelIOError("explicit socket and SSL modules required")

    def connect(host, port, *, timeout, register, refresh_timeout):
        _positive(timeout)
        if host != "127.0.0.1" or type(port) is not int or not 1024 <= port <= 65535:
            raise WheelIOError("native connect requires canonical numeric loopback endpoint")
        _positive(refresh_timeout())
        raw = register(socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM,
                                            socket_module.IPPROTO_TCP))
        raw.settimeout(min(timeout, _positive(refresh_timeout())))
        raw.connect((host, port))
        refresh_timeout()
        return raw

    def tls_wrap(raw, *, configuration, timeout, register, refresh_timeout):
        _positive(timeout)
        required = {"server_hostname": HOST, "check_hostname": True,
                    "verify_mode": "CERT_REQUIRED", "minimum_version": "TLSv1.2",
                    "alpn_protocols": ("http/1.1",), "default_trust": False,
                    "do_handshake_on_connect": True}
        if (any(configuration.get(key) != value for key, value in required.items()) or
                configuration.get("check_hostname") is not True or
                configuration.get("default_trust") is not False or
                configuration.get("do_handshake_on_connect") is not True):
            raise WheelIOError("native TLS binding refuses altered verification configuration")
        trust = configuration.get("trust_bytes")
        if (type(trust) is not bytes or not trust or
                hashlib.sha256(trust).hexdigest() != configuration.get("trust_sha256")):
            raise WheelIOError("native TLS binding requires observed exact trust pin")
        cadata = trust.decode("ascii", "strict")
        _positive(refresh_timeout())
        context = ssl_module.SSLContext(ssl_module.PROTOCOL_TLS_CLIENT)
        context.check_hostname = True
        context.verify_mode = ssl_module.CERT_REQUIRED
        context.minimum_version = ssl_module.TLSVersion.TLSv1_2
        context.set_alpn_protocols(["http/1.1"])
        context.load_verify_locations(cadata=cadata)
        refresh_timeout()
        raw.settimeout(min(timeout, _positive(refresh_timeout())))
        tls = register(context.wrap_socket(raw, server_hostname=HOST, do_handshake_on_connect=False))
        tls.settimeout(min(timeout, _positive(refresh_timeout())))
        tls.do_handshake()
        refresh_timeout()
        if tls.selected_alpn_protocol() != "http/1.1":
            raise WheelIOError("native TLS binding requires HTTP/1.1 ALPN")
        return tls

    return connect, tls_wrap
