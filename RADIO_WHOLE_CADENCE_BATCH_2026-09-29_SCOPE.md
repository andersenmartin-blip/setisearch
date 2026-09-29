# Prospective batched-publication latency scope — engineering only

29 September 2026; parent d30319338c1ae0be78b22ca4b80cd95aa8fe25b4.
The two old remote scopes and the lossless two-case scope stay CLOSED. Their
reservations are not refunded. No scientific or telescope admission is issued.

One fresh case in `results_radio_whole_cadence_batch_2026-09-29/live01` archives
524,305 fixed bytes, `bytes((i*31+19)%256 for i in range(524305))`, plus one JSON
witness. Fresh identity, recipe and full Git-aware execution/runtime freeze are
published and independently read back before work. This is a different API and
handoff implementation, not a replay/completion of an old case. No RNG.

Use GitHub's documented Create Tree `content` entries for ASCII envelopes. Compute
the exact new Git tree hash locally from verified immutable parent trees; require
the returned root hash to match before committing. Unrelated entries remain
identical by construction. No destructive entries, mixed `sha`/`content`, path
collisions, changed file modes or existing artifact overwrites are allowed.
All envelope bytes still require fresh immutable-path external readback and full
raw decoding. Exact-parent fresh branch checks, `force=false`, atomic artifact
plus seal publication, durable prior consumption and non-resumable process-local
capabilities remain required. A fresh store must verify the finished archive.

Combine atomic response delivery and next-request framing in one local handoff;
retrieve large immutable request-file chunks concurrently. Do not pause the
broker for periodic model yields. Retain every request/response, timings, branch
publication and error. A technical/ambiguous/capacity failure stops without retry.
The one fixed engineering case reserves **80 seconds / 1 MiB actual encoded
artifact bytes**, plus a distinct 8 KiB failure reserve. Every ledger version is
charged under a 64 KiB history reserve. Completion seals do not attest their own
future publication duration; the worker's post-publication timer does. Assess
40/80-second scientific timing separately and conservatively: one fixed binary
case cannot qualify Gaussian/native/physical execution or a 151-case phase.

New-scope ceilings: **600 active seconds, 160 GitHub calls, 16 MiB returned JSON,
2 MiB archive/support evidence, 16 MiB local saved evidence, 512 MiB RSS, six
branch advances** including freeze, two live transitions, report and main README.
Keep the prior conservative remote-scope charges of 316 calls and
1,636.04648012 seconds (including published closure reserves) and 1,920 s of
nonrefundable case reservations separate and cumulative. These are additional
bounded engineering resources; the scientific 7,200 s / 1 GiB ceiling and all
scientific counters remain unchanged. Do not activate 127/24 or use its seeds.

Before live execution, test new tree reconstruction/content-entry risk, exact
parent preservation, readback corruption, rejected overwrite/mode changes,
ambiguous update, timing/call/byte caps and combined handoff framing. Do not
replay old closed fixtures as new progress. If timing is still inadequate, retain
that outcome; do not raise this case's cap or create a corrective live scope here.

After closure follow the measured result. Any actual Gaussian/native qualification
needs distinct engineering identities and a separate prospective executable scope;
never impersonate a scientific lease. HD189733/85030, neighbor9, original source
preparations, HD1461 hold, GJ724 reserve, old failures/holdouts, LS pause and CHEOPS
UNSENT are unchanged. No messages, subagents, paid services, booking, automation or
plan extension. Consolidate 9 October.

API reference checked 29 September 2026:
https://docs.github.com/en/rest/git/trees#create-a-tree — content entries create
blobs; `sha` and `content` must not be supplied together. This documented ability
still requires the actual fixed live qualification; the connector may differ.
