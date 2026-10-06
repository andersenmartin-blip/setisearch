# Independent read-only source review

Two independent agents reviewed the unexecuted implementation and original
immutable inputs. Neither executed tests, selected normalizer code, native
imports, HDF5 operations or controls.

The normalization/import review found complete maintained AST bindings and
no signature mismatch: all required NumPy names, constants, helper functions
and two original exception classes are supplied. The receiver call matches
the original pure metadata interface; module registration supports its
dataclasses and no closure/loader API is invoked. Integer construction is
exactly representable in binary32 and does not overflow the original uint32
pattern. Descending, ascending and normalized row hashes remain distinct.
Scientific package imports and selected compilation are deferred; CLI refuses
dispatch. The old tiny synthetic fixture and completed-pilot APIs are not used.

The independent resource review identified two material prospective bounds:
read size must be bounded before allocation, and compressed chunk size/mask
must be inspected before raw payload allocation. Both source fixes are applied:
ordinary-file fstat precedes a maximum-plus-one read; chunk metadata size/mask
precedes read_direct_chunk and returned size/mask are checked again.

The leaf now checks individual84 MiB HDF5 caps plus184 MiB aggregate output
snapshots. The192 MiB overall draft envelope includes a separate8 MiB outer
terminal reserve. The96 MiB number describes forecast incremental memory,
not file storage. Continuous RSS/address-space/lifetime/descendant enforcement,
the512 MiB opaque read reserve, full runtime/source/input checks and terminal
reaping remain duties of a new frozen outer scope. They are not supplied by
this preparation or claimed as measured.

One controlled sixteen-row handoff is useful partial engineering evidence.
It is not twelve handoffs, all22 laws, actual archive provenance or scientific
admission. Actual future native interfaces have not been exercised; this is
safe to publish as a prototype with status NO_DISPATCHED, not as a runnable
qualified scope.

Pure administrative validation first passed7 tests, then9 after negative
dispatch fixtures, and10 after the independently requested oversized-read
rejection fixture. Final10-test raw logs are retained. These checks never
generated control payloads or imported installed scientific packages. No
further tests or execution are planned in this draft checkpoint.
