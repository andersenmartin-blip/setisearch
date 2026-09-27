# Local codec/direct handoff and publication boundary — 27 September 2026

**Local engineering passes; telescope execution remains BLOCKED.** This package
continues from science commit `0a45500905537b814ffc0a11a9d94ca42af70e68` and
closes its stated local adapter/publication-protocol work item. Twenty-four new
tests pass. No telescope request, scientific evaluation or new trigger search
was performed.

## New codec-to-direct integration evidence

Twelve local codec receipts (six scans encoded in each of two codecs) now cross
an independently pinned manifest into the direct-native score store. Both actual
gzip and bitshuffle/LZ4 decoding are exercised. Each scan contains 16 synthetic
rows; extraction uses descending native columns `[501, 9014)`, retaining 8513
channels including a partial normalization block.

| Changed-boundary check | Verified result |
| --- | ---: |
| Codec/source receipts | 12 |
| Normalized float32 cells, bit-exact against independent sorting | 1,634,496 |
| Direct-native score cells, bit-exact against independent window sums | 14,112 |
| Filter widths | 1, 3, 5, 9, 17, 33, 65, 129 channels |
| Real telescope requests and opened values | 0 |

The two codecs encode the **same synthetic six-scan cadence**. They are one
background realization, not two independent observations or recovery panels.
The three-template motion table is a small local interface fixture with no
physical ephemeris claim. The existing normalization, direct-factor arithmetic
and downstream code were reused unchanged; the new result concerns their
receipt-bound connection.

The adapter binds scan order, native interval, normalization origin, direct bank,
header clock, source-contract hash, runtime and downstream window. It refuses
mixed codecs/scans, changed clocks/contracts, untrusted hashes, real-source URLs,
telescope-kind receipts, altered transport claims and changed native files.
Cadence inventory and capacity checks run before native-row reads. A second
hash check catches a row changed between verification and use. Reconstructing
the gzip fixture in another scratch path reproduces its complete receipt
inventory and binding identity. No old scratch path is needed.

## Demonstrated publication defect and scoped repair

The earlier local v2 CAS primitive validates a document's internal consistency,
but its direct `publish` method can replace a committed ledger with a valid empty
one. A new test reproduces this on a temporary store. The normal `reserve_role`
controller did not perform that reset; no published ledger was reset or damaged.

The new `BoundRoleStore` adds a pinned store/resource/genesis boundary and
requires exactly one ordered append with the old prefix preserved. It rejects
resets, changed namespaces, replacement reservations, wrong locations and bad
confirmation. Concurrent workers with the same parent yield exactly one winner.
A reply lost after durable CAS leaves the reservation spent, and a stale retry
is refused. Three ordered local reservations exhaust the unchanged cumulative
limits; a fourth fails and no network budget is returned.

The [protocol](RADIO_CODEC_PUBLICATION_2026-09-27_PROTOCOL.md) and machine-readable
store specification pin the future GitHub repository/branch/path, parent and
content checks, append-only rules and `force=false` requirement. The prospective
remote path is **not created**. This package qualifies the local boundary and
freezes remote obligations; it does not claim a running or qualified remote
v2 backend. The old CAS primitive is retained unchanged for reproducibility;
future v2 callers must use the guarded boundary.

## Evidence, runtime and unchanged limits

`results_radio_codec_publication_2026-09-27/` retains both complete codec receipt
inventories, manifests, direct-bank records, input and score hashes, simulated
HTTP inventories, local publication evidence, runtime supplement, result and
test log. The fixed generator reproduces native values and HDF5 fixtures; these
generated arrays are not duplicated as binary payloads in the repository.
`RESULTS_MANIFEST_RADIO_CODEC_PUBLICATION_2026-09-27.sha256` covers the package.

Runtime: Python 3.12.14, NumPy 2.3.5, h5py 3.16.0 / HDF5 2.0.0 and hdf5plugin
7.1.0. Fourteen existing input/code files are independently hash-checked before
and after qualification. The parent execution envelope is unchanged; the new
runtime supplement pins only this continuation's implementation.

```sh
PYTHONPATH=src:scripts python scripts/radio_codec_publication_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_CODEC_PUBLICATION_2026-09-27.sha256
```

The original preparation contract remains
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.
The published synthetic acquisition ledger is still closed and exhausted; its
file SHA remains `b77c59e4e1772b27ef7c170bb1c08d1f6c7483d1f12a6c5a0a0deedfca82fd83`.
The prospective telescope namespace has zero reservations. The original
seven preparation gates and five blockers are not relabelled by local tests.

## Precise continuation

The fixture adapter and publication-specification tasks are complete. Do not
repeat these tests unchanged as progress or activate the prospective ledger.
The next useful metadata/model task is a bounded **physical-motion accuracy
and coverage contract**: distinguish the already verified factor arithmetic
from unresolved orbital reference/omega/time conventions, parameter uncertainty,
relativistic terms and continuous template coverage. Use retained metadata and
the existing motion audit first; investigate a new primary reference only if it
can resolve a named missing model input. Do not rerun the old 2048-phase audit,
expand the bank, tune the failed control panel or open any evaluation spectra.
If no missing term can be bounded from available evidence, record the exact
missing information instead of asserting a qualified bank.

Pointing still requires a genuinely new same-scan original RAW/FIL header, log
or file-specific conversion for AGBT16A_999_189 scans 0015/0017/0019. No old
catalogue/public-code lookup was repeated here. The 34.23-arcminute discrepancy
and both coordinate identities remain. The remote v2 backend, telescope receipt
handoff, numeric cross-window transfer and fresh 24-case scientific panel remain
unqualified/unexecuted. No new telescope path may run without the complete
published and verified prospective protocol.

`neighbor9` is unchanged. M43AI remains failed/closed; the original 112+128
M43AF holdouts stay untouched. M15 GJ581 and M33 HD3651 remain unresolved with
all prior dispositions retained. LS remains paused at LS8BD–LS8BE, LS8BF unopened,
and CHEOPS unsent. No external message, paid service, booking or delegation was
used. The two-week plan still ends with consolidation on 9 October.
