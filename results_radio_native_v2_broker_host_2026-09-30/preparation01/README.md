# Host preparation failure, before transport

The raw captured exception is ReferenceError: TextEncoder is not defined.
It occurred before any connector/Git call, RNG, case reservation or telescope
read. The captured result retains its original diagnostic wording. It is
not the canonical live01 result, which was concurrently completed by another
continuation and is preserved separately in the public live-probe directory.
No shared live01/live02 namespace was mutated by this preparation.

The generic standard ECMAScript executor and six deterministic tests are
retained as offline host-compatibility evidence only. No invocation of that
executor or full-size connector qualification is claimed here.
