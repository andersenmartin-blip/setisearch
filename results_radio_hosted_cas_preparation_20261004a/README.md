# Inert hosted exact-revision CAS preparation

**19 focused synthetic tests pass. No actual service is invoked or qualified.**
The [current preparation report](../RADIO_HOSTED_CAS_2026-10-04_PREPARATION.md)
records the historically available Actions `updateRefs` route and the requirements
for a future complete hosted integration. The existing scientific store is unchanged.

`hosted_cas.py` maps the exact expected revision and independently pinned
pre-created candidate into a fixed, non-forced GraphQL mutation. Its injected
callbacks check the immutable raw commit/blob identity, sole parent, fixed
location, declaration of tree, expected branch and post-mutation readback.
The declared tree is **not** a complete tree-membership or permitted-delta proof.
`historical-service-mapping.json` binds six unchanged source/evidence inputs and
two exact historical request/response bodies; it reuses no old invocation.

The final tests cover concurrent head changes and simulated server conflict,
malformed/error acknowledgement, ambiguous timeout, candidate/readback tampering,
source mutation, forbidden location/force/fallback, type-confusable identity pins,
unsupported pin input types and false authority. They provide synthetic software
evidence; they do not measure an actual hosted conflict or process lifetime.

Every attempt consumes **this Python instance only**, including precheck failures.
Reinstantiating the adapter is possible: it is not a durable or globally unique
dispatch registry. A future integration must provide that separate irreversible
claim and allocation. Returned receipts include explicit synthetic/preparation
fields and false authority, so they do not satisfy the unchanged production
store's exact acknowledgement schema. No credential reader or HTTP transport,
workflow, activation marker, scientific allocation or source loader is present.

## Development evidence

The first suite passed 16 tests in `development-tests01.log`. Root code review
then found a semantic pin ambiguity: bytes were encoded like a caller-supplied
dictionary, allowing a type substitution to keep its hash. The initial regression
fixture itself had two errors, retained in `development-tests02.log`. The corrected
regression reproduced two bypass failures in `development-tests02b.log`.

Recursive type tagging repairs that ambiguity. The complete final suite passes
**19 tests in 0.006 seconds**, exit 0, in `development-tests03.log`. No unchanged
historical test suite or closed service control was rerun as new progress.
`initial/` preserves the exact pre-fix adapter and the corrected failure-reproducing
test source. Exact earlier test-source snapshots for tests01/tests02 were not
retained; the saved initial test source supports tests02b, not those earlier runs.
All four logs remain unchanged.

Run these preparation tests locally from this directory with:

```bash
python3 -B -m unittest -v test_hosted_cas
```

No telescope spectra, holdouts, native8 or 127/24 scientific trials are opened by
these tests. Actual hosted service, complete tree delta, runtime/resource/session,
source and scientific qualification remain pending. Consolidate 9 October 2026;
no automatic experiment, target change or extension is authorized by this package.
