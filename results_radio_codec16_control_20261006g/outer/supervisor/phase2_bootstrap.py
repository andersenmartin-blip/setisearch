"""Frozen cooperative bootstrap: seal exec before pip/native imports."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys


def main(argv):
    if len(argv) < 4:
        raise RuntimeError("phase2 arguments missing")
    seal_path, expected_hash, mode, payload, *args = argv
    path = Path(seal_path)
    if not path.is_absolute() or path.resolve() != path or \
            hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise RuntimeError("phase2 native seal pin mismatch")
    seal = ctypes.CDLL(str(path), use_errno=True)
    seal.radio_seal_exec.argtypes = ()
    seal.radio_seal_exec.restype = ctypes.c_int
    if seal.radio_seal_exec() != 0:
        raise RuntimeError("phase2 exec seal refused; no fallback")
    ready = dict(schema="radio-leaf-phase2-v1", no_new_privs=1,
                 seccomp_mode=2, exec_denied=True, scientific_imports_started=False)
    os.write(2, b"RADIO_PHASE2_ACTIVATED " +
             (json.dumps(ready, sort_keys=True) + "\n").encode())
    # Neither scientific/native package nor original leaf code is run before
    # the mandatory marker. The two seccomp filters now survive any attempt.
    if mode == "code":
        sys.argv = ["-c", *args]
        exec(compile(payload, "<frozen-leaf-code>", "exec"),
             {"__name__": "__main__", "__builtins__": __builtins__})
    elif mode == "path":
        sys.argv = [payload, *args]
        runpy.run_path(payload, run_name="__main__")
    else:
        raise RuntimeError("phase2 original driver mode refused")


if __name__ == "__main__":
    main(sys.argv[1:])
