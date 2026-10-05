# Inert wheel acquisition and static preflight preparation

`wheel_io.py` supplies bounded acquisition and archive inspection for a future,
separately frozen engineering bootstrap. This preparation used synthetic ZIP
fixtures and an injected in-memory HTTP response only. It made no genuine
network request, read no official wheel, extracted or installed no wheel, and
imported no wheel package or HDF5 runtime. The original three wheel identities
and their materialization plan have not been changed.

The final synthetic run is `wheel-io-tests-05.log`: **55 tests passed** with the
primary Python invoked using `-I -B -S`. Earlier development logs remain visible.
`wheel-io-development-failure-01/` preserves the exact source, tests and failed
second run before any correction. Its two failures were fixture expectations:
after the stored-compression consistency check was strengthened, size-cap
fixtures failed at that earlier check. The fixtures now set both declared
compressed and uncompressed lengths to reach the intended cap checks. No
genuine attempt was made or retried.

## Caller interfaces

```python
acquire_wheel(wheel, held_wheelhouse_fd, budget, deadline_callback, opener=None)
inspect_wheel(held_archive_fd, wheel, budget, deadline_callback)
```

The wheel object uses the unchanged plan fields `filename`, `url`, `bytes`,
`sha256`, `name`, `version`, and the complete expanded `tags` list. The caller
must authenticate that object against the frozen original plan before invoking
either function. Checking HTTPS shape is not a substitute for a plan pin.

Budget methods are `check()`, `debit_read(n)`, `debit_network(n)`,
`before_write(n)`, and `after_write()`. The debit methods **precharge requested
bytes before a syscall**, including EOF/oversize probes; they do not refund a
short read. Optional `check_directory(fd)` lets the caller authenticate the held
and named directory hierarchy. The module independently checks held directory
identity and the held/named sole output inode, mode and link count throughout
acquisition. Optional `record_received(n, kind=...)` records actual bytes
returned to the module, with kinds `network` or `zip`.

ZIP physical reads use `debit_read`, so the parent budget's charged regular
category includes archive reads. Actual ZIP bytes are labeled `zip` separately;
the preflight receipt also contains its complete requested and actual archive
read sums. There is no double read/network debit for a socket body read.

`before_write` is a prospective filesystem allowance check, not a consumed-byte
counter. It is called for the full next bounded receive before that receive,
again for the actual observed chunk before writing, and after writes through
`after_write`. This prevents a prospective artifact-cap refusal from stranding
a newly observed chunk. Receipt body/written byte counters are actual counts.
Filesystem failures can still interrupt a write; the receipt distinguishes
received and successfully written bytes instead of claiming those are equal.

The deadline callback must raise on expiration. It may return remaining seconds
to set each initial HTTPS socket timeout, capped at five seconds. The caller's
supervision remains responsible for the whole bootstrap wall limit and for any
kernel/provider operation whose completion this module cannot certify.

Successful acquisition has status `ACQUIRED_HASH_MATCH`. Successful preflight
has status `STATIC_WHEEL_PREFLIGHT_VERIFIED`. Failures raise `WheelIOError` with
the partial acquisition/preflight `.receipt`; callers must retain it. The held
archive descriptor is owned and closed by the caller. The injected opener is a
test seam; the genuine caller uses the fixed HTTPS implementation.

## Acquisition law

The genuine implementation issues one attempted GET to the exact pinned
`https://files.pythonhosted.org/packages/.../<fixed filename>` URL, directly
without proxy discovery, redirects, retries or resume. TLS certificate
verification uses the standard default context. Every returned body chunk is
bounded by the remaining pinned length plus one byte. That extra byte, if
observed, is preserved in the sole exclusive output and causes refusal.
Output creation uses `O_EXCL | O_NOFOLLOW` and mode `0600`; an existing regular
file or symlink is never adopted or replaced.

The bounded response parser accepts one HTTP/1.0 or HTTP/1.1 status/header
block. It caps raw status/header bytes at 16 KiB, each line at 8 KiB, and fields
at 128. A bounded +1 refusal prefix may also be retained. It does not skip
interim responses or accept folded headers. The admitted response must have
status 200, one canonical Content-Length equal to the pinned byte count, no
transfer coding and no content coding except sole `identity`. Reading continues
to connection close so a declared length cannot hide the single oversize probe.
The caller should allow up to 64 KiB per acquisition header receipt, because
retaining parsed strings and the raw header prefix as base64 takes more bytes
than the raw 16 KiB header cap.

Hash, length and network failures retain the successfully written raw output;
there is no unlink or automatic successor. Receipt `requests` counts attempted
opens/requests, not packets successfully placed on the wire. DNS, TLS native
loader activity, kernel buffering and implicit bootstrap I/O are unqualified.
No fsync/crash/power-loss durability or provider peak certificate is claimed.

## Static archive law

Before constructing `ZipFile`, a held-file parser verifies one terminal EOCD,
at most 2 MiB of central directory and 8192 entries per wheel. ZIP64, multiple
disks, encryption, unsupported compression/features, Unicode-name alias extras,
symlinks and special files are refused. Only stored and raw-DEFLATE members are
supported. Local and central names, flags, timestamps, CRC/length fields and
optional signed/unsigned data descriptors must agree. Local regions must be
contiguous, start at archive offset zero, never overlap, and end at the central
directory. Unknown preambles, gaps, appended data and overlap are refused.

Paths are checked without changing their spelling: absolute paths, traversal,
empty/dot components, control characters, backslashes, drive separators,
normalization/case aliases, reserved portable components, trailing dot/space
components and file/directory prefix collisions are refused. Implied directory
prefixes participate in the alias check. Safe `.data` members are allowed only
under the pinned distribution/version and known wheel schemes.

The complete held archive is independently SHA256 checked. Every regular member
is then streamed through bounded raw compressed reads, with a 128 MiB member
limit and a 512 MiB aggregate payload limit per wheel. Raw-DEFLATE has explicit
bounded output and must reach exactly its end marker without ignored trailing
compressed bytes; inspection does not rely on `ZipExtFile` trimming output to a
declared length. Streamed lengths and CRC32 values must match declarations.
The `ZipFile` central view is compared against the manual structural preflight.
Held inode, byte length, timestamps and link count are checked around reads.

METADATA Name/Version, sole Wheel-Version `1.0`, canonical Root-Is-Purelib and
the exact expanded WHEEL tag set are checked. RECORD must cover precisely every
regular member, with canonical unpadded URL-safe SHA256 hashes and canonical
decimal sizes; RECORD's own row alone has blank hash/size. Deprecated
`RECORD.jws` and `RECORD.p7s` signatures are explicitly refused. Metadata,
RECORD and entrypoint capture is capped at 2 MiB per member. The receipt includes
every member path, declared/streamed bytes and SHA256, metadata, entrypoint text,
and extension-shaped native member paths. Native members are **not** ELF parsed
or imported.

`metadata.data_paths_remapped: false` records that this static inspector has
performed no `.data` remapping. It does **not** promise that pip keeps wheel
archive paths as installed paths. The installer/verifier must independently
model pip's schemes or refuse an unsupported `.data` cohort before child launch.
Global installed file/directory and whole-cohort bounds belong to the caller;
the per-wheel 8192 entry ceiling does not waive those global limits.

These engineering checks provide no scientific runtime, CAS, host/native peak,
receiver handoff, trial allocation or data-analysis qualification.
