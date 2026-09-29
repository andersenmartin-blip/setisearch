# Complete receiver evidence exceeds the present reader's logical capacity

29 September 2026. Evidence checkpoint:
`f6a91931282bcd38a12a48625dfe784e6c8f0172`.

**Preflight decision: do not start a new native qualification with the current
physical evidence representation.** For the already observed 9,792-member
workload, a conservative lower bound on the physical report including receiver
evidence is **29,821,434 bytes**. The present reader refuses expansion above
**25,165,824 bytes (24 MiB)**. This incompatibility is established without
regenerating the closed case, computing a receiver peak or reserving a new trial.

The receiver batching improvement remains valid: it reduces a demonstrated
computational cost while preserving the old signature and receipt bytes. That
byte preservation also preserves the size of the complete output. Faster query
processing does not resolve this separate representational limit.

## Evidence and lower-bound construction

The source is the original public partial physical report from the closed native
engineering case, SHA256
`6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd`.
The audit retrieves its immutable Git archive, verifies all twelve transport
parts, the compressed archive and the original report hash, and reads only
saved evidence. The original report is 14,979,354 bytes.

Its 9,792 retained ON members comprise **7,668 two-epoch members and 2,124
three-epoch members**, requiring **21,708 individual receiver queries** under
the unchanged contract. Batching avoids repeated arithmetic and validation but
retains each of these member/epoch receipts in the output.

| Lower-bound term | Bytes |
|---|---:|
| Existing accumulated report, without failure and with the shorter `true` completion flag | 14,979,265 |
| Receiver signature mapping, using one-character placeholders for unknown numbers | 3,085,237 |
| Native per-query receipt list, with the same numeric lower bound | 11,756,877 |
| Additional minimal JSON field/wrapper punctuation | 55 |
| **Minimum physical report** | **29,821,434** |
| Present reader's maximum logical report | **25,165,824** |
| **Minimum excess** | **4,655,610** |

Every unknown number contributes only the single JSON character `0`; required
64-character identities retain their length. These are symbolic byte-count
terms, **not receiver measurements, valid signatures or generated receipts**.
No artificial report is saved or admitted. Real numerical precision can only
increase this bound. The obsolete failure is removed, and the shorter complete
flag is used, so those fields do not inflate the bound.

The count deliberately omits the other native receipt fields, the source-receipt
bridge wrapper, normalized signature hash, identity partition, receiver-alias
witnesses, final decisions/clusters, final digest and checkpoint/closure
metadata. All of these can only add bytes. The seven already saved base
artifacts add another 2,004,352 bytes, giving **at least 31,825,786 bytes** for
the uncompressed case representation before those omitted terms.

## What fails, and what this does not prove

`physical_evidence_radio._decode` explicitly checks the sum of expanded logical
field lengths against `MAX_BYTES = 24*1024**2`. Therefore deduplicating stored
parts alone cannot make the current reader restore a report of this lower-bound
size. The earlier 22-view storage PASS exercised the **partial** report, before
receiver evidence; it never qualified this larger complete workload. That old
PASS and the earlier native failure retain their original meanings.

This is a bound for one already observed workload, not a claim that every fresh
draw has the same retained members. It is also **not a lower bound on a different
lossless compressed representation**. The scientific evaluation allocation is
18 MiB of stored case evidence; raw logical bytes must not be confused with
encoded stored bytes. The result rules out the present reader/representation
for the known load, not all possible designs or the radio method itself.

## Required continuation and stop condition

The earlier instruction to proceed immediately to a fresh full native run is
superseded by this preflight obstruction. First specify a complete evidence
representation that can preserve all original receiver signatures, query
receipts, vetoes, decisions, failure evidence and identities within the unchanged
stored-case and journal budgets. It must distinguish bounded logical decoding
from actual stored and transported bytes and must not truncate, omit, round,
merge away or relabel individual members. Any changed representation requires
its own explicit prospective contract and compatibility/readback checks; no
historical limit or closed outcome may be silently changed.

Only then freeze a new integrated native physical/resource qualification with
fresh identities, the batching correction, full stage timing and bounded
interruption handling. A full native result, integrated remote evidence,
scientific 127/24 validation and the separate telescope protocol remain required
before telescope admission. This review launches no new storage experiment,
native attempt, calibration, telescope read or corrective live scope.

At the 2 October review and 9 October consolidation, count this as a documented
execution obstruction. Do not describe the radio pilot as underway or its
scientific readiness as nearly complete. The current representation is blocked
for the known workload; the original end date remains unchanged.

## Reproduction and state

Run `python scripts/radio_receiver_evidence_capacity.py` in a checkout containing
the immutable checkpoint above. The script uses only the Python standard
library and Git; it emits the saved
[`result.json`](results_radio_receiver_capacity_2026-09-29/result.json). It does
not require the transient unpacked archive or import any experiment module.
An independent direct JSON construction was also compared with the arithmetic
byte count; only the verification result is saved, not the symbolic report.

All previous failures, reservations, spent identities, thresholds and resource
limits remain unchanged. HD189733/85030 is still selected; HD1461 remains on
HOLD and GJ724 is the reserve. Telescope spectra and old holdouts are unopened;
LS is paused and CHEOPS is UNSENT. No messages, delegation, new scheduled task
or plan extension.
