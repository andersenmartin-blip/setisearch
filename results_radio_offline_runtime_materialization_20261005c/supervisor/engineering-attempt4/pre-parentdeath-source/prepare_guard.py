"""Single finite compiler + harmless stdlib engineering-test preparation."""
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--tests", nargs="*", default=[])
    args = parser.parse_args()
    if args.attempt < 2:
        raise ValueError("original failed engineering attempt is closed")
    started = time.monotonic()
    attempt_root = ROOT / ("engineering-attempt%d" % args.attempt)
    attempt_root.mkdir(exist_ok=False)
    spent = attempt_root / "engineering-preparation.spent.json"
    with spent.open("x") as stream:
        json.dump(dict(schema="radio-guard-engineering-preparation-v1",
            attempt=args.attempt, wall_seconds=30, address_space_bytes=512*1024**2,
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
        process = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
                 "RADIO_ENGINEERING_OUTPUT": str(attempt_root/"test-evidence")})
        try:
            out, err = process.communicate(timeout=min(timeout,
                max(0.01, 30-(time.monotonic()-started))))
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = process.communicate(timeout=1)
            raise
        index = len(list(attempt_root.glob("operation-*.stdout.bin")))
        (attempt_root/("operation-%03d.stdout.bin"%index)).write_bytes(out)
        (attempt_root/("operation-%03d.stderr.bin"%index)).write_bytes(err)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, argv, out, err)
        return subprocess.CompletedProcess(argv, process.returncode, out, err)
    try:
        sources = [ROOT/"leaf_guard.c", ROOT/"exec_seal.c"]
        evidence["compiler"] = dict(path=str(compiler),
            sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
            version=run([str(compiler), "--version"], 2).stdout.decode())
        headers = set()
        for source in sources:
            deps = run([str(compiler), *flags, "-M", str(source)], 5).stdout.decode()
            headers.update(shlex.split(deps.replace("\\\n", " ").split(":",1)[1]))
        evidence["source_and_header_pins"] = {str(Path(p).resolve()):
            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(headers)}
        evidence["compiler_flags"] = flags
        build = run([str(compiler), *flags, str(ROOT/"leaf_guard.c"), "-o", str(ROOT / "leaf_guard")], 8)
        evidence["compiler_stdout"] = build.stdout.decode()
        evidence["compiler_stderr"] = build.stderr.decode()
        guard = ROOT / "leaf_guard"
        evidence["guard"] = dict(path=str(guard), bytes=guard.stat().st_size,
                                sha256=hashlib.sha256(guard.read_bytes()).hexdigest())
        run([str(compiler), *flags, "-shared", "-fPIC", str(ROOT/"exec_seal.c"),
             "-o", str(ROOT/"exec_seal.so")], 8)
        evidence["exec_seal"] = dict(path=str(ROOT/"exec_seal.so"),
            sha256=hashlib.sha256((ROOT/"exec_seal.so").read_bytes()).hexdigest())
        evidence["python_sources"] = {str(ROOT/p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in ("leaf_supervisor.py","phase2_bootstrap.py","test_leaf_supervisor.py","prepare_guard.py")}
        (attempt_root/"test-evidence").mkdir()
        test_argv = [str(Path(sys.executable).resolve()), "-I", "-B", "-S",
                    str(ROOT / "test_leaf_supervisor.py"), "-v", *args.tests]
        evidence["test_argv"] = test_argv
        tests = run(test_argv, 16)
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
        with (attempt_root / "engineering-preparation.result.json").open("x") as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    print(evidence["status"])
    return 0 if evidence["status"] == "HARMLESS_ENGINEERING_TESTS_PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
