# Scope of the static Python ELF preparation input

The preparation reader ran under the selected primary Python3.12.14 interpreter
with -I -B -S. That interpreter is also the file whose bytes were inspected.
The diagnostic's `target_executed:false` describes **no additional execution or
loading of the inspected bytes by the inspection operation**; it does not mean
that the preparation interpreter itself was never executed. Its kernel/loader
startup and implicit reads are outside the one-pass explicit input read count.

The reader performed one 30,894,944-byte selected file-content pass, verified the
externally expected SHA256 and held/named identity, and decoded fixed ELF header,
program-header and PT_DYNAMIC fields with struct. It did not invoke either
collector, supervisor, a native package, loader helper, ldd/readelf, or telescope
case. Header/table regions are retained exactly. Full binary custody and loader
semantics are not certified from those regions or from a file hash.

This is a new read-only prerequisite input used to design synthetic fixtures.
It does not alter the closed original scope, identify its exact failed ELF path,
adopt a runtime result, allocate a genuine live scope or refund a reservation.
