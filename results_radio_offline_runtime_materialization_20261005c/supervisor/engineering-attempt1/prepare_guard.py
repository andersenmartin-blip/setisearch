"""Single finite compiler + harmless stdlib engineering-test preparation."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    started = time.monotonic()
    spent = ROOT / "engineering-preparation.spent.json"
    with spent.open("x") as stream:
        json.dump(dict(schema="radio-guard-engineering-preparation-v1",
            wall_seconds=30, address_space_bytes=512*1024**2,
            compilation_and_harmless_stdlib_tests_only=True,
            package_imports_authorized=False, scientific_authority=False), stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2, 512*1024**2))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("preparation deadline")))
    signal.setitimer(signal.ITIMER_REAL, 30)
    evidence = dict(schema="radio-guard-engineering-result-v1", status="FAILED_CLOSED",
                    scientific_authority=False, package_imports=False)
    compiler = Path("/usr/bin/cc").resolve()
    flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"]
    def run(argv, timeout):
        return subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
            timeout=min(timeout, max(0.01, 30-(time.monotonic()-started))),
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"})
    try:
        source = ROOT / "leaf_guard.c"
        evidence["compiler"] = dict(path=str(compiler),
            sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
            version=run([str(compiler), "--version"], 2).stdout.decode())
        deps = run([str(compiler), *flags, "-M", str(source)], 5).stdout.decode()
        headers = shlex.split(deps.replace("\\\n", " ").split(":", 1)[1])
        evidence["source_and_header_pins"] = {str(Path(p).resolve()):
            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in headers}
        evidence["compiler_flags"] = flags
        build = run([str(compiler), *flags, str(source), "-o", str(ROOT / "leaf_guard")], 8)
        evidence["compiler_stdout"] = build.stdout.decode()
        evidence["compiler_stderr"] = build.stderr.decode()
        guard = ROOT / "leaf_guard"
        evidence["guard"] = dict(path=str(guard), bytes=guard.stat().st_size,
                                sha256=hashlib.sha256(guard.read_bytes()).hexdigest())
        tests = run([str(Path(sys.executable).resolve()), "-I", "-B", "-S",
                    str(ROOT / "test_leaf_supervisor.py"), "-v"], 16)
        evidence["test_stdout"] = tests.stdout.decode()
        evidence["test_stderr"] = tests.stderr.decode()
        evidence["status"] = "HARMLESS_ENGINEERING_TESTS_PASSED"
    except BaseException as exc:
        evidence["error"] = type(exc).__name__
        if isinstance(exc, subprocess.CalledProcessError):
            evidence["failure_stdout"] = exc.stdout.decode(errors="replace")
            evidence["failure_stderr"] = exc.stderr.decode(errors="replace")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        evidence["elapsed_seconds"] = time.monotonic()-started
        with (ROOT / "engineering-preparation.result.json").open("x") as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    print(evidence["status"])
    return 0 if evidence["status"] == "HARMLESS_ENGINEERING_TESTS_PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
