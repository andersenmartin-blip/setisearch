# LS7O continuation — reference availability contract closed

Completed and audited 14 September 2026. Read [LS7O_FINDINGS.md](LS7O_FINDINGS.md)
and the [full report](results_ls7o_response/REPORT.md).

## Decision

Twelve simultaneous 20-second reference products are established, with exact
time joins, finite moment centroids/errors and disjoint detector masks. The
six-reference geometry surrounds the target. The exact LS7O rule requiring
every reference to be QUALITY=0 throughout every sideband blocks all 420
windows. **Zero new native corrections and zero pulse transfers were measured.**
LS7O is an eligibility obstruction, not a third measured correction failure.
Preserve LS7J and LS7N and all their original outcomes.

Do not remove references, waive quality bits, adjust weights or alter motion
gain/sign/lag/profile to turn the completed LS7O into an available or passing
result. The archive itself is not empty or mistimed: there are at least three
individually usable references at every saved cadence. Those counts are
descriptive and do not qualify a relaxed or variable-reference estimator.

## Next useful work

Establish a **pixel-level quality and centroid-response contract** for the same
fixed reference identities before proposing another target correction. The
mission supplies matching FAST-TP products for all twelve; their exact names,
URIs and full sizes (3,719,056,320 bytes combined) are already in
results_ls7o_metadata/inventory.json. Their pixel time series remain unread.

Combine the next work into one substantive package:

1. Determine how the observed optimal-aperture/collateral cosmic-ray flags,
   pre-cotrending outlier flags and scattered-light exclusions relate to the
   actual moment-centroid pixels and uncertainty propagation. The bit labels
   alone do not justify accepting their centroid measurements.
2. Use metadata/header information first to specify only the same 20-context
   pixel/cosmic-ray records, exact files/ranges and a fixed transfer budget.
   Do not download the full 3.72 GB by default. Preserve the seven-star pool
   and the existing target contexts; do not seek a more favorable star set.
3. If a documented, target-excluded measurement can be derived, freeze its
   pixel/quality treatment, response to source displacement and flux changes,
   temporal interpretation, uncertainty, fit exclusions and an integrated
   comparison together before reading new pixel values. Include known-answer
   and independent raw-byte/numerical verification. A proposed missing-data
   estimator needs its own justified contract and separate outcome; the
   existing availability histogram is not its validation.
4. If that measurement contract cannot be established, explicitly reassess
   optical products/instruments capable of 30–100-second work. Do not repeat
   the failed target PRF correction, relax its thresholds or open unused TESS
   sectors or M43 panels as a default reaction.

This route is a research proposal, not evidence that reference pixels will
produce a useful correction. Existing PRF/exposure/protected-plane code is
reusable; its numerical correctness is not detector qualification. Standing
publication authorization on m43-support-qualification and README updates on
main remains in force. No unattended continuation is scheduled.

## Reproduction

For reproduction, use an isolated checkout of source freeze
`f2d7aef6e82f90a357ec7f54e349cfc2b43953dc`, where new reference table extracts
and the response result directory are absent:

~~~bash
python -m pip install -r requirements_ls7g.txt
PYTHONPATH=src python -m unittest discover -s tests -p test_ls7o_reference_motion.py -v
python scripts/ls7o_acquire.py
python scripts/ls7o_evaluate.py
python scripts/ls7o_audit.py
~~~

The current published extracts allow audit without re-downloading. The later
quality diagnosis, explicit scope accounting and report generators are
post-evaluation descriptive additions; they do not create a new prediction or
change the frozen quality rule. Rebuilding a completed output should use a
separate checkout because producers refuse to overwrite their result paths.
Recorded runtime is Python 3.12.14.
