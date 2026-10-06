# J loader-event source component — 6 October 2026

Disposition: **SOURCE_COMPONENT_NO_COLLECTOR_NO_DISPATCH**.

The authority is science commit `71d0073faac7cd1a487e950f28a6f74b7daf75ab`.
This component continues I and preserves H's complete-lifetime condition. It
does not modify I's producer, H's 12-handoff protocol, the original preparation
contract, any ledger, trial panel, cumulative spend or scientific disposition.

## Concrete risk and fixed component

The closed G source explicitly describes before/after inventories as snapshots,
not continuous loader custody. A native object can be loaded and unloaded
between snapshots. The reducer retains every supplied object generation after
close, rather than retaining only the live endpoint set. A later open of the same
file gets a new generation; an old generation cannot be reused. The fixture
starts and ends with the main executable alone yet retains the transient object.

The normalized event vocabulary is `handshake`, `object_open`, `preinit`,
`object_close`, `collector_end`. Raw canonical JSON lines have sequence, previous
raw-body SHA256, monotonic timestamp and an exact local/outer PID, namespace and
start-time identity. The handshake binds I's source-freeze SHA256. Only one
process and loader namespace zero are supported. Exact expected file path,
nonempty byte count and SHA256 bind each supplied object event; these supplied
values do **not** prove a held file's actual bytes or continuous integrity.
The main executable's empty loader name has one explicit executable binding.
Relative/symlink names, kernel pseudo-objects, additional namespaces and all
unsupported event types are refused rather than guessed.

Bounds are 8,192 bytes per raw event, 8 MiB aggregate raw events, 4,096 events,
256 total object generations and 256 file expectations. These are prospective
component input limits, not a new control allocation. Refused raw inputs remain
charged, poison the stream and cannot be resumed. Incomplete, truncated,
reordered, wrong-process, lost-event or unsuccessful-exit declarations refuse a
receipt. A declared zero event-loss count does not itself establish completeness.

## Origin and coverage remain missing

The documented GNU loader callbacks inform the conceptual open/close/preinit
vocabulary. [Linux man-pages `rtld-audit(7)`](https://www.man7.org/linux/man-pages/man7/rtld-audit.7.html)
describes separate notifications for object load, object unload and entry to the
application. This is a proposed normalized contract, **not** a glibc audit module,
syscall tracer, parser of actual audit output, symbol-binding verifier or kernel
coverage claim. The documented interface was checked on 6 October 2026; the
retrieved page identifies Linux man-pages 6.19 and HTML generation 9 September
2026. No documentation example or external code is executed or copied.

A self-authored event stream can omit a complete open/close pair and recompute
its chain. The explicit omission test demonstrates this limit. Therefore every
structurally valid receipt still has collector authentication, full loader/syscall
coverage, continuous file custody, descendant/terminal IO qualification, runtime
qualification, codec certification, execution and spectra authority **false**.
The public dispatch entry always refuses. The input hashes are expectations,
not authentication of a real loader or file descriptor. An authenticated
collector, startup/audit-library/kernel-object coverage, actual path/descriptor
custody, namespace/symbol handling, fresh runtime inventory and externally
observed terminal wait4/IO must be joined before a separate executable freeze.

## Current runtime boundary and next step

The previously published canonical G runtime path is absent in this workspace.
`CURRENT_RUNTIME_BOUNDARY.json` records that missing pathname and fresh stable
read-only pins for currently available administrative binary inputs. A present
`strace` file proves only an available file; it proves no ptrace access, successful
trace, installed target cohort or observer qualification. No binary is launched
to obtain those observations. Do not silently substitute the base Python or
rebind G's historical inode witnesses as a restored current runtime.

Next: recover authenticated archived package inputs under a distinct explicit
current-storage/runtime contract, then implement and qualify an authenticated
collector spanning startup through terminal observation, including transient
objects and unmodeled namespaces/kernel objects. Join it to I, unchanged H and
the existing direct-child/process/terminal-IO evidence before freezing any
executable outer scope, public preread or one-shot activation. There is no
collector result to replay. The codec600s/540CPU/448MiB/4GiB+1GiB proposal remains
unallocated. The selected spent subtotal remains 2,920s/5,512MiB plus the separate
five guard controls; the original synthetic acquisition ledger remains exhausted.
Consolidate 9 October without extension.
