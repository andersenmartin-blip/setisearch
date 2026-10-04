# Bounded scientific runner — prospective result, 4 October 2026

## Result

The previously separate admission, per-load clock and lossless failure-output
components are now joined by a new bounded one-shot runner. Its **25-test**
suite passes with zero failures, errors or skips and process exit 0. The result
is a **synthetic interface qualification only**. Scientific readiness remains
false and no telescope spectrum or held-out scientific case was opened.

The runner now enforces one continuous authentication chain:

1. the maintained `VerifiedAdmission` must bind the maintained
   `VerifiedClosure` by its exact payload SHA256;
2. the executable-freeze raw document must be the exact document hash recorded
   by that closure;
3. every launcher, retention and receiver file must name a distinct identity
   in the freeze inventory and match its location, mode, byte count and SHA256;
4. files are read through no-follow held descriptors before launch and their
   held and visible identities must remain stable across dispatch;
5. argv, a non-inherited explicit environment, timeout, stream caps, admission,
   session, receiver adapter and dispatch identity are fixed in one pinned spec;
6. the source-session clock is checked immediately before and after the child,
   while the receiver result must retain its checks before and after every load;
7. the existing exclusive outside-repository retention destination is the
   one-shot claim. It cannot be reopened, overwritten, refunded or retried.

The child returns one canonical envelope. A nonzero exit, timeout, stream-cap
breach, persistence error, malformed/duplicate/noncanonical JSON, wrong
identity, missing per-load clock, clock regression/expiry or a synthetic claim
to telescope/scientific authority closes the dispatch. The nonzero regression
retains the exact binary stderr `root-cause\0bytes`; timeout retains `started`;
the cap regression retains the exact 64-byte prefix. These are tiny disjoint
test processes, not F reconstruction or a new protected engineering control.

## Verification

- New runner tests: **25 passed**, 0 failed, 0 errors, 0 skipped.
- Selected admission/runtime/store/receiver regression: **148 passed**.
- Selected lossless failure-retention regression: **24 passed**.
- Python compile and Git whitespace checks pass.
- Frozen adjacent component SHA256 values remain:
  - receiver adapter: `2994d633397fe78153c6d73f7119e975b751fb9a666dc9c50324abd7a4c59a68`
  - failure retention: `730e98f128a6f548b0dada5352b4ef6eb57d4d85f2f195607e7353d977947f12`

The 172 adjacent tests are regression evidence because the new module imports
those maintained types/utilities; they are not counted as new scientific
progress. The new runner source SHA256 is
`93a1031736ba7a488de875c2114031b0efea39ad20a99b4935a86fe99e9f559f`.

## What remains blocked

This code is not a sandbox and does not qualify complete descendant lifetime,
memory/RSS enforcement or the real hosted execution service. An actual run
still requires a newly published complete executable freeze containing this
runner and its real child, authentic public-runtime/native/plugin evidence, a
qualified atomic expected-revision CAS service (ordinary fast-forward is not
enough), fresh irreversible allocations and ledgers, a live bounded source
session and the real one-shot child/result path. Those missing artifacts cannot
be replaced by the synthetic fixtures or passing unit tests.

Therefore all eleven original source/scientific evidence fields remain pending.
The 127 calibration/evaluation cases and 24 evaluations remain NOT ACTIVATED;
native8 remains unreserved. F stays CLOSED_FAILED, 0/8 and permanently spent;
its missing 3,000 stderr bytes were not reconstructed. No prior control was
rerun, refunded or rearmed.

## Preserved scientific scope and exact continuation

HD189733/HIP98505 cadence 85030 remains selected. HD1461/HIP1499 cadence 71139
remains `HOLD_POINTING_PROVENANCE_UNRESOLVED`; GJ724/HIP91608 cadence 73005
remains the untouched reserve. Spectra and original 112+128 M43AF holdouts stay
unopened. M43AI remains failed/closed; M15 GJ581 and M33 HD3651 remain
unresolved. LS remains paused at LS8BD–LS8BE with LS8BF untouched; CHEOPS stays
unsent. No external message was sent.

**Next:** freeze this runner plus one real child into a fresh actual executable
closure, then obtain/qualify the authentic hosted-native/public-runtime and
atomic-CAS services and run only a fresh, explicitly allocated one-shot
engineering qualification. Do not use F, reserved 127/24 identities or telescope
values for that work. If those real service/evidence inputs remain unavailable,
record the blocker and consolidate on **9 October 2026** without extending the
plan or manufacturing readiness.
