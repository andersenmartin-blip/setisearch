# LS7K continuation — input assessment complete

Completed 14 September 2026.

The [assessment and response contract](LS7K_INPUT_FINDINGS.md) now replace
LS7J's open input question. All fifty mission PRFs and both sets of 4,010
timing rows are restored and audited. Four matching engineering products are
listed. Their time-series contents are not yet inspected.

## Next integrated work package

Develop a separately specified coordinate/PRF forward-model benchmark on the
same twenty closed-sector contexts. Resolve the calibration/science absolute
coordinate convention, verify the 9-by-9 subpixel phase layout and source
normalization, and account for finite stamp boundaries and the recorded
ten-frame exposure. Use the saved calibration grid and uncertainty images;
do not construct another empirical profile retry from LS7J outcomes.

Inspect the exact listed engineering products for actual time system,
cadence, camera/coordinate definition, quality and coverage of the saved
spacecraft-time ranges. Bound acquisition before starting. Establish the
relation to the fast POS_CORR product and target participation where
documentation or file metadata allows. Preserve explicit unknowns if it does
not; do not infer guide membership merely from the target's camera.

Prepare coordinate and flux known-answer checks together with the physical
model. Any closed-data response comparison needs its own fixed numerical
specification and explicit treatment of calibration uncertainty and upstream
pulse dependence. LS7K is input preparation; it has not established that a
calibrated response will improve the native residuals.

Do not append gain, sign, lag, profile or threshold tuning to LS7J. Its outcome,
historical trial counts and all old ledgers stay closed. No unused TESS sector
or M43 held-out panel is opened automatically. Implementation and publication,
including main README updates, remain authorized without another approval stop.

## Reproduce the completed input packet

Use the science branch and install requirements_ls7g.txt with Python 3.12.14.
The output directory must not exist:

~~~bash
python scripts/ls7k_instrument_inputs.py --cache data_ls7k_inputs --output /tmp/ls7k-reproduction
python scripts/ls7k_review_inputs.py --cache data_ls7k_inputs --output /tmp/ls7k-reproduction
~~~

The original LC files are restored by exact hashes. New acquisition should
also compare the PRF hashes with the sealed original inventory; the mission
URLs themselves are not immutable. The standalone audit does not need the
first workflow artifact. Its extra first-attempt comparison is already
preserved in the published audit and correction record.

To regenerate only the readable summary, use the Node command in the
[findings](LS7K_INPUT_FINDINGS.md). This does not reread pixel cubes or evaluate
a detector.

Corrected source freeze: 4084f29a0ad1be192a0126a378f128f22d0fb572.
Audited input result: f1ce03ec5f278a8850125a169a98490ba2cfa204.
[Successful execution 34828406647](https://github.com/andersenmartin-blip/setisearch/actions/runs/34828406647).
The published input package contains 62 files including its checksum manifest.
There is no unattended continuation scheduled between active sessions.
