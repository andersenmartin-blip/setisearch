# LS8B — fixed four-visit L2 transfer and tail study

The visit selection was made public at
`45bf61fb8fd2883124bd481ddeadc6e8e37f86ea`, before metadata access.
The four entries and metadata-only byte boundaries in
[the selection scope](LS8B_FOUR_VISIT_SCOPE.md) remain binding.

## Two-stage execution

1. Acquire only the primary and first BINTABLE headers, at most 64 KiB per
   exact DEFAULT product. Require HTTP 206, exact byte range and length,
   stable nonempty ETag and Content-Disposition. Verify filename, schema,
   flux units and finite positive TEXPTIME. Publish every visit's receipt;
   an unavailable product blocks the suite without substitution.
2. Only after all four metadata preflights pass, publish the metadata together
   with the final code identity. That commit is the evaluation freeze. Acquire
   only those four exact declared table ranges using If-Match and the saved
   identities. The evaluation requires a clean tracked checkout at that commit.

No L2 table value is opened during stage 1. No source-image data, alternative
aperture or additional visit is authorized by this protocol.

## Unchanged statistic and endpoints

Reuse `seti_repeater.cheops_l2` without modification: durations 1/2/3 rows,
12+12 sidebands, two-row guards, STATUS/finite/error/gap eligibility,
sideband-only linear fit, robust/formal noise floor and prediction leverage,
with positive score >=8.5 and negative score <=-8.5. The existing LS8A
independent struct parser and scalar normal-equation score are also unchanged.
Dependency SHA-256 pins are enforced in `scripts/ls8b_l2_suite.py`.

Report separately for every visit and duration: eligible windows, positive
and negative threshold windows, score extrema, and the union of eligible event
rows. Report positive clusters with the original overlap/adjacency rule.
As a supplementary symmetric control fixed before table access, apply that
identical clustering rule to negated scores and report negative clusters,
retaining the original signed scores. This changes no eligibility or statistic.
Do not pool adjacent visits into one continuous series or merge their clusters.

The primary outputs are the four per-visit results. A total is descriptive;
neither overlapping windows nor clusters establish independent noise trials.
Row-union seconds are a sampling descriptor, not qualified search coverage.
No Gaussian significance, false-alarm probability or population limit follows.

## Verification and stopping rule

Before acquisition, the original known-answer screen tests and focused suite
tests must pass. After evaluation, an independent auditor must parse the raw
table with `struct`, enumerate every eligible and ineligible window, recompute
the scalar score, verify positive and negative cluster representatives and
members, all per-duration counts, row unions, extrema, source hashes and all
four summary identities. It may reuse the unchanged LS8A scalar functions but
must not import the LS8B producer or its scoring implementation.
Numerical comparison tolerance is the existing LS8A 2e-8 relative/2e-10 absolute.

Publish all four visits, including unfavorable controls and empty eligible
sets. If access or audit fails, retain evidence and publish the obstruction;
never substitute a visit or silently rerun the science. An implementation
repair must be identified explicitly and cannot change the frozen method.

The suite alone does not qualify a detector. Any positive excursion remains an
L2 diagnostic, requiring a separately frozen follow-up after this complete
suite is reported. No image follow-up is automatic, and no threshold, duration,
sideband, noise rule or aperture is retuned in response to these results.
