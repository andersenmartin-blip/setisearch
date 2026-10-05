# Independent actual review: offline materialization C

The sole scope closed FAILED_CLOSED. Installation achieved INSTALLED_BYTES_VERIFIED_NO_PACKAGE_IMPORT; metadata capture was incomplete. This review used retained bytes and frozen source only, without scientific imports or a second run.

- Installer exit 0, capture exit 2, outer parent exit 1; both direct leaves were guarded and reaped with exact two-phase receipts. No watchdog kill.
- All 1,643 frozen source/runtime pins independently match SHA-256, size and mode. Retained artifact and stream content hashes agree. Storage-block allocation is an observation that may change after delayed filesystem allocation; it is separate from content identity.
- 1,025 original wheel members match complete bytes. The producer's verified_original_members=1028 counts its original-member table, including 3 regenerated .dist-info/RECORD files. These 3 records differ as allowed generated metadata. No original member is missing or otherwise mutated.
- Complete parent lifetime 5.143505303 s / 300 s. Explicit parent reads 1,494,993,927 bytes plus opaque child reservations 1,073,741,824 bytes give 2,568,735,751 bytes within 4,294,967,296 bytes. Joined RSS 459,104,256 bytes is a conservative bound formed from lifetime peaks, not a measured simultaneous peak. Child proc IO was unavailable; full native IO is unqualified.
- Raw capture stderr records Refusal: dynamic string table outside unique PT_LOAD. Frozen flow invokes maps_before_packages before scientific importers. The authenticated Python has DT_STRTAB 0x3ff5d8, size 42,266, end 0x409af2, crossing adjacent file-backed LOADs [0x3ff000,0x400000) and [0x400000,0x420d70). The frozen single-segment rule necessarily refuses that table.
- The pre-import failure phase is an inference from authenticated source flow and ELF geometry, not a traceback naming a file. No explicit scientific package importer, HDF5 operation or dataset read was reached. No HDF5/plugin version or filter capability was observed.

The successful installation and failed capture are preserved separately. All 11 scientific fields remain pending. Parser repair belongs to a separate inert preparation; this spent scope is not rerun.
