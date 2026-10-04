# Capture b: bounded current-runtime preread

This is a separately bounded, read-only preparation for capture identity
`e3d5aae494ef041c668a9fbec11edc2ac821a0e27bef15588181d166e125736c`.
It does not invoke the collector or supervisor, create an activation marker,
reserve a live trial, install a package, or inspect telescope data. The closed
capture a and its sources remain unchanged. The engineering subtotal remains
970 seconds / 48 MiB, and all eleven scientific fields remain pending.

The reader selects the resolved primary Python executable, all regular
non-symlink stdlib files outside site-packages, cache directories and bytecode,
the same ten named loader libraries, three NumPy distribution metadata files,
and the loader configuration/cache and OS release files. Selected file content
is hashed in one pass. It is not parsed as ELF, Python source, package metadata
or telescope data. JSON parsing is confined to the unchanged original plan and
the previous preread manifest used for comparison. The eight previously absent
native-package/materialization paths receive current `lstat` existence results;
their content is not opened.

The application content cap is **64 MiB total**, including the plan and old
comparison manifest, with **64 MiB per file**, **1,024 total regular content
files** and **1,024 selected files**.
Enumeration is capped at 16,384 entries, 2,048 entries per directory, 512 held
directories, 32 components below an enumerated root, 4,096 UTF-8 bytes per path,
and 64 explicit symlink resolutions. The metadata output cap is 1 MiB and the
post-bootstrap wall deadline is 45 seconds. A SIGALRM deadline guards blocking
operations as well as explicit clock checks. Every selected regular file must
have one hard link and mode 0644 or 0755. No-follow directory/file descriptors
bind the canonical path; device, inode, full mode, size, link count, mtime and
ctime must agree before and after the hash pass. Held ancestor descriptors and
their named directory entries are checked again before output.

The reader runs once under the trusted primary interpreter with `-I -B -S`.
This necessarily executes that interpreter and its ordinary bootstrap; hashing
the selected Python executable does not additionally execute or load the
inspected bytes. Only explicit reader content bytes are counted. Interpreter
startup, implicit module/loader/kernel/provider IO, source-file loading, and
filesystem metadata/enumeration IO are excluded from that content counter and
must not be treated as a complete runtime/peak-resource certificate. No native
package is imported by this operation. The emitted pins are prospective inputs,
not an adopted collector observation or scientific qualification.

On any failure, keep the source and log, report the concrete failure, and do not
automatically repeat this prerequisite. Output uses exclusive creation and is
written only after all selected inputs pass their stability checks.

## Completed prerequisite

The one preread completed successfully. No failed run or retry occurred.
`runtime-preread-pins.json` is 423,262 bytes with SHA256
`b5fe9e7b6cba36d726ecfe4c9bcd3d7bd5ff884cd1a3f6ecd7cb999005d27cac`.
The executed reader is 20,229 bytes with SHA256
`1d4b1bf2fc57a4d19d96ecc4d2e45294ec8dc518576e957694256fd954366535`.
The source was not changed after execution.

| Selected role | Files | Explicit content bytes |
| --- | ---: | ---: |
| ELF bytes hashed without parsing | 14 | 39,679,664 |
| Runtime/source and three NumPy metadata files | 746 | 14,078,513 |
| Loader configuration/cache and OS release | 5 | 34,593 |
| Total selected cohort | 765 | 53,792,770 |

The stdlib subset contains 746 regular files, including four zero-byte files.
Across the selected cohort and two prerequisite JSON inputs, 767 content files
and 54,015,039 explicit content bytes were read. The inputs are the unchanged
24,739-byte original plan and 197,530-byte old preread manifest. All 765 selected
path/role/size/SHA256/mode rows match the previous cohort exactly; there are no
added, removed or changed rows. This comparison does not claim that historical
inode metadata remained constant between separate preparations.

The reader enumerated 830 entries, held 69 distinct ancestor directories and
resolved three symlinks explicitly. All eight previously absent paths returned
current `lstat` ENOENT results. OS release text came from the already counted
selected-file pass; there was no extra release-file read. The log reports
0.069099176 seconds from the post-bootstrap reader start through output writing,
before the log summary is printed. This boundary excludes process startup and
final provider/CLI completion and conveys no scientific or aggregate-resource
qualification. The pins, identities, limits and current existence observations
are fully retained in the manifest; raw runtime file contents are not copied.
